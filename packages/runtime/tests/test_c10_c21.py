# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from coalitionkit_contracts import new_ulid
from coalitionkit_runtime.store import Document

from .conftest import NOW, World, accepted, error


def offer(task: str) -> Document:
    return {
        "offer_id": new_ulid(),
        "target": {"kind": "task", "id": task},
        "capacity": 1,
        "cost": {"minutes": 5, "money": 0, "effort": "low"},
        "valid_until": NOW,
    }


def test_c10_two_task_statuses_are_independent(world: World) -> None:
    task_a = world.need().accepted["payload"]["need_id"]
    task_b = world.need().accepted["payload"]["need_id"]
    world.committed(task_a)
    world.committed(task_b, world.bob)
    accepted(world.alice.send("ripple", {"change": "Changed", "invalidates": [task_a]}))
    assert world.host.state.tasks[task_a]["status"] == "negotiating"
    assert world.host.state.tasks[task_b]["status"] == "committed"
    query = world.query(task_a)
    accepted(
        world.alice.send(
            "answer",
            {"query_id": query.accepted["payload"]["query_id"], "result": "yes"},
            query.accepted["scope"],
        )
    )
    accepted(world.alice.send("offer", offer(task_a)))
    accepted(
        world.alice.send(
            "match",
            {
                "match_id": "one",
                "task_id": task_a,
                "peer": "bob",
                "round": "setup",
                "blob": "AAAAAA",
                "reveal": "overlap",
            },
            causation_id=query.accepted["event_id"],
            scope=query.accepted["scope"],
        )
    )
    error(world.alice.send("done", {"task_id": task_a, "evidence": []}), "stage_mismatch")
    old_query = next(q for q in world.host.state.queries.values() if q["subject"] == task_b)
    error(
        world.bob.send("answer", {"query_id": old_query["query_id"], "result": "yes"}),
        "stage_mismatch",
    )
    accepted(world.bob.send("done", {"task_id": task_b, "evidence": []}))
    accepted(world.host.host_emit("dissolve", {"reason": "cancelled", "skills_written": []}))
    error(world.alice.send("done", {"task_id": task_a, "evidence": []}), "stage_mismatch")
    assert world.host.state.tasks[task_a]["status"] == "withdrawn"


def test_c21_charter_acceptance_and_suspended_commitments(world: World) -> None:
    task = world.need().accepted["payload"]["need_id"]
    commitment = world.committed(task)
    charter = world.host.state.charter
    accepted(world.host.host_emit("charter", charter, {"audience": "coalition"}))
    assert world.host.state.charter["revision"] == 2
    assert not world.host.state.accepted_charter("alice")
    assert world.host.state.subject("commitment", commitment)["suspended"]
    error(world.alice.send("done", {"task_id": task, "evidence": []}), "not_authorized")
    accepted(world.alice.decide("charter", world.host.coalition_id, 2))
    assert not world.host.state.subject("commitment", commitment)["suspended"]
    accepted(world.alice.send("done", {"task_id": task, "evidence": []}))
