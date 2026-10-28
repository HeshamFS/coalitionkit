# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json

from coalitionkit_runtime.projector import derive_scope, patch
from coalitionkit_runtime.steward import FakeSteward, Verdict
from coalitionkit_vault.canary import Canaries

from coalitionkit_contracts import verify_envelope

from .conftest import World, accepted, error


def test_c11_scopes_redaction_and_first_projection(world: World) -> None:
    hidden = accepted(
        world.alice.send("observe", {"source": "chat", "content": "hidden"}, {"audience": "self"})
    )
    redacted = accepted(
        world.alice.send(
            "observe",
            {"source": "chat", "content": "redacted"},
            {"audience": "coalition", "redact": ["payload.content"]},
        )
    )
    public = accepted(world.alice.send("observe", {"source": "chat", "content": "public"}))
    initial = world.host.view("observer")
    assert "hidden" not in json.dumps(initial) and "redacted" not in json.dumps(initial)
    replay = world.host.replay("observer", hidden.accepted["seq"] - 1)
    assert set(replay[0]) == {"seq", "prev_hash", "hash"}
    assert replay[1]["type"] == "coalition.projection"
    assert replay[1]["sig"] != redacted.accepted["sig"]
    verify_envelope(replay[1], world.host.private_key.public_key())
    assert replay[2] == public.accepted
    assert patch(initial, initial) == []
    accepted(world.alice.send("observe", {"source": "chat", "content": "later"}))
    delta = patch(initial, world.host.view("observer"))
    assert delta[0]["value"] == world.host.view("observer")
    assert "hidden" not in json.dumps(delta)


def test_c11_proposal_is_viewer_specific(world: World) -> None:
    task = world.need().accepted["payload"]["need_id"]
    world.query(task)
    proposal = world.propose(task)
    alice = world.host.replay("alice", proposal.accepted["seq"] - 1)[0]
    bob = world.host.replay("bob", proposal.accepted["seq"] - 1)[0]
    assert alice["type"] == bob["type"] == "coalition.projection"
    assert alice["payload"]["payload"]["plans"][0]["assignments"]
    assert bob["payload"]["payload"]["plans"][0]["assignments"] == []


def test_c12_steward_before_commit_and_delivery(world: World) -> None:
    task = world.need().accepted["payload"]["need_id"]
    world.query(task)
    steward = FakeSteward(Verdict("block", "policy-test"))
    world.host.steward = steward
    before = world.store.read(world.host.coalition_id)
    error(
        world.host.host_emit(
            "propose",
            {
                "proposal_set_id": "blocked",
                "plans": [
                    {
                        "assignments": [{"task_id": task, "assignee": "alice"}],
                        "objective_scores": {},
                    }
                ],
            },
            {"audience": "coalition"},
        ),
        "steward_blocked",
    )
    assert len(steward.calls) == 1
    assert world.store.read(world.host.coalition_id) == before


def test_c16_derived_scope_intersection_and_widening(world: World) -> None:
    first = accepted(
        world.alice.send(
            "observe",
            {"source": "chat", "content": "one"},
            {"audience": "self", "redact": ["payload.content"]},
        )
    )
    second = accepted(
        world.bob.send("observe", {"source": "chat", "content": "two"}, {"audience": "self"})
    )
    scope = derive_scope(world.host.state, [first.accepted, second.accepted])
    assert scope == {"audience": "host", "redact": ["payload.content"]}
    error(
        world.host.host_emit(
            "need",
            {
                "description": "derived",
                "requirements": [],
                "window": {"start": "2026-10-28T12:00:00Z", "end": "2026-10-29T12:00:00Z"},
            },
            {"audience": "coalition"},
            sources=[first.accepted["event_id"]],
        ),
        "scope_violation",
    )


def test_canaries_never_enter_host_outputs(world: World) -> None:
    canaries = Canaries(tuple(f"private-canary-{i}" for i in range(20)))
    for value in canaries.values:
        error(
            world.alice.send("answer", {"query_id": "x", "result": "yes", "private": value}),
            "schema_invalid",
        )
    task = world.need().accepted["payload"]["need_id"]
    query = world.query(task)
    result = accepted(
        world.alice.send(
            "answer",
            {"query_id": query.accepted["payload"]["query_id"], "result": "yes"},
            query.accepted["scope"],
        )
    )
    from dataclasses import asdict

    assert not canaries.scan(world.store.read(world.host.coalition_id))
    assert not canaries.scan(asdict(world.host.state))
    assert not canaries.scan(world.host.view("observer"))
    assert not canaries.scan(result.receipt)
