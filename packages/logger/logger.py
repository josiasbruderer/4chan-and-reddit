import logging
import sys

NOTSET = logging.NOTSET
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL


class ExitHandler(logging.StreamHandler):
    def emit(self, record):
        super().emit(record)
        if record.levelno == logging.CRITICAL:
            sys.exit(1)


def setup(name, file, level):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Create a console handler
    console_formatter = logging.Formatter('\r%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    console_handler = ExitHandler()
    console_handler.setLevel(logging.DEBUG)  # Set the logging level for the console handler
    console_handler.setFormatter(console_formatter)  # Set the formatter for the console handler
    logger.addHandler(console_handler)

    if file:
        # Create a file handler
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                      datefmt='%Y-%m-%d %H:%M:%S')
        file_handler = logging.FileHandler(file)
        file_handler.setLevel(logging.INFO)  # Set the logging level for the file handler
        file_handler.setFormatter(file_formatter)  # Set the formatter for the file handler
        logger.addHandler(file_handler)

    return logger


def queue_processor(log_queue, log):
    while True:
        log_message = log_queue.get()
        if log_message == "STOP":
            break
        if log_message.startswith("CRITICAL"):
            log.critical(log_message.lstrip("CRITICAL").lstrip(" "))
        elif log_message.startswith("ERROR"):
            log.error(log_message.lstrip("ERROR").lstrip(" "))
        elif log_message.startswith("WARNING"):
            log.warning(log_message.lstrip("WARNING").lstrip(" "))
        elif log_message.startswith("INFO"):
            log.info(log_message.lstrip("INFO").lstrip(" "))
        else:
            log.debug(log_message)
