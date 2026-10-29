# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from coalitionkit_contracts import new_ulid, sign_consent
from coalitionkit_runtime.consents import ConsentLedger

from .conftest import World, accepted, error


def test_c15_two_deciders_first_answer_and_owner_signature(world: World) -> None:
    task = world.need().accepted["payload"]["need_id"]
    world.query(task)
    plan = world.propose(task).accepted["payload"]["plans"][0]["plan_id"]
    wrong = world.alice.decision("plan", plan)
    wrong["consent_sig"] = sign_consent(
        world.host.coalition_id, wrong, world.alice.agent, "alice", participant="alice"
    )
    error(world.alice.send("decide", wrong), "bad_signature")
    error(world.observer.decide("plan", plan), "not_a_decider")
    error(world.alice.decide("plan", plan, 2), "stale_subject")
    accepted(world.alice.decide("plan", plan))
    assert world.host.state.tasks[task]["status"] == "proposed"
    error(world.alice.decide("plan", plan), "not_authorized")
    # No connection is held by the durable ledger between answers.
    with world.store.transaction(world.host.coalition_id) as tx:
        assert (
            ConsentLedger(tx, world.host.coalition_id).tally(
                {"kind": "plan", "id": plan, "revision": 1}, ["alice", "bob"]
            )
            == "pending"
        )
    accepted(world.bob.decide("plan", plan))
    assert world.host.state.tasks[task]["status"] == "decided"


def test_c15_concurrent_answers_and_refusal(world: World) -> None:
    task = world.need().accepted["payload"]["need_id"]
    world.query(task)
    proposal = world.propose(task)
    plan = proposal.accepted["payload"]["plans"][0]["plan_id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(m.decide, "plan", plan) for m in (world.alice, world.bob)]
        results = [accepted(f.result()) for f in futures]
    assert len({r.accepted["seq"] for r in results}) == 2
    assert world.host.state.tasks[task]["status"] == "decided"
    accepted(world.alice.send("ripple", {"change": "Changed", "invalidates": [task]}))
    proposal_body = proposal.accepted["payload"]
    accepted(world.host.host_emit("propose", proposal_body, {"audience": "coalition"}))
    assert world.host.state.subject("plan", plan)["revision"] == 2
    error(world.bob.decide("plan", plan), "stale_subject")
    accepted(world.bob.decide("plan", plan, 2, False))
    assert world.host.state.tasks[task]["status"] == "negotiating"


def test_c15_pending_requests_superseded(world: World) -> None:
    old = world.host.state.charter
    accepted(world.host.host_emit("charter", old, {"audience": "coalition"}))
    accepted(world.host.host_emit("charter", old, {"audience": "coalition"}))
    with world.store.transaction(world.host.coalition_id) as tx:
        rows = tx.execute(
            "SELECT status FROM consents WHERE coalition_id = ? "
            "AND kind = 'charter' AND revision = 2",
            (world.host.coalition_id,),
        ).fetchall()
    assert len(rows) == 3 and all(row[0] == "superseded" for row in rows)


def test_c20_target_authorization(world: World) -> None:
    task = world.need().accepted["payload"]["need_id"]
    query = world.query(task)
    body = {"query_id": query.accepted["payload"]["query_id"], "result": "yes"}
    error(world.bob.send("answer", body), "not_authorized")
    accepted(world.alice.send("answer", body, query.accepted["scope"]))
    error(world.alice.send("answer", body, query.accepted["scope"]), "not_authorized")
    error(world.alice.send("need", world.need().accepted["payload"]), "not_authorized")
    plan = world.propose(task).accepted["payload"]["plans"][0]["plan_id"]
    accepted(world.alice.decide("plan", plan))
    accepted(world.bob.decide("plan", plan))
    commitment = new_ulid()
    body = {"commitment_id": commitment, "task_id": task, "status": "pending"}
    error(world.bob.send("commit", body), "not_authorized")
    accepted(world.alice.send("commit", body))
    error(world.alice.send("commit", {**body, "commitment_id": new_ulid()}), "not_authorized")
    error(world.bob.decide("commitment", commitment), "not_a_decider")
    accepted(world.alice.decide("commitment", commitment))
    error(world.bob.send("done", {"task_id": task, "evidence": []}), "not_authorized")
    error(
        world.bob.send("commit", {**body, "status": "withdrawn", "revision": 1}), "not_authorized"
    )


def test_c20_match_parties_and_rounds(world: World) -> None:
    need = world.need()
    task = need.accepted["payload"]["need_id"]
    world.query(task)
    body = {
        "match_id": "rounds",
        "task_id": task,
        "peer": "bob",
        "round": "setup",
        "blob": "AAAAAA",
        "reveal": "overlap",
    }
    setup = accepted(world.alice.send("match", body, causation_id=need.accepted["event_id"]))
    error(world.observer.send("match", {**body, "round": "request"}), "not_authorized")
    error(world.bob.send("match", {**body, "peer": "alice", "round": "response"}), "not_authorized")
    accepted(world.bob.send("match", {**body, "peer": "alice", "round": "request"}))
    error(world.alice.send("match", {**body, "round": "request"}), "not_authorized")
    accepted(world.alice.send("match", {**body, "round": "response"}))
    assert setup.accepted["payload"]["round"] == "setup"
