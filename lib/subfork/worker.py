#!/usr/bin/env python
#
# Copyright (c) Subfork. All rights reserved.
#

__doc__ = """
Contains task worker classes and functions.
"""

import os
import sys
import json
import time
import signal
import inspect
from typing import Callable

from subfork import config
from subfork import sample
from subfork import threads
from subfork import util
from subfork.api.task import Task
from subfork.logger import log


class Worker(threads.StoppableThread):
    """Thread that dequeues tasks and spawns runners."""

    def __init__(
        self,
        client,
        queue_name: str,
        func_name: str,
        limit: int = 1,
        wait_time: int = config.WAIT_TIME,
    ):
        super(Worker, self).__init__()
        self.client = client
        self.func_name = func_name
        self.name = "%s worker" % queue_name
        self.limit = limit
        self.queue = self.client.get_queue(queue_name)
        self.sessionid = self.client.conn().get_session_token()
        self.wait_time = wait_time
        self.version = util.get_version()

    def get_tasks(
        self,
        chunk_size: int = config.TASK_BATCH_SIZE,
        throttle: int = config.TASK_RATE_THROTTLE,
    ):
        """Generator that yields tasks from the queue in chunks."""

        queue_size = self.queue.length()
        task_num = 0

        for _ in range(min((queue_size or 0), chunk_size)):
            task = self.queue.dequeue_task()
            if not task:
                continue
            task_num += 1
            yield (task_num, task)
            time.sleep(throttle)

    def run(self):
        """Called when thread starts."""
        log.info("starting %s" % self.queue.name)
        while not self.stopped():
            for task_num, task in self.get_tasks():
                worker_thread = TaskRunner(self, task, task_num)
                worker_thread.start()
            self._stop_event.wait(self.wait_time)
        log.info("stopping %s", self)
        stop_running()


class TaskRunner(threads.StoppableThread):
    """Thread that runs task function."""

    def __init__(self, parent, task: Task, task_num: int = 1):
        super(TaskRunner, self).__init__()
        self.name = "%s worker %s" % (task.queue.name, task_num)
        self.parent = parent
        self.task = task

    @property
    def func_name(self):
        return self.parent.func_name

    @property
    def limit(self):
        return self.parent.limit

    def run(self):
        """Called when thread starts."""
        log.info("starting %s", self.name)
        try:
            # execute task function and save results
            process_task(self, self.task)
        except Exception as e:
            log.exception("unexpected error: %s", str(e))
        finally:
            log.debug("%s done", self.name)

    def sample(self):
        """Returns a data sample in time for this task runner."""
        samp = sample.Sample(
            data={
                "name": self.name,
                "queue": self.task.queue.name,
                "sessionid": self.parent.sessionid,
                "version": self.parent.version,
            }
        )
        return samp


def validate_worker_input(func: Callable, input_data: dict):
    """
    Validate the input data is compatible with the expected input
    of the worker function.

    :param func: worker function.
    :param input_data: data being passed to worker function.
    :returns: True if the input data matches expectations.
    """

    signature = inspect.signature(func)
    function_name = func.__name__
    expected_arguments = ", ".join(signature.parameters.keys())
    is_valid = True

    try:
        if isinstance(input_data, tuple):
            bound_args = signature.bind(*input_data)
            bound_args.apply_defaults()
        elif isinstance(input_data, dict):
            bound_args = signature.bind(**input_data)
            bound_args.apply_defaults()
        else:
            is_valid = False

    except TypeError:
        is_valid = False

    if not is_valid:
        log.warning("%s expects input: %s", function_name, expected_arguments)

    return is_valid


def import_function(func_name: str):
    """
    Imports a Python function with a given import path.

    :param func_name: Python path to function (e.g. pyseq.get_sequences).
    :returns: tuple of module, callable function.
    """
    import importlib

    mod, func = None, None

    try:
        m, f = func_name.rsplit(".", 1)
        mod = importlib.import_module(m)
        func = getattr(mod, f)

    except ModuleNotFoundError as err:
        log.error("module not found: %s", str(err))

    except Exception as err:
        log.exception(err)

    return mod, func


def process_task(runner: TaskRunner, task: Task):
    """
    Executes task function, updates task, and returns exit code.

    :param runner: worker.TaskRunner instance.
    :param task: subfork.api.task.Task instance.
    :returns: process exit code.
    """

    # check for invalid task data from server
    if not task or not task.is_valid():
        return

    log.info("starting: %s", task)

    # update task start time
    task.update(
        {
            "started": util.get_time(),
        }
    )

    # worker has exceeded retry limit
    num_failures = task.get_num_failures()
    if num_failures and (num_failures > runner.limit):
        return

    # set some default values
    error = None
    exitcode = 0
    input_is_valid = None
    results = None
    success = None
    worker_func = None
    worker_mod = None

    # process the task function
    try:
        worker_mod, worker_func = import_function(runner.func_name)
        worker_data = task.get_worker_data()

        if not worker_mod and worker_func:
            raise Exception("error getting worker function: %s" % runner.func_name)

        # update task function data
        task.update(
            {
                "func": {
                    "name": worker_func.__name__,
                    "module": worker_mod.__file__,
                },
                "worker": runner.sample().data(),
            }
        )

        # validate worker function input data
        input_is_valid = validate_worker_input(worker_func, worker_data)

        # execute worker function
        if type(worker_data) == dict:
            results = worker_func(**worker_data)
        else:
            results = worker_func(worker_data)

    except Exception as e:
        log.exception(e)
        success = False
        error = str(e)
        exitcode = 1
        num_failures += 1

    else:
        success = True

    finally:
        log.info("completed: %s", task)
        now = util.get_time()

        # update task data and save task
        task.update(
            {
                "completed": now,
                "elapsed_time": now - task.data().get("started", now),
                "error": error,
                "exitcode": exitcode,
                "failures": num_failures,
                "results": json.dumps(results),
            }
        )
        resp = task.save()
        if not resp:
            log.warning("task not saved")

        # requeue task if within retry limit and the data input was valid
        if not success and (num_failures < runner.limit) and input_is_valid:
            log.info("requeueing: %s", task)
            resp = task.requeue()
            if not resp:
                log.warning("task not requeued")
        else:
            return 1

        # garbage collection
        del worker_mod, worker_func, results, task

    return exitcode


