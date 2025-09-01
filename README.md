Subfork Python API
==================

[Quickstart](#quickstart) |
[Basic Commands](#basic-commands) |
[Workers](#workers) |
[Config File](#config-file) |
[Environments](#environments) |
[Distribution](#distribution)

Subfork is the easiest way to build and deploy static sites and micro web apps.
This package provides the Subfork Python API and command line interface.

- Docs: https://docs.fork.io
- GitHub: https://github.com/subforkdev/subfork
- PyPI: https://pypi.org/project/subfork
- Demo: https://test.fork.io

## Installation

The easiest way to install:

```bash
$ pip install -U subfork
```

Installing from source:

```bash
$ git clone https://github.com/subforkdev/subfork
$ cd subfork
$ pip install .
```

Or modify the `subfork.env` file as needed and use the provided Makefile to
install using distman:

```bash
$ sudo make install
```

Requires Python 3.6+.

## Setup

In order to authenticate with the Subfork API, you will first need to create
a site and API access keys for your site at [subfork.com](https://subfork.com).

Subfork uses [envstack](https://github.com/rsgalloway/envstack) to manage
environment variables. Environment variables can be stored in different .env
files, for example `prod.env`, `dev.env` or `default.env` files. Access keys can
be stored securely in an .env file (see
[instructions here](https://github.com/rsgalloway/envstack?tab=readme-ov-file#encryption)
for generating encryption keys):

```bash
$ envstack keys -eo secrets.env
```

Or to use environment variables without .env files, set the following:

```bash
$ export SUBFORK_ACCESS_KEY=<access key>
$ export SUBFORK_SECRET_KEY=<secret key>
```

Modify the `subfork.yml` [config file](#config-file) at the root of your project
or set `$SUBFORK_CONFIG_FILE` to the path to `subfork.yml`:

```bash
$ export SUBFORK_CONFIG_FILE=/etc/subfork/conf/subfork.yml
```

## Quickstart

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

```bash
$ subfork create -t <templates folder> -s <static folder>
```

where the templates folder is the folder containing all of the html files, and the
static folder is the folder containing all of the static files (.jpg, .js, .css, etc).
Be sure to update the values in the new `subfork.yml` if necessary.

To test a site locally using the dev server:

```bash
$ subfork run
```

To deploy and release a site:

```bash
$ subfork deploy -c "initial deployment" --release
```

To process queued tasks using workers defined in the [config file](#config-file):

```bash
$ subfork worker
```

## Workers

Task workers are decentralized Python functions that poll task queues for new jobs.
As new jobs are added to the queue, task workers pull them off and pass data
to the specified Python function.

See the `subfork.worker.test` function for an example of a simple worker that takes jobs
from the `test` queue and returns a string.

To run a worker that pulls jobs from the `test` queue and runs the test function:

```bash
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

#### systemd

For convenience, a systemd service file is included that can run workers defined
in the `subfork.yml` config file as a service. The Makefile has a `start` target
defined to install and run the service after the install step:

```bash
$ sudo make start
```

## Config File

The `subfork.yml` config file contains required auth info, page templates,
routes (or endpoints), static files and task worker definitions.

```bash
$ curl -o subfork.yml https://raw.githubusercontent.com/subforkdev/master/subfork.yml
```

The example config file contains two endpoints and a worker:

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

## Environments

Settings can be easily managed using [envstack](https://github.com/rsgalloway/envstack)
to manage environments. By default, subfork looks for a `subfork.env`
environment file, but you can easily create different environments, for example
a `prod.env` environment file, or a `dev.env` environment file:

```bash
$ ./dev.env -- subfork run
```

## Distribution

File distribution can be optionally managed using the `dist.json` file and
installed using [distman](https://github.com/rsgalloway/distman):

```bash
$ pip install -U distman
$ ./subfork.env -- dist [OPTIONS]
```

The `subfork.env` file defines the `${DEPLOY_ROOT}` environment variable which is
used by distman for deployment.

## Demo

See [test.fork.io](https://test.fork.io) for an example of a simple demo site,
or get the source code here:

```bash
$ git clone https://github.com/subforkdev/test.fork.io
```
