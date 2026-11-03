# SPDX-License-Identifier: Apache-2.0
"""Begin, seats and helpers.

The charter names every seat as a decider, so a room with empty seats would wait for ever. The
owner (or the room itself, once every seat has signed) begins: the door stops and, if seats are
open, the host publishes a charter revision whose deciders are the people seated. The owner's
click counts as accepting that revision and is signed by the owner's own key through the same
path as any consent. A helper is an ordinary hosted member that says it is an agent, holds its
own keys, signs only its own charter acceptance, and is never a decider.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

from coalitionkit_runtime import Acknowledgement
from coalitionkit_runtime.lifecycle import State
from coalitionkit_surfaces import AgentSession, ConsentError, open_requests

from ..adapter import Document
from ..genesis import enroll_member
from ..views import OwnerSigner

if TYPE_CHECKING:
    from .engine import RoomEngine

LOG = logging.getLogger(__name__)
# Helpers serve the kinds an agent can make; a schedule needs a person's calendar.
HELPER_ORDER = ("budget", "list", "draft", "place", "schedule")
HELPER_KINDS = {
    "budget": "Budget",
    "list": "List",
    "draft": "Draft",
    "place": "Place",
    "schedule": "Schedule",
}


def people(state: State, doc: Document) -> list[str]:
    """Seated members that are not helpers, in the order they joined."""
    return [p for p in state.members if p not in doc["helpers"]]


def total_seats(engine: RoomEngine, coalition: str, state: State) -> int:
    door = engine.doors.door_row("coalition", coalition)
    seats = sum(r["count"] for r in door["roles"]) if door else len(state.charter["deciders"])
    return max(seats, len(state.members))


def open_seats(engine: RoomEngine, coalition: str, state: State, doc: Document) -> int:
    if doc["begun"] or doc["request"]:
        return 0
    return max(0, total_seats(engine, coalition, state) - len(people(state, doc)))


async def sign_charter(engine: RoomEngine, coalition: str, who: str) -> int:
    """Answer ``who``'s open charter asks yes with their own owner key; how many were signed."""
    host = engine.server.hosts[coalition]

    def run() -> int:
        session = AgentSession(
            host,
            who,
            OwnerSigner(engine.server.registry, coalition, who),
            clock=time.monotonic,
        )
        signed = 0
        for request in open_requests(host, who):
            if request.kind != "charter":
                continue
            try:
                session.answer(request.interrupt_id, True)
                signed += 1
            except ConsentError as exc:
                LOG.warning("Charter acceptance for %s refused: %s", who, exc.code)
        return signed

    return await asyncio.to_thread(run)


def revision_payload(state: State, deciders: list[str]) -> Document:
    charter = state.charter
    payload: Document = {k: charter[k] for k in ("goal", "roles", "rules", "deadline")}
    payload["deciders"] = deciders
    for key in ("pack", "budget", "count_trusted"):
        if charter.get(key) is not None:
            payload[key] = charter[key]
    return payload


async def read_state(engine: RoomEngine, coalition: str) -> State:
    host = engine.server.hosts[coalition]
    return await asyncio.to_thread(lambda: host.state)


async def request_begin(engine: RoomEngine, coalition: str, *, helpers: bool, auto: bool) -> None:
    """Ask for the room to begin and carry it as far as it goes. The caller holds the room lock."""
    doc = engine.read(coalition)
    if doc["begun"] or doc["request"]:
        return
    engine.update(
        coalition,
        lambda d: d.__setitem__(
            "request", {"helpers": helpers, "auto": auto, "revised": False, "helpers_done": False}
        ),
    )
    await advance(engine, coalition)


def all_signed(state: State, doc: Document, seats: int) -> bool:
    members = people(state, doc)
    return len(members) >= seats and all(state.accepted_charter(p) for p in members)


