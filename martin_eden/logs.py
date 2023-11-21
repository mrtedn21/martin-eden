import logging
import sys


def configure_logging(level: str = 'DEBUG'):
    logging.basicConfig(
        level=level,
        format=(
            '%(asctime)s : %(levelname)s : %(module)s : '
            '%(funcName)s : %(lineno)d : %(message)s'
        ),
        handlers=[
            logging.StreamHandler(stream=sys.stdout),
        ]
    )
