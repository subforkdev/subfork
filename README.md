Subfork Python API
==================

Subfork is the easiest way to build and deploy static sites and micro web apps.
This package provides the Subfork Python API and command line interface.

- Docs: https://docs.subfork.com
- GitHub: https://github.com/subforkdev/subfork
- PyPI: https://pypi.org/project/subfork

## Installation

The easiest way to install:

```shell
$ pip install subfork
```

Source code:

```shell
$ git clone https://github.com/subforkdev/subfork
```

Requires Python 3.6+.

## Setup

In order to authenticate with the Subfork API, you will first need to create
a site and API access keys for your site at [subfork.com](https://subfork.com).

To use environment variables, set the following:

```shell
$ export SUBFORK_ACCESS_KEY=<access key>
$ export SUBFORK_SECRET_KEY=<secret key>
```

Or create a `subfork.yml` [config file](#config-file) at the root of your project
or set `$SUBFORK_CONFIG_FILE` to the path to `subfork.yml`:

```shell
$ export SUBFORK_CONFIG_FILE=/path/to/subfork.yml
```

## Quick Start

To use the Subfork Python API you must first complete the configuration steps
below. Then instantiate a client using the site domain and access keys:

```python
import subfork

client = subfork.get_client()
site = client.site()
```

Getting pages:

```python
# get all the pages
pages = site.pages()

# or a specific page
page = site.get_page("index.html")
```

Getting data:

```python
# get all of the 'bookings' for 'Sally'
params = [["guestid", "=", "Sally"]]
results = site.get_data("bookings").find(params)
```

Updating data:

```python
# update the 'total' value for a booking
data = site.get_data("bookings").find_one(params)
data["total"] = 600.00
results = site.get_data("bookings").update(data["id"], data)
```

## Basic Commands

To create a `subfork.yml` [config file](#config-file) from existing html templates
and static files:

```shell
$ subfork create -t <templates folder> -s <static folder>
```

where the templates folder is the folder containing all of the html files, and the
static folder is the folder containing all of the static files (.jpg, .js, .css, etc).
Be sure to update the values in the new `subfork.yml` if necessary.

To test a site locally using the dev server:

```shell
$ subfork run
```

To deploy and release a site:

```shell
$ subfork deploy -c "initial deployment" --release
```

To process queued tasks using workers defined in the [config file](#config-file):

```shell
$ subfork worker
```

## Workers

Task workers are decentralized Python functions that poll task queues for new jobs.
As new jobs are added to the queue, task workers pull them off and pass data
to the specified Python function.

See the `subfork.worker.test` function for an example of a simple worker that takes jobs
from the `test` queue and returns a string.

To run a worker that pulls jobs from the `test` queue and runs the test function:

```shell
$ subfork worker --queue test --func subfork.worker.test
```

Workers will automatically retry failed jobs.

Getting task results:

```python
queue = site.get_queue("test")
task = queue.get_task(taskid)
results = task.get_results()
```

Creating new tasks:

```python
task = queue.create_task({"t": 1})
```

Tasks and task data can be viewed on the tasks page of the subfork dashboard.

## Config File

The `subfork.yml` config file contains required auth info, page templates,
routes (or endpoints), static files and task worker definitions.

For example, this config file contains two endpoints and a worker:

```yaml
# enter site domain (e.g. mysite.fork.io)
domain: ${SUBFORK_DOMAIN}

# enter site credentials here
access_key: ${SUBFORK_ACCESS_KEY}
secret_key: ${SUBFORK_SECRET_KEY}

# path to templates and static files (optional)
template_folder: templates
static_folder: static

# page template definitions
templates:
  index:
    route: /
    file: index.html
  user:
    route: /user/<username>
    file: user.html

# task worker definitions (optional)
workers:
  test:
    queue: test
    function: subfork.worker.test
```

## Demo

See [test.fork.io](https://test.fork.io) for an example of a simple demo site,
or get the source code here:

```shell
$ git clone https://github.com/subforkdev/test.fork.io
```
