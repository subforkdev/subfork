#!/usr/bin/env python
#
# Copyright (c) Subfork. All rights reserved.
#

__doc__ = """
Contains dev server classes and functions.
"""

import os
import sys
import signal
import time
import webbrowser
from functools import wraps
from typing import Callable, Any, Optional

import flask

import subfork
from subfork import build
from subfork import config
from subfork import util
from subfork.threads import FileWatcher, StoppableThread
from subfork.logger import log, setup_stream_handler

setup_stream_handler("subfork")

# global list of template files
templates = []


def client_required(f: Callable, client: Any):
    """Decorator that passes client to wrapped function.

    :param f: function to be wrapped.
    :param client: Subfork client instance.
    :returns: decorated function.
    """

    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        return f(client, *args, **kwargs)

    return decorated


def catch_all(client, path: Optional[str] = ""):
    """Catch-all page request handler.

    :param client: Subfork client instance.
    :param path: requested path.
    :returns: redirect response to the requested path.
    """

    host = client.conn().host
    redirect_path = f"http://{host}/{path}"
    log.info("redirect: %s", redirect_path)
    return flask.redirect(redirect_path, code=302)


def api_request(client, **kwargs):
    """API endpoint stub handler.

    :param client: Subfork client instance.
    :param kwargs: url parameters.
    :returns: json response from the api request.
    """

    data = flask.request.get_json()
    error = None
    results = {}
    success = False
    url = "/".join(list(kwargs.values()))

    try:
        results = client._request(url, data)
        success = True
    except Exception as e:
        log.error(e)
        error = str(e)
    finally:
        return flask.jsonify(
            {
                "error": error,
                "data": results,
                "success": success,
            }
        )


def get_session_data(client):
    """
    Returns session data.

    :param client: Subfork client instance.
    """

    session_data = client.conn().session
    log.info("get_session_data: %s", session_data.get("sessionid"))

    return flask.jsonify(
        {
            "data": session_data,
            "success": True,
        }
    )


def read_page_configs(template_data: dict):
    """
    Reads subfork template file and returns route->page map.

    :param template_data: subfork template data.
    :returns: route->page map.
    """

    route_map = {}

    for _, page_config in template_data.get("templates", {}).items():
        route_map.update(
            {
                page_config.get("route"): {
                    "attrs": page_config.get("attrs", {}),
                    "file": page_config.get("file"),
                }
            }
        )

    return route_map


class MockUser(dict):
    """Mock user class."""

    def __init__(self, *args, **kwargs):
        super(MockUser, self).__init__(*args, **kwargs)
        self["is_authenticated"] = 1


def render_wrapper(client, template_folder, template, page_config):
    """
    Decorator that wraps the render template function.

    :param client: Subfork client instance
    :param template_folder: templates folder
    :param template: template file name
    :param page_config: page config
    """

    def get_user(username: str):
        user = client.get_user(username)
        if user:
            return user.data()
        return {}

    def render(**kwargs: Any):
        login_required = page_config.get("login_required")
        page_attrs = page_config.get("attrs")
        _, ext = os.path.splitext(template)

        # jinja stubs
        kwargs.update(
            {
                "args": flask.request.args,
                "get_user": get_user,
                "page": {
                    "attrs": page_attrs,
                    "site": client.site().data(),
                },
                "site": client.site().data(),
                "user": MockUser(client.user().data()),
            }
        )

        try:
            if ext in (
                ".html",
                ".htm",
            ):
                return flask.render_template(template, **kwargs)
            source = open(os.path.join(template_folder, template), "r").read()
            mimetype = util.get_mime_type(template)
            return flask.Response(source, mimetype=mimetype)

        except subfork.client.RequestError as e:
            log.error("response from server: %s", str(e))
            return str(e)

        except Exception as e:
            log.exception(e)
            return flask.abort(500)

    render.__name__ = "render_%s" % len(templates)
    templates.append(render)

    return render


class App(flask.Flask):
    """Development server app class."""

    def __init__(self, *args, **kwargs):
        super(App, self).__init__(*args, **kwargs)
        self.setup_logger()

    def setup_logger(self):
        """Redirects werkzeug logger."""
        import logging
        from werkzeug.serving import WSGIRequestHandler

        werkzeug_logger = logging.getLogger("werkzeug")
        WSGIRequestHandler.log.debug = log.debug
        WSGIRequestHandler.log.info = log.info