def create_workers(
    client,
    queue_name: str,
    func_name: str,
    limit: int = 1,
    wait_time: int = config.WAIT_TIME,
):
    """
    Creates and starts workers.

    :param client: subfork client.
    :param queue_name: name of the queue.
    :param func_name: function import path.
    :param limit: max times a task should be re-run after failure.
    :param wait_time: queue polling interval (min. 30 seconds).
    """

    worker_thread = None

    def signal_handler(signum, frame):
        if worker_thread:
            worker_thread.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        worker_thread = Worker(
            client=client,
            queue_name=queue_name,
            func_name=func_name,
            limit=limit,
            wait_time=wait_time,
        )
        worker_thread.start()

    except Exception as e:
        log.error("error creating workers: %s", str(e))
        return False

    return True


def restart_all():
    """Restarts workers by restarting main thread."""

    try:
        log.info("restarting workers")
        os.execv(sys.executable, [sys.executable] + sys.argv)

    except Exception as err:
        log.exception("restart error: %s", str(err))


def start_running():
    """Sets global running variable to True."""
    global running
    running = True


def stop_running():
    """Sets global running variable to False."""
    global running
    running = False


def is_running():
    """Returns value of global running variable."""
    global running
    return running


def validate_worker_config(worker_config: dict):
    """
    Validates a given worker config.

    :param worker_config: Worker config dict.
    :returns: True of config is valid.
    """

    # validate queue name
    queue_name = worker_config.get("queue")
    if not queue_name:
        log.error("task queue not defined: %s", queue_name)
        return False

    # validate worker function
    func_name = worker_config.get("function")
    if not func_name:
        log.error("worker function not defined: %s", func_name)
        return False

    worker_mod, worker_func = import_function(func_name)
    if not worker_mod or not worker_func:
        log.error("could not import function: %s", func_name)
        return False

    # validate worker retry limit and wait time
    limit = worker_config.get("limit", config.TASK_RETRY_LIMIT)
    if limit > config.TASK_MAX_RETRY_LIMIT:
        log.error("invalid retry limit: %s", limit)
        return False

    wait_time = worker_config.get("wait", config.WAIT_TIME)
    if wait_time < config.MIN_WAIT_TIME:
        log.error("invalid wait time: %s", wait_time)
        return False

    return True


def run_workers(
    client, worker_configs: dict, autorestart: bool = config.AUTO_RESTART_WORKERS
):
    """
    Main thread that spawns workers.

    :param client: subfork client.
    :param worker_configs: dict of worker configs {name: config}.
    :param autorestart: automatically restart workers on config changes.
    """

    def pause():
        if sys.platform == "win32":
            while is_running():
                time.sleep(1)
        else:
            signal.pause()

    # total worker thread counter
    worker_count = 0

    # iterate through worker configs and start workers
    for config_name, worker_config in worker_configs.items():
        log.debug("loading worker config %s", config_name)

        if not validate_worker_config(worker_config):
            continue

        success = create_workers(
            client=client,
            queue_name=worker_config.get("queue"),
            func_name=worker_config.get("function"),
            limit=worker_config.get("limit", config.TASK_RETRY_LIMIT),
            wait_time=worker_config.get("wait", config.WAIT_TIME),
        )

        if success:
            worker_count += 1

    # return early if no valid workers started
    if worker_count == 0:
        log.warning("no valid workers found")
        return 2
    else:
        start_running()

    # worker host health check thread
    healthcheck = threads.HealthCheck(client)
    healthcheck.start()

    # config file change watcher thread
    if autorestart:
        watcher = threads.FileWatcher(config.config_file, restart_all)
        watcher.start()

    pause()

    log.info("done")

    return 0


def echo(**kwargs):
    """Example worker that returns input kwargs.

    :param kwargs: **kwargs.
    :returns: worker kwargs.
    """
    log.info("subfork.worker.echo: kwargs=%s", kwargs)

    try:
        json.dumps(kwargs)
        return kwargs

    except Exception:
        log.warning("kwargs are not JSON serializable")

    return {"message": "there was an error"}


def stress(t: int = 5):
    """Stress test example worker. Available params:

    :param t: time in secs to run.
    :returns: worker message.
    """
    log.info("subfork.worker.stress: t=%s", t)

    ts = time.time()
    n, x = 1, 2
    timeout = time.time() + float(t)
    buffer = []

    while True:
        if time.time() > timeout:
            break
        buffer.append(n * x)

    buffer.sort()
    return "%s completed its task in %ss" % (sample.hostname, int(time.time() - ts))


def test(**kwargs):
    """Test example worker that prints task data.

    :param t: time in secs to sleep.
    :param error: raise exception with error message.
    :returns: worker message.
    """
    log.info("subfork.worker.test: kwargs=%s", kwargs)

    time.sleep(kwargs.get("t", 1))
    if kwargs.get("error"):
        raise Exception(kwargs["error"])

    return f"greetings from {sample.hostname} ({kwargs})"


def throw(**kwargs):
    """Test example worker that throws an exception."""
    log.info("subfork.worker.throw: kwargs=%s", kwargs)

    raise Exception(kwargs.get("error", "something went wrong"))
