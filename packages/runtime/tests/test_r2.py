# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_contracts import (
    SignatureError,
    check_receipts,
    genesis_hash,
    new_ulid,
    public_key_to_jwk,
    sign_owner_proof,
    verify_chain,
    verify_projection,
    verify_receipt,
)
from coalitionkit_runtime import Acknowledgement
from coalitionkit_runtime.store import Document

from .conftest import NOW, PUBLIC, Member, World, accepted, error


def join_body(member: Member) -> Document:
    jwk = public_key_to_jwk(member.owner.public_key(), member.name + "-owner")
    return {
        "card_url": member.auth.card_url,
        "owner_key": jwk,
        "owner_proof": sign_owner_proof(
            member.host.coalition_id, member.name, member.auth.card_url, jwk, member.owner
        ),
        "roles_requested": ["member"],
        "surfaces": [],
        "vault": "local",
    }


def newcomer(world: World, name: str = "new") -> Member:
    member = Member(world.host, name, Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate())
    world.host.pin_card(member.auth, member.agent.public_key(), name)
    return member


def test_invitation_required_and_leave_is_final(world: World) -> None:
    member = newcomer(world)
    error(member.send("join", join_body(member)), "not_authorized")
    world.host.invite(member.auth)
    accepted(member.send("join", join_body(member)))
    assert isinstance(member.send("leave", {}), Acknowledgement)
    error(member.send("join", join_body(member)), "not_authorized")


def test_owner_key_cannot_be_shared_even_after_leave(world: World) -> None:
    member = newcomer(world)
    member.owner = world.alice.owner
    world.host.invite(member.auth)
    error(member.send("join", join_body(member)), "not_authorized")
    assert isinstance(world.alice.send("leave", {}), Acknowledgement)
    error(member.send("join", join_body(member)), "not_authorized")
    assert "new" not in world.host.state.members


@pytest.mark.parametrize(
    "scope, form",
    [
        (PUBLIC, "coalition.observe"),
        ({"audience": "coalition", "redact": ["payload.content"]}, "coalition.projection"),
        ({"audience": "host"}, None),
    ],
)
def test_ack_and_duplicate_obey_scope(world: World, scope: Document, form: str | None) -> None:
    event = world.alice.envelope("observe", {"source": "chat", "content": "secret"}, scope)
    first = world.host.accept(event, world.alice.auth)
    assert isinstance(first, Acknowledgement)
    second = world.host.accept(event, world.alice.auth)
    assert isinstance(second, Acknowledgement)
    for reply in (first, second):
        if form is None:
            assert reply.accepted is None
        else:
            assert reply.accepted is not None and reply.accepted["type"] == form
            if form == "coalition.projection":
                assert "content" not in reply.accepted["payload"]["payload"]
                verify_projection(reply.accepted, world.host.private_key.public_key())
    assert first.receipt == second.receipt


def test_projected_replay_verifies_and_rejects_forgery(world: World) -> None:
    ack = accepted(
        world.alice.send(
            "observe",
            {"source": "chat", "content": "secret"},
            {"audience": "coalition", "redact": ["payload.content"]},
        )
    )
    replay = world.host.replay("bob")
    key = world.host.private_key.public_key()
    genesis = genesis_hash(world.host.coalition_id, world.host.card_url, NOW)
    assert verify_chain(replay, genesis, key) == len(replay)
    receipts = [verify_receipt(ack.receipt, key)]
    check_receipts(replay, receipts, key)
    forged = deepcopy(replay)
    forged[-1]["payload"]["source"]["hash"] = "0" * 64
    with pytest.raises(SignatureError):
        verify_chain(forged, genesis, key)
    with pytest.raises(SignatureError):
        check_receipts(forged, receipts, key)


def tension(world: World, task: str) -> str:
    result = accepted(
        world.host.host_emit(
            "tension",
            {
                "task_ids": [task],
                "options": [
                    {"option_id": "a", "summary": "First"},
                    {"option_id": "b", "summary": "Second"},
                ],
                "tradeoffs": [],
                "deciders": ["alice", "bob"],
                "decision_deadline": "2026-10-28T13:00:00Z",
            },
            PUBLIC,
        )
    )
    assert result.accepted is not None
    return result.accepted["payload"]["tension_id"]


def test_split_consensus_replans(world: World) -> None:
    task = world.need().accepted["payload"]["need_id"]
    identifier = tension(world, task)
    for member, choice in [(world.alice, "a"), (world.bob, "b")]:
        accepted(
            member.send("decide", member.decision("tension_option", identifier, choice=choice))
        )
    assert world.host.state.tasks[task]["status"] == "negotiating"


def pending(world: World, task: str) -> str:
    plan = world.propose(task).accepted["payload"]["plans"][0]["plan_id"]
    accepted(world.alice.decide("plan", plan))
    accepted(world.bob.decide("plan", plan))
    identifier = new_ulid()
    accepted(
        world.alice.send(
            "commit", {"commitment_id": identifier, "task_id": task, "status": "pending"}
        )
    )
    return identifier


