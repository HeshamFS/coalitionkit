# SPDX-License-Identifier: Apache-2.0
"""One valid example per message type, shared by the tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

COALITION_ID = "01M4XRC000000G40R40M30E209"
EVENT_ID = "01M4XRC0Z8185GR38E1W8124GK"
OTHER_ID = "01M4XRC1J00000000000000000"

COST: dict[str, Any] = {"minutes": 90, "money": 2500, "effort": "medium"}
WINDOW: dict[str, Any] = {"start": "2026-11-02T09:00:00Z", "end": "2026-11-02T17:00:00+01:00"}

PAYLOADS: dict[str, dict[str, Any]] = {
    "coalition.charter": {
        "goal": "Find two hours next week when all three are free.",
        "roles": [{"id": "organizer", "required": True}, {"id": "member"}],
        "rules": ["no private data leaves a vault"],
        "deadline": "2026-11-05T12:00:00Z",
        "pack": {"name": "scheduling", "version": "0.1.0"},
        "budget": {"amount": 10000, "currency": "EUR"},
        "deciders": ["p1"],
        "version": 2,
    },
    "coalition.join": {
        "card_url": "https://agents.example.org/p2/card.json",
        "owner_proof": "eyJhbGciOiJFZERTQSJ9..c2ln",
        "roles_requested": ["member"],
        "surfaces": ["web", "mcp_app"],
        "vault": "local",
    },
    "coalition.leave": {"reason": "no longer available"},
    "coalition.observe": {
        "source": "voice",
        "content": "the room is free on Wednesday",
        "evidence_ref": "clip-17",
    },
    "coalition.need": {
        "need_id": "n-1",
        "description": "A room for two hours",
        "requirements": ["seats >= 3"],
        "window": WINDOW,
    },
    "coalition.offer": {
        "offer_id": "o-1",
        "target": {"kind": "need", "id": "n-1"},
        "capacity": 2,
        "cost": COST,
        "valid_until": "2026-11-02T18:00:00.500Z",
    },
    "coalition.query": {
        "query_id": "q-1",
        "kind": "availability",
        "subject": "n-1",
        "deadline_ms": 10000,
    },
    "coalition.answer": {"query_id": "q-1", "result": COST},
    "coalition.match": {
        "match_id": "m-1",
        "round": "request",
        "blob": "AAECAwQFBgc_-w",
        "reveal": "overlap",
    },
    "coalition.propose": {
        "proposal_set_id": "ps-1",
        "plans": [
            {
                "plan_id": "plan-a",
                "revision": 1,
                "assignments": [{"task_id": "t-1", "assignee": "p2"}],
                "objective_scores": {"cost": 0.25, "speed": 1.5},
            }
        ],
    },
    "coalition.tension": {
        "tension_id": "tn-1",
        "revision": 3,
        "options": [
            {"option_id": "a", "summary": "Wednesday afternoon"},
            {"option_id": "b", "summary": "Thursday morning"},
        ],
        "tradeoffs": ["a is cheaper", "b is quieter"],
        "deciders": ["p1", "p2"],
    },
    "coalition.decide": {
        "subject": {"kind": "plan", "id": "plan-a", "revision": 1},
        "choice": "plan-a",
        "consent": True,
    },
    "coalition.commit": {
        "commitment_id": "c-1",
        "task_id": "t-1",
        "status": "pending",
        "revision": 1,
    },
    "coalition.ripple": {"change": "room closed on Wednesday", "invalidates": ["t-1", "t-2"]},
    "coalition.done": {
        "task_id": "t-1",
        "evidence": [{"kind": "document", "ref": "doc-9", "verified_by": "steward"}],
    },
    "coalition.dissolve": {"reason": "completed", "skills_written": ["skill-1"]},
    "coalition.error": {
        "code": "rate_limited",
        "detail": {"message": "slow down", "retry_after_ms": 500},
        "ref": EVENT_ID,
    },
}

SCOPE: dict[str, Any] = {
    "audience": "participants",
    "participants": ["p2", "p5"],
    "roles": [],
    "redact": ["payload.window"],
}


def make_envelope(message_type: str = "coalition.offer", **overrides: Any) -> dict[str, Any]:
    """A valid envelope (signature is a placeholder unless a test signs it)."""
    envelope: dict[str, Any] = {
        "ext_version": "0.1",
        "coalition_id": COALITION_ID,
        "event_id": EVENT_ID,
        "type": message_type,
        "sender": "https://agents.example.org/p2/card.json",
        "on_behalf_of": "p2",
        "scope": {"audience": "coalition"},
        "causation_id": OTHER_ID,
        "correlation_id": OTHER_ID,
        "payload": PAYLOADS[message_type],
        "sig": "placeholder",
    }
    envelope.update(overrides)
    return envelope


REPO = Path(__file__).resolve().parents[3]


def load_vector(name: str) -> dict[str, Any]:
    """Load a shared test vector file from spec/vectors."""
    data: dict[str, Any] = json.loads((REPO / "spec" / "vectors" / name).read_text("utf-8"))
    return data
