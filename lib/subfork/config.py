#!/usr/bin/env python
#
# Copyright (c) Subfork. All rights reserved.
#

__doc__ = """
Contains configs and settings.
"""

import os

falsy = [False, "False", "false", 0, "0", "null", "no"]
truthy = [True, "True", "true", 1, "1", "yes"]


def get_config(key: str, default: str = None, dataclass: type = None):
    """Returns config setting from the environment then config file.

    :param key: config key name.
    :param default: default value if not found.
    :param dataclass: type to cast the value to (str, int, bool, etc).
    :returns: config value.
    """

    env_key = "_".join(["SUBFORK", key.upper()])
    value = os.getenv(env_key, settings.get(key, default))

    if default is not None and dataclass is None:
        dataclass = type(default)
    elif dataclass is None:
        dataclass = str

    if dataclass == bool and value in falsy:
        return False
    elif dataclass == bool and value in truthy:
        return True

    return dataclass(value)


def get_config_file():
    """Returns path to found config file in order of:

        ${SUBFORK_CONFIG_FILE}
        ./subfork.yml

    :returns: filesystem path to config file
    """

    config_file = os.path.join(os.getcwd(), "subfork.yml")
    return os.getenv("SUBFORK_CONFIG_FILE", config_file)


def load_file(filename: str):
    """Reads a given subfork template file and returns data dict.
    Automatically expands embedded environment variables.

    :param filename: path to subfork template file (subfork.yml).
    :returns: template data as a dict.
    """

    data = {}

    if not os.path.exists(filename):
        return data

    import yaml

    with open(filename, "r") as stream:
        try:
            data.update(yaml.safe_load(stream))
        except (TypeError, yaml.YAMLError) as e:
            raise Exception("invalid template: %s" % filename)
        except yaml.parser.ParserError as e:
            raise Exception("invalid template: %s" % filename)

    def expand_env_vars(obj):
        if isinstance(obj, str):
            return os.path.expandvars(obj)
        elif isinstance(obj, dict):
            return {key: expand_env_vars(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [expand_env_vars(item) for item in obj]
        else:
            return obj

    return expand_env_vars(data)


# get and load config file settings
config_file = get_config_file()
settings = load_file(config_file)

# global debug switch
DEBUG = get_config("debug", False)

# remote host settings
HOST = get_config("domain")
PORT = get_config("port", 80)

# which api version endpoint to use
API_VERSION = get_config("api_version", "api")

# get access keys
ACCESS_KEY = get_config("access_key")
SECRET_KEY = get_config("secret_key")

# auto minimize js and css files
AUTO_MINIMIZE = get_config("auto_minimize", True)

# restart workers when config file changes, or every 12 hours
AUTO_RESTART_WORKERS = get_config("auto_restart", True)

# default build directory
BUILD_FOLDER = get_config("build_folder", "public")

# maximum upload size in bytes
MAX_UPLOAD_BYTES = 1e7

# minimum wait time between queue checks
MIN_WAIT_TIME = 30

# maximum number of tasks to process at once
TASK_BATCH_SIZE = int(get_config("task_batch_size", 100))

# default worker function
TASK_FUNCTION = get_config("task_function")

# name of the default task queue
TASK_QUEUE = get_config("task_queue")

# task dequeue rate throttle (dequeue wait time in seconds)
TASK_RATE_THROTTLE = float(get_config("task_rate_throttle", 0.1))

# maximum number of task retry attempts
TASK_MAX_RETRY_LIMIT = 3

# default failure retry limit
TASK_RETRY_LIMIT = int(get_config("task_retry_limit", 2))

# max task data size in bytes
TASK_MAX_BYTES = 10240

# default request interval in seconds
WAIT_TIME = float(get_config("request_interval", MIN_WAIT_TIME))

# worker settings
WORKERS = get_config("workers", {})

# ignorable file patterns when deploying
IGNORABLE = [
    "*~",
    "*.bat",
    "*.bak",
    "*.dll",
    "*.exe",
    ".git*",
    "*.jar",
    "*.php",
    "*.py",
    "*.pyc",
    "*.reg",
    "*.sh",
    "*.slo",
    "*.so",
    "*.tmp",
    ".env*",
    ".venv*",
    "subfork.yml",
    "venv*",
    "__pycache__",
    "Thumbs.db",
    ".DS_Store",
]
