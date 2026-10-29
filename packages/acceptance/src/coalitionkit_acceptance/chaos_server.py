# SPDX-License-Identifier: Apache-2.0
"""Acceptance test 7 over the real server: kill it, drop its database, race the deciders.

The old "split NATS" case is gone: ADR 014 replaced NATS with an in-process bus, so there is no
bus to split. What remains is the host process, the database, the deciders and the viewers.

* ``kill_server``: the server process is killed with a decision in flight and started again on
  the same store. Recovery time is kill to the first accepted event after the restart.
* ``database_fault`` (Postgres only): the database container is killed and started again, or its
  connections are terminated. The store holds one connection and does not reconnect, so the
  server process is restarted; whether it healed by itself is recorded.
* ``concurrent_deciders``: both deciders answer at once from two connections each.
* ``viewer_disconnect``: an SSE viewer goes away with a consent open and returns.
"""

from __future__ import annotations

import asyncio
import time
from collections import Counter
from pathlib import Path
from typing import Any

import httpx

from coalitionkit_edges.a2a.testing import free_port
from coalitionkit_models import ModelGateway
from coalitionkit_runtime import (
    CoalitionHost,
    EventStore,
    PostgresStore,
    SQLiteStore,
)
from coalitionkit_server import Settings

from .chaos import decisions_per_revision
from .gateways import Kit, scripted_kit
from .harness import (
    FAR,
    ChildServer,
    Document,
    Instance,
    Member,
    emit,
    make_settings,
    new_need,
    provision,
)
from .metrics import Recorder
from .postgres import PostgresContainer
from .sse import ViewerPool
from .watch import check_log

NAMES = ["p1", "p2", "p3"]
DECIDERS = ["p1", "p2"]


class Rig:
    """One Coalition on one store, seeded in-process and then served by a killable child."""

    def __init__(self, directory: Path, store_url: str, kit: Kit | None = None) -> None:
        self.settings: Settings = make_settings(store_url, directory, free_port())
        self.store_url = store_url
        self.directory = directory
        self.kit = kit or scripted_kit()
        self.gateway: ModelGateway = self.kit.gateway
        self.members: dict[str, Member] = {}
        self.coalition = ""
        self.plan = ""
        self.task = ""
        self.acknowledged: set[str] = set()
        self.child = ChildServer(self.settings)
        self.state: Any = None
        self.pool = ViewerPool()

    async def seed(self) -> None:
        """Three members, one task and one plan waiting for the deciders."""
        with Instance(self.settings, self.gateway) as server, httpx.Client(timeout=60) as admin:
            self.state = server.state
            self.coalition, self.members = provision(
                server.base, server.state, NAMES, DECIDERS, admin
            )
            await self._join(server)
            host = server.host(self.coalition)
            self.task = new_need(host)
            plan: Document = {
                "proposal_set_id": "01M63DQ1WZXXR2N3QZT9MW9F5V",
                "decision_deadline": FAR,
                "plans": [
                    {
                        "assignments": [{"task_id": self.task, "assignee": "p3"}],
                        "objective_scores": {"variant": 0.0},
                    }
                ],
            }
            self.plan = str(emit(host, "propose", plan)["payload"]["plans"][0]["plan_id"])
            self.acknowledged = {e["event_id"] for e in host.store.read(self.coalition)}

    async def _join(self, server: Instance) -> None:
        async with httpx.AsyncClient(timeout=60) as http:
            for member in self.members.values():
                await member.connect(http, server.state)
                await member.send(member.join_envelope())
            revision = server.host(self.coalition).state.charter["revision"]
            for member in self.members.values():
                await member.send(member.decision_envelope("charter", self.coalition, revision))
            for member in self.members.values():
                await member.client.close()  # pyright: ignore[reportOptionalMemberAccess]
                member.client = None

    async def connect(self, http: httpx.AsyncClient, names: list[str] | None = None) -> None:
        for name in names or list(self.members):
            await self.members[name].connect(http, self.state)

    async def send(self, name: str, envelope: Document) -> bool:
        """Send and remember the acknowledgement; False when the call failed."""
        try:
            await self.members[name].send(envelope)
        except Exception:
            return False
        self.acknowledged.add(envelope["event_id"])
        return True

    def store(self) -> EventStore:
        if self.store_url.startswith("sqlite:///"):
            return SQLiteStore(self.store_url.removeprefix("sqlite:///"))
        return PostgresStore(self.store_url)

    def audit(self, recorder: Recorder) -> None:
        """Count what must be zero, from a fresh connection to the store."""
        store = self.store()
        try:
            host = CoalitionHost(
                store, self.coalition, self.state.signer.card_url, self.state.key, "host"
            )
            events = store.read(self.coalition)
            stored = [e["event_id"] for e in events]
            recorder.count("lost_events", len(self.acknowledged - set(stored)))
            recorder.count("duplicate_events", len(stored) - len(set(stored)))
            recorder.count("events", check_log(host))
            per = decisions_per_revision(events)
            recorder.count("max_decisions_per_revision", max(per.values(), default=0))
            recorder.count("plan_decided", int(_decided(host, self.plan)))
        finally:
            close = getattr(store, "close", None)
            if callable(close):
                close()

    def close(self) -> None:
        self.child.kill()
        self.pool.close()


