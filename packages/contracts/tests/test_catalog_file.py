# SPDX-License-Identifier: Apache-2.0
"""The core A2UI catalog file: well-formed, unique, generic."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
CATALOG = ROOT / "spec" / "catalog" / "coalitionkit-v0_9.json"
DENYLIST = ROOT / "tools" / "discipline-denylist.txt"
DOORS = {"wide", "compact", "message", "voice", "lens", "mcp-app", "push"}


def load() -> dict[str, Any]:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def test_catalog_is_the_closed_v0_9_catalog() -> None:
    doc = load()
    assert doc["catalogId"] == "coalitionkit/v0_9"
    assert doc["a2ui"] == "v0.9"
    assert doc["rules"]["maxComponents"] == 500
    assert doc["rules"]["maxDepth"] == 24


def test_components_are_unique_and_complete() -> None:
    components = load()["components"]
    names = [c["name"] for c in components]
    assert len(names) == len(set(names))
    for component in components:
        assert re.fullmatch(r"[A-Z][A-Za-z0-9]+", component["name"]), component["name"]
        assert component["doors"], component["name"]
        assert set(component["doors"]) <= DOORS, component["name"]
        assert isinstance(component["props"], dict), component["name"]
        assert component["states"], component["name"]
        assert component["family"] in load()["families"], component["name"]


def test_core_catalog_carries_no_discipline_words() -> None:
    words = [
        w.strip().lower()
        for w in DENYLIST.read_text(encoding="utf-8").splitlines()
        if w.strip() and not w.startswith("#")
    ]
    text = CATALOG.read_text(encoding="utf-8").lower()
    found = [w for w in words if re.search(rf"\b{re.escape(w)}\b", text)]
    assert not found, found
