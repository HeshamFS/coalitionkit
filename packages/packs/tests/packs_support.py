# SPDX-License-Identifier: Apache-2.0
"""Helpers for the pack tests: fixture copies, a core catalog and a signing key."""

from __future__ import annotations

import shutil
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_surfaces import Catalog, load_catalog

FIXTURES = Path(__file__).parent / "fixtures"
CORE_CATALOG = Path(__file__).parents[2] / "surfaces" / "tests" / "fixtures" / "catalog.json"
CORE_VERSION = "0.1.0"


def core_catalog() -> Catalog:
    return load_catalog(CORE_CATALOG)


def copy_pack(name: str, target: Path) -> Path:
    dest = target / name
    shutil.copytree(FIXTURES / name, dest)
    return dest


def rewrite(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} not in {path}"
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")


def append(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as out:
        out.write(text)


def new_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()
