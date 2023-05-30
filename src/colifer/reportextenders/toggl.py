import base64
from collections import namedtuple
from datetime import datetime, timedelta
from typing import Dict, Tuple

import requests
from colifer import tense_rules
from colifer.config import Config
from colifer.reportextenders.report_extender import ReportExtender
from colifer.reporting import Report
from colifer.sectionstats import SectionStats
from colifer.tag_order import TagOrder

SECTION_STAT_PATH_SEPARATOR = '$'
CHARACTERS_IN_DATE = 10
NO_CLIENT = "Default"
NO_PROJECT = "Default"
ProjectWithClient = namedtuple('ProjectWithClient', 'client project')


class TogglEntriesParser(ReportExtender):
    def __init__(self, section_entries):
        super().__init__(section_entries)
        if Config.get_section_param(section_entries, "enabled"):
            self.api_token = Config.get_section_param(section_entries, "api_token")
            string = self.api_token + ':api_token'
            self.headers = {'Authorization': 'Basic ' + base64.b64encode(string.encode('ascii')).decode("utf-8"),
                            'Cache-Control': 'no-cache',
                            'Content-Type': 'application/json'}
            self.entries_endpoint = Config.get_section_param(section_entries, "entries_endpoint")
            self.projects_endpoint = Config.get_section_param(section_entries, "projects_endpoint")
            self.clients_endpoint = Config.get_section_param(section_entries, "clients_endpoint")
            self.tag_order = TagOrder(
                Config.get_section_param(section_entries, "tag_order_filename"))            
            past_tense_rules_file = Config.get_section_param(section_entries, "past_tense_rules_file")
            if past_tense_rules_file:
                self.past_tense_rules_obj = tense_rules.TenseRules()
                self.past_tense_rules_obj.read_tense_rules(past_tense_rules_file)
            else:
                self.past_tense_rules_obj = None
        else:
            self.api_token = None

    def get_clients(self) -> Dict[str, str]:
        response = requests.get(self.clients_endpoint, headers=self.headers)
        clients_list = response.json()
        clients_dict = {client['id']: client['name'] for client in clients_list}
        return clients_dict

    def get_projects(self) -> Dict[str, ProjectWithClient]:
        clients = self.get_clients()
        response = requests.get(self.projects_endpoint, headers=self.headers)
        projects_list = response.json()
        projects_dict = dict()
        for project in projects_list:
            client = clients.get(project.get('cid', None), NO_CLIENT)
            projects_dict[project['id']] = ProjectWithClient(client, project['name'])
        return projects_dict

    @staticmethod
    def toggl_entry_to_section_stat(entry: Dict[str, str],
                                    projects_with_client: Dict[str, ProjectWithClient]):
        project_name, client = projects_with_client.get(entry.get('pid', None),
                                                        ProjectWithClient(NO_CLIENT, NO_PROJECT))
        days = set()
        entry_date = datetime.strptime(entry['start'][:CHARACTERS_IN_DATE], '%Y-%m-%d').date()
        days.add(entry_date)
        entry_duration = entry['duration']
        tags = set(entry.get('tags', set()))
        section_stat = SectionStats(
            path=SECTION_STAT_PATH_SEPARATOR.join([client, project_name, entry['description']]),
            seconds=entry_duration, tags=tags,
            days=days)
        return section_stat

    @staticmethod
    def _diff_months(datetime1: datetime, datetime2: datetime):
        if datetime1 < datetime2:
            datetime1, datetime2 = datetime2, datetime1
        return (datetime1.year - datetime2.year) * 12 + datetime1.month - datetime2.month

    @staticmethod
    def _chunk_date_ranges(start, end) -> Tuple[datetime, datetime]:
        num_chunks = TogglEntriesParser._diff_months(start, end) + 1
        diff = (end - start) / num_chunks
        range_start = start
        for i in range(1, num_chunks + 1):
            range_end = (start + diff * i)
            yield range_start, range_end
            range_start = range_end + timedelta(seconds=1)

    def get_section_stats(self, report_parameters,
                          projects_with_client: Dict[str, ProjectWithClient]):
        date_ranges = self._chunk_date_ranges(report_parameters.period_start,
                                              report_parameters.period_end)
        section_stats_dict = {}
        for start_date, end_date in date_ranges:
            start_date_str = str(start_date).replace(" ", "T") + "Z"
            end_date_str = str(end_date).replace(" ", "T") + "Z"
            response = requests.get(self.entries_endpoint.format(start_date_str, end_date_str),
                                    headers=self.headers)
            entries_list = response.json()

            for entry in entries_list:
                section_stat = self.toggl_entry_to_section_stat(entry, projects_with_client)
                if section_stat.path in section_stats_dict:
                    section_stats_dict[section_stat.path].add_stats(section_stat)
                else:
                    section_stats_dict[section_stat.path] = section_stat

        return section_stats_dict

    def get_report_path(self, section_stat):
        client_name, project_name, leaf_name = section_stat.path.split(SECTION_STAT_PATH_SEPARATOR)
        init_path = [project_name, client_name]
        if self.past_tense_rules_obj:
            leaf_name_processed = self.past_tense_rules_obj.convert_tense(leaf_name)
        else:
            leaf_name_processed = leaf_name
        tags_with_order = []
        for tag in section_stat.common_tags:
            order = self.tag_order.get_order(tag)
            if order is not None:
                tags_with_order.append((tag.title(), order))
        ordered_meaningful_tags = [tag_and_order[0]
                                   for tag_and_order in
                                   sorted(tags_with_order, key=lambda x: (x[1], x[0]))]
        init_path.extend(ordered_meaningful_tags)
        return init_path, leaf_name_processed

    def extend_report(self, report, report_parameters):
        if not self.api_token:
            raise RuntimeError("Can't connect to Toggl: auth token is empty")

        projects_with_client = self.get_projects()
        event_stats_list = self.get_section_stats(report_parameters, projects_with_client)
        sorted_event_stats_list = sorted(event_stats_list.values(), key=lambda x: x.seconds,
                                         reverse=True)
        for event_stats in sorted_event_stats_list:
            init_path, leaf_name = self.get_report_path(event_stats)
            print(init_path, leaf_name)
            section = report.find_or_create_leaf(init_path, leaf_name)
            section.stats = event_stats
            Report.propagate_stats_to_parent(section, section.stats)