def _decided(host: CoalitionHost, plan: str) -> bool:
    return host.state.subject("plan", plan).get("status") == "decided"


async def send_while_killing(rig: Rig, name: str, envelope: Document) -> bool:
    """Start a send, then kill the child before the reply can arrive."""
    send = asyncio.create_task(rig.send(name, envelope))
    await asyncio.sleep(0)
    rig.child.kill()
    return await send


async def kill_server(
    directory: Path, store_url: str, label: str, kit: Kit | None = None
) -> Recorder:
    """Kill the server mid-negotiation (one decider answered, one in flight); restart it."""
    recorder = Recorder(f"chaos_server_kill_{label}")
    rig = Rig(directory, store_url, kit)
    try:
        await rig.seed()
        recorder.sample("start_s", rig.child.start())
        async with httpx.AsyncClient(timeout=30) as http:
            await rig.connect(http)
            rig.pool.add("p2", "p2", rig.child.base, rig.members["p2"].token)
            assert await rig.send("p1", rig.members["p1"].decision_envelope("plan", rig.plan, 1))
            second = rig.members["p2"].decision_envelope("plan", rig.plan, 1)
            killed_at = time.perf_counter()
            reached = await send_while_killing(rig, "p2", second)
            recorder.count("in_flight_acknowledged", int(reached))
            recorder.count("in_flight_lost_reply", int(not reached))
            recorder.sample("restart_s", rig.child.start())
        async with httpx.AsyncClient(timeout=30) as http:
            await rig.connect(http, ["p2"])
            # The client retries the same envelope: accepted once, or its receipt replayed.
            assert await rig.send("p2", second)
            recorder.sample("recovery_s", time.perf_counter() - killed_at)
            viewer = rig.pool.reconnect("p2")
            await _wait_for(lambda: len(viewer.event_ids()) >= len(rig.acknowledged), 20)
            recorder.count("viewer_missing_events", len(rig.acknowledged - viewer.event_ids()))
        rig.child.kill()
        rig.audit(recorder)
        return recorder
    finally:
        rig.close()


async def _wait_for(check: Any, timeout: float) -> bool:
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        if check():
            return True
        await asyncio.sleep(0.1)
    return bool(check())


async def database_fault(
    directory: Path, container: PostgresContainer, mode: str, *, seconds_down: float = 1.0
) -> Recorder:
    """Kill the database (``mode="kill"``) or terminate its connections (``"drop"``)."""
    recorder = Recorder(f"chaos_postgres_{mode}")
    rig = Rig(directory, container.new_database())
    try:
        await rig.seed()
        recorder.sample("start_s", rig.child.start())
        async with httpx.AsyncClient(timeout=30) as http:
            await rig.connect(http)
            assert await rig.send("p1", rig.members["p1"].decision_envelope("plan", rig.plan, 1))
            second = rig.members["p2"].decision_envelope("plan", rig.plan, 1)
            faulted_at = time.perf_counter()
            if mode == "kill":
                container.kill()
                recorder.count("refused_while_down", int(not await rig.send("p2", second)))
                time.sleep(seconds_down)
                recorder.sample("database_restart_s", container.start())
            else:
                recorder.count("connections_dropped", container.drop_connections())
            healed = await rig.send("p2", second)
            recorder.count("server_healed_without_restart", int(healed))
            if not healed:
                rig.child.kill()
                recorder.sample("restart_s", rig.child.start())
                await rig.connect(http, ["p2"])
                assert await rig.send("p2", second)
            recorder.sample("recovery_s", time.perf_counter() - faulted_at)
        rig.child.kill()
        rig.audit(recorder)
        return recorder
    finally:
        rig.close()


