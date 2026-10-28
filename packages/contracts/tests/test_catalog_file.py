# SPDX-License-Identifier: Apache-2.0
"""The core A2UI catalog file: well-formed, typed, unique, generic."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
CATALOG = ROOT / "spec" / "catalog" / "coalitionkit-v0_9.json"
DENYLIST = ROOT / "tools" / "discipline-denylist.txt"
DOORS = {"wide", "compact", "message", "voice", "lens", "mcp-app", "push"}
TYPES = {
    "string",
    "number",
    "integer",
    "boolean",
    "datetime",
    "id",
    "enum",
    "binding",
    "subject",
    "scope",
    "child",
    "children",
    "array",
    "object",
    "any",
}
CONSENT = {
    "ConsentCard",
    "ApprovalButton",
    "OwnerSign",
    "ConsentSeal",
    "TensionCard",
    "CommitmentCard",
}


def load() -> dict[str, Any]:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def test_catalog_is_the_closed_v0_9_catalog() -> None:
    doc = load()
    assert doc["catalogId"] == "coalitionkit/v0_9"
    assert doc["a2ui"] == "v0.9"
    assert doc["rules"]["maxComponents"] == 500
    assert doc["rules"]["maxDepth"] == 24


def test_every_component_is_complete_and_typed() -> None:
    doc = load()
    for name, component in doc["components"].items():
        assert re.fullmatch(r"[A-Z][A-Za-z0-9]+", name), name
        assert component["doors"] and set(component["doors"]) <= DOORS, name
        assert component["states"], name
        assert component["family"] in doc["families"], name
        for prop, spec in component["props"].items():
            assert spec["type"] in TYPES, (name, prop)
            if spec["type"] == "enum":
                assert spec["values"], (name, prop)


def test_consent_components_bind_a_revisioned_subject() -> None:
    components = load()["components"]
    for name in CONSENT:
        props = components[name]["props"]
        assert props["subject"] == props["subject"] | {"type": "subject", "required": True}, name
        assert props["decision_deadline"]["type"] == "datetime", name


def test_no_vault_value_travels_in_a_tree() -> None:
    components = load()["components"]
    assert "value" not in components["PrivateField"]["props"]
    assert "value" not in components["AvailabilityGrid"]["props"]


def test_core_catalog_carries_no_discipline_words() -> None:
    words = [
        w.strip().lower()
        for w in DENYLIST.read_text(encoding="utf-8").splitlines()
        if w.strip() and not w.startswith("#")
    ]
    text = CATALOG.read_text(encoding="utf-8").lower()
    found = [w for w in words if re.search(rf"\b{re.escape(w)}\b", text)]
    assert not found, found
