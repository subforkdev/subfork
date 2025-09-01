#!/usr/bin/env python
#
# Copyright (c) Subfork. All rights reserved.
#

try:
    import envstack

    envstack.init("subfork")

except Exception as err:
    print("Could not initialize envstack:", err)

from subfork.client import Subfork  # noqa: F401
from subfork.util import get_client  # noqa: F401
