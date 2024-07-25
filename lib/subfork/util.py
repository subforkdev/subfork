#!/usr/bin/env python
#
# Copyright (c) Subfork. All rights reserved.
#

__doc__ = """
Contains utility functions and classes.
"""

import os
import re
import sys
import json
import time
import yaml
import requests
import fnmatch
from functools import wraps

import subfork
from subfork import config
from subfork.logger import log
from subfork.version import __prog__, __version__

# work in chunks to limit mem usage when reading
BUF_SIZE = 65536

# store current working directory
CWD = os.getcwd()

# regex that matches ignorable file patterns
IGNORABLE_PATHS = re.compile(
    "(" + ")|(".join([fnmatch.translate(i) for i in config.IGNORABLE]) + ")"
)

# regex pattern that matches version strings
VERSION_PATTERN = re.compile(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?([a-zA-Z]*)$")

# define some times
HOURS_1 = 3600
HOURS_6 = 21600
HOURS_12 = 43200
HOURS_24 = 86400


def b2h(bytes, format="%(value).1f%(symbol)s"):
    """Converts bytes to a human readable format."""
    symbols = ("B", "K", "M", "G", "T")
    prefix = {}
    for i, s in enumerate(symbols[1:]):
        prefix[s] = 1 << (i + 1) * 10
    for symbol in reversed(symbols[1:]):
        if bytes >= prefix[symbol]:
            value = float(bytes) / prefix[symbol]
            return format % locals()
    return format % dict(symbol=symbols[0], value=bytes)


def parse_version(version):
    """Parses a version string and returns a tuple of its components."""
    match = re.match(VERSION_PATTERN, version)
    if match:
        major = int(match.group(1))
        minor = int(match.group(2)) if match.group(2) is not None else 0
        patch = int(match.group(3)) if match.group(3) is not None else 0
        alpha = match.group(4)
        return (major, minor, patch, alpha)
    else:
        raise ValueError("Invalid version string format")


def check_version():
    """Checks PyPI for version updates."""
    try:
        current_version = parse_version(__version__)
        name = f"{__prog__} {__version__}"
        pypi_url = "https://pypi.org/pypi/%s/json" % __prog__
        request = requests.get(pypi_url)

        if request.status_code == 404:
            log.warning("package %s not found in PyPI", __prog__)

        elif request.status_code == 200:
            pypi_versions = request.json()["releases"].keys()
            all_versions = sorted(list(parse_version(v) for v in pypi_versions))
            latest_version = all_versions[-1]
            version_string = ".".join(map(str, latest_version[:3])) + latest_version[3]
            if current_version not in all_versions:
                log.warning("%s not found in PyPI", name)
                return False
            elif current_version < latest_version:
                name = f"{__prog__} {version_string}"
                log.warning("newer version available: %s", name)
                return False

        else:
            log.debug("PyPI returned code %s", request.status_code)

        return True

    except requests.exceptions.ConnectionError as e:
        log.warning("PyPI connection error: %s", str(e))

    except Exception as e:
        log.warning("error getting version: %s", str(e))

    return


def checksum(path):
    """Returns an MD5 checksum for a given filepath."""

    import hashlib

    md5_hash = hashlib.md5()

    if os.path.isdir(path):
        for filepath in walk(path):
            for data in _read_file(filepath):
                md5_hash.update(data)
    else:
        for data in _read_file(path):
            md5_hash.update(data)

    return md5_hash.hexdigest()


def get_templates(folder, noext=False):
    """
    For a given folder, return a list of template file definitions
    as a dict that include the relative path to the file, and an
    assumed http route. Routes for files named "index.html" will be
    replaced with "/".

    Example templates folder:

        templates
        |- index.html
        `- sub
            `- test.html

    produces:

        {
            "templates": {
                "index_html": {
                    "file": "index.html",
                    "route": "/",
                },
                "sub_test_html": {
                    "file": "sub/test.html",
                    "route": "sub/test.html",
                }
            }
        }

    :param folder: folder to look for HTML template files.
    :param noext: exclude .html ext from routes.
    :returns: templates data.
    """

    templates = {}

    for path in walk(folder):
        path = normalize_path(path, start=folder)
        basename = str(os.path.basename(path)).lower()
        name, ext = os.path.splitext(basename)
        node = "".join(
            ["_" if char in ",.?!;`'\":/-" else char for char in path]
        ).lower()

        if str(ext).lower() in (".html", ".htm"):
            if noext:
                route = f"/{name}"
            else:
                route = f"/{path}"
            if basename in ("index.html", "index.htm"):
                route = route.replace(basename, "")
            log.info("found template: %s", path)
            templates[node] = {
                "file": os.path.relpath(path),
                "route": route,
            }
        else:
            log.debug("found static file: %s", path)

    return templates


def create_zip_file(targets, outfile=None):
    """Creates a zip file for a given list of target dirs."""

    import zipfile

    def zipdir(path, ziph):
        os.chdir(path)
        for root, _, files in os.walk("."):
            for f in files:
                ziph.write(os.path.join(root, f))

    if not outfile:
        outfile = "subfork.zip"

    zipf = zipfile.ZipFile(outfile, "w", zipfile.ZIP_DEFLATED)
    for target in targets:
        if os.path.exists(target):
            zipdir(target, zipf)
    zipf.close()

    return outfile


def deprecated(f):
    """Decorator that logs deprecation warning."""

    @wraps(f)
    def decorated(*args, **kwargs):
        log.warning("%s is deprecated", f.__name__)
        return f(*args, **kwargs)

    return decorated


def encodeurl(params):
    """python 2/3 compatible url encoder."""

    try:
        from urllib.parse import urlencode
    except Exception:
        from urllib import urlencode

    return urlencode(params)


def get_client(host=config.HOST, port=config.PORT):
    """Returns a client connection object."""

    try:
        return subfork.Subfork(
            host=host,
            port=port,
            access_key=config.ACCESS_KEY,
            secret_key=config.SECRET_KEY,
        )

    except (subfork.client.RequestError, subfork.client.ConnectError):
        log.error("could not connect to %s", host)
        raise


def get_mime_type(filename):
    """Returns the MIME type for a given filename."""

    import mimetypes

    mime_types = {
        ".bmp": "image/bmp",
        ".css3": "text/css",
        ".gz": "application/gzip",
        ".map": "application/json",
    }

    mime_type, _ = mimetypes.guess_type(filename)
    _, ext = os.path.splitext(filename)
    mime_type = mime_types.get(ext, mime_type)

    if mime_type:
        return mime_type
    else:
        return "octet/binary-stream"


def get_python_version():
    """Returns Python version as major.minor."""
    return ".".join(map(str, sys.version_info[0:2]))


def get_session_id():
    """Returns unique session id."""
    import uuid

    return str(uuid.uuid4())


def get_status_message(status_code):
    """Returns a status code message."""
    return {
        400: "bad request",
        401: "unauthorized",
        402: "payment required",
        403: "forbidden",
        404: "not found",
        405: "method not allowed",
        408: "request timed out",
        413: "payload too large",
        417: "missing parameters",
        423: "locked",
        426: "update required",
        429: "too many requests",
        500: "there was a server error",
        504: "gateway timeout",
    }.get(status_code, "unhandled error: %s" % status_code)


def get_time():
    """Returns epoch time in millis as an int."""
    return int(time.time() * 1000.0)


def get_version():
    """Returns subfork version as a string."""
    from subfork.version import __version__

    return __version__


def is_ignorable(path):
    """Returns True if path is ignorable (includes dot files)."""

    if path.startswith("."):
        return True

    return re.search(IGNORABLE_PATHS, path) is not None


def is_subpath(filepath, directory):
    """
    Returns True if both `filepath` and `directory` have a common prefix.
    """

    d = os.path.join(os.path.realpath(directory), "")
    f = os.path.realpath(filepath)

    return os.path.commonprefix([f, d]) == d


def minify(src, dst):
    """Minify a given src file and output to a dst file."""

    minimized_src = minify_file(src)

    if minimized_src:
        fp = open(dst, "w")
        fp.write(minimized_src)
        fp.close()
    else:
        print("error minify'ing source")


def minify_file(filepath):
    """Returns minified file contents."""
    minified = ""

    if not os.path.exists(filepath):
        log.warning("file not found: %s" % filepath)

    else:
        try:
            from jsmin import jsmin

            with open(filepath) as js_file:
                minified = jsmin(js_file.read(), quote_chars="'\"`")

        except Exception as e:
            log.error(e)

    return minified


def normalize_path(path, start=os.getcwd()):
    """Returns a normalized path."""

    npath = os.path.normpath(path)

    if start is None or is_subpath(path, start):
        return os.path.relpath(npath, start=start).replace("\\", "/")

    return os.path.abspath(npath).replace("\\", "/")


def _read_file(filepath):
    """File reader data generator."""

    start = time.time()
    limit = 10  # secs

    with open(filepath, "rb") as f:
        while True:
            data = f.read(BUF_SIZE)  # io.DEFAULT_BUFFER_SIZE
            if not data:
                break
            if (time.time() - start) > limit:
                break
            yield data


def read_file(filepath):
    """File reader data."""

    binary_content = b""

    for data in _read_file(filepath):
        binary_content += data

    return binary_content


# deprecated
def read_template(template_file):
    """Reads a template.yml file and returns template data as a dict.

    :param template_file: site template file.
    :returns: template data dict.
    """
    log.warning("util.read_template() is deprecated, use config.load_file")

    if not os.path.exists(template_file):
        return

    with open(template_file) as stream:
        data = yaml.safe_load(stream)

    return data


def sanitize_data(data, default={}):
    """
    Validates data. Returns input data or an empty dict.

    :param data: data dict to sanitize.
    :param default: default value if data is None.
    """

    try:
        if data is None:
            data = default

        # data must be json serializable
        json.dumps(data)

        # data size limits
        assert sys.getsizeof(data) < 8192, "data too large"

        # data dict num keys limit
        if type(data) == dict:
            assert len(data.keys()) < 50, "too many keys"

    except AssertionError as err:
        log.warning(err)
        return {}

    except TypeError as err:
        log.warning("data is not JSON serializable: %s", err)
        return {}

    return data


def splitext(src):
    """Returns tuple of relative file path and file extension.

    :param src: source file path.
    :returns: (rel file path, file extension).
    """

    try:
        name = src.split(CWD)[-1]

    except Exception:
        name = os.path.basename(src)

    _, ext = os.path.splitext(name)
    return name, ext


def walk(path):
    """Generator that yields found filepaths.

    :param path: path to walk.
    :yields: filenames.
    """

    if not is_ignorable(path) and os.path.isfile(path):
        yield path

    path = os.path.abspath(path)
    for dirname, dirs, files in os.walk(path, topdown=True):
        if is_ignorable(dirname):
            continue
        for d in dirs:
            if is_ignorable(d):
                dirs.remove(d)
        for name in files:
            if not is_ignorable(name):
                yield os.path.join(dirname, name)


def write_file(filepath, contents):
    """Writes text content to a filepath.

    :param filepath: output file path.
    :param contents: template data dict.
    """

    dirname = os.path.dirname(filepath)
    if dirname and not os.path.isdir(dirname):
        os.makedirs(dirname)

    fp = open(filepath, "w")
    fp.write(contents)
    fp.close()

    return True


def write_template(filepath, contents):
    """Writes template data to filepath.

    :param filepath: output file path.
    :param contents: template data dict.
    """

    return write_file(
        filepath=filepath,
        contents=yaml.dump(contents, default_flow_style=False, sort_keys=False),
    )
