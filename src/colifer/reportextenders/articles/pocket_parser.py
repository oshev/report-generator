import datetime

from colifer.reportextenders.articles import pocket
from colifer.config import Config
from colifer.namingrules import NamingRules
from colifer.reportextenders.report_extender import ReportExtender

SECTION_SEPARATOR = '/'
DEFAULT_LABEL_RULE = "Default"


class PocketParser(ReportExtender):
    api = None

    def __init__(self, section_entries):
        super().__init__(section_entries)
        if Config.get_section_param(section_entries, "enabled"):
            self.pocket_consumer_key = Config.get_section_param(
                section_entries, "consumer_key")
            self.pocket_access_token = Config.get_section_param(
                section_entries, "access_token")
            self.api = pocket.Pocket(
                self.pocket_consumer_key, self.pocket_access_token)
            self.naming_rules = NamingRules()
            naming_rules_filename = Config.get_section_param(
                section_entries, "naming_rules_file")
            self.naming_rules.read_naming_rules(naming_rules_filename)
        else:
            self.api = None

    @staticmethod
    def safe_get(article, field, alternative):
        if field in article:
            return article[field]
        elif alternative:
            return article[alternative]
        else:
            return ''

    def extend_report(self, report, report_parameters):
        if self.api:
            path = self.naming_rules.get_path(DEFAULT_LABEL_RULE)
            if path is None:
                print("You must put Default path to Pocket naming rules file")
                exit(1)

            init_section_path_elements = path.split(SECTION_SEPARATOR)
            report.find_or_create_section(
                report.root_section, init_section_path_elements, False)

            result = self.api.get(state='archive', detailType='simple')
            if result is not None and len(result) > 0 and result[0]['list'] is not None:
                for key in result[0]['list'].keys():
                    section_path_elements = init_section_path_elements.copy()
                    time_read = datetime.datetime.fromtimestamp(
                        int(result[0]['list'][key]['time_read']))
                    if report_parameters.period_start <= time_read <= report_parameters.period_end:
                        init_section_path_elements = section_path_elements.copy()
                        if "quora.com" in self.safe_get(result[0]['list'][key], 'resolved_url', 'given_url'):
                            section_path_elements.append("Quora")
                        print("Processing Pocket article: " + self.safe_get(result[0]['list'][key],
                                                                            'resolved_title', 'given_title'))
                        word_count = self.safe_get(
                            result[0]['list'][key], 'word_count', None)
                        article_title = self.safe_get(
                            result[0]['list'][key], 'resolved_title', 'given_title')
                        article_url = self.safe_get(
                            result[0]['list'][key], 'resolved_url', 'given_url')
                        # TODO: Find a way to make links agnostic to generated format (atm it's md)
                        section_path_elements.append("[{}]({}) ({} words)".format(article_title, article_url,
                                                                                  word_count))
                        report.find_or_create_section(
                            report.root_section, section_path_elements, False)
