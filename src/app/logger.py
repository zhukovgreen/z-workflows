import logging
import sys


def setup_logger(level: str = "INFO"):
    logging.basicConfig(
        level=level,
        stream=sys.stderr,
        format="| %(asctime)s | %(name)s | %(levelname)s | %(filename)s | %(message)s",
    )
    logging.getLogger().setLevel(level)