class DevServer(StoppableThread):
    """Thread that runs an instance of the dev server app."""

    def __init__(self, host, port, client, template):
        super(DevServer, self).__init__()
        self.client = client
        self.template = template
        self.host = host
        self.port = port

    def run(self):
        """Called when the thread starts."""
        self.app = create_app(self.client, self.template)
        return run_app(self.app, self.host, self.port)


def create_app(client, template: dict):
    """
    Creates and returns an instance of the dev server for testing.

    :param client: Subfork client instance.
    :param template: file path to subfork template file.
    :returns: dev server app instance.
    """

    # read subfork site template file
    root_folder = os.path.dirname(template)
    template_data = config.load_file(template)

    # get template and static file folders
    template_folder = os.path.join(
        root_folder, template_data.get("template_folder", "templates")
    )
    static_folder = os.path.join(
        root_folder, template_data.get("static_folder", "static")
    )

    # create an app instance and set template and static folders
    app = App(
        "devserver",
        template_folder=template_folder,
        static_folder=static_folder,
    )
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    # api endpoint stubs
    app.route("/api/get_session_data", methods=["POST"])(
        client_required(get_session_data, client)
    )
    app.route("/api/<obj>/<op>", methods=["POST"])(client_required(api_request, client))

    # catch-all page endpoint stub
    app.route("/<path:path>", methods=["GET"])(client_required(catch_all, client))

    # get the routes and pages from the template
    page_configs = read_page_configs(template_data)

    def _get_index(route):
        """Returns index for a given route."""
        if route:
            return len(route)
        return 0

    # configure dev page routes
    for route, page_config in sorted(
        page_configs.items(), key=lambda x: _get_index(x[0])
    ):
        try:
            if not route:
                continue
            template_file = page_config.get("file")
            log.debug("route %s -> template %s", route, template_file)
            app.route(route, methods=["GET"])(
                render_wrapper(client, template_folder, template_file, page_config)
            )

        except Exception:
            log.exception("error creating route: %s", route)

    return app


def build_app(template: dict):
    """Builds the app files and returns build template file.

    :param template: path to subfork template file.
    :returns: path to build subfork.yml file.
    """

    return build.build(template)


def run_app(app, host: str = "localhost", port: int = 8080):
    """
    Run the dev server for testing.

    :param app: dev server app instance.
    :param host: dev server host (default localhost).
    :param port: dev server port (default 8080).
    """

    return app.run(host=host, debug=False, port=port, threaded=False)


def start_running():
    """Sets global running variable to True."""

    global running
    running = True


def is_running():
    """Returns value of global running variable."""

    global running
    return running


def watch_template_files(template: dict):
    """Creates FileWatcher threads to watch for changes on app files.

    :param template: app subfork.yml file.
    :returns: list of file watcher threads.
    """

    template_data = config.load_file(template)
    root_folder = os.path.dirname(template)

    template_folder = os.path.join(
        root_folder, template_data.get("template_folder", "templates")
    )
    static_folder = os.path.join(
        root_folder, template_data.get("static_folder", "static")
    )

    watcher_threads = []
    for filepath in [
        template,
        template_folder,
        static_folder,
    ]:
        watcher_thread = FileWatcher(filepath, build_app, {"template": template})
        watcher_thread.start()
        watcher_threads.append(watcher_thread)

    return watcher_threads


def run(client, template: dict, host: str = "localhost", port: int = 8080):
    """
    Starts a simple dev server process, and opens a webbrowser to
    the running dev server.

    :param client: Subfork client instance.
    :param template: path to template file.
    :param host: dev server host (optional)
    :param port: dev server port (optional)
    """

    def pause():
        if sys.platform == "win32":
            while is_running():
                time.sleep(1)
        else:
            signal.pause()

    if not os.path.exists(template):
        log.error("file not found: %s", template)
        return 2

    try:
        # build the app
        build_file = build_app(template)

        # start file watcher threads
        watchers = watch_template_files(template)

        # start up the dev server thread
        server = DevServer(host, port, client, build_file)
        server.start()

        # open the site
        hostname = f"http://{server.host}:{server.port}"
        log.info("dev server running at %s", hostname)
        webbrowser.open(hostname)
        start_running()

        # wait for sigint
        pause()

    except KeyboardInterrupt:
        log.info("shutting down dev server")
        server.stop()
        del server
        for thread in watchers:
            thread.stop()
            del thread

    except Exception as e:
        log.exception("unexpected error: %s", str(e))
        return 1

    log.info("done")

    return 0
