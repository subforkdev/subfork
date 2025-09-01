#!/usr/bin/env python
#
# Copyright (c) Subfork. All rights reserved.
#

__doc__ = """
Contains minify functions and classes.
"""

import os
import re

from subfork.logger import log


def minify(src: str, dst: str):
    """Minify a given src file and output to a dst file.

    :param src: path to the source file to be minified
    :param dst: path to the destination file to write the minified content
    """

    minimized = minify_file(src)

    if minimized:
        fp = open(dst, "w")
        fp.write(minimized)
        fp.close()
    else:
        log.error("minify error")


def minify_css(src: str):
    """Returns minified css source.

    :param src: path to the css file to be minified
    :return: minified css source code
    """

    minified = ""

    with open(src, "r") as infile:
        minified = infile.read()
        minified = re.sub(r"/\*.*?\*/", "", minified, flags=re.DOTALL)
        minified = re.sub(r"\s+", " ", minified)
        minified = re.sub(r"\s*([{}:;,])\s*", r"\1", minified)
        minified = re.sub(r"}\s*", "}", minified)
        minified = re.sub(r"{\s*", "{", minified)

    return minified


def minify_js(src: str):
    """Returns minified js source code.

    :param src: path to the js file to be minified
    :return: minified js source code
    """

    minified = ""

    from jsmin import jsmin

    with open(src) as js_file:
        minified = jsmin(js_file.read(), quote_chars="'\"`")

    return minified


def minify_file(filepath: str):
    """Returns minified file contents.

    :param filepath: path to the file to be minified
    :return: minified file contents
    """

    minified = ""

    if not os.path.exists(filepath):
        log.warning("file not found: %s" % filepath)

    else:
        _, ext = os.path.splitext(filepath)

        try:
            if ext in (".js",):
                minified = minify_js(filepath)
            elif ext in (".css", ".css3"):
                minified = minify_css(filepath)

        except Exception as e:
            log.error(e)

    return minified
