#!/usr/bin/env python
#
# Copyright (c) Subfork. All rights reserved.
#

try:
    import envstack

    envstack.init("subfork")

except ImportError as err:
    print("error initializing environment: %s" % err)

from subfork.client import Subfork
from subfork.util import get_client
