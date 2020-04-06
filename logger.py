# -*- coding: utf-8 -*-

import logging
import sys


def get_console_handler():
    console_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s %(name)s [%(levelname)s]: %(message)s", "%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(formatter)
    return console_handler


def get_logger(logger_name):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(get_console_handler())
    logger.propagate = False
    return logger
