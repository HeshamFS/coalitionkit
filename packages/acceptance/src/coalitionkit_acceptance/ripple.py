# SPDX-License-Identifier: Apache-2.0
"""Acceptance test 4: a change in the middle of a 20-task plan touches only its ripple."""

from __future__ import annotations

import time
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from coalitionkit_contracts import new_ulid
from coalitionkit_contracts.payloads import Cost
from coalitionkit_gardener import (
    Change,
    Offer,
    Problem,
    Task,
    build_propose,
    generate_plans,
    invalidated,
    replan,
    ripple_payload,
)
from coalitionkit_runtime import SQLiteStore
from coalitionkit_runtime.lifecycle import State

from .arena import DEADLINE, PUBLIC, Arena, accepted
from .metrics import Recorder
from .watch import Viewer, check_log

TASKS = 20
MEMBERS = ("ana", "ben", "cho", "dee")
SHARES = {"ana": 2, "ben": 1, "cho": 1, "dee": 1}
#: Two dependency chains; the change lands on task 10, in the middle of the second chain.
CHAINS = (range(0, 5), range(8, 15))
CHANGED = 10


@dataclass(frozen=True)
class RippleResult:
    affected: frozenset[str]
    replanned: frozenset[str]
    renegotiated: frozenset[str]
    proposed_after: frozenset[str]
    unchanged_assignments: bool
    final_status: dict[str, str]
    viewers_lost: int
    metrics: dict[str, Any]


def problem_from_state(state: State) -> Problem:
    """The planning problem as the Coalition's own log describes it (counted offers only)."""
    tasks = tuple(Task(task_id) for task_id in sorted(state.tasks))
    offers = tuple(
        Offer(item["owner"], item["target"]["id"], Cost.model_validate(item["cost"]))
        for item in state.offers.values()
        if item.get("counted")
    )
    return Problem(
        tasks, offers, {m: SHARES.get(m, 1) for m in state.members}, max_ratio=Fraction(7)
    )


def run_ripple() -> RippleResult:
    recorder = Recorder("ripple")
    store = SQLiteStore()
    arena = Arena.open(store, deciders=["ana", "ben"])
    host = arena.host
    for name in MEMBERS:
        arena.enroll(name)
    viewers = {name: Viewer(host, name) for name in MEMBERS}
    tasks = [arena.need() for _ in range(TASKS)]
    prices = {"ana": 3, "ben": 4, "cho": 5, "dee": 6}
    for index, task in enumerate(tasks):
        for name in MEMBERS:
            cost = (30 + 10 * (index % 3), prices[name] + index % 4)
            accepted(arena.members[name].offer(task, *cost))
    problem = problem_from_state(host.state)
    plan_set = generate_plans(problem)
    assert plan_set.plans, "the scripted problem has a plan"
    proposal = build_propose(plan_set, deadline=DEADLINE, proposal_set_id=new_ulid())
    reply = accepted(host.host_emit("propose", proposal.model_dump(mode="json"), PUBLIC))
    plan = reply.accepted["payload"]["plans"][0]["plan_id"]
    arena.decide_all("plan", plan)
    current = dict(plan_set.plans[0].assignments)
    before = {t: dict(v) for t, v in host.state.tasks.items()}
    assert {v["status"] for v in before.values()} == {"decided"}

    graph = {tasks[i]: [tasks[i - 1]] for chain in CHAINS for i in chain if i - 1 in chain}
    change = Change("task 10 changed", tasks=frozenset({tasks[CHANGED]}))
    affected = invalidated(change, graph, current)
    head = len(arena.events())

    started = time.perf_counter()
    accepted(
        arena.members["ana"].send(
            "ripple", ripple_payload(change, affected).model_dump(mode="json")
        )
    )
    recorder.sample("ripple_ack_s", time.perf_counter() - started)
    for name in MEMBERS:
        host.view(name)
        recorder.sample("projection_s", time.perf_counter() - started)
    for viewer in viewers.values():
        viewer.pump()
        recorder.sample("bus_delivery_s", time.perf_counter() - started)

    # The holders of the changed work now ask for more; the Gardener re-plans only the ripple.
    holder = {current[task] for task in affected}
    for name in sorted(holder):
        for task in sorted(affected):
            if current[task] == name:
                accepted(arena.members[name].offer(task, 120, 90, f"{name}-{task}"))
    result = replan(problem_from_state(host.state), current, affected)
    assert not result.unresolved
    mine = {t: a for t, a in result.assignments.items() if t in result.replanned}
    plan_ids = arena.propose(mine)
    arena.decide_all("plan", plan_ids[0])

    after = host.state
    events = arena.events()
    proposed_after = frozenset(
        a["task_id"]
        for event in events[head:]
        if event["type"] == "coalition.propose"
        for p in event["payload"]["plans"]
        for a in p["assignments"]
    )
    renegotiated = frozenset(
        t for t, v in after.tasks.items() if v["revision"] != before[t]["revision"]
    )
    unchanged = all(
        result.assignments[t] == current[t] for t in tasks if t not in affected
    ) and all(after.tasks[t]["assignee"] == current[t] for t in tasks if t not in affected)
    for viewer in viewers.values():
        viewer.pump()
    lost = sum(viewer.lost(len(events)) for viewer in viewers.values())
    recorder.count("events", check_log(host))
    recorder.count("tasks", TASKS)
    recorder.count("affected_tasks", len(affected))
    recorder.count("lost_events", lost)
    arena.close()
    return RippleResult(
        affected=affected,
        replanned=result.replanned,
        renegotiated=renegotiated,
        proposed_after=proposed_after,
        unchanged_assignments=unchanged,
        final_status={t: v["status"] for t, v in after.tasks.items()},
        viewers_lost=lost,
        metrics=recorder.result(),
    )
