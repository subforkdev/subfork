#!/usr/bin/env python
#
# Copyright (c) Subfork. All rights reserved.
#

__doc__ = """
Contains data api classes and functions.
"""

from subfork import util
from subfork.logger import log
from subfork.api.base import Base


class DatatypeError(Exception):
    """Custom exception class for Datatype errors."""

    pass


class Datatype(Base):
    """Subfork Datatype class."""

    def __init__(self, client, name):
        super(Datatype, self).__init__(client)
        self.name = name

    def __repr__(self):
        return "<Datatype %s>" % (self.name)

    @classmethod
    def get(cls, client, name):
        """
        Gets and returns a new Datatype object instance

        :param client: Subfork client instance.
        :param: Datatype name.
        """
        return cls(client, name)

    def batch(self):
        """Perform batch operations for this datatype."""
        raise NotImplementedError

    def delete(self, params):
        """
        Deletes data rows from a given data collection matching
        a set of search params.

            >>> sf = subfork.get_client()
            >>> sf.get_data(datatype).delete(params)

        :param params: dictionary of key/value data.
        :returns: True if delete was successful.
        """
        if not params:
            raise DatatypeError("Datatype.find(): missing params")
        return self.client._request(
            "data/delete",
            data={
                "collection": self.name,
                "params": params,
            },
        )

    def find(self, params, expand=False, page=1, limit=100):
        """
        Query a data collection matching a given set of search params.
        Returns matching results up to a givem limit.

            >>> sf = subfork.get_client()
            >>> results = sf.get_data(datatype).find(params)

        :param params: list of search params, e.g.

            [[field1, "=", value1], [field2, ">", value2]]

            Supported operands:

                ">": greater than
                "<": less than
                ">=": greater than or equal
                "<=": less then or or equal
                "=": equal to
                "in": in a list
                "not_in": not in a list
                "!=": not equal to
                "~=": regex pattern matching

        :param expand: expand nested datatypes.
        :param page: current page number.
        :param limit: limit the query results.
        :returns: list of results as data dicts.
        """
        if not params:
            raise DatatypeError("Datatype.find(): missing params")
        params = {
            "collection": self.name,
            "expand": expand,
            "limit": limit,
            "paging": {"current_page": page, "results_per_page": limit},
            "params": params,
        }
        return self.client._request("data/get", data=params)

    def find_one(self, params, expand=False):
        """
        Query a data collection matching a given set of search params.
        Returns at most one result.

            >>> sf = subfork.get_client()
            >>> data = sf.get_data(datatype).find_one(params)

        :param params: list of search params, e.g. ::

            [[field1, "=", value1], [field2, ">", value2]]

        :param expand: expand collection ids.

        :returns: results as data dict.
        """
        results = self.find(params, expand, page=1, limit=1)
        if results:
            return results[0]
        return

    def create(self, data):
        """
        Creates new data for this datatype.

            >>> sf = subfork.get_client()
            >>> sf.get_data(datatype).create(datadict)

        :param data: dictionary of key/value data to create.
        :returns: data creation results if successful, or None.
        """
        if data.get("id"):
            raise DatatypeError("Datatype.create(): data contains id")
        return self.client._request(
            "data/create",
            data={
                "collection": self.name,
                "data": util.sanitize_data(data),
            },
        )

    def insert(self, data):
        """
        DEPRECATED: use create() instead.

        Inserts new data into for this datatype.

        :param data: dictionary of key/value data to insert.
        :returns: created data dict or None.
        """
        log.warning("Datatype.insert() is deprecated, use Datatype.create()")
        return self.create(data)

    def upsert(self, data):
        """
        Convenience method that upserts new data into for this datatype.

        :param data: dictionary of key/value data to insert.
        :returns: created data dict or None.
        """
        log.warning("Datatype.upsert() is deprecated")
        if data.get("id"):
            return self.update(data["id"], data)
        return self.create(data)

    def update(self, dataid, data):
        """
        Updates existing data for a this datatype with a given id.

            >>> sf = subfork.get_client()
            >>> sf.get_data(datatype).update(dataid, datadict)

        :param dataid: id of the data to update.
        :param data: dictionary of key/value data to update.
        :returns: updated results if successful, or None.
        """
        if data.get("id") and data["id"] != dataid:
            raise DatatypeError("Datatype.update(): id mismatch")
        if not data:
            raise DatatypeError("Datatype.update(): data is empty")
        return self.client._request(
            "data/update",
            data={
                "collection": self.name,
                "id": dataid,
                "data": util.sanitize_data(data),
            },
        )
