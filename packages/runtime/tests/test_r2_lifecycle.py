# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from coalitionkit_contracts import new_ulid

from .conftest import PUBLIC, World, accepted, error
from .test_r2 import pending


def test_query_requires_explicit_task_to_start_planning(world: World) -> None:
    task = world.need().accepted["payload"]["need_id"]
    ack = accepted(
        world.host.host_emit(
            "query",
            {
                "query_id": "unbound",
                "kind": "feasible",
                "subject": task,
            },
            {"audience": "participants", "participants": ["alice"]},
        )
    )
    assert world.host.state.tasks[task]["status"] == "open"
    accepted(
        world.alice.send("answer", {"query_id": "unbound", "result": "yes"}, ack.accepted["scope"])
    )
    world.query(task)
    assert world.host.state.tasks[task]["status"] == "negotiating"


def test_refused_commitment_is_superseded(world: World) -> None:
    task = world.need().accepted["payload"]["need_id"]
    identifier = pending(world, task)
    accepted(world.alice.decide("commitment", identifier, consent=False))
    assert world.host.state.subject("commitment", identifier)["status"] == "superseded"
    assert world.host.state.tasks[task]["status"] == "negotiating"
    error(world.alice.decide("commitment", identifier), "stale_subject")


def test_plan_deadline_and_no_deadline_on_replacement(world: World) -> None:
    task = world.need().accepted["payload"]["need_id"]
    proposal = world.propose(task).accepted["payload"]
    plan = proposal["plans"][0]["plan_id"]
    world.host.clock = lambda: "2026-10-29T12:00:01Z"
    error(world.alice.decide("plan", plan), "deadline_exceeded")
    assert world.host.state.tasks[task]["status"] == "negotiating"


def test_query_and_proposal_do_not_restart_proposed_task(world: World) -> None:
    task = world.need().accepted["payload"]["need_id"]
    proposal = world.propose(task).accepted["payload"]
    error(
        world.host.host_emit(
            "query",
            {
                "query_id": new_ulid(),
                "kind": "feasible",
                "subject": task,
                "task_id": task,
            },
            {"audience": "participants", "participants": ["alice"]},
        ),
        "stage_mismatch",
    )
    error(world.host.host_emit("propose", proposal, PUBLIC), "stage_mismatch")
