import logging
from logging.handlers import RotatingFileHandler

import os

MB = 1024 * 1024

logger = logging.getLogger(__name__)


def init_logging(log_file: str, max_file_size_mb: int, max_backup_count: int, log_level=logging.DEBUG):
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    # logging_format_extended = logging.Formatter("[%(asctime)s][%(levelname)-8s][%(name)-16s] - %(message)s (%(filename)s:%(lineno)s)")
    logging_format_simple = logging.Formatter("[%(asctime)s][%(levelname)-8s] - %(message)s")

    # File handler
    file_handler = RotatingFileHandler(filename=log_file, maxBytes=max_file_size_mb * MB, backupCount=max_backup_count)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging_format_simple)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging_format_simple)

    # Add handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logger.info("Setting up logging to file: {0}".format(log_file))
