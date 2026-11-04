# SPDX-License-Identifier: Apache-2.0
"""Installed data paths, including extraction for non-filesystem resource loaders."""

import atexit
from contextlib import ExitStack
from functools import cache
from importlib.resources import as_file, files
from pathlib import Path

_resources = ExitStack()
atexit.register(_resources.close)


@cache
def resource_path(package: str, *parts: str) -> Path:
    """Keep extracted resources alive until the process exits."""
    return _resources.enter_context(as_file(files(package).joinpath(*parts)))


def spec_path(*parts: str) -> Path:
    return resource_path("coalitionkit_contracts", "data", "spec", *parts)
