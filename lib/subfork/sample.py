#!/usr/bin/env python
#
# Copyright (c) Subfork. All rights reserved.
#

__doc__ = """
Contains worker process data sample classes and functions.
"""

import os
import sys
import psutil
import socket
import getpass

from subfork import util


# cache some information for worker processes
hostname = socket.gethostname()
ip_address = socket.gethostbyname(hostname)
platform = sys.platform
process_id = os.getpid()
process = psutil.Process(process_id)
py_version = util.get_python_version()
username = getpass.getuser()


class Sample(object):
    """Worker process stats sample class."""

    def __init__(self, interval=0, data={}):
        """
        :param interval: how long in seconds to sample cpu data (blocking)
        :param data: extra data to store on sample
        """
        super(Sample, self).__init__()
        self._data = {
            "host": self.get_host_info(),
            "process": self.get_process_info(interval),
        }
        self._data.update(data)

    def data(self):
        """Returns sample data dict."""
        return self._data

    def get_host_info(cls):
        """Returns worker info dict."""
        return {
            "hostname": hostname,
            "ip_address": ip_address,
            "platform": platform,
            "username": username,
        }

    def get_process_info(cls, interval: int = 0):
        """Samples and returns process info dict.

        :param interval: how long in seconds to sample cpu data (blocking)
        :returns: process info dict
        """
        return {
            "cpu_percent": process.cpu_percent(interval=interval),
            "create_time": process.create_time(),
            "exe": process.exe(),
            "memory": {
                "rss": process.memory_info().rss,
                "vms": process.memory_info().vms,
            },
            "name": process.name(),
            "pid": process.pid,
        }
