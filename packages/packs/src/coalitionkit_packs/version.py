# SPDX-License-Identifier: Apache-2.0
"""The ``core`` range of a pack, such as ``>=0.1,<0.2``, checked against a core version."""

from __future__ import annotations

import operator
import re
from collections.abc import Callable
from importlib import metadata

_NUM = re.compile(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?")
_CLAUSE = re.compile(r"^(>=|<=|==|!=|>|<)\s*(\d+(?:\.\d+){0,2})$")
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")


Triple = tuple[int, int, int]
_OPS: dict[str, Callable[[Triple, Triple], bool]] = {
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    "<": operator.lt,
}


def _tuple(text: str) -> tuple[int, int, int]:
    match = _NUM.match(text.strip())
    if match is None:
        raise ValueError(f"not a version: {text!r}")
    a, b, c = (int(g) if g else 0 for g in match.groups())
    return (a, b, c)


def parse_range(text: str) -> list[tuple[str, tuple[int, int, int]]]:
    clauses: list[tuple[str, tuple[int, int, int]]] = []
    for raw in text.split(","):
        match = _CLAUSE.match(raw.strip())
        if match is None:
            raise ValueError(f"bad clause {raw.strip()!r}; use forms like >=0.1,<0.2")
        clauses.append((match.group(1), _tuple(match.group(2))))
    return clauses


def in_range(version: str, text: str) -> bool:
    """True when the release part of ``version`` (pre-release tags are ignored) fits."""
    current = _tuple(version)
    return all(_OPS[op](current, bound) for op, bound in parse_range(text))


def core_version() -> str:
    """The installed core version (the contracts package carries it)."""
    return metadata.version("coalitionkit-contracts")
