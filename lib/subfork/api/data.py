#!/usr/bin/env python3
#
# Copyright (c) Subfork. All rights reserved.
#

__doc__ = """
Contains data api classes and functions.
"""

from subfork import util
from subfork.api.base import Base


class DatatypeError(Exception):
    """Custom exception class for Datatype errors."""

    pass


class Datatype(Base):
    """Subfork Datatype class."""

    def __init__(self, client, name: str):
        """Initializes Datatype instance.

        :param client: subfork.api.client.Client instance.
        :param name: Datatype name.
        :returns: Datatype instance.
        """
        super(Datatype, self).__init__(client)
        self.name = name

    def __repr__(self):
        """Returns string representation of Datatype instance."""
        return f"<Datatype {self.name}>"

    @classmethod
    def get(cls, client, name: str):
        """Gets and returns a new Datatype object instance

        :param client: subfork.api.client.Client instance.
        :param name: Datatype name.
        :returns: Datatype instance.
        """
        return cls(client, name)

    def delete(self, params: dict):
        """Deletes data rows from a given data collection matching
        a set of search params.

            >>> sf = subfork.get_client()
            >>> sf.get_data(datatype).delete(params)

        :param params: dictionary of key/value data.
        :raises: DatatypeError for invalid params.
        :returns: True if delete was successful.
        """
        if not params:
            raise DatatypeError("missing params")
        return self.client._request(
            "data/delete",
            data={
                "collection": self.name,
                "params": params,
            },
        )

    def find(
        self,
        params: dict,
        expand: bool = False,
        page: int = 1,
        limit: int = 100,
    ):
        """Query a data collection matching a given set of search params.
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
        :raises: DatatypeError for invalid params.
        :returns: list of results as data dicts.
        """
        if not params:
            raise DatatypeError("missing params")
        params = {
            "collection": self.name,
            "expand": expand,
            "limit": limit,
            "paging": {"current_page": page, "results_per_page": limit},
            "params": params,
        }
        return self.client._request("data/get", data=params)

    def find_one(self, params: dict, expand: bool = False):
        """Query a data collection matching a given set of search params.
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

    def create(self, data: dict):
        """Creates new data for this datatype. Data dict must not
        contain an "id" key. Use update() to modify existing data.

            >>> sf = subfork.get_client()
            >>> sf.get_data(datatype).create(data)

        :param data: dictionary of key/value data to create.
        :raises: DatatypeError for invalid data.
        :returns: data creation results if successful, or None.
        """
        if data.get("id"):
            raise DatatypeError("data contains id")
        return self.client._request(
            "data/create",
            data={
                "collection": self.name,
                "data": util.sanitize_data(data),
            },
        )

    def upsert(self, data: dict):
        """Convenience method that upserts new data into for this datatype.

            >>> sf = subfork.get_client()
            >>> sf.get_data(datatype).upsert(data)

        :param data: dictionary of key/value data to insert.
        :returns: created data dict or None.
        """
        if data.get("id"):
            return self.update(data["id"], data)
        return self.create(data)

    def update(self, dataid: str, data: dict):
        """Updates existing data for a this datatype with a given id.

            >>> sf = subfork.get_client()
            >>> sf.get_data(datatype).update(dataid, datadict)

        :param dataid: id of the data to update.
        :param data: dictionary of key/value data to update.
        :raises: DatatypeError for invalid data.
        :returns: updated results if successful, or None.
        """
        if data.get("id") and data["id"] != dataid:
            raise DatatypeError("id mismatch")
        elif not data:
            raise DatatypeError("data is empty")
        return self.client._request(
            "data/update",
            data={
                "collection": self.name,
                "id": dataid,
                "data": util.sanitize_data(data),
            },
        )
