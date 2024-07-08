"""Module to gather basic Pocket stats."""

import logging
from time import sleep
from colifer.config import Config
from colifer.constants import LOGGING_FORMAT
from colifer.reportextenders.articles.pocket_parser import PocketParser

logging.basicConfig(level="INFO", format=LOGGING_FORMAT)
logger = logging.getLogger(__name__)

MAX_RETURN_ITEMS = 300


def main():
    config = Config()
    pocket_parser = PocketParser(config.get_param('Pocket'))
    result_unread = pocket_parser.api.get(state='unread', detailType='simple')
    is_finished = False
    offset = 0
    total_archived_count = 0
    while not is_finished:
        result_archived = pocket_parser.api.get(
            state='archive', detailType='simple', offset=offset, count=MAX_RETURN_ITEMS)
        if not result_archived or 'list' not in result_archived[0]:
            logger.error("Incorrect response from API: %s", result_archived)
            break
        archived_count = len(result_archived[0]['list'])
        if archived_count < MAX_RETURN_ITEMS:
            is_finished = True
        total_archived_count += archived_count
        logger.info("Requesting archived: %s...", total_archived_count)
        offset += MAX_RETURN_ITEMS
    print(result_archived)
    logger.info("\nPocket stats: \n"
                "   Unread queue size: %s\n"
                "   Number archived: %s", len(result_unread[0]['list']), total_archived_count)


# time_added
if __name__ == '__main__':
    main()
