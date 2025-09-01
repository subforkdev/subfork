#!/usr/bin/env python
#
# Copyright (c) Subfork. All rights reserved.
#

import codecs
import os
import sys

from setuptools import find_packages, setup

if sys.version_info < (3, 6):
    raise RuntimeError("Subfork requires Python 3.6+")

here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    return codecs.open(os.path.join(here, *parts), "r").read()


exec(read("lib", "subfork", "version.py"))


setup(
    name="subfork",
    description="Subfork Python API",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    author="Subfork",
    author_email="help@subfork.com",
    url="https://github.com/subforkdev/subfork",
    version=__version__,
    license="BSD 3-Clause License",
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    package_dir={"": "lib"},
    packages=find_packages("lib"),
    entry_points={
        "console_scripts": [
            "subfork = subfork.cli:main",
        ],
    },
    install_requires=[
        "jsmin>=3.0.1",
        "psutil>=5.9.3",
        "PyYAML>=5.4",
        "requests>=2.25.1",
        "urllib3>=1.26.3",
    ],
    python_requires=">=3.6",
    zip_safe=False,
)
