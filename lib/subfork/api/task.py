#!/usr/bin/env python
#
# Copyright (c) Subfork. All rights reserved.
#

__doc__ = """
Contains task api classes and functions.
"""

import sys
import copy
import json
import time

from subfork import config
from subfork import util
from subfork.api.base import Base
from subfork.logger import log


def is_valid_task(task_data):
    """Returns True if task is valid."""

    try:
        if not task_data:
            return False
        if "id" not in task_data:
            log.warning("task is missing id")
            return False
        results = task_data.get("results")
        if results and type(results) not in (str,):
            log.warning("invalid results type: %s", type(results))
            return False
        if sys.getsizeof(task_data) > config.TASK_MAX_BYTES:
            log.warning("data too large")
            return False
        json.dumps(task_data)

    except (Exception, TypeError) as err:
        log.warning("task is not JSON serializable: %s", err)
        return False

    return True


class Queue(Base):
    """Subfork Task Queue class."""

    def __init__(self, client, name):
        """ "
        :param client: Subfork client instance.
        :param name: Queue name.
        """
        super(Queue, self).__init__(client)
        self.name = name

    def __repr__(self):
        return "<Queue %s>" % self.name

    @classmethod
    def get(cls, client, name):
        return cls(client, name)

    def create_task(self, data=None):
        """
        Adds a task to a this Queue.

            >>> sf = subfork.get_client()
            >>> task = sf.get_queue(queue).create_task(data)

        :param data: task worker function kwargs or None.
        :returns: Task instance.
        """
        results = self.client._request(
            "task/create",
            data={
                "queue": self.name,
                "data": util.sanitize_data(data),
            },
        )
        if is_valid_task(results):
            return Task(self.client, queue=self, data=results)
        return None

    def dequeue_task(self):
        """
        Dequeues next Task from this Queue.

            >>> sf = subfork.get_client()
            >>> task = sf.get_queue(queue).dequeue_task()

        :returns: Task instance or None.
        """
        results = self.client._request(
            "task/dequeue",
            data={
                "queue": self.name,
            },
        )
        if is_valid_task(results):
            return Task(self.client, queue=self, data=results)
        return None

    def get_task(self, taskid):
        """
        Gets a task for a given queue name and task id.

            >>> sf = subfork.get_client()
            >>> task = sf.get_queue(queue).get_task(taskid)

        :param taskid: the id of the task to get.
        :returns: Task instance or None.
        """
        results = self.client._request(
            "task/get",
            data={
                "queue": self.name,
                "taskid": taskid,
            },
        )
        if results:
            return Task(self.client, queue=self, data=results)
        return None

    def length(self):
        """
        Returns the current size of a given queue.

            >>> sf = subfork.get_client()
            >>> num_tasks = sf.get_queue(queue).length()

        :returns: Number of Tasks in the Queue.
        """
        resp = self.client._request(
            "queue/size",
            data={
                "queue": self.name,
            },
        )
        if type(resp) != int:
            log.debug("bad response from server: %s", resp)
            return 0
        return resp


class Task(Base):
    """Subfork Task class."""

    def __init__(self, client, queue, data):
        """ "
        :param client: Subfork client instance.
        :param queue: Queue instance.
        :param data: Task data.
        """
        super(Task, self).__init__(client, data)
        self.queue = queue

    def __repr__(self):
        return "<Task %s [%s]>" % (self.queue.name, self.data().get("id"))

    def get_num_failures(self):
        """Returns number of execution failures."""
        return self.data().get("failures", 0)

    def get_results(self):
        """Returns Task results."""
        results = self.data().get("results")
        try:
            return json.loads(results)
        except (json.decoder.JSONDecodeError, TypeError):
            return results
        except Exception as err:
            log.warning("invalid task results: %s", err)
            return results

    def get_worker_data(self):
        """Returns kwargs data passed to worker function."""
        return self.data().get("data", {})

    def is_done(self):
        """Returns True if Task has been processed and is done."""
        return (
            self.data().get("completed") is not None
            or self.data().get("error") is not None
            or self.data().get("exitcode") is not None
        )

    def is_valid(self):
        """Returns True if Task data is valid."""
        return is_valid_task(self.data())

    def requeue(self):
        """
        Requeues a Task with a given id.

        :returns: True if Task was requeued.
        """
        return self.client._request(
            "task/requeue",
            data={
                "queue": self.queue.name,
                "taskid": self.data().get("id"),
            },
        )

    def wait(self, timeout=600):
        """
        Waits for Task to complete in a blocking way.

        :param timeout: maximum amount of time to wait in seconds.
        """
        start_time = time.time()
        wait_time = config.WAIT_TIME
        while not self.is_done():
            time.sleep(wait_time)
            self.sync()
            if timeout and (time.time() - start_time) >= timeout:
                log.debug("timeout exceeded")
                break
        log.debug("task completed: %s", self.data().get("id"))

    def update(self, data, save=False):
        """
        Update and optionally save Task.

        :param data: Data dict to add to Task data.
        :param save: Save this Task (optional).
        """
        self.data().update(data)
        if save:
            return self.save()
        return True

    def save(self):
        """Saves Task data to server."""
        if self.is_valid():
            task_data = copy.deepcopy(self.data())
            results = self.client._request(
                "task/save",
                data={
                    "queue": self.queue.name,
                    "taskid": self.data().get("id"),
                    "data": task_data,
                },
            )
            if is_valid_task(results):
                return Task(self.client, queue=self, data=results)
        else:
            log.warning("invalid task data: %s" % self)
        return False

    def sync(self):
        """Syncs Task data with server."""
        try:
            task = self.queue.get_task(self.data().get("id"))
            if task:
                self.update(task.data())
        except Exception as e:
            log.error(e)


class Worker(Base):
    """Subfork Task Worker class."""

    def __init__(self, client, config):
        """ "
        :param client: Subfork client instance.
        :param config: Worker config.
        """
        super(Worker, self).__init__(client, config)

    def __repr__(self):
        return "<Worker %s>" % self.data().get("name")
