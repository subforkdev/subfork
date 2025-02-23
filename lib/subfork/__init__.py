#!/usr/bin/env python
#
# Copyright (c) Subfork. All rights reserved.
#

try:
    import envstack

    envstack.init("subfork")

except ImportError:
    print("envstack is not installed: `pip install -U envstack`")

from subfork.client import Subfork
from subfork.util import get_client
