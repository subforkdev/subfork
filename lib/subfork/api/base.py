#!/usr/bin/env python
#
# Copyright (c) Subfork. All rights reserved.
#

__doc__ = """
Contains base api classes and functions.
"""


class Base(object):
    """Object base class."""

    def __init__(self, client, data={}):
        super(Base, self).__init__()
        self.client = client
        self.set_data(data)

    def __eq__(self, other):
        """Equality operator."""
        if self.__class__ != other.__class__:
            return False
        if self.__data["id"] != other.__data["id"]:
            return False
        return True

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.data().get("id"))

    @classmethod
    def get(cls, client):
        """
        Implement this method on the subclass to fetch data from server.

        :param client: Subfork connection class instance.
        :returns: subclass instance.
        """
        raise NotImplementedError("must be implemented on subclass")

    def data(self):
        """Object data accessor."""
        return self.__data

    def set_data(self, data):
        """Object data setter.

        :param data: data dict.
        """
        self.__data = data
