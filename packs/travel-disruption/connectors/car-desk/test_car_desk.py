# SPDX-License-Identifier: Apache-2.0
"""Checks for the car desk connector (uv run pytest packs/travel-disruption/connectors)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from google.protobuf.json_format import ParseDict

sys.path.insert(0, str(Path(__file__).parent))
import car_desk

SEED = bytes(range(32))


def test_signature_matches_the_reference_implementation() -> None:
    key = Ed25519PrivateKey.from_private_bytes(SEED)
    assert car_desk.public_key(SEED) == key.public_key().public_bytes_raw()
    assert car_desk.sign(SEED, b"seat") == key.sign(b"seat")


def test_card_verifies_under_the_hosts_card_check() -> None:
    from a2a.types import AgentCard

    from coalitionkit_edges.a2a.identity import card_keys, verify_card

    card = ParseDict(car_desk.build_card("https://desk.example.invalid", SEED), AgentCard())
    key = verify_card(card, card_keys(card).get)
    assert key.kid == "agent"


NEEDS: list[dict[str, Any]] = [
    {"destination": "Northgate", "party_size": 3, "latest_arrival": "2030-03-02T07:00:00Z"},
    {"destination": "Eastport", "party_size": 9, "latest_arrival": "2030-03-02T08:00:00Z"},
    {"destination": "Southfield", "party_size": 3, "latest_arrival": "2030-03-02T05:00:00Z"},
    {"destination": "Elsewhere", "party_size": 1, "latest_arrival": "2030-03-02T09:00:00Z"},
]


def test_offers_are_deterministic_and_only_for_seats_it_holds() -> None:
    first = car_desk.offers_for(NEEDS)
    assert first == car_desk.offers_for(NEEDS)
    assert [o["need"] for o in first] == [0]  # too large, too late, and unknown destinations skip
    assert first[0]["ext"]["price"] == "EUR 45.00" and not first[0]["needs_person"]


def test_a_need_drafted_from_a_sentence_gets_no_offer() -> None:
    sentence_need: dict[str, Any] = {"description": "get the group to the city by morning"}
    offers = car_desk.offers_for([sentence_need, NEEDS[0]])
    assert [o["need"] for o in offers] == [1]
