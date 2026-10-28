# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
from coalitionkit_runtime.lifecycle import State
from coalitionkit_runtime.projector import derive_scope
from coalitionkit_runtime.steward import FakeSteward, Verdict
from coalitionkit_runtime.store import Document
from coalitionkit_vault.canary import Canaries
from coalitionkit_vault.store import Capacity, Facts, Vault

from coalitionkit_contracts import new_ulid, sign_envelope
from coalitionkit_contracts.payloads import QueryPayload

from .conftest import World, accepted, error
from .test_c10_c21 import offer


def test_c16_published_scope_vectors() -> None:
    path = Path(__file__).resolve().parents[3] / "spec/vectors/scope.json"
    vectors: dict[str, Any] = json.loads(path.read_text())
    for case in vectors["cases"]:
        state = State(new_ulid())
        for member in case["members"]:
            state.members[member] = {
                "roles_requested": [
                    role for role, holders in case["role_holders"].items() if member in holders
                ]
            }
        events: list[Document] = [
            {"scope": s["scope"], "on_behalf_of": s["owner"]} for s in case["sources"]
        ]
        assert derive_scope(state, events) == case["expected"], case["name"]


def test_c12_steward_redaction_is_durable_and_original_signature_survives(world: World) -> None:
    world.host.steward = FakeSteward(Verdict("redact", "remove-content", ("payload.content",)))
    result = accepted(world.alice.send("observe", {"source": "chat", "content": "protected"}))
    assert result.accepted["payload"]["content"] == "protected"
    world.host.steward = FakeSteward()
    assert "protected" not in json.dumps(world.host.view("bob"))
    replay = world.host.replay("bob", result.accepted["seq"] - 1)[0]
    assert replay["payload"]["redacted"] == ["payload.content"]
    from coalitionkit_contracts import verify_envelope

    verify_envelope(replay, world.host.private_key.public_key())
    verify_envelope(result.accepted, world.alice.agent.public_key())


@pytest.mark.parametrize("action", ["quarantine", "escalate"])
def test_c12_nonallow_verdicts_hold_delivery(world: World, action: str) -> None:
    verdict = Verdict("quarantine" if action == "quarantine" else "escalate", "hold")
    world.host.steward = FakeSteward(verdict)
    before = world.store.read(world.host.coalition_id)
    error(world.alice.send("observe", {"source": "chat", "content": "hold"}), "steward_blocked")
    assert world.store.read(world.host.coalition_id) == before


def test_c21_offers_only_count_at_current_charter(world: World) -> None:
    task = world.need().accepted["payload"]["need_id"]
    body = offer(task)
    accepted(world.alice.send("offer", body))
    assert world.host.state.offers[body["offer_id"]]["counted"]
    accepted(world.host.host_emit("charter", world.host.state.charter, {"audience": "coalition"}))
    assert not world.host.state.offers[body["offer_id"]]["counted"]
    accepted(world.alice.decide("charter", world.host.coalition_id, 2))
    assert world.host.state.offers[body["offer_id"]]["counted"]


def test_c20_invisible_targets_and_host_only_types(world: World) -> None:
    hidden = world.need({"audience": "participants", "participants": ["alice"]})
    task = hidden.accepted["payload"]["need_id"]
    error(world.bob.send("offer", offer(task)), "not_authorized")
    error(world.bob.send("ripple", {"change": "Changed", "invalidates": [task]}), "not_authorized")
    cases: list[tuple[str, Document]] = [
        ("charter", world.host.state.charter),
        ("query", {"query_id": "unknown", "kind": "feasible", "subject": task}),
        ("dissolve", {"reason": "cancelled", "skills_written": []}),
        ("receipt", {"coalition_id": world.host.coalition_id, "seq": 1, "head_hash": "0" * 64}),
        ("error", {"code": "not_authorized", "detail": {}, "ref": new_ulid()}),
    ]
    for kind, body in cases:
        error(world.alice.send(kind, body), "not_authorized")


def test_c14_malformed_event_id_and_bad_signature(world: World) -> None:
    event = world.alice.envelope("observe", {"source": "chat", "content": "okay"})
    event["event_id"] = []
    result = error(world.host.accept(event, world.alice.auth), "schema_invalid")
    assert isinstance(result["payload"]["ref"], str)
    event["event_id"] = new_ulid()
    event["sig"] = sign_envelope(event, world.bob.agent, "bob")
    error(world.host.accept(event, world.alice.auth), "bad_signature")


def test_planted_vault_content_never_enters_outputs(world: World) -> None:
    vault = Vault("alice")
    canaries = Canaries.plant(vault, 20)
    task = world.need().accepted["payload"]["need_id"]
    vault.put(task, Facts(capacities=(Capacity(7, "private-unit-name"),)))
    query = world.query(task)
    body = vault.answer(QueryPayload.model_validate(query.accepted["payload"])).to_wire()
    reply = accepted(world.alice.send("answer", body, query.accepted["scope"]))
    outputs = [
        world.store.read(world.host.coalition_id),
        asdict(world.host.state),
        world.host.view("alice"),
        world.host.view("observer"),
        reply.receipt,
    ]
    for output in outputs:
        assert not canaries.scan(output)
        assert "private-unit-name" not in json.dumps(output)


def test_c12_redaction_propagates_to_derived_sources(world: World) -> None:
    world.host.steward = FakeSteward(Verdict("redact", "hide", ("payload.description",)))
    source = accepted(world.alice.send("observe", {"source": "chat", "content": "source"}))
    world.host.steward = FakeSteward()
    need = accepted(
        world.host.host_emit(
            "need",
            {
                "description": "derived",
                "requirements": [],
                "window": {"start": "2026-10-28T12:00:00Z", "end": "2026-10-29T12:00:00Z"},
            },
            sources=[source.accepted["event_id"]],
        )
    )
    assert need.accepted["scope"]["redact"] == ["payload.description"]
    assert "derived" not in json.dumps(world.host.view("observer"))
