#!/usr/bin/env python
#
# Copyright (c) Subfork. All rights reserved.
#

__doc__ = """
Contains page api classes and functions.
"""

from subfork.api.base import Base


class Page(Base):
    """Subfork Page class."""

    def __init__(self, client, data):
        super(Page, self).__init__(client, data)

    def __repr__(self):
        return "<Page %s>" % (self.data().get("name"))

    @classmethod
    def get(cls, client, name, revision=None):
        """
        Get a Page with a given name, e.g. test.html.
        """
        results = client._request(
            "page/get",
            data={
                "name": name,
                "revision": revision,
            },
        )
        if results:
            return cls(client, results)
        return None

    def get_content(self):
        """Returns Page content."""
        raise NotImplementedError

    def set_content(self, value):
        """Sets Page content."""
        raise NotImplementedError

    def routes(self):
        """Returns Routes for this Page."""
        return [Route(self.client, route) for route in self.data().get("routes")]


class Route(Base):
    """Subfork Route class."""

    def __init__(self, client, data):
        super(Route, self).__init__(client, data)

    def __repr__(self):
        return "<Route %s>" % (self.data().get("path"))

    @classmethod
    def get(cls, client, path):
        """Returns list of site routes."""
        results = client._request(
            "site/routes",
            data={
                "path": path,
            },
        )
        if results:
            return cls(client, results)
        return None
