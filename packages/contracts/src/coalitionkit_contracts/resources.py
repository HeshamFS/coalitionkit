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


@cache
def checkout_root() -> Path | None:
    """The repository root when this code runs from a source checkout, None when installed."""
    module = Path(__file__).resolve()
    if module.parts[-5:-1] != ("packages", "contracts", "src", "coalitionkit_contracts"):
        return None
    root = module.parents[4]
    return root if (root / "spec" / "schemas").is_dir() else None


def spec_path(*parts: str) -> Path:
    """A checkout reads its own ``spec/``; an installed wheel reads the copy it was built with."""
    root = checkout_root()
    if root is not None:
        return root.joinpath("spec", *parts)
    return resource_path("coalitionkit_contracts", "data", "spec", *parts)
