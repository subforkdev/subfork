#!/usr/bin/env python
#
# Copyright (c) Subfork. All rights reserved.
#

__doc__ = """
Contains logging handlers.
"""

import sys
import logging

from subfork import config
from subfork.version import __prog__, __version__

log = logging.Logger(__prog__)
log.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)
log.addHandler(logging.NullHandler())


class CustomFormatter(logging.Formatter):
    """
    Custom logging Formatter to add colors and count warning / errors.

    Options:

        %(pathname)s Full pathname of the source file
        %(filename)s Filename portion of pathname
        %(module)s Module (name portion of filename)
        %(funcName)s Name of function containing the logging call
        %(lineno)d Source line number where the logging call was issued
    """

    grey = "\x1b[38m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    blue = "\x1b[34m"
    red = "\x1b[31m"
    bold_red = "\x1b[31m"
    reset = "\x1b[0m"
    if sys.platform == "win32":
        fmt = "[%(asctime)s] - %(name)s - %(module)10s:%(lineno)3d - %(levelname)-7s - %(message)s"
    else:
        fmt = "[%(asctime)s] - %(name)s - %(module)10s:%(lineno)3d - {color}%(levelname)-7s{reset} - %(message)s"
    datefmt = "%y-%m-%d %H:%M:%S"

    # TODO: get ANSI escape codes for win32
    FORMATS = {
        logging.DEBUG: blue,
        logging.INFO: green,
        logging.WARNING: yellow,
        logging.ERROR: red,
        logging.CRITICAL: bold_red,
    }

    def __init__(self):
        super(CustomFormatter, self).__init__(self.fmt, datefmt=self.datefmt)

    def format(self, record):
        log_fmt = self.fmt.format(
            color=self.FORMATS.get(record.levelno), reset=self.reset
        )
        formatter = logging.Formatter(log_fmt, self.datefmt)
        return formatter.format(record)


def setup_stream_handler(name=__prog__):
    """Adds a new stdout stream handler."""
    for h in log.handlers:
        if h.name == name and "StreamHandler" in str(h):
            del log.handlers[log.handlers.index(h)]

    log.name = name
    handler = logging.StreamHandler()
    handler.set_name(name)
    handler.setFormatter(CustomFormatter())
    log.addHandler(handler)

    return handler
