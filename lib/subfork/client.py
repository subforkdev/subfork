#!/usr/bin/env python3
#
# Copyright (c) Subfork. All rights reserved.
#

__doc__ = """
Contains client classes and functions.
"""

import hashlib
import json
import re
import sys
import threading
from typing import Any, Callable, Optional, Tuple

import requests
import socketio
import subfork.config as config
import subfork.util as util
from subfork.api.site import Site
from subfork.api.user import User
from subfork.logger import log, setup_stream_handler
from subfork.version import __prog__, __version__

setup_stream_handler(__prog__)


class ClientError(Exception):
    """Custom exception class for authentication errors."""

    pass


class ConfigError(Exception):
    """Custom exception class for config errors."""

    pass


class ConnectError(Exception):
    """Custom exception class for connection errors."""

    pass


class RequestError(Exception):
    """Custom exception class for request errors."""

    pass


class SubforkHttpClient(object):
    """General purpose HTTP Client for interacting with the Subfork REST API."""

    last_error = None
    last_request_ts = 0
    session = {}
    sessionid = None

    def __init__(
        self,
        host: str = config.HOST,
        port: int = config.PORT,
        api_version: str = config.API_VERSION,
        access_key: str = config.ACCESS_KEY,
        secret_key: str = config.SECRET_KEY,
    ):
        """Instantiates an instance of the Subfork Http client.

        :param host: site domain ($SUBFORK_DOMAIN).
        :param port: site port ($SUBFORK_PORT).
        :param api_version: api endpoint to use ($SUBFORK_API_VERSION).
        :param access_key: access key ($SUBFORK_ACCESS_KEY).
        :param secret_key: secret key ($SUBFORK_SECRET_KEY).
        """
        super(SubforkHttpClient, self).__init__()
        self.host = re.sub(r"^https?://", "", host)
        self.port = int(port)
        self.base_url = self.format_base_url(host, port)
        self.api_url = self.base_url + "/" + api_version
        self.auth = (access_key, secret_key)
        self.sessionid = None
        self.token = None
        self.connected = False
        self.headers = {
            "sid": None,
            "token": None,
            "user-agent": f"python-{__prog__}/{__version__}",
        }
        self.check_config()
        self.get_session_data()

    def __repr__(self):
        return "<SubforkHttpClient %s>" % self.host

    def __get_auth(self):
        return self.__auth

    def __set_auth(self, auth: Tuple[Optional[str], Optional[str]]):
        """Sets authentication credentials.

        :param auth: tuple of (access_key, secret_key).
        :raises ConfigError: if auth is invalid.
        """
        access_key, secret_key = auth
        self.__auth = (
            access_key,
            hashlib.sha256(
                "{accesskey}:{secretkey}".format(
                    accesskey=access_key, secretkey=secret_key
                ).encode("utf-8")
            ).hexdigest(),
        )

    auth = property(__get_auth, __set_auth)

    def check_config(self):
        """Validates client connection configuration."""
        if not self.host:
            raise ConfigError("missing host")
        if not self.__auth:
            raise ConfigError("missing auth")

    def _request(
        self,
        url: str,
        data: Optional[dict] = None,
        file_data: Optional[bytes] = None,
    ):
        """Makes an HTTP POST Request with data provided.

        :param url: API endpoint url.
        :param data: request data (optional, must be JSON serializable dict).
        :param file_data: binary file data (optional).
        :returns: response data.
        """
        if data is None:
            data = {}

        if file_data:
            if not url.endswith("deploy"):
                raise RequestError("invalid request")
            elif sys.getsizeof(file_data) > 1e8:
                raise RequestError(f"file too large")

        if (sys.getsizeof(data) > 10240) or len(data) > 45:
            log.error("data too large (max 10K / 45 keys)")
            return {}

        self.last_request_ts = util.get_time()
        url = self.format_url(url)

        try:
            if file_data:
                resp = requests.post(
                    url,
                    auth=self.auth,
                    data=data,
                    headers=self.headers,
                    files={
                        "json": (None, json.dumps(data)),
                        "file": ("template.zip", file_data),
                    },
                )
            else:
                resp = requests.post(
                    url,
                    auth=self.auth,
                    headers=self.headers,
                    json=data,
                )
            return self.handle_response(resp)
        except RequestError as e:
            self.last_error = str(e)
            log.warning("request error: %s", e)
        except requests.exceptions.ConnectionError as e:
            self.last_error = str(e)
            log.debug(self.last_error)
            log.warning("could not connect to host: %s", self.host)
        return

    def format_base_url(self, host: str, port: Optional[int] = None):
        """Returns formatted base url for API requests for a given host and
        port (optional). Uses http for the protocol."""
        if host == "localhost":
            return f"http://localhost:{port}"
        return f"https://{host}"

    def format_url(self, url: str):
        """Returns a formatted api request url."""
        return "/".join([self.api_url, url])

    def handle_response(self, resp: Optional[requests.Response]):
        """Request response handler."""
        if resp is None:
            log.warning("no response from server")
        elif resp.ok:
            if self.last_error:
                log.info("connection restored")
                self.last_error = None
            try:
                data = resp.json()
                if not data.get("success"):
                    log.warning(data.get("error", "there was a server error"))
                else:
                    self.connected = True
                return data.get("data", None)
            except Exception:
                log.debug(resp.content)
                raise RequestError("bad response from server")
        else:
            status_message = util.get_status_message(resp.status_code)
            if resp.status_code == 500:
                log.warning(status_message)
            elif resp.status_code in (401, 402, 403):
                raise ClientError(status_message)
            else:
                raise RequestError(status_message)
        return None

    def get_session_data(self):
        """Requests and returns session data from remote server."""
        if self.session:
            return self.session
        self.session = self._request(
            "session",
            data={
                "source": "python-client",
                "version": util.get_version(),
            },
        )
        if self.session and self.session.get("sessionid"):
            self.sessionid = str(self.session["sessionid"])
        else:
            raise ConnectError("could not get session data")
        if self.session and self.session.get("token"):
            self.token = self.session.get("token")
        else:
            raise ConnectError("could not get session data")
        self.headers.update(
            {
                "sid": self.sessionid,
                "Authorization": f"Bearer {self.token}",
                "user-agent": f"subfork-python/{__version__}",
                "x-client": "subfork-python",
                "x-client-version": __version__,
            }
        )
        return self.session

    def get_session_token(self):
        """Return the session id for with the current connection."""
        if self.sessionid:
            return self.sessionid
        if self.session:
            self.sessionid = str(self.session.get("sessionid"))
        return self.sessionid


