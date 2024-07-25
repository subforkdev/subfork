#!/usr/bin/env python
#
# Copyright (c) Subfork. All rights reserved.
#

__doc__ = """
Contains user api classes and functions.
"""

from subfork.api.base import Base


class UserNotFound(Exception):
    """Custom exception class for User not found errors."""

    pass


class Message(Base):
    """Subfork User Message class."""

    def __init__(self, client, data):
        super(Message, self).__init__(client, data)


class User(Base):
    """Subfork User class."""

    def __init__(self, client, data):
        super(User, self).__init__(client, data)

    def __repr__(self):
        return "<User %s>" % self.data().get("username")

    @classmethod
    def find(cls, client, **kwargs):
        """
        Finds and returns Users.
        """
        results = client._request(
            "user/find",
            data={
                "params": kwargs,
            },
        )
        if results:
            return [cls(client, r) for r in results]
        return None

    @classmethod
    def create(cls, client, username, email):
        """
        Create new User with a given username and email.

        :param client: Subfork client instance.
        :param username: User username.
        :param email: User email.
        :returns: new User instance, or None.
        """
        results = client._request(
            "user/create",
            data={
                "username": username,
                "email": email,
            },
        )
        if results:
            return cls(client, results)
        return None

    @classmethod
    def get(cls, client, username):
        """
        Get a User with a given username.
        """
        results = client._request(
            "user/get",
            data={
                "username": username,
            },
        )
        if results:
            return cls(client, results)
        return None

    def create_message(self, title, content, level=None):
        """
        Creates a new Message for this User.

        :param title: message title.
        :param content: message content.
        :returns: Message instance or None.
        """
        results = self.client._request(
            "message/create",
            data={
                "content": content,
                "level": level,
                "siteid": self.client.site().data().get("id"),
                "title": title,
                "userid": self.data().get("id"),
                "username": self.data().get("username"),
            },
        )
        if results:
            return Message(self.client, results)
        return None

    def disable(self):
        """Disable this User."""
        return self.client._request(
            "user/disable",
            data={
                "id": self.data().get("id"),
            },
        )

    def get_messages(self):
        """
        Gets Messages for this User.
        """
        results = self.client._request(
            "user/messages",
            data={
                "userid": self.data().get("id"),
            },
        )
        if results:
            return [Message(self.client, r) for r in results]
        return []
