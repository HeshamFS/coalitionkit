# SPDX-License-Identifier: Apache-2.0
"""Restartable host driver for Genesis; members retain every member action."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from datetime import datetime
from fractions import Fraction
from typing import TYPE_CHECKING

from coalitionkit_gardener._ids import derive_ulid
from coalitionkit_gardener.plans import PlanCandidate, PlanSet
from coalitionkit_gardener.tension import tension_from_plans
from coalitionkit_runtime import Acknowledgement
from coalitionkit_runtime.bus import Subscription

if TYPE_CHECKING:
    from .app import Server

LOG = logging.getLogger(__name__)
RETRY_BASE_S = 2.0  # first retry after a failed step; doubles per failure, capped at 60 s


class GardenerLoop:
    def __init__(self, server: Server) -> None:
        self.server = server
        self.tasks: dict[str, asyncio.Task[None]] = {}
        self.wakes: dict[str, tuple[asyncio.AbstractEventLoop, asyncio.Event]] = {}

    def resume(self) -> None:
        with self.server.store.transaction("") as tx:
            rows = tx.execute("SELECT coalition FROM server_genesis").fetchall()
        for (coalition,) in rows:
            if self.server.hosts[coalition].state.stage != "Dissolve":
                self.restore_refusals(coalition)
                self.start(coalition)

    def restore_refusals(self, coalition: str) -> None:
        with self.server.store.transaction(coalition) as tx:
            rows = tx.execute(
                "SELECT g.participant, r.error FROM server_genesis g "
                "JOIN server_genesis_refusals r ON g.coalition = r.coalition "
                "WHERE g.coalition = ?",
                (coalition,),
            ).fetchall()
        for owner, error in rows:
            self.server.surfaces[coalition].state.hub.say(
                owner, json.dumps({"genesis_need_refused": json.loads(error)})
            )

    def start(self, coalition: str) -> None:
        if coalition not in self.tasks:
            self.tasks[coalition] = asyncio.create_task(self.run(coalition))

    async def release(self, coalition: str) -> None:
        """Stop driving a coalition for good: a caller that plays the Gardener itself (an
        acceptance harness) would otherwise race this loop's needs and proposals."""
        task = self.tasks.pop(coalition, None)
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        with self.server.store.transaction(coalition) as tx:
            tx.execute("DELETE FROM server_genesis WHERE coalition = ?", (coalition,))

    def wake(self, coalition: str) -> None:
        """Look at this room again now (the room engine calls this when it has made progress)."""
        pair = self.wakes.get(coalition)
        if pair is not None:
            with contextlib.suppress(RuntimeError):  # the loop has closed; nobody is listening
                pair[0].call_soon_threadsafe(pair[1].set)

    async def close(self) -> None:
        for task in self.tasks.values():
            task.cancel()
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        self.tasks.clear()

    async def run(self, coalition: str) -> None:
        host = self.server.hosts[coalition]
        loop, wake = asyncio.get_running_loop(), asyncio.Event()
        self.wakes[coalition] = (loop, wake)

        def notify() -> None:
            # This subscriber reads folded state, not a bounded event queue.
            sub.cursor += 1
            loop.call_soon_threadsafe(wake.set)

        sub: Subscription = host.bus.subscribe(
            coalition,
            since=max((e["seq"] for e in host.state.events.values()), default=0),
            notify=notify,
        )
        wake.set()
        failures = 0
        retry: asyncio.TimerHandle | None = None
        try:
            while host.state.stage != "Dissolve":
                await wake.wait()
                # Coalesce a burst before reading authoritative state, including on restart.
                await asyncio.sleep(1)
                wake.clear()
                sub.cursor = max((e["seq"] for e in host.state.events.values()), default=0)
                try:
                    self.step(coalition)
                    failures = 0
                except Exception:
                    LOG.exception("Genesis Gardener failed for %s", coalition)
                    # Try again without waiting for new activity; back off up to a minute.
                    failures += 1
                    if retry is not None:
                        retry.cancel()
                    retry = loop.call_later(min(RETRY_BASE_S * 2 ** (failures - 1), 60), wake.set)
        finally:
            if retry is not None:
                retry.cancel()
            host.bus.unsubscribe(sub)

    def step(self, coalition: str) -> None:
        host = self.server.hosts[coalition]
        if host.state.stage == "Dissolve":
            return
        room = self.server.room
        if room is not None:
            room.ensure(coalition)
        with self.server.store.transaction(coalition) as tx:
            row = tx.execute(
                "SELECT participant, needs FROM server_genesis WHERE coalition = ?", (coalition,)
            ).fetchone()
        if not row or not host.state.accepted_charter(row[0]):
            return
        # The engine turns the goal into needs first; seeding the draft's would race it.
        if room is not None and not room.needs_ready(coalition):
            return
        self.seed(coalition, row[0], json.loads(row[1]))
        self.tensions(coalition)
        state = host.state
        # A proposal moves the coalition to Decide, where nobody can join any more; proposing
        # before every decider has said yes would leave a seat that can never approve.
        if not all(state.accepted_charter(d) for d in state.charter["deciders"]):
            return
        # Offers and the rounds that compare them come before any plan.
        if room is not None and not room.may_plan(coalition):
            return
        open_ids = {k for k, t in state.tasks.items() if t["status"] in {"open", "negotiating"}}
        offers = sorted(
            k
            for k, o in state.offers.items()
            if o["counted"]
            and o["target"]["id"] in open_ids
            and datetime.fromisoformat(o["valid_until"]) > datetime.fromisoformat(host.clock())
        )
        if not offers:
            return
        inputs = sorted(
            e["event_id"]
            for e in state.events.values()
            if e["type"] == "coalition.need"
            or (e["type"] == "coalition.ripple" and set(e["payload"]["invalidates"]) & open_ids)
        )
        marker = derive_ulid(
            "genesis-plan",
            str(state.charter["revision"]),
            *inputs,
            *(json.dumps(state.offers[k], sort_keys=True) for k in offers),
        )
        if any(e["payload"].get("proposal_set_id") == marker for e in state.events.values()):
            return
        result = self.server.plan(coalition, state.charter["deadline"], proposal_set_id=marker)
        if not isinstance(result, Acknowledgement):
            LOG.warning(
                "Genesis plan refused for %s: %s",
                coalition,
                result.get("payload", {}).get("code", "unresolved"),
            )
        self.tensions(coalition)

    def seed(self, coalition: str, owner: str, needs: list[str]) -> None:
        host = self.server.hosts[coalition]
        markers = [derive_ulid("genesis-need", coalition, str(i)) for i in range(len(needs))]
        events = list(host.state.events.values())
        # A separately driven coalition may already have seeded its needs.
        if any(
            e["type"] == "coalition.need" and e["payload"].get("need_id") not in markers
            for e in events
        ):
            return
        for marker, description in zip(markers, needs, strict=True):
            if any(e["payload"].get("need_id") == marker for e in events):
                continue
            with self.server.store.transaction(coalition) as tx:
                refused = tx.execute(
                    "SELECT error FROM server_genesis_refusals WHERE id = ?", (marker,)
                ).fetchone()
            if refused:
                continue
            result = host.host_emit(
                "need",
                {
                    "need_id": marker,
                    "description": description,
                    "requirements": [],
                    "window": {"start": host.clock(), "end": host.state.charter["deadline"]},
                },
                {"audience": "coalition"},
            )
            if not isinstance(result, Acknowledgement):
                # Owner-facing metadata, not a delivery of the host-scoped error envelope.
                refusal = {
                    "description": description,
                    "code": result["payload"]["code"],
                    "ref": result["payload"]["ref"],
                }
                with self.server.store.transaction(coalition) as tx:
                    tx.execute(
                        "INSERT INTO server_genesis_refusals VALUES (?, ?, ?)",
                        (marker, coalition, json.dumps(refusal)),
                    )
                self.server.surfaces[coalition].state.hub.say(
                    owner,
                    json.dumps({"genesis_need_refused": refusal}),
                )

    def tensions(self, coalition: str) -> None:
        host = self.server.hosts[coalition]
        events = list(host.state.events.values())
        for event in events:
            if event["type"] != "coalition.propose":
                continue
            if any(e.get("causation_id") == event["event_id"] for e in events):
                continue
            body = event["payload"]
            if any(
                (
                    host.state.subject("plan", p["plan_id"]).get("status") != "pending"
                    or host.state.subject("plan", p["plan_id"]).get("proposal_set_id")
                    != body["proposal_set_id"]
                )
                for p in body["plans"]
            ):
                continue
            plans = PlanSet(
                tuple(
                    PlanCandidate(
                        {a["task_id"]: a["assignee"] for a in p["assignments"]},
                        (
                            Fraction(p["objective_scores"]["total_cost"]),
                            Fraction(p["objective_scores"]["max_share_ratio"]),
                            Fraction(p["objective_scores"]["third"]),
                        ),
                        p["plan_id"],
                    )
                    for p in body["plans"]
                )
            )
            tension = tension_from_plans(
                plans, deciders=host.state.charter["deciders"], deadline=body["decision_deadline"]
            )
            if tension:
                host.host_emit(
                    "tension",
                    tension.to_wire(),
                    sources=[event["event_id"]],
                    causation_id=event["event_id"],
                )
