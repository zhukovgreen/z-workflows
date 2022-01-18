import logging
import sys


def setup_logger():
    logging.basicConfig(
        level="DEBUG",
        stream=sys.stderr,
        format="| %(asctime)s | %(name)s | %(levelname)s | %(filename)s | %(message)s",
    )
