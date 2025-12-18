#!/usr/bin/env python3
#
# Copyright (c) Subfork. All rights reserved.
#

__doc__ = """
Contains page api classes and functions.
"""

from subfork.api.base import Base


class Page(Base):
    """Subfork Page class."""

    def __init__(self, client, data: dict):
        """Initializes Page instance.

        :param client: subfork.api.client.Client instance.
        :param data: page data dict.
        :returns: Page instance.
        """
        super(Page, self).__init__(client, data)

    def __repr__(self):
        return "<Page %s>" % (self.data().get("name"))

    @classmethod
    def get(cls, client, name: str, revision: int = None):
        """Get a Page with a given name, e.g. test.html.

        :param client: subfork.api.client.Client instance.
        :param name: page name, e.g. test.html.
        :param revision: optional revision number.
        :returns: Page instance or None.
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

    def routes(self):
        """Returns Routes for this Page."""
        return [Route(self.client, route) for route in self.data().get("routes")]


class Route(Base):
    """Subfork Route class."""

    def __init__(self, client, data: dict):
        """Initializes Route instance.

        :param client: subfork.api.client.Client instance.
        :param data: route data dict.
        :returns: Route instance.
        """
        super(Route, self).__init__(client, data)

    def __repr__(self):
        """Returns string representation of Route instance."""
        return "<Route %s>" % (self.data().get("path"))

    @classmethod
    def get(cls, client, path: str):
        """Returns list of site routes.

        :param client: subfork.api.client.Client instance.
        :param path: route path, e.g. "/about".
        :returns: Route instance or None.
        """
        results = client._request(
            "site/routes",
            data={
                "path": path,
            },
        )
        if results:
            return cls(client, results)
        return None
