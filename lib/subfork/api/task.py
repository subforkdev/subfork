#!/usr/bin/env python3
#
# Copyright (c) Subfork. All rights reserved.
#

__doc__ = """
Contains task api classes and functions.
"""

import copy
import json
import sys
import time
from typing import Any, Callable

from subfork import config, util
from subfork.api.base import Base
from subfork.logger import log


def is_valid_task(task_data: dict):
    """Returns True if task is valid.

    :param task_data: Task data dict.
    :returns: True if valid task data.
    """

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

    def __init__(self, client, name: str):
        """Queue constructor.

        :param client: Subfork client instance.
        :param name: Queue name.
        """
        super(Queue, self).__init__(client)
        self.name = name

    def __repr__(self):
        """Returns string representation of Queue."""
        return "<Queue %s>" % self.name

    @classmethod
    def get(cls, client, name: str):
        """Classmethod to get Queue instance.

        :param client: Subfork client instance.
        :param name: Queue name.
        :returns: Queue instance.
        """
        return cls(client, name)

    def create_task(self, data: dict = None):
        """Adds a task to a this Queue.

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
        """Dequeues next Task from this Queue.

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

    def get_task(self, taskid: str):
        """Gets a task for a given queue name and task id.

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
        """Returns the current size of a given queue.

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

    def on(self, event_name: str, handler: Callable[[Any], None]):
        """Register a handler for a single event name for this task.

            >>> task.on("created", handler)

        The handler is called with the event data, but the task still exists in
        the queue to be processed by workers.

        :param event_name: event name string, e.g. "created", "done".
        :param handler: function that receives event data.
        """
        if not self.client.ws():
            raise Exception("WebSocket client not connected")
        self.client.ws().on(f"task:{self.name}:{event_name}", handler)

    def listen(self):
        """Listen for events in a blocking way. This does not process tasks.
        Use a Worker to process tasks.

            >>> sf = subfork.get_client()
            >>> q = sf.get_queue("test")
            >>> q.on("created", lambda task: print("task created", task))
            >>> q.listen()
        """
        if not self.client.ws():
            raise Exception("WebSocket client not connected")
        try:
            self.client.ws().wait()
        except KeyboardInterrupt:
            log.info("exiting")
        except Exception as e:
            log.error("error: %s", e)
        finally:
            self.client.ws().close()


class Task(Base):
    """Subfork Task class."""

    def __init__(self, client, queue: str, data: dict):
        """Task constructor.

        :param client: subfork.api.client.Client instance.
        :param queue: Queue instance.
        :param data: Task data.
        """
        super(Task, self).__init__(client, data)
        self.queue = queue

    def __repr__(self):
        """Returns string representation of Task."""
        return "<Task %s [%s]>" % (self.queue.name, self.id())

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

    def wait(self, timeout: int = 600):
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
                log.warning("timeout exceeded")
                break
        log.info("task completed: %s", self)

    def update(self, data: dict, save: bool = False):
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
    """Subfork Worker class."""

    def __init__(self, client, config: dict):
        """Worker constructor.

        :param client: subfork.api.client.Client instance.
        :param config: Worker config.
        """
        super(Worker, self).__init__(client, config)

    def __repr__(self):
        """Returns string representation of Worker."""
        return "<Worker %s>" % self.data().get("name")