async def concurrent_deciders(directory: Path, rounds: int = 12) -> Recorder:
    """Both deciders answer at once, twice each, from four connections, on a tension."""
    recorder = Recorder("chaos_server_concurrent_deciders")
    rig = Rig(directory, f"sqlite:///{directory / 'host.db'}")
    try:
        await rig.seed()
        outcomes: Counter[str] = Counter()
        with Instance(rig.settings, rig.gateway) as server:
            host = server.host(rig.coalition)
            async with httpx.AsyncClient(timeout=60) as http:
                spare = {
                    n: Member(n, m.token, m.person, m.coalition_id) for n, m in rig.members.items()
                }
                await rig.connect(http)
                for member in spare.values():
                    await member.connect(http, server.state)
                for index in range(rounds):
                    tension = _tension(host, new_need(host))
                    picks = {"p1": "a", "p2": "a" if index % 2 == 0 else "b"}
                    attempts: list[tuple[Member, Document]] = []
                    for name, pick in picks.items():
                        for member in (rig.members[name], spare[name]):
                            attempts.append(
                                (
                                    member,
                                    member.decision_envelope("tension_option", tension, 1, pick),
                                )
                            )
                    results = await asyncio.gather(
                        *(m.send(e) for m, e in attempts), return_exceptions=True
                    )
                    for (member, envelope), result in zip(attempts, results, strict=True):
                        if isinstance(result, BaseException):
                            code = str(getattr(result, "code", type(result).__name__))
                            outcomes[f"refused_{code}"] += 1
                        else:
                            rig.acknowledged.add(envelope["event_id"])
                            outcomes[f"accepted_{member.name}"] += 1
                    status = host.state.subject("tension_option", tension)["status"]
                    outcomes[f"outcome_{status}"] += 1
        for key, amount in sorted(outcomes.items()):
            recorder.count(key, amount)
        rig.audit(recorder)
        return recorder
    finally:
        rig.close()


def _tension(host: CoalitionHost, task: str) -> str:
    body: Document = {
        "task_ids": [task],
        "options": [
            {"option_id": "a", "summary": "First"},
            {"option_id": "b", "summary": "Second"},
        ],
        "tradeoffs": [],
        "deciders": DECIDERS,
        "decision_deadline": FAR,
    }
    return str(emit(host, "tension", body)["payload"]["tension_id"])


async def viewer_disconnect(directory: Path) -> Recorder:
    """A decider's SSE viewer leaves with a plan consent open; others act; it returns."""
    recorder = Recorder("chaos_server_viewer_disconnect")
    rig = Rig(directory, f"sqlite:///{directory / 'host.db'}")
    try:
        await rig.seed()
        with Instance(rig.settings, rig.gateway) as server:
            host = server.host(rig.coalition)
            async with httpx.AsyncClient(timeout=60) as http:
                await rig.connect(http)
                viewer = rig.pool.add("p2", "p2", server.base, rig.members["p2"].token)
                rig.pool.disconnect("p2")
                gone_at = len(viewer.event_ids())
                assert await rig.send(
                    "p1", rig.members["p1"].decision_envelope("plan", rig.plan, 1)
                )
                for index in range(5):
                    assert await rig.send("p3", rig.members["p3"].observe_envelope(f"away {index}"))
                recorder.count("consent_still_open", len(host.open_consents("p2")))
                recorder.count("plan_still_pending", int(not _decided(host, rig.plan)))
                started = time.perf_counter()
                back = rig.pool.reconnect("p2")
                recorder.sample("catch_up_s", time.perf_counter() - started)
                recorder.count("events_caught_up", len(back.event_ids()) - gone_at)
                assert await rig.send(
                    "p2", rig.members["p2"].decision_envelope("plan", rig.plan, 1)
                )
                await _wait_for(lambda: back.event_ids() == set(host.view("p2")["events"]), 20)
                recorder.count(
                    "viewer_lost_events", len(set(host.view("p2")["events"]) - back.event_ids())
                )
            rig.pool.close()
        rig.audit(recorder)
        return recorder
    finally:
        rig.close()


def open_container() -> PostgresContainer:
    return PostgresContainer()
