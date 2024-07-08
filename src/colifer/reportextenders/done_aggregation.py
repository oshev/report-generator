"""Module to aggregate 'Done Stuff.md' into weekly reports.

Done Stuff.md is expected to be formatted as follows:
------------------------------------
### Week <WEEK_NUMBER>

#### <DAY_NUMBER>/<MONTH_NUMBER> <DAY_OF_WEEK>

- <TOGGL_ENTRY>
    - <COMMENT>
        - <COMMENT>
        <...>
    <...>
<...>
- <TOGGL_ENTRY>
<...>
#### <DAY_NUMBER>/<MONTH_NUMBER> <DAY_OF_WEEK>
<...>
------------------------------------

Toggle entries can be on a second level of identation, e.g. groupped by category like "Work" or project like "CoLifer":
- <CATEGORY>
    - <TOGGL_ENTRY>
        - <COMMENT>
            - <COMMENT>
            <...>
        <...>
    <...>
"""
import argparse
import logging
import re
from typing import Dict, List, Optional
from types import SimpleNamespace
from colifer.constants import LOGGING_FORMAT

logging.basicConfig(level="INFO", format=LOGGING_FORMAT)
logger = logging.getLogger(__name__)


ENTRY_NAME_REGEX = re.compile(r"- \*\*([^*]+)\*\*.*")
DAY_DONE_REGEX = re.compile(r"#### (\d+)/(\d+) (\w+)")
TRACKED_TAG = " (Tracked)"

# TODO: move this to the configuration
CATEGORIES = {"Work", "Colifer", "Gaming"}
IGNORED_CATEGORIES = {"Work"}
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class DoneAction(SimpleNamespace):
    """Done line with its identation width."""
    identation_width: int
    name: str
    category: str
    weekday_nums: str
    notes: List[str]


def _aggregate_report(report_lines: List[str], week_done_actions_dict: Dict[str, DoneAction]) -> str:
    """Aggregate the report lines into weekly reports."""
    ext_weekly_report = ""
    overview_section = "## Overview\n"
    week_done_actions_dict_copy = week_done_actions_dict.copy()
    used_action_names = set()
    for report_line in report_lines:
        ext_weekly_report += f"{report_line}\n"
        if not report_line.strip():
            continue
        # Take only the text inside bold from report lines,
        #   e.g. "- **Free up space on the shared machine**  *(01:58, 2 times, 1 days)* <!--02/16 Thu-->""
        #   -> "Free up space on the shared machine"
        action_name_match = ENTRY_NAME_REGEX.match(report_line.strip())
        action_name_identation = len(report_line) - len(report_line.lstrip())
        if action_name_match:
            action_name = action_name_match.group(1)
            if action_name in used_action_names:
                logger.warning(
                    f"Duplicate action (Toggl entry) '{action_name}' found in report.")
            elif action_name in week_done_actions_dict_copy:
                used_action_names.add(action_name)
                action = week_done_actions_dict_copy[action_name]
                if action.category not in IGNORED_CATEGORIES:
                    base_identation = " " * action_name_identation if action_name_identation else ""
                    for note in action.notes:
                        ext_weekly_report += f"{base_identation}{note}\n"
                    del week_done_actions_dict_copy[action.name]
    # TODO: check why some comments are not added to the report
    # e.g. those for "Play "Zero Caliber" with Leha on Oculus Quest 2"
    # TODO: extract project from lines like "### Avoidable Side Work"
    # TODO: map projects to 3 categories "Work", "Family & Friends", and "Other" in Overview
    # TODO: add keywords for each category (e.g. Michelle, Dylan, Paola, Leha)
    # TODO: Include Work stuff to Overview
    # TODO: how to map non-tracked actions? put them to "Other"?
    action_tuples = [((f"- {action.weekday_nums} " if action.weekday_nums else "") + f"- {action.name} ", action)
                      for action in week_done_actions_dict.values()]
    sorted_action_tuples = sorted(action_tuples, key=lambda x: x[0])
    for action_name, action in sorted_action_tuples:
        if action.weekday_nums:
            weekdays = ', '.join([WEEKDAYS[int(weekday_num)] for weekday_num in action.weekday_nums.split(', ')])
            action_weekdays = (f"- {weekdays} ") 
        else: 
            action_weekdays = ""
        tracked_tag = TRACKED_TAG if action.name not in week_done_actions_dict_copy else ""
        overview_section += f"{action_weekdays}- {action.name}{tracked_tag}\n"
        for note in action.notes:
            overview_section += f"{note}\n"
    return overview_section + "\n" + ext_weekly_report


