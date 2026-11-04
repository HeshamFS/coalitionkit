# SPDX-License-Identifier: Apache-2.0
"""Acceptance test 5 over the real server: one big Coalition, and many Coalitions at once.

Every agent is a member with its own keys that talks to ``coalitionkit-server`` over A2A. Each
agent asks a model for its offer terms (scripted, or live for the agents named in ``live``),
offers on two tasks, and the deciders decide the Gardener's plan, which the Steward audits with
a model. SSE viewers on ``/v1/feed`` follow a sample of the agents; the events each one holds at
the end are compared with what the host shows it. Cost comes from the one meter every model call
of the server and of the agents goes through.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import httpx

from coalitionkit_contracts import new_ulid
from coalitionkit_edges.a2a.testing import free_port
from coalitionkit_gardener import build_propose, generate_plans
from coalitionkit_models import CostMeter, ModelGateway
from coalitionkit_models.gateway import ChatMessage

from .gateways import Kit, scripted_kit
from .harness import (
    FAR,
    PUBLIC,
    Document,
    HookChannel,
    Instance,
    Member,
    emitted,
    make_settings,
    new_need,
    provision,
)
from .metrics import Recorder
from .ripple import problem_from_state
from .ripple_server import arrivals_by_event
from .sse import ViewerPool

OFFERS_PER_AGENT = 2
#: The live Steward may answer escalate; a plan is offered again (a new audit) up to this often.
PROPOSE_ATTEMPTS = 3
LIVE_PROMPT = (
    "You are a scheduling agent in a shared-task group. Offer terms for one task. "
    'Answer with ONE JSON object only: {"minutes": <integer 10 to 120>, '
    '"money": <integer 1 to 20>}.'
)


@dataclass
class CohortResult:
    coalition_id: str
    agents: int
    events: int
    lost_events: int
    viewers: int
    viewer_lost: int
    decided: bool
    metered_micro_usd: int
    model_calls: int
    live_agents: int = 0
    live_unparsed: int = 0
    live_latencies: list[float] = field(default_factory=lambda: list[float]())


@dataclass
class Cohort:
    coalition: str
    names: list[str]
    members: dict[str, Member]


def terms(index: int, step: int) -> tuple[int, int]:
    """Scripted offer terms, the same shape as the in-process scale run."""
    return 30 + 10 * (index % 3), 3 + (index + step) % 5


async def live_terms(
    gateway: ModelGateway, coalition: str, name: str, result: CohortResult
) -> tuple[int, int]:
    message: ChatMessage = {"role": "user", "content": f"Task for {name}. Offer your terms."}
    system: ChatMessage = {"role": "system", "content": LIVE_PROMPT}
    started = time.perf_counter()
    done = await gateway.complete(
        "hosted_agent", [system, message], coalition_id=coalition, participant=name,
        reasoning_effort="minimal",
    )  # fmt: skip
    result.live_latencies.append(time.perf_counter() - started)
    found = re.search(r"\{.*?\}", done.text, flags=re.DOTALL)
    try:
        data: dict[str, Any] = json.loads(found.group(0)) if found else {}
        return max(10, min(120, int(data["minutes"]))), max(1, min(20, int(data["money"])))
    except (ValueError, KeyError, TypeError):
        result.live_unparsed += 1
        return 30, 5


def prepare(server: Instance, agents: int, admin: httpx.Client) -> Cohort:
    names = [f"a{i}" for i in range(agents)]
    coalition, members = provision(server.base, server.state, names, names[:2], admin)
    return Cohort(coalition, names, members)


async def run_cohort(
    server: Instance,
    cohort: Cohort,
    tasks: int,
    viewers: int,
    gate: asyncio.Semaphore,
    http: httpx.AsyncClient,
    pool: ViewerPool,
    recorder: Recorder,
    gateway: ModelGateway,
    scripted: ModelGateway,
    meter: CostMeter,
    live: frozenset[str] = frozenset(),
) -> CohortResult:
    host = server.host(cohort.coalition)
    acknowledged: set[str] = set()
    result = CohortResult(cohort.coalition, len(cohort.names), 0, 0, 0, 0, False, 0, 0)

    async def send(member: Member, envelope: Document) -> None:
        async with gate:
            started = time.perf_counter()
            await member.send(envelope)
            recorder.sample("send_s", time.perf_counter() - started)
        acknowledged.add(envelope["event_id"])

    async def join(member: Member) -> None:
        async with gate:
            await member.connect(http, server.state)
        await send(member, member.join_envelope())

    await asyncio.gather(*(join(m) for m in cohort.members.values()))
    revision = host.state.charter["revision"]
    await asyncio.gather(
        *(send(m, m.decision_envelope("charter", cohort.coalition, revision))
          for m in cohort.members.values())
    )  # fmt: skip
    for index in range(viewers):
        name = cohort.names[index]
        pool.add(f"{cohort.coalition}:{name}", name, server.base, cohort.members[name].token)
    ids = [new_need(host) for _ in range(tasks)]

    async def offers(index: int, name: str) -> None:
        member = cohort.members[name]
        for step in range(OFFERS_PER_AGENT):
            task = ids[(index + step) % tasks]
            if name in live:
                minutes, money = await live_terms(gateway, cohort.coalition, name, result)
            else:
                message: ChatMessage = {"role": "user", "content": f"offer for {name}"}
                await scripted.complete(
                    "hosted_agent", [message], coalition_id=cohort.coalition, participant=name
                )
                minutes, money = terms(index, step)
            await send(member, member.offer_envelope(task, minutes, money, f"{name}-{task}"))

    await asyncio.gather(*(offers(i, n) for i, n in enumerate(cohort.names)))
    plans = generate_plans(problem_from_state(host.state))
    if plans.plans:
        event = None
        for _ in range(PROPOSE_ATTEMPTS):
            proposal = build_propose(plans, deadline=FAR, proposal_set_id=new_ulid())
            reply = host.host_emit("propose", proposal.model_dump(mode="json"), PUBLIC)
            event = emitted(reply)
            recorder.count("propose_attempts")
            if event is not None:
                break
            payload = cast(Document, reply)["payload"]
            recorder.count(f"propose_refused_{payload['code']}")
            detail = cast(Document, payload.get("detail") or {})
            policy = detail.get("policy_id")
            if policy:
                recorder.count(f"propose_refused_by_{policy}")
        if event is not None:
            plan = str(event["payload"]["plans"][0]["plan_id"])
            for name in cohort.names[:2]:
                member = cohort.members[name]
                await send(member, member.decision_envelope("plan", plan, 1))
            result.decided = {t["status"] for t in host.state.tasks.values()} == {"decided"}
    await _finish(server, cohort, pool, acknowledged, result, meter)
    return result


async def _finish(
    server: Instance,
    cohort: Cohort,
    pool: ViewerPool,
    acknowledged: set[str],
    result: CohortResult,
    meter: CostMeter,
) -> None:
    host = server.host(cohort.coalition)
    mine = {k: v for k, v in pool.viewers.items() if k.startswith(cohort.coalition + ":")}
    until = time.monotonic() + 90
    while time.monotonic() < until and any(
        v.event_ids() != set(host.view(v.name)["events"]) for v in mine.values()
    ):
        await asyncio.sleep(0.25)
    stored = host.store.read(cohort.coalition)
    result.events = len(stored)
    result.lost_events = len(acknowledged - {e["event_id"] for e in stored})
    result.viewers = len(mine)
    result.viewer_lost = sum(
        len(set(host.view(v.name)["events"]) ^ v.event_ids()) for v in mine.values()
    )
    result.metered_micro_usd = meter.total(cohort.coalition)
    result.model_calls = sum(1 for r in meter.records if r.coalition_id == cohort.coalition)


def delta_latencies(pool: ViewerPool, channel: HookChannel, recorder: Recorder) -> None:
    """Server acceptance (its own stamp) to the delta that reached each sampled viewer."""
    stamps = {
        line["event_id"]: float(line["t"])
        for line in channel.lines()
        if line["stage"] == "persisted"
    }
    for viewer in pool.viewers.values():
        for event_id, arrived in arrivals_by_event(viewer).items():
            if event_id in stamps:
                took = arrived - stamps[event_id]
                recorder.sample("accept_to_delta_s", took)
                recorder.count("negative_latencies", int(took < 0))


def summarise(name: str, outcomes: list[CohortResult], recorder: Recorder) -> dict[str, Any]:
    recorder.count("coalitions", len(outcomes))
    recorder.count("agents_total", sum(o.agents for o in outcomes))
    recorder.count("events_total", sum(o.events for o in outcomes))
    recorder.count("lost_events", sum(o.lost_events for o in outcomes))
    recorder.count("viewers", sum(o.viewers for o in outcomes))
    recorder.count("viewer_lost_events", sum(o.viewer_lost for o in outcomes))
    recorder.count("coalitions_decided", sum(1 for o in outcomes if o.decided))
    recorder.count("model_calls", sum(o.model_calls for o in outcomes))
    recorder.value("cost_micro_usd_metered", sum(o.metered_micro_usd for o in outcomes))
    for outcome in outcomes:
        for seconds in outcome.live_latencies:
            recorder.sample("live_call_s", seconds)
    return recorder.result()


async def run_scale_server(
    directory: Path,
    *,
    agents: int,
    coalitions: int,
    coalition_agents: int,
    tasks: int,
    big_viewers: int,
    small_viewers: int,
    concurrency: int,
    live: int = 0,
    kit: Kit | None = None,
) -> dict[str, Any]:
    """One big Coalition, then ``coalitions`` small ones at once (``coalitions=0`` skips them).

    ``live`` names the first agents of the big Coalition that ask the model for terms; pass a
    live ``kit`` for them to reach the real model (the server's Steward uses it too).
    """
    live_run = kit is not None
    kit = kit or scripted_kit()
    #: Scripted agents never reach the model; their notional cost is metered apart in a live run.
    notional = scripted_kit() if live_run else kit
    meter, gateway, scripted = kit.meter, kit.agents, notional.agents
    settings = make_settings(f"sqlite:///{directory / 'host.db'}", directory, free_port())
    pool = ViewerPool()
    big_rec, small_rec, total = (
        Recorder("scale_big"),
        Recorder("scale_concurrent"),
        Recorder("scale"),
    )
    channel = HookChannel(directory / "hook")
    with Instance(settings, kit.gateway, channel) as server, httpx.Client(timeout=120) as admin:
        try:
            big = prepare(server, agents, admin)
            smalls = [prepare(server, coalition_agents, admin) for _ in range(coalitions)]
            limits = httpx.Limits(max_connections=None)
            async with httpx.AsyncClient(timeout=180, limits=limits) as http:
                first = await run_cohort(
                    server, big, tasks, big_viewers, asyncio.Semaphore(concurrency), http, pool,
                    big_rec, gateway, scripted, meter, frozenset(big.names[2 : 2 + live]),
                )  # fmt: skip
                first.live_agents = live
                gate = asyncio.Semaphore(concurrency)
                rest = await asyncio.gather(
                    *(
                        run_cohort(
                            server,
                            c,
                            tasks,
                            small_viewers,
                            gate,
                            http,
                            pool,
                            small_rec,
                            gateway,
                            scripted,
                            meter,
                        )
                        for c in smalls
                    )
                )
        finally:
            pool.close()
    outcomes = [first, *rest]
    delta_latencies(pool, channel, total)
    for seconds in big_rec.series("send_s") + small_rec.series("send_s"):
        total.sample("send_s", seconds)
    result = summarise("scale", outcomes, total)
    result["big"] = summarise("big", [first], big_rec)
    result["concurrent"] = summarise("concurrent", list(rest), small_rec) if rest else {}
    result["values"]["scripted_notional_micro_usd"] = (
        sum(r.cost_micro_usd for r in notional.meter.records) if live_run else 0
    )
    result["outcomes"] = [o.__dict__ | {"live_latencies": []} for o in outcomes]
    return result