async def advance(engine: RoomEngine, coalition: str) -> None:
    """Do the next missing part of beginning. Safe to call again at any time."""
    state = await read_state(engine, coalition)
    doc = engine.read(coalition)
    owner = engine.owner(coalition)
    if owner is None or doc["needs_state"] != "ready":
        return
    if doc["request"] is None and not doc["begun"]:
        if state.stage in {"Germinate", "Gather"} and all_signed(
            state, doc, total_seats(engine, coalition, state)
        ):
            await request_begin(engine, coalition, helpers=False, auto=True)
        return
    if doc["request"] is not None:
        await carry_begin(engine, coalition, owner)
    # Helpers answer their own charter asks, whenever a revision asks again.
    for helper in engine.read(coalition)["helpers"]:
        if helper in state.members and not state.accepted_charter(helper):
            await sign_charter(engine, coalition, helper)


async def carry_begin(engine: RoomEngine, coalition: str, owner: str) -> None:
    host = engine.server.hosts[coalition]
    request = engine.read(coalition)["request"]
    state = await read_state(engine, coalition)
    doc = engine.read(coalition)
    seated = people(state, doc)
    engine.doors.stop(coalition)
    if not request["revised"]:
        if total_seats(engine, coalition, state) > len(seated) and set(
            state.charter["deciders"]
        ) != set(seated):
            result = await asyncio.to_thread(
                host.host_emit,
                "charter",
                revision_payload(state, seated),
                {"audience": "coalition"},
            )
            if not isinstance(result, Acknowledgement):
                raise RuntimeError("charter revision refused: " + result["payload"]["code"])
            engine.note(
                coalition,
                "changing",
                "Closed the door; the people seated now decide",
                source="host",
                event=result.receipt["payload"].get("event_id"),
            )
        engine.update(coalition, lambda d: d["request"].__setitem__("revised", True))
    await sign_charter(engine, coalition, owner)
    if request["helpers"] and not request["helpers_done"]:
        await add_helpers(engine, coalition)
        engine.update(coalition, lambda d: d["request"].__setitem__("helpers_done", True))
    state = await read_state(engine, coalition)
    for helper in engine.read(coalition)["helpers"]:
        if helper in state.members and not state.accepted_charter(helper):
            await sign_charter(engine, coalition, helper)

    def done(d: Document) -> None:
        d["begun"], d["request"] = True, None

    engine.update(coalition, done)
    engine.note(coalition, "planning", "The room has begun")


def helper_plan(doc: Document, count: int) -> list[tuple[str, str]]:
    """(need id, kind) for each helper: at most one per need, agent-makeable kinds first."""
    order = {kind: i for i, kind in enumerate(HELPER_ORDER)}
    needs = sorted(doc["needs"], key=lambda n: order.get(n["kind"], len(order)))
    return [(n["id"], n["kind"]) for n in needs[:count]]


async def add_helpers(engine: RoomEngine, coalition: str) -> None:
    state = await read_state(engine, coalition)
    doc = engine.read(coalition)
    free = max(0, total_seats(engine, coalition, state) - len(people(state, doc)))
    # One helper per open seat, never more than the needs there are, and none twice on resume.
    wanted = helper_plan(doc, max(free, len(doc["helpers"])))
    for index, (need_id, kind) in enumerate(wanted, start=1):
        pid = f"helper-{index}"
        label = f"{HELPER_KINDS.get(kind, 'Task')} helper"
        engine.update(
            coalition,
            lambda d, pid=pid, kind=kind, need_id=need_id, label=label: d["helpers"].setdefault(
                pid, {"kind": kind, "need_id": need_id, "label": label}
            ),
        )
        if pid not in state.members:
            await make_helper(engine, coalition, pid, label, state)


async def make_helper(
    engine: RoomEngine, coalition: str, pid: str, label: str, state: State
) -> None:
    server = engine.server
    redeemed: Document
    try:
        await asyncio.to_thread(server.registry.hosted_for, coalition, pid)
        redeemed = {"coalition_id": coalition, "participant": pid}
    except ValueError:
        token = await asyncio.to_thread(server.registry.issue, coalition, pid)
        redeemed = await asyncio.to_thread(
            server.registry.redeem, token, server.ports, None, None, label
        )
    role: Any = state.charter["roles"][0]["id"]
    await enroll_member(server, redeemed, role, surfaces=())
