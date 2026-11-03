# SPDX-License-Identifier: Apache-2.0
"""``room_state(viewer)``: the ``room`` key of one viewer's feed state (docs/ux/room-engine.md).

Only ``mine`` is private to the viewer. Anything taken from the log is limited to what the
viewer's own projection lets them see. What later slices own (offers' comparison, plan notes,
results, stops, changes) is returned empty here, with the contract's shape.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from coalitionkit_runtime.lifecycle import State

from ..adapter import Document
from .brief import KEY as BRIEF_KEY
from .brief import chosen_slots
from .engine import FEED, FOR_YOU
from .seats import open_seats

if TYPE_CHECKING:
    from .engine import RoomEngine

FEED_SHOWN = 30
SHOWN = ("id", "at", "seat", "verb", "need", "label", "state", "ms", "source", "event")
PHASES = {"Decide": "decide", "Act": "commit", "Live": "live"}


def room_state(engine: RoomEngine, coalition: str, viewer: str) -> Document | None:
    """The viewer's room, or None when they are not seated. Cached until the room moves."""
    key = (engine.version(coalition), engine.ticks.get(coalition, 0))
    cached = engine.cache.get((coalition, viewer))
    if cached is not None and cached[0] == key:
        return cached[1]
    if engine.owner(coalition) is None:
        return None  # not a room the engine drives (made by an operator, not by Genesis)
    state = engine.server.hosts[coalition].state
    if viewer not in state.members:
        return None
    built = build(engine, coalition, viewer, state)
    engine.cache[(coalition, viewer)] = (key, built)
    return built


def phase_of(state: State, doc: Document) -> str:
    if state.stage == "Dissolve":
        return "ended"
    if not doc["begun"]:
        return "gather"
    if not doc["briefs_done"]:
        return "brief"
    return PHASES.get(state.stage, "work")


def build(engine: RoomEngine, coalition: str, viewer: str, state: State) -> Document:
    doc = engine.read(coalition)
    phase = phase_of(state, doc)
    mine = my_side(engine, coalition, viewer, doc)
    waiting = bool(engine.server.hosts[coalition].open_consents(viewer)) or any(
        q["status"] == "open" for q in mine["brief"]
    )
    owner = engine.owner(coalition)
    return {
        "phase": phase,
        "lights": "day" if phase in {"gather", "ended"} or waiting else "night",
        "goal": str(state.charter.get("goal", "")),
        "seats": seats_of(engine, coalition, viewer, state, doc),
        "needs": needs_of(viewer, state, doc),
        "activity": [
            {k: item[k] for k in SHOWN}
            for item in doc["activity"]
            if item.get("only") in (None, viewer)
        ],
        "slots": list(doc["slots"]),
        "common": common_of(engine, coalition, viewer, doc),
        "plan_notes": notes_of(viewer, state, doc),
        "results": [],
        "stops": [],
        "checked": checked_of(engine, coalition, state),
        "change": None,
        "begin": begin_of(engine, coalition, viewer, owner, state, doc),
        "mine": mine,
    }


def begin_of(
    engine: RoomEngine, coalition: str, viewer: str, owner: str | None, state: State, doc: Document
) -> Document | None:
    if viewer != owner or doc["begun"] or doc["request"] or state.stage == "Dissolve":
        return None
    return {
        "can": doc["needs_state"] == "ready",
        "open_seats": open_seats(engine, coalition, state, doc),
    }


def seats_of(
    engine: RoomEngine, coalition: str, viewer: str, state: State, doc: Document
) -> list[Document]:
    door = engine.doors.door_row("coalition", coalition)
    labels = {r["id"]: r.get("label", r["id"]) for r in door["roles"]} if door else {}
    counts: dict[str, int] = {}
    seats: list[Document] = []
    for person, member in state.members.items():
        helper = doc["helpers"].get(person)
        role = str(member["roles_requested"][0]) if member["roles_requested"] else "member"
        signed = state.accepted_charter(person)
        counts[role] = counts.get(role, 0) + 1
        if helper:
            label, kind, status = f"{helper['label']} (agent)", "helper", "signed"
        else:
            name = str(labels.get(role, role)).capitalize()
            label, kind, status = f"{name} {counts[role]}", "person", "signed"
        brief = doc["briefs"].get(person)
        if not signed:
            status = "waiting"
        elif brief is not None and not brief["closed"]:
            status = "briefing"
        seats.append(
            {
                "seat": person,
                "role": role,
                "label": label,
                "kind": kind,
                "you": person == viewer,
                "signed": signed,
                "state": status,
            }
        )
    if door and not doc["begun"] and not doc["request"]:
        for role in engine.doors.open_roles(door):
            name = str(labels.get(role["id"], role["id"])).capitalize()
            for n in range(role["open"]):
                seats.append(
                    {
                        "seat": f"open-{role['id']}-{n + 1}",
                        "role": role["id"],
                        "label": f"{name} seat",
                        "kind": "open",
                        "you": False,
                        "signed": False,
                        "state": "open",
                    }
                )
    return seats


