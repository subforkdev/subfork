#!/usr/bin/env python
#
# Copyright (c) Subfork. All rights reserved.
#

__doc__ = """
Contains build classes and functions.
"""

import os
import shutil
from html.parser import HTMLParser

from subfork import config
from subfork import minify
from subfork import util
from subfork.logger import log


class InvalidTemplate(Exception):
    """Exception class for template errors"""


class LinkParser(HTMLParser):
    """HTML link parser that builds a list of href and src links."""

    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag in ["a", "link", "script", "img"]:
            for attr, value in attrs:
                if attr == "href" or attr == "src":
                    self.links.append(value)


def replace_links(src, dst, static_files, static_folder="static"):
    """Takes an input `src` file and replaces local static file links with
    new links that reference the static files location. Writes a modified
    file with updated links to `dst`.

    :param src: source file path.
    :param dst: destination file path.
    :param static_files: list of static file links to replace.
    :param static_folder: target static files folder.
    """

    with open(src, "r", encoding="utf-8") as sf:
        content = sf.read()

    parser = LinkParser(src)
    parser.feed(content)

    for link in parser.links:
        for filename in static_files:
            if link.endswith(filename) and not link.startswith(static_folder):
                new_link = f"/{static_folder}/{filename}".replace("//", "/")
                log.debug(f"{src} replace {link} -> {new_link}")
                content = content.replace(link, new_link)

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    outfile = open(dst, "w")
    outfile.write(content)
    outfile.close()


def copy_file(src, dst, minimize=config.AUTO_MINIMIZE):
    """Copies a file, with optional minimization of js and css files.

    :param src: source file path.
    :param dst: destination file path.
    :param minimize: minimize destination file (optional).
    """

    if not os.path.isfile(src):
        log.error("file not found: %s", src)
        return

    # get relative file path and extension
    _, ext = util.splitext(src)
    name = util.normalize_path(src)

    if not ext:
        log.error("could not determine file ext: %s", name)
        return

    if minimize and ext in (".js", ".css", ".css3"):
        log.info("minimizing %s", name)
        minimized_src = minify.minify_file(src)
        if minimized_src:
            util.write_file(dst, minimized_src)
        elif os.path.isfile(src):
            copy_file(src, dst, minimize=False)

    else:
        if os.path.getsize(src) > 1e6:  # 1MB size limit
            log.error("file too large: %s", src)
            return
        else:
            log.info("copying %s", name)
            dirname = os.path.dirname(dst)
            if not os.path.exists(dirname):
                os.makedirs(dirname, exist_ok=True)
            shutil.copy(src, dst)

    if not dst or not os.path.exists(dst):
        log.error("copy failed: %s", dst)

    return dst


def create_template(filepath, template_folder, static_folder, templates, **kwargs):
    """Creates a new config file.

    :param filepath: output path config file.
    :param template_folder: path to folder containing template files.
    :param static_folder: path to folder containing static files.
    :param templates: template file data as a dict.
    :param **kwargs: template kwargs.
    """

    start = os.path.dirname(filepath)
    template_folder_path = util.normalize_path(template_folder, start)
    static_folder_path = util.normalize_path(static_folder, start)

    template_data = {
        "domain": kwargs.get("domain", config.HOST),
        "access_key": kwargs.get("access_key", "${SUBFORK_ACCESS_KEY}"),
        "secret_key": kwargs.get("secret_key", "${SUBFORK_SECRET_KEY}"),
        "auto_minimize": kwargs.get("auto_minimize", config.AUTO_MINIMIZE),
        "static_folder": static_folder_path,
        "template_folder": template_folder_path,
    }

    if templates:
        template_data["templates"] = templates
    else:
        log.warning("no templates found in %s", template_folder)

    return util.write_template(filepath, template_data)


def create_build_template(source, build_root):
    """Creates a template.yml build file.

    :param source: path to subfork.yml.
    :param build_root: build output root directory.
    :returns: path to build file.
    """

    if not os.path.isfile(source):
        raise Exception("file not found: %s" % source)

    data = config.load_file(source)
    build_file = os.path.join(build_root, "template.yml")

    return create_template(
        filepath=build_file,
        domain=data.get("domain"),
        auto_minimize=data.get("auto_minimize", False),
        template_folder=os.path.join(build_root, "templates"),
        static_folder=os.path.join(build_root, "static"),
        templates=data.get("templates"),
    )


def build(template_file, build_root=None, update_links=True):
    """Creates a build directory for a given site. The build directory
    has the following structure:

        build
          |- templates
          |    `- <page>.html
          |- static
          |    `- <file>.ext
          `- template.yml

    :param template_file: path to template.yml file.
    :param build_root: build output root directory.
    :param update_links: update links to static files.
    :returns: path to build file.
    """

    if not os.path.exists(template_file):
        log.error("file not found: %s", template_file)
        return

    # read the template file
    log.info("building %s", os.path.abspath(template_file))
    root_directory = os.path.dirname(template_file)
    template_data = config.load_file(template_file)

    # domain is a required template setting
    if "domain" not in template_data:
        raise InvalidTemplate("missing domain value")

    # get some template settings
    minimize = template_data.get("minimize", config.AUTO_MINIMIZE)
    template_folder = template_data.get("template_folder", "templates")
    log.info("templates folder: %s", template_folder)
    static_folder = template_data.get("static_folder", "static")
    log.info("static folder: %s", static_folder)

    # create the build tree
    if not build_root:
        build_root = os.path.join(root_directory, "build")

    if os.path.exists(build_root):
        log.debug("deleting existing build: %s", build_root)
        shutil.rmtree(build_root)

    build_template_folder = os.path.join(build_root, "templates")
    build_static_folder = os.path.join(build_root, "static")

    # make temp folders
    try:
        os.makedirs(build_root, exist_ok=True)
        os.makedirs(build_template_folder, exist_ok=True)
        os.makedirs(build_static_folder, exist_ok=True)
    except Exception as err:
        log.exception("error making build dirs")
        raise err

    # copy the template file to template.yml file (expected name)
    build_template_file = os.path.join(build_root, "template.yml")
    create_build_template(template_file, build_root)

    # process static files
    static_folder_root = os.path.join(root_directory, static_folder)
    file_count = 0
    static_files = []
    for src in util.walk(static_folder_root):
        npath = util.normalize_path(src, static_folder_root)
        static_files.append(npath)
        dst = os.path.join(
            root_directory,
            build_static_folder,
            npath,
        )
        copy_file(src, dst, minimize)
        file_count += 1
        if file_count > 50:
            raise InvalidTemplate("too many static files")

    # process template files
    template_folder_root = os.path.join(root_directory, template_folder)
    page_count = 0
    seen_files = []
    for _name, pageconfig in template_data.get("templates", {}).items():
        filename = pageconfig.get("file")
        if not filename:
            raise InvalidTemplate("missing file on %s" % _name)
        if len(filename) > 100:
            raise InvalidTemplate("filename too long: %s (max 100)" % filename)

        src = os.path.join(template_folder_root, filename)
        dst = os.path.join(build_template_folder, filename)

        if src not in seen_files:
            _, ext = os.path.splitext(src)
            if update_links and ext in (".html", ".htm"):
                try:
                    replace_links(src, dst, static_files)
                except Exception as e:
                    log.error("error updating links: %s", e)
                    copy_file(src, dst, pageconfig.get("minimize", minimize))
            else:
                copy_file(src, dst, pageconfig.get("minimize", minimize))
            seen_files.append(src)

        page_count += 1
        if page_count > 25:
            raise InvalidTemplate("too many templates: %s (max 25)" % page_count)

    return build_template_file