@pytest.mark.parametrize("approved", [False, True])
def test_replan_supersedes_commitment_and_closes_requests(world: World, approved: bool) -> None:
    task = world.need().accepted["payload"]["need_id"]
    identifier = pending(world, task)
    if approved:
        accepted(world.alice.decide("commitment", identifier))
    accepted(world.alice.send("ripple", {"change": "Changed", "invalidates": [task]}))
    assert world.host.state.subject("commitment", identifier)["status"] == "superseded"
    with world.store.transaction(world.host.coalition_id) as tx:
        rows = tx.execute(
            "SELECT status FROM consents WHERE subject_id = ?", (identifier,)
        ).fetchall()
    assert rows and all(row[0] != "pending" for row in rows)
    replacement = pending(world, task)
    assert replacement != identifier
    assert world.host.state.tasks[task]["status"] == "decided"


def test_pending_withdrawal_and_id_reuse(world: World) -> None:
    task = world.need().accepted["payload"]["need_id"]
    identifier = pending(world, task)
    accepted(
        world.alice.send(
            "commit",
            {"commitment_id": identifier, "task_id": task, "status": "withdrawn", "revision": 1},
        )
    )
    assert world.host.state.tasks[task]["status"] == "negotiating"
    plan = world.propose(task).accepted["payload"]["plans"][0]["plan_id"]
    accepted(world.alice.decide("plan", plan))
    accepted(world.bob.decide("plan", plan))
    error(
        world.alice.send(
            "commit", {"commitment_id": identifier, "task_id": task, "status": "pending"}
        ),
        "not_authorized",
    )


def test_lazy_expiry_rejects_late_decision(world: World) -> None:
    task = world.need().accepted["payload"]["need_id"]
    identifier = tension(world, task)
    world.host.clock = lambda: "2026-10-28T13:00:01Z"
    assert world.host.state.tasks[task]["status"] == "negotiating"
    error(
        world.alice.send("decide", world.alice.decision("tension_option", identifier, choice="a")),
        "deadline_exceeded",
    )
    assert not world.host.state.subject("tension_option", identifier)["answers"]


def test_deciding_a_plan_supersedes_its_siblings(world: World) -> None:
    task = world.need().accepted["payload"]["need_id"]
    proposal = world.propose(task).accepted["payload"]
    accepted(world.alice.send("ripple", {"change": "Changed", "invalidates": [task]}))
    other = deepcopy(proposal["plans"][0])
    other["plan_id"] = new_ulid()
    proposal["plans"].append(other)
    accepted(world.host.host_emit("propose", proposal, PUBLIC))
    chosen = proposal["plans"][0]["plan_id"]
    accepted(world.alice.decide("plan", chosen, 2))
    accepted(world.bob.decide("plan", chosen, 2))
    assert world.host.state.subject("plan", other["plan_id"])["status"] == "superseded"


def test_match_cannot_change_task(world: World) -> None:
    first = world.need().accepted["payload"]["need_id"]
    second = world.need().accepted["payload"]["need_id"]
    world.query(first)
    world.query(second)
    body = {
        "match_id": "bound",
        "task_id": first,
        "peer": "bob",
        "round": "setup",
        "blob": "",
        "reveal": "overlap",
    }
    accepted(world.alice.send("match", body))
    error(
        world.alice.send("match", {**body, "round": "request", "task_id": second}), "not_authorized"
    )


def test_commit_ack_is_viewer_specific_including_duplicate(world: World) -> None:
    task = world.need().accepted["payload"]["need_id"]
    plan = world.propose(task).accepted["payload"]["plans"][0]["plan_id"]
    accepted(world.alice.decide("plan", plan))
    accepted(world.bob.decide("plan", plan))
    event = world.alice.envelope(
        "commit", {"commitment_id": new_ulid(), "task_id": task, "status": "pending"}
    )
    for _ in range(2):
        reply = accepted(world.host.accept(event, world.alice.auth))
        assert reply.accepted["type"] == "coalition.projection"
        assert reply.accepted["payload"]["payload"]["revision"] == 1


def test_replan_closes_task_consent_and_superseded_decision_is_stale(world: World) -> None:
    task = world.need().accepted["payload"]["need_id"]
    identifier = pending(world, task)
    accepted(world.alice.send("ripple", {"change": "Changed", "invalidates": [task]}))
    with world.store.transaction(world.host.coalition_id) as tx:
        rows = tx.execute(
            "SELECT status FROM consents WHERE subject_id IN (?, ?)", (task, identifier)
        ).fetchall()
    assert rows and all(row[0] != "pending" for row in rows)
    error(world.alice.decide("commitment", identifier), "stale_subject")


def test_expired_read_closes_requests(world: World) -> None:
    task = world.need().accepted["payload"]["need_id"]
    identifier = tension(world, task)
    world.host.clock = lambda: "2026-10-28T13:00:01Z"
    world.host.view("alice")
    with world.store.transaction(world.host.coalition_id) as tx:
        rows = tx.execute(
            "SELECT status FROM consents WHERE subject_id = ?", (identifier,)
        ).fetchall()
    assert rows and all(row[0] != "pending" for row in rows)
