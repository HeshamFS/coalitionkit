# SPDX-License-Identifier: Apache-2.0
"""Acceptance test 4 over the real server: a change in the middle of a 20-task plan.

Eight members hold a decided 20-task plan. One holder reports a change; the Gardener re-plans
only the ripple. Every member has an SSE viewer on ``/v1/feed``. For each event of the
re-negotiation the time from the host's acceptance to the ``STATE_DELTA`` that carries it is
measured at every viewer that may see it; viewers outside the ripple must get no delta at all.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from coalitionkit_contracts import new_ulid
from coalitionkit_edges.a2a import ReceivedError
from coalitionkit_edges.a2a.testing import free_port
from coalitionkit_gardener import (
    Change,
    build_propose,
    generate_plans,
    invalidated,
    replan,
    ripple_payload,
)

from .gateways import new_meter, scripted_gateway
from .harness import (
    FAR,
    HOST_ONLY,
    Document,
    Instance,
    Member,
    emit,
    make_settings,
    new_need,
    provision,
    scoped,
)
from .metrics import Recorder
from .ripple import CHAINS, CHANGED, TASKS, problem_from_state
from .sse import FeedViewer, ViewerPool

NAMES = [f"p{i}" for i in range(1, 13)]
DECIDERS = ["p1", "p2"]
#: p9 to p12 only watch: they offer on nothing, so the ripple never reaches them.
OFFERING = NAMES[2:8]


def specialist(index: int) -> str:
    """The member that offers the lowest price for task ``index``."""
    if index < 10:
        return "p3" if index % 2 == 0 else "p4"
    if index <= 14:
        return ("p5", "p6", "p7")[index % 3]
    return "p6" if index <= 17 else "p7"


@dataclass
class Mark:
    """An accepted event and the moment the host accepted it."""

    event_id: str
    at: float
    kind: str


@dataclass
class RippleServerResult:
    affected: frozenset[str]
    renegotiated: frozenset[str]
    proposed_after: frozenset[str]
    replanned: frozenset[str]
    decided: bool
    unchanged_assignments: bool
    audience: set[str]
    unaffected: set[str]
    unaffected_deltas: int
    unaffected_saw_new_events: int
    lost_events: int
    extra_events: int
    samples: int
    viewers: int
    metrics: dict[str, Any] = field(default_factory=lambda: dict[str, Any]())


def arrivals_by_event(viewer: FeedViewer) -> dict[str, float]:
    found: dict[str, float] = {}
    for arrival in list(viewer.arrivals):
        for op in arrival.ops:
            parts = str(op.get("path", "")).split("/")
            if len(parts) == 3 and parts[1] == "events" and op.get("op") == "add":
                found.setdefault(parts[2], arrival.at)
    return found


async def settle(pool: ViewerPool, server: Instance, coalition: str, timeout: float) -> None:
    """Wait until every viewer holds exactly the events the host shows its member."""
    host = server.host(coalition)
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        if all(v.event_ids() == set(host.view(v.name)["events"]) for v in pool.viewers.values()):
            return
        await asyncio.sleep(0.1)


async def seed(server: Instance, members: dict[str, Member], coalition: str) -> list[str]:
    host = server.host(coalition)
    tasks: list[str] = []
    for _ in range(TASKS):
        tasks.append(new_need(host))
    for index, task in enumerate(tasks):
        for name, member in members.items():
            if name in OFFERING:
                money = 2 if name == specialist(index) else 9 + (int(name[1:]) * 3 + index) % 5
                await member.send(member.offer_envelope(task, 30, money, f"{name}-{task}"))
    return tasks


async def run_ripple_server(directory: Path) -> RippleServerResult:
    recorder = Recorder("ripple_server")
    settings = make_settings(f"sqlite:///{directory / 'host.db'}", directory, free_port())
    gateway, _ = scripted_gateway(new_meter())
    pool = ViewerPool()
    with Instance(settings, gateway) as server, httpx.Client(timeout=60) as admin:
        try:
            coalition, members = provision(server.base, server.state, NAMES, DECIDERS, admin)
            host = server.host(coalition)
            async with httpx.AsyncClient(timeout=60) as http:
                for member in members.values():
                    await member.connect(http, server.state)
                    await member.send(member.join_envelope())
                revision = host.state.charter["revision"]
                for member in members.values():
                    await member.send(member.decision_envelope("charter", coalition, revision))
                tasks = await seed(server, members, coalition)
                plan_set = generate_plans(problem_from_state(host.state))
                assert plan_set.plans, "the scripted problem has a plan"
                proposal = build_propose(plan_set, deadline=FAR, proposal_set_id=new_ulid())
                event = emit(host, "propose", proposal.model_dump(mode="json"))
                plan = str(event["payload"]["plans"][0]["plan_id"])
                for name in DECIDERS:
                    await members[name].send(members[name].decision_envelope("plan", plan, 1))
                current = dict(plan_set.plans[0].assignments)
                before = {t: dict(v) for t, v in host.state.tasks.items()}
                assert {v["status"] for v in before.values()} == {"decided"}
                for name, member in members.items():
                    pool.add(name, name, server.base, member.token)
                return await renegotiate(
                    server, members, coalition, tasks, current, before, pool, recorder
                )
        finally:
            pool.close()


async def renegotiate(
    server: Instance,
    members: dict[str, Member],
    coalition: str,
    tasks: list[str],
    current: dict[str, str],
    before: dict[str, Document],
    pool: ViewerPool,
    recorder: Recorder,
) -> RippleServerResult:
    host = server.host(coalition)
    graph = {tasks[i]: [tasks[i - 1]] for chain in CHAINS for i in chain if i - 1 in chain}
    change = Change("task changed", tasks=frozenset({tasks[CHANGED]}))
    affected = invalidated(change, graph, current)
    holders = {current[t] for t in affected}
    audience = set(DECIDERS) | holders
    marks: list[Mark] = []
    head = len(host.store.read(coalition))
    t0 = time.perf_counter()

    reporter = members[sorted(holders)[0]]
    envelope = reporter.envelope(
        "ripple", ripple_payload(change, affected).model_dump(mode="json"), HOST_ONLY
    )
    try:
        await reporter.send(envelope)
    except ReceivedError as error:
        raise AssertionError(f"ripple refused: {error.code} {error.detail}") from error
    marks.append(Mark(envelope["event_id"], time.perf_counter(), "ripple"))
    for name in sorted(holders):
        for task in sorted(t for t in affected if current[t] == name):
            offer = members[name].offer_envelope(task, 120, 90, f"{name}-{task}", HOST_ONLY)
            await members[name].send(offer)
            marks.append(Mark(offer["event_id"], time.perf_counter(), "offer"))
    result = replan(problem_from_state(host.state), current, affected)
    assert not result.unresolved
    mine = {t: a for t, a in result.assignments.items() if t in result.replanned}
    audience |= set(mine.values())
    body: Document = {
        "proposal_set_id": new_ulid(),
        "decision_deadline": FAR,
        "plans": [
            {
                "assignments": [{"task_id": t, "assignee": a} for t, a in sorted(mine.items())],
                "objective_scores": {"variant": 0.0},
            }
        ],
    }
    event = emit(host, "propose", body, scoped(*audience))
    marks.append(Mark(event["event_id"], time.perf_counter(), "propose"))
    plan = str(event["payload"]["plans"][0]["plan_id"])
    for name in DECIDERS:
        decision = members[name].decision_envelope("plan", plan, 1, scope=scoped(*audience))
        await members[name].send(decision)
        marks.append(Mark(decision["event_id"], time.perf_counter(), "decide"))
    await settle(pool, server, coalition, 20.0)

    after = host.state
    events = host.store.read(coalition)
    new_ids = {e["event_id"] for e in events[head:]}
    unaffected = set(NAMES) - audience
    lost = extra = samples = unaffected_deltas = unaffected_saw = 0
    for name, viewer in pool.viewers.items():
        truth = set(host.view(name)["events"])
        lost += len(truth - viewer.event_ids())
        extra += len(viewer.event_ids() - truth)
        arrived = arrivals_by_event(viewer)
        if name in audience and viewer.deltas_after(t0):
            recorder.sample("change_to_surface_s", viewer.deltas_after(t0)[0].at - t0)
        if name in unaffected:
            unaffected_deltas += len(viewer.deltas_after(t0))
            unaffected_saw += len(viewer.event_ids() & new_ids)
        for mark in marks:
            if mark.event_id in truth and mark.event_id in arrived:
                recorder.sample("accept_to_delta_s", arrived[mark.event_id] - mark.at)
                recorder.sample(f"{mark.kind}_to_delta_s", arrived[mark.event_id] - mark.at)
                samples += 1
    recorder.count("viewers", len(pool.viewers))
    recorder.count("audience", len(audience))
    recorder.count("unaffected_viewers", len(unaffected))
    recorder.count("lost_events", lost)
    recorder.count("affected_tasks", len(affected))
    recorder.count("unaffected_deltas", unaffected_deltas)
    return RippleServerResult(
        affected=affected,
        renegotiated=frozenset(
            t for t, v in after.tasks.items() if v["revision"] != before[t]["revision"]
        ),
        proposed_after=frozenset(
            a["task_id"]
            for event in events[head:]
            if event["type"] == "coalition.propose"
            for p in event["payload"]["plans"]
            for a in p["assignments"]
        ),
        replanned=result.replanned,
        decided={v["status"] for v in after.tasks.values()} == {"decided"},
        unchanged_assignments=all(
            after.tasks[t]["assignee"] == current[t] for t in tasks if t not in affected
        ),
        audience=audience,
        unaffected=unaffected,
        unaffected_deltas=unaffected_deltas,
        unaffected_saw_new_events=unaffected_saw,
        lost_events=lost,
        extra_events=extra,
        samples=samples,
        viewers=len(pool.viewers),
        metrics=recorder.result(),
    )
