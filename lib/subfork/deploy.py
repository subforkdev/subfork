#!/usr/bin/env python
#
# Copyright (c) Subfork. All rights reserved.
#

__doc__ = """
Contains deployment classes and functions.
"""

import os

from subfork import build
from subfork import config
from subfork import util
from subfork.logger import log


def deploy(client, template_file, comment, release=False, force=False):
    """
    Deploy a site build.

    :param template_file: path to template.yml build file.
    :param comment: version comment.
    :param release: release deployment.
    :param force: force deployment (optional).
    """

    # run build step
    build_file = build.build(template_file)
    build_root = os.path.dirname(build_file)

    # deploy the build
    response = deploy_build(client, build_root, comment, release, force)

    # response handler
    if (
        response
        and response.get("version")
        and response.get("version") != client.site().data().get("version")
        and release
    ):
        results = client._request(
            "site/get",
        )
        if results:
            client.site().set_data(results)
        return None
    return None


def create_archive(build_root, filename="subfork.zip"):
    """Creates an archive file of a given build for deployment.

    :param build_root: a given build folder
    :returns: path to archive file
    """

    # create the dist folder
    dist_root = os.path.join(os.path.dirname(build_root), "dist")
    os.makedirs(dist_root, exist_ok=True)

    # prep build archive in dist folder
    archive_file = os.path.abspath(os.path.join(dist_root, filename))
    if os.path.exists(archive_file):
        os.remove(archive_file)

    # create the archive file
    util.create_zip_file([build_root], outfile=archive_file)
    if not os.path.isfile(archive_file):
        raise Exception(f"build archive failed: {archive_file}")

    return archive_file


def deploy_build(
    client,
    build_root,
    comment,
    release=False,
    force=False,
    wait=True,
):
    """Deploy a site template.

    :param client: Subfork client
    :param build_root: a given build folder
    :param comment: deployment message
    :param release: release version (optional)
    :param force: force upload (optional)
    :param wait: wait for deployment to complete (optional)
    """

    log.info("deploying %s", build_root)
    archive_file = create_archive(build_root)
    archive_file_size = os.path.getsize(archive_file)
    max_size = client.site().data().get("max_size", config.MAX_UPLOAD_BYTES)
    log.info("build: %s (%s)", archive_file, util.b2h(archive_file_size))

    if archive_file_size > max_size:
        raise Exception(f"build too large (max {util.b2h(max_size)})")

    file_data = util.read_file(archive_file)
    if not file_data:
        raise Exception("could not read build archive")

    data = {
        "comment": comment,
        "release": release,
        "force": force,
        "wait": wait,
    }

    resp = client._request("site/deploy", data, file_data=file_data)
    if resp:
        message = resp.get("message")
        if resp.get("success"):
            log.info(message)
        else:
            log.error(message)
    else:
        log.warning("no response from server")

    return resp