class SubforkWsClient:
    """WebSocket/Socket.IO client for workers and event listeners."""

    def __init__(
        self,
        http_client: SubforkHttpClient,
        url: str = config.EVENTS_URL,
    ):
        """Instantiates an instance of the Subfork WebSocket client.

        :param http_client: An existing SubforkHttpClient
        :param url: Events base URL
        """
        self.http_client = http_client
        self.url = url.rstrip("/")
        self._sio = socketio.Client(reconnection=True)
        self._connect_lock = threading.Lock()
        self._connected = False
        self._connecting = False

        # get session data
        sid = self.http_client.get_session_token()
        token = None
        if self.http_client.session:
            token = self.http_client.session.get("token")

        if not sid:
            raise ConnectError(
                "No session id available; ensure get_session_data() succeeded."
            )
        if not token:
            raise ConnectError(
                "No token available; ensure get_session_data() succeeded."
            )

        # default headers
        headers = {
            "sid": sid,
            "Authorization": f"Bearer {token}",
            "user-agent": self.http_client.headers.get("user-agent", "subfork-python"),
        }
        self._connect_kwargs = {
            "headers": headers,
            "auth": {"token": token},
            "socketio_path": config.SOCKETIO_PATH,
            "transports": ["websocket"],
        }

        # lifecycle hooks
        @self._sio.event
        def connect():
            with self._connect_lock:
                self._connected = True
            log.debug("SubforkWsClient: connected to %s", self.url)

        @self._sio.event
        def disconnect():
            with self._connect_lock:
                self._connected = False
            log.debug("SubforkWsClient: disconnected from %s", self.url)

    def __repr__(self):
        return "<SubforkWsClient %s>" % self.url

    def close(self):
        """Close the WebSocket connection."""
        try:
            self._sio.disconnect()
        except Exception:
            pass
        with self._connect_lock:
            self._connected = False

    def connect(self):
        """Open the Socket.IO connection (idempotent + thread-safe)."""
        with self._connect_lock:
            if self.is_connected() or self._connecting:
                return
            self._connecting = True
        try:
            self._sio.connect(self.url, **self._connect_kwargs)
        except socketio.exceptions.ConnectionError as e:
            log.error("SubforkWsClient connection error: %s", e)
        except Exception as e:
            log.error("SubforkWsClient unhandled error: %s", e)
        finally:
            with self._connect_lock:
                self._connecting = False

    def is_connected(self):
        """Returns True if the WebSocket connection is open."""
        try:
            return bool(self._sio.connected)
        except Exception:
            return False

    def on(self, event_name: str, handler: Callable[[Any], None]):
        """Register a handler for a single event name (string).

        :param event_name: event name string, e.g. "created", "done".
        :param handler: function that receives event data.
        """
        log.debug("listening for event: %s", event_name)

        @self._sio.on(event_name)
        def _handler(data):
            try:
                handler(data)
            except Exception as e:
                log.warning("handler error for event %s: %s", event_name, e)

    def wait(self):
        """Block the current thread and pump the Socket.IO event loop."""
        if not self.is_connected():
            self.connect()
        self._sio.wait()


