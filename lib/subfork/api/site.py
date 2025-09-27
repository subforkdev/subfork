#!/usr/bin/env python3
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
        """Initializes Site instance.

        :param client: subfork.api.client.Client instance.
        :param data: site data dict.
        :returns: Site instance.
        """
        super(Site, self).__init__(client, data)

    def __repr__(self):
        return "<Site %s>" % self.data().get("name")

    @classmethod
    def get(cls, client: object):
        """Fetch and return Site data for the given Client connection.

        :param client: subfork.api.client.Client instance.
        :returns: subfork.api.site.Site instance.
        :raises: SiteNotFound.
        """
        results = client._request(
            "site/get",
        )
        if results:
            return cls(client, results)
        raise SiteNotFound(client.conn().host)

    def create_user(self, username: str, email: str):
        """Creates and returns new User instance.

        :param username: username value.
        :param email: user email value.
        :returns: User instance.
        """
        from subfork.api.user import User

        return User.create(self.client, username, email)

    def get_data(self, name: str):
        """Returns a Datatype object.

        :param name: datatype name, e.g. "test".
        :returns: Datatype instance.
        """
        from subfork.api.data import Datatype

        return Datatype.get(self.client, name)

    def get_page(self, name: str):
        """Returns a Page object matching `name`.

        :param name: page name, e.g. "test.html".
        :returns: Page instance.
        """
        from subfork.api.page import Page

        return Page.get(self.client, name)

    def get_queue(self, name: str):
        """Returns a Task Queue object.

        :param name: queue name, e.g. "test".
        :returns: Queue instance.
        """
        from subfork.api.task import Queue

        return Queue.get(self.client, name)

    def get_user(self, username: str):
        """Returns a User instance with username, or None.

        :param username: site username value.
        :returns: User instance.
        """
        from subfork.api.user import User

        return User.get(self.client, username)

    def get_version(self, version_number: int):
        """Returns a requested Site Version.

        :param version_number: version number.
        :returns: Version instance or None.
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

    def pages(self, include_inherited: bool = False):
        """Returns list of Page instances.

        :param include_inherited: include inherited pages.
        :returns: list of Page instances.
        """
        from subfork.api.page import Page

        if type(include_inherited) != bool:
            raise ValueError("include_inherited must be a boolean")

        results = self.client._request(
            "site/pages",
            data={
                "include_inherited": include_inherited,
            },
        )
        if results:
            return [Page(self, r) for r in results]
        return []

    def routes(self, include_inherited: bool = False):
        """Returns list of site Route instances.

        :param include_inherited: include inherited routes.
        :returns: list of Route instances.
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
        """Returns a list of Versions for this Site.

        :returns: list of Version instances.
        """
        results = self.client._request(
            "site/versions",
        )
        if results:
            return [Version(self.client, self, r) for r in results]
        return []


class Version(Base):
    """Subfork Site Version class."""

    def __init__(self, client, site: Site, data: dict):
        """Initializes Version instance.

        :param client: subfork.api.client.Client instance.
        :param site: parent Site instance.
        :param data: version data dict.
        :returns: Version instance.
        """
        super(Version, self).__init__(client, data)
        self.site = site

    def __repr__(self):
        """String representation of Version instance."""
        return "<Version %s>" % self.data().get("number")

    def release(self):
        """Set the Site to this Version."""
        results = self.client._request(
            "site/update",
            data={
                "version": self.data().get("number"),
            },
        )
        if results:
            self.site.reload()
        return None