def _read_file(filename: str) -> List[str]:
    """Read a file."""
    with open(filename, "r") as f:
        lines = f.readlines()
        lines = [line.rstrip() for line in lines]
    return lines


def _week_done_lines_to_dict(week_done_lines: List[str]) -> Dict[str, DoneAction]:
    """Parse done lines and create a dictionary of action lines and their comments.

    :param week_done_lines: The list of week done lines.
    :return: Dictionary of actions lines and their comments.
    """
    week_done_action_dict: Dict[str, DoneAction] = {}
    active_key: Optional[DoneAction] = None
    last_category: str = ""
    weekday_num = ""
    for week_done_line in week_done_lines:
        week_done_line_stripped = week_done_line.lstrip("- ").strip()
        if not week_done_line_stripped:  # skip empty lines
            continue
        day_done_regex_match = DAY_DONE_REGEX.match(week_done_line)
        if day_done_regex_match:  # extract the weekday
            weekday = day_done_regex_match.group(3)
            weekday_num = WEEKDAYS.index(weekday)
            last_category = ""
            active_key = None
            continue
        identation_width = len(week_done_line) - len(week_done_line.lstrip())
        if week_done_line_stripped in CATEGORIES:  # check if the line is a category
            active_key = None
            last_category = week_done_line_stripped
            continue
        if identation_width == 0:
            last_category = ""
        if identation_width == 0:
            if week_done_line_stripped not in week_done_action_dict:
                active_key = DoneAction(identation_width=identation_width,
                                        name=week_done_line_stripped,
                                        category=last_category,
                                        weekday_nums=str(weekday_num),
                                        notes=[])
                week_done_action_dict[active_key.name] = active_key
            else:
                active_key = week_done_action_dict[week_done_line_stripped]
                if str(weekday_num) not in active_key.weekday_nums:
                    active_key.weekday_nums = active_key.weekday_nums + f", {weekday_num}"
        elif active_key is not None:
            week_done_line_shifted = week_done_line[active_key.identation_width:]
            # week_done_action_dict[active_key.name].notes.insert(
            #     0, week_done_line_shifted)  # done stuff lines are filled in reverse order (latest event first)
            week_done_action_dict[active_key.name].notes.append(week_done_line_shifted)
    return week_done_action_dict


def _extract_week_done_lines(done_lines: List[str], week_number: int) -> List[str]:
    """Extract the lines for the week."""
    week_separator = "### Week "
    target_week_start = f"{week_separator}{week_number:02d}"
    week_lines: List[str] = []
    target_week_started = False
    for line in done_lines:
        line_stripped = line.strip()
        if target_week_started:
            if line_stripped.startswith(week_separator):
                break
            week_lines.append(line)
        if line_stripped == target_week_start:
            target_week_started = True
    return week_lines


def main():
    """Entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-file", required=True,
                        help="The path to the report file", type=str)
    parser.add_argument("--done-file", required=True,
                        help="The path to the done file", type=str)
    args = parser.parse_args()

    # extract week number from report file name using pattern "YYYY Week N.md", e.g. "2021 Week 01.md"
    week_number = int(args.report_file.split(" ")[-1].replace(".md", ""))

    done_lines = _read_file(args.done_file)
    week_done_lines = _extract_week_done_lines(done_lines, week_number)
    report_lines = _read_file(args.report_file)
    week_done_actions_dict = _week_done_lines_to_dict(week_done_lines)

    result_report = _aggregate_report(report_lines, week_done_actions_dict)
    output_file = args.report_file.replace(".md", "_done.md")
    with open(output_file, "w") as f:
        f.write(result_report)


if __name__ == "__main__":
    main()
