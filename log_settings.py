import logging
import sys
import os

LOG_FILE = 'logs.log'
ERRORS_LOG_FILE = 'errors.log'
LOGS_DIRECTORY = 'logs'
LOG_FORMAT = '%(asctime)s  =>  %(levelname)-10.10s  =>  %(message)s'


def init_console_only(log_level=logging.WARNING):
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    logging.basicConfig(level=log_level, format=LOG_FORMAT, handlers=[console_handler])


def init_full_logs(channel: str, console_log_level=logging.DEBUG, file_log_level=logging.INFO) -> None:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_log_level)

    os.makedirs(LOGS_DIRECTORY, exist_ok=True)
    channel_directory = os.path.join(LOGS_DIRECTORY, channel)
    os.makedirs(channel_directory, exist_ok=True)

    file_handler = logging.FileHandler(filename=os.path.join(channel_directory, LOG_FILE), mode='w')
    file_handler.setLevel(file_log_level)

    file_errors_handler = logging.FileHandler(filename=os.path.join(channel_directory, ERRORS_LOG_FILE), mode='w')
    file_errors_handler.setLevel(logging.ERROR)

    logging.basicConfig(
        level=logging.DEBUG,
        format=LOG_FORMAT,
        handlers=[
            file_handler,
            file_errors_handler,
            console_handler
        ]
    )