class Subfork(object):
    """
    Subfork API client class.

    Instantiate client:

        >>> import subfork
        >>> sf = subfork.get_client()

    Get page info:

        >>> page = sf.get_page("test.html")

    Find data in a datatype:

        >>> dt = sf.get_data("test")
        >>> params = [["foo", "=", "bar"]]
        >>> data = dt.find(params)
    """

    __conn = None
    __site = None
    __user = None
    __ws = None

    def __init__(
        self,
        host: str = config.HOST,
        port: int = config.PORT,
        api_version: str = config.API_VERSION,
        access_key: str = config.ACCESS_KEY,
        secret_key: str = config.SECRET_KEY,
    ):
        """
        Instantiates an instance of the Subfork API client.

        :param host: site domain ($SUBFORK_DOMAIN).
        :param port: optional site port ($SUBFORK_PORT).
        :param api_version: api endpoint to use ($SUBFORK_API_VERSION).
        :param access_key: access key ($SUBFORK_ACCESS_KEY).
        :param secret_key: secret key ($SUBFORK_SECRET_KEY).
        """
        super(Subfork, self).__init__()
        Subfork._set_conn(host, port, api_version, access_key, secret_key)

    def __repr__(self):
        return "<Subfork %s>" % self.conn().host

    @classmethod
    def conn(cls):
        """Returns shared SubforkHttpClient object."""
        return cls.__conn

    @classmethod
    def ws(cls):
        """Returns shared SubforkWsClient object."""
        if not cls.__ws:
            cls.__ws = SubforkWsClient(cls.__conn)
        return cls.__ws

    @classmethod
    def _set_conn(
        cls,
        host: str,
        port: int,
        api_version: str,
        access_key: str,
        secret_key: str,
    ):
        """Establishes a shared server connection.

        :param host: site domain ($SUBFORK_DOMAIN).
        :param port: optional site port ($SUBFORK_PORT).
        :param api_version: api endpoint to use ($SUBFORK_API_VERSION).
        :param access_key: access key ($SUBFORK_ACCESS_KEY).
        :param secret_key: secret key ($SUBFORK_SECRET_KEY).
        :raises ConnectError: if connection could not be established.
        """
        if not cls.__conn:
            cls.__conn = SubforkHttpClient(
                host, port, api_version, access_key, secret_key
            )
        if cls.__conn and cls.__conn.connected:
            log.info("Subfork: connected to %s", host)

    def _request(
        self,
        url: str,
        data: Optional[dict] = None,
        file_data: Optional[bytes] = None,
    ):
        """Makes an Http request to the server and returns response data.

        :param url: API endpoint url.
        :param data: request data (optional, must be JSON serializable).
        :param file_data: binary file data (optional).
        :returns: response data.
        """
        return self.conn()._request(url, data, file_data)

    def get_data(self, name: str):
        """
        Returns a Datatype object.

        :param name: datatype name, e.g. "test".
        :returns: data.Datatype instance.
        """
        return self.site().get_data(name)

    def get_page(self, name: str):
        """
        Returns a Page object matching `name`.

            >>> sf = subfork.get_client()
            >>> page = sf.get_page(name)

        :param name: page name, e.g. "test.html".
        :returns: page.Page instance.
        """
        return self.site().get_page(name)

    def get_queue(self, name: str):
        """
        Returns a Task Queue object.

            >>> sf = subfork.get_client()
            >>> sf.get_queue(name)

        :param name: queue name, e.g. "test".
        :returns: task.Queue instance.
        """
        return self.site().get_queue(name)

    def get_user(self, username: str):
        """
        Returns a subfork site user matching a given username.

            >>> sf = subfork.get_client()
            >>> sf.get_user(username)

        :param username: site username value.
        :returns: user.User instance.
        """
        return self.site().get_user(username)

    def site(self):
        """Returns shared Site object."""
        if not self.__site:
            self.__site = Site.get(self)
        return self.__site

    def user(self):
        """Returns API User object."""
        if not self.__user:
            self.__user = User(self, self.conn().session.get("user"))
        return self.__user
