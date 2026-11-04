# SPDX-License-Identifier: Apache-2.0
"""Checks for the simulated grocer connector (uv run pytest packs/supper-club/connectors)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from google.protobuf.json_format import ParseDict

sys.path.insert(0, str(Path(__file__).parent))
import grocer

SEED = bytes(range(32))


def test_signature_matches_the_reference_implementation() -> None:
    key = Ed25519PrivateKey.from_private_bytes(SEED)
    assert grocer.public_key(SEED) == key.public_key().public_bytes_raw()
    assert grocer.sign(SEED, b"basket") == key.sign(b"basket")


def test_card_verifies_and_says_simulated() -> None:
    from a2a.types import AgentCard

    from coalitionkit_edges.a2a.identity import card_keys, verify_card

    raw = grocer.build_card("https://grocer.example.invalid", SEED)
    card = ParseDict(raw, AgentCard())
    assert verify_card(card, card_keys(card).get).kid == "agent"
    assert "simulated" in raw["name"].lower() and "simulated" in raw["description"].lower()


NEEDS: list[dict[str, Any]] = [
    {"id": "n1", "title": "Fresh bread from a bakery nearby", "kind": "place"},
    {"id": "n2", "title": "Menu and shopping list for six", "kind": "list"},
    {"id": "n3", "title": "Book the oven for the roast", "kind": "schedule"},
]


def test_offers_only_on_the_shopping_need_and_are_deterministic() -> None:
    first = grocer.offers_for(NEEDS)
    assert first == grocer.offers_for(NEEDS)
    assert [o["need_id"] for o in first] == ["n2"]
    assert first[0]["hold"] == "slot-1" and first[0]["ext"]["simulated"] is True
    assert not first[0]["needs_person"]


def test_a_held_slot_is_not_offered_again() -> None:
    offers = grocer.offers_for(NEEDS, held=frozenset({"slot-1"}))
    assert offers[0]["hold"] == "slot-2"
    none_left = grocer.offers_for(NEEDS, held=frozenset({"slot-1", "slot-2", "slot-3"}))
    assert none_left == []


def test_a_slot_is_held_once_for_one_need() -> None:
    held: dict[str, str] = {}
    first = grocer.hold("slot-1", "n2", held)
    assert first["ok"] and first["state"] == "held"
    assert grocer.hold("slot-1", "n2", held) == first  # the same need asking again is a no-op
    assert grocer.hold("slot-1", "n9", held) == {"ok": False, "reason": "slot already held"}
    assert grocer.hold("slot-9", "n2", held)["ok"] is False


def test_the_order_summary_is_fixed_and_labelled_simulated() -> None:
    summary = grocer.order_summary("slot-1")
    assert summary == grocer.order_summary("slot-1")
    assert summary["total"] == "EUR 39.50"
    assert summary["items"][-1] == "Delivery 14:00-15:00: EUR 4.00"
    assert "simulated" in summary["title"].lower() and "simulated" in summary["note"].lower()
