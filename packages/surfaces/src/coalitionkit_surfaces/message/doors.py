# SPDX-License-Identifier: Apache-2.0
"""Which components of the catalog render on the message door."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

MESSAGE_DOOR = "message"

Doors = Mapping[str, frozenset[str]]


def load_doors(path: str | Path) -> dict[str, frozenset[str]]:
    """Read ``{component: doors}`` from the catalog file (each component lists its ``doors``)."""
    data: Any = json.loads(Path(path).read_text(encoding="utf-8"))
    whole = cast(dict[str, Any], data) if isinstance(data, dict) else {}
    specs: Any = whole.get("components")
    if not isinstance(specs, dict):
        raise ValueError("catalog file needs a components object")
    doors: dict[str, frozenset[str]] = {}
    for name, spec in cast(dict[str, Any], specs).items():
        body = cast(dict[str, Any], spec) if isinstance(spec, dict) else {}
        listed: Any = body.get("doors", [])
        if not isinstance(listed, list):
            raise ValueError(f"component {name}: doors must be a list")
        doors[name] = frozenset(str(door) for door in cast(list[Any], listed))
    return doors


def on_message_door(doors: Doors, component: str) -> bool:
    return MESSAGE_DOOR in doors.get(component, frozenset())
