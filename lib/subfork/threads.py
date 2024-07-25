#!/usr/bin/env python
#
# Copyright (c) Subfork. All rights reserved.
#

__doc__ = """
Contains threading classes and functions.
"""

import os
import time
import threading

from subfork import config
from subfork import sample
from subfork import util
from subfork.logger import log

FILE_WATCHER_WAIT_TIME = 3  # seconds


class StoppableThread(threading.Thread):
    """Thread class with a stop() method."""

    def __init__(self, *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()
        self.daemon = True

    def stop(self):
        """Stop the thread."""
        self.alive = False
        self._stop_event.set()

    def stopped(self):
        """Returns True if thread is stopped."""
        return self._stop_event.isSet()


class FileWatcher(StoppableThread):
    """Watches for file changes and runs a callback function."""

    def __init__(self, filepath, callback=None, kwargs={}):
        """
        :param filepath: filepath to watch.
        :param callback: callback function (called when file changes).
        :param kwargs: kwargs dict passed to callback function (optional).
        """
        super(FileWatcher, self).__init__()
        self.filepath = filepath
        self.callback = callback
        self.kwargs = kwargs
        self.wait_time = FILE_WATCHER_WAIT_TIME
        self.start_time = util.get_time()
        self.last_modified = None
        self.last_checksum = None
        self.running = threading.Event()

    def elapsed_time(self):
        """Returns elapsed time in seconds."""
        return (util.get_time() - self.start_time) / 1000.0

    def has_changed(self):
        """Returns True if filepath has changed."""
        current_modified = os.path.getmtime(self.filepath)
        current_checksum = util.checksum(self.filepath)

        # check mtime and checksum values
        if (
            current_modified != self.last_modified
            or current_checksum != self.last_checksum
        ):
            self.last_modified = current_modified
            self.last_checksum = current_checksum
            return True

        return False

    def run(self):
        """Called when thread starts."""
        if os.path.exists(self.filepath):
            self.last_modified = os.path.getmtime(self.filepath)
            self.last_checksum = util.checksum(self.filepath)
        else:
            log.warning("path not found: %s", self.filepath)

        self.running.set()

        while self.running.is_set():
            time.sleep(self.wait_time)
            if os.path.exists(self.filepath):
                # restart workers if config file has changed
                if self.has_changed() and self.callback:
                    self.callback(**self.kwargs)
                # automatically restart workers every 12 hours
                elif self.elapsed_time() >= util.HOURS_12:
                    if self.callback:
                        self.callback(**self.kwargs)
            else:
                log.warning("path not found: %s", self.filepath)
                time.sleep(300)

    def stop(self):
        """Stop the thread."""
        self.running.clear()


class HealthCheck(StoppableThread):
    """Runs health checks on a given host and logs updates."""

    def __init__(self, client, wait_time=config.WAIT_TIME):
        """
        :param client: subfork client instance.
        :param wait_time: interval in seconds between checks.
        """
        super(HealthCheck, self).__init__()
        self.client = client
        self.start_time = util.get_time()
        self.wait_time = wait_time

    def run(self):
        """Called when thread starts."""
        self.start_time = util.get_time()
        while not self.stopped():
            samp = sample.Sample(interval=self.wait_time).data()
            runtime = int((util.get_time() - self.start_time) / 1000.0)
            kwargs = {
                "cpu": samp["process"]["cpu_percent"],
                "rss": util.b2h(samp["process"]["memory"]["rss"]),
                "runtime": time.strftime("%H:%M:%S", time.gmtime(runtime)),
                "vms": util.b2h(samp["process"]["memory"]["vms"]),
            }
            msg = "cpu:{cpu}% rss:{rss} vms:{vms} runtime:{runtime}".format(**kwargs)
            if runtime % 3600:
                log.debug(msg)
            else:
                log.info(msg)
