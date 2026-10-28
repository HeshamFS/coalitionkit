# SPDX-License-Identifier: Apache-2.0
"""Acceptance test 5: many scripted agents in one Coalition, and many Coalitions at once.

Every agent joins, accepts the charter, asks the scripted model for one offer (metered) and
offers on a few tasks. The Gardener plans from the log, the deciders decide, and every agent's
viewer must have received every event.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from coalitionkit_gardener import build_propose, generate_plans
from coalitionkit_models import CostMeter, ModelGateway, Settings, load_price_table
from coalitionkit_models.gateway import ChatMessage, RawCompletion, Usage
from coalitionkit_models.settings import ROLES, Route
from coalitionkit_runtime import SQLiteStore

from .arena import DEADLINE, PUBLIC, Arena, accepted
from .metrics import Recorder
from .ripple import problem_from_state
from .watch import Viewer, check_log

OFFERS_PER_AGENT = 2


class ScriptedTransport:
    """A model that answers with fixed text and usage that depends on the caller only."""

    def __init__(self) -> None:
        self.calls = 0

    async def create(
        self, route: Route, messages: Sequence[ChatMessage], opts: Mapping[str, Any]
    ) -> RawCompletion:
        self.calls += 1
        size = sum(len(m["content"]) for m in messages)
        return RawCompletion("offer: 30 minutes", Usage(300 + size, 40 + size % 7, 100))


def scripted_gateway(meter: CostMeter) -> ModelGateway:
    limits = dict.fromkeys(ROLES, 10_000_000)
    settings = Settings(_env_file=None, rate_limit_per_minute=limits)  # pyright: ignore[reportCallIssue]
    return ModelGateway(settings, transport=ScriptedTransport(), meter=meter)


@dataclass(frozen=True)
class CoalitionOutcome:
    coalition_id: str
    agents: int
    events: int
    lost_events: int
    decided: bool
    model_cost_micro_usd: int
    metered_micro_usd: int


def run_coalition(
    agents: int, tasks: int, meter: CostMeter, recorder: Recorder, *, deciders: int = 2
) -> CoalitionOutcome:
    names = [f"a{i}" for i in range(agents)]
    arena = Arena.open(SQLiteStore(), deciders=names[:deciders])
    arena.timer = lambda seconds: recorder.sample("accept_s", seconds)
    host = arena.host
    gateway = scripted_gateway(meter)
    viewers = [Viewer(host, name) for name in names]
    spent = 0
    for name in names:
        arena.enroll(name)
    ids = [arena.need() for _ in range(tasks)]
    for index, name in enumerate(names):
        message: ChatMessage = {"role": "user", "content": f"offer for {name}"}
        done = asyncio.run(
            gateway.complete(
                "hosted_agent", [message], coalition_id=host.coalition_id, participant=name
            )
        )
        spent += done.cost_micro_usd
        for step in range(OFFERS_PER_AGENT):
            task = ids[(index + step) % tasks]
            accepted(arena.members[name].offer(task, 30 + 10 * (index % 3), 3 + index % 5))
    plans = generate_plans(problem_from_state(host.state))
    decided = False
    if plans.plans:
        proposal = build_propose(plans, deadline=DEADLINE, proposal_set_id="scale")
        reply = accepted(host.host_emit("propose", proposal.model_dump(mode="json"), PUBLIC))
        arena.decide_all("plan", reply.accepted["payload"]["plans"][0]["plan_id"])
        decided = {t["status"] for t in host.state.tasks.values()} == {"decided"}
    head = check_log(host)
    for viewer in viewers:
        viewer.pump()
    lost = sum(viewer.lost(head) for viewer in viewers)
    with recorder.timed("view_s"):
        host.view(names[-1])
    arena.close()
    return CoalitionOutcome(
        host.coalition_id,
        agents,
        head,
        lost,
        decided,
        spent,
        meter.total(host.coalition_id),
    )


def run_scale(
    big_agents: int, coalitions: int, coalition_agents: int, tasks: int, workers: int
) -> tuple[dict[str, Any], list[CoalitionOutcome]]:
    """One Coalition of ``big_agents``, then ``coalitions`` Coalitions of ``coalition_agents``."""
    totals = Recorder("scale")
    meter = CostMeter(load_price_table())
    big_recorder, small_recorder = Recorder("scale_big"), Recorder("scale_concurrent")
    big = run_coalition(big_agents, tasks, meter, big_recorder)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(run_coalition, coalition_agents, tasks, meter, small_recorder)
            for _ in range(coalitions)
        ]
        outcomes = [big, *(f.result() for f in futures)]
    totals.count("agents_total", sum(o.agents for o in outcomes))
    totals.count("events_total", sum(o.events for o in outcomes))
    totals.count("lost_events", sum(o.lost_events for o in outcomes))
    totals.count("coalitions", len(outcomes))
    totals.count("coalitions_decided", sum(1 for o in outcomes if o.decided))
    totals.count("model_calls", sum(o.agents for o in outcomes))
    totals.value("cost_micro_usd_metered", sum(o.metered_micro_usd for o in outcomes))
    totals.value("cost_micro_usd_returned", sum(o.model_cost_micro_usd for o in outcomes))
    result = totals.result()
    result["big"] = big_recorder.result()
    result["concurrent"] = small_recorder.result()
    return result, outcomes
