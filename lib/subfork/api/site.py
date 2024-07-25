#!/usr/bin/env python
#
# Copyright (c) Subfork. All rights reserved.
#

__doc__ = """
Contains site and version api classes and functions.
"""

from subfork.api.base import Base


class SiteNotFound(Exception):
    """Custom exception class for Site not found errors."""

    pass


class Site(Base):
    """Subfork Site class."""

    def __init__(self, client, data):
        super(Site, self).__init__(client, data)

    def __repr__(self):
        return "<Site %s>" % self.data().get("name")

    @classmethod
    def get(cls, client):
        """
        Fetch and return Site data for the given Client connection.

        :returns: subfork.api.site.Site instance.
        :raises: SiteNotFound.
        """
        results = client._request(
            "site/get",
        )
        if results:
            return cls(client, results)
        raise SiteNotFound(client.conn().host)

    def create_user(self, username, email):
        """
        Creates and returns new User instance.

        :param username: username value.
        :param email: user email value.
        :returns: User instance.
        """
        from subfork.api.user import User

        return User.create(self.client, username, email)

    def get_data(self, name):
        """
        Returns a Datatype object.

        :param name: datatype name, e.g. "test".
        """
        from subfork.api.data import Datatype

        return Datatype.get(self.client, name)

    def get_page(self, name):
        """
        Returns a Page object matching `name`.

        :param name: page name, e.g. "test.html".
        """
        from subfork.api.page import Page

        return Page.get(self.client, name)

    def get_queue(self, name):
        """
        Returns a Task Queue object.

        :param name: queue name, e.g. "test".
        """
        from subfork.api.task import Queue

        return Queue.get(self.client, name)

    def get_user(self, username):
        """
        Returns a User instance with username, or None.

        :param username: site username value.
        :returns: User instance.
        """
        from subfork.api.user import User

        return User.get(self.client, username)

    def get_version(self, version_number):
        """
        Returns a requested Site Version.

        :param version_number: version number.
        """
        results = self.client._request(
            "version/get",
            data={
                "version": version_number,
            },
        )
        if results:
            return Version(self.client, self, results)
        return None

    def pages(self, include_inherited=False):
        """Returns list of site pages, e.g. ::

            {
                'id': 1234,
                'lang': 'html',
                'name': 'foobar.html',
                'revision': 2,
                'route': '/foo/<foo>/<bar>',
                'siteid': 6,
                'userid': 4
            }

        :param include_inherited: include inherited pages.
        """
        from subfork.api.page import Page

        results = self.client._request(
            "site/pages",
            data={
                "include_inherited": include_inherited,
            },
        )
        if results:
            return [Page(self, r) for r in results]
        return []

    def routes(self, include_inherited=False):
        """Returns list of site routes, e.g. ::

            {
                'id': 1234,
                'path': '/foo/<foo>/<bar>',
                'siteid': 6,
                'userid': 4
            }

        :param include_inherited: include inherited routes.
        """
        from subfork.api.page import Route

        results = self.client._request(
            "site/routes",
            data={
                "include_inherited": include_inherited,
            },
        )
        if results:
            return [Route(self, r) for r in results]
        return []

    def versions(self):
        """Returns a list of Versions for this Site."""
        results = self.client._request(
            "site/versions",
        )
        if results:
            return [Version(self.client, self, r) for r in results]
        return []


class Version(Base):
    """Subfork Site Version class."""

    def __init__(self, client, site, data):
        super(Version, self).__init__(client, data)
        self.site = site

    def __repr__(self):
        return "<Version %s>" % self.data().get("number")

    def delete(self):
        raise NotImplementedError

    def release(self):
        """
        Set the Site to this Version.
        """
        results = self.client._request(
            "site/update",
            data={
                "version": self.data().get("number"),
            },
        )
        if results:
            self.site.reload()
        return None