def needs_of(viewer: str, state: State, doc: Document) -> list[Document]:
    seen_offers = {
        e["payload"]["offer_id"]
        for e in state.events.values()
        if e["type"] == "coalition.offer" and state.visible(e, viewer)
    }
    shown: list[Document] = []
    for need in doc["needs"]:
        task = state.tasks.get(need["id"])
        if task is not None and not state.visible(task["source"], viewer):
            continue
        offers = sum(
            1
            for k, o in state.offers.items()
            if o["target"]["id"] == need["id"] and k in seen_offers
        )
        shown.append(
            {
                "id": need["id"],
                "title": need["title"],
                "kind": need["kind"],
                "detail": need["detail"],
                "status": status_of(need["id"], task, offers, doc),
                "offers": offers,
                "assignee": task["assignee"] if task else None,
                "result": None,
                "source": doc["needs_source"],
            }
        )
    return shown


def status_of(need: str, task: Document | None, offers: int, doc: Document) -> str:
    if task is None:
        return "pending"
    if doc["offers_done"] and offers == 0 and task["status"] in {"open", "negotiating"}:
        return "no offers"
    return str(task["status"])


def my_side(engine: RoomEngine, coalition: str, viewer: str, doc: Document) -> Document:
    """The viewer's own questions and tasks. Nothing here is built for anyone else."""
    brief: list[Document] = []
    closed = bool(doc["briefs"].get(viewer, {}).get("closed"))
    record: Document = (
        engine.vault(coalition, viewer).get(BRIEF_KEY, {}) if viewer in doc["briefs"] else {}
    )
    questions: list[Document] = record.get("questions", [])
    for q in questions:
        status = q["status"] if q["status"] != "open" or not closed else "skipped"
        brief.append(
            {
                "id": q["id"],
                "ask": q["ask"],
                "why": q["why"],
                "component": q["component"],
                "messages": q["messages"],
                "status": status,
            }
        )
    lines: Document = engine.vault(coalition, viewer).get(FOR_YOU, {})
    feed: list[Document] = engine.vault(coalition, viewer).get(FEED, [])
    return {
        "brief": brief,
        "feed": feed[-FEED_SHOWN:],
        "for_you": {pid: item["line"] for pid, item in lines.items()},
        "tasks": [],
    }


def common_of(engine: RoomEngine, coalition: str, viewer: str, doc: Document) -> Document | None:
    """The times that fit everyone who compared. ``count_private`` is this viewer's own number."""
    cmp = doc["compare"]
    if cmp is None or cmp["state"] != "done" or cmp["slots"] is None:
        return None
    own = set(chosen_slots(engine, coalition, viewer)) if viewer in cmp["took_part"] else None
    return {
        "slots": list(cmp["slots"]),
        "count_private": None if own is None else len(own - set(cmp["slots"])),
        "compared": cmp["compared"],
    }


def notes_of(viewer: str, state: State, doc: Document) -> Document:
    """Names and lines of the plans this viewer can see."""
    seen = {
        p["plan_id"]
        for e in state.events.values()
        if e["type"] == "coalition.propose" and state.visible(e, viewer)
        for p in e["payload"]["plans"]
    }
    return {pid: note for pid, note in doc["plan_notes"].items() if pid in seen}


def checked_of(engine: RoomEngine, coalition: str, state: State) -> int:
    """Events the Steward has reviewed: every accepted event, and the ones it stopped."""
    hub = engine.server.surfaces[coalition].state.hub
    stopped = sum(len(items) for items in hub.refusals.values())
    return len(state.events) + stopped
