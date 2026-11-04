# SPDX-License-Identifier: Apache-2.0
"""``room_state(viewer)``: the ``room`` key of one viewer's feed state.

Only ``mine`` is private to the viewer. Anything taken from the log is limited to what the
viewer's own projection lets them see. Parts owned by other modules (offers' comparison, plan notes,
results, stops, changes) are returned empty here, with the contract's shape.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from coalitionkit_runtime.lifecycle import State

from ..adapter import Document
from .brief import BRIEF_SECONDS, chosen_slots
from .brief import KEY as BRIEF_KEY
from .engine import FEED, FOR_YOU
from .seats import open_seats, people
from .talk_view import talk_of
from .view_results import change_of, latest_by_need, results_of, tasks_of

if TYPE_CHECKING:
    from .engine import RoomEngine

FEED_SHOWN = 30
STOP_FIELDS = ("id", "at", "seat", "to", "policy", "explain")
SHOWN = ("id", "at", "seat", "verb", "need", "label", "state", "ms", "source", "event")


def room_state(engine: RoomEngine, coalition: str, viewer: str) -> Document | None:
    """The viewer's room, or None when they are not seated. Cached until the room moves."""
    key = (engine.version(coalition), engine.ticks.get(coalition, 0))
    cached = engine.cache.get((coalition, viewer))
    if cached is not None and cached[0] == key:
        return cached[1]
    if cached is not None and coalition in engine.checking:
        # The host is holding its lock while the Steward audits; show what was last built, plus
        # the audit that is running, rather than wait for the lock.
        old = cached[1]
        running = engine.running_checks(coalition)
        shown = {a["id"] for a in old["activity"]}
        return {
            **old,
            "activity": [*old["activity"], *[a for a in running if a["id"] not in shown]],
        }
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
    statuses = {t["status"] for t in state.tasks.values()}
    if statuses & {"open", "negotiating"} or not statuses:
        return "work"
    if "proposed" in statuses:
        return "decide"
    if "decided" in statuses:
        return "commit"
    unmade = any(
        t["status"] == "committed" and not doc["made"].get(k, {}).get("result")
        for k, t in state.tasks.items()
    )
    return "make" if unmade else "live"


def build(engine: RoomEngine, coalition: str, viewer: str, state: State) -> Document:
    doc = engine.read(coalition)
    phase = phase_of(state, doc)
    mine = my_side(engine, coalition, viewer, state, doc)
    made = results_of(engine, state, doc, viewer)
    mine["tasks"] = tasks_of(state, doc, viewer, made)
    waiting = (
        bool(engine.server.hosts[coalition].open_consents(viewer))
        or any(q["status"] == "open" for q in mine["brief"])
        or any(t["can_mark_done"] for t in mine["tasks"])
    )
    owner = engine.owner(coalition)
    return {
        "phase": phase,
        "lights": "day" if phase in {"gather", "ended"} or waiting else "night",
        "goal": str(state.charter.get("goal", "")),
        "closes": str(state.charter.get("deadline", "")),
        "seats": seats_of(engine, coalition, viewer, state, doc),
        "needs": needs_of(viewer, state, doc, latest_by_need(made)),
        "activity": [
            {k: item[k] for k in SHOWN}
            for item in [*doc["activity"], *engine.running_checks(coalition)]
            if item.get("only") in (None, viewer)
        ],
        "slots": [{"start": None, **s} for s in doc["slots"]],
        "common": common_of(engine, coalition, viewer, doc),
        "plan_notes": notes_of(viewer, state, doc),
        "results": made,
        "stops": [{k: s[k] for k in STOP_FIELDS} for s in doc["stops"]],
        "checked": checked_of(engine, coalition, state),
        "change": change_of(state, doc),
        "begin": begin_of(engine, coalition, viewer, owner, state, doc),
        "measured": measured_of(engine, coalition, state, doc),
        "talk": talk_of(engine, coalition, viewer, state, doc),
        "mine": mine,
    }


def measured_of(engine: RoomEngine, coalition: str, state: State, doc: Document) -> Document:
    """Real numbers for the closing screen: what was shared, how long, what it cost."""
    cmp = doc["compare"]
    meter = engine.server.cost_meter(coalition)
    started = doc.get("started")
    spent = None
    if meter is not None:
        unit = "$" if meter["currency"] == "USD" else f"{meter['currency']} "
        spent = f"{unit}{meter['spent']:.2f}"
    return {
        "calendars_shared": len(cmp["took_part"]) if cmp and cmp["state"] == "done" else 0,
        "minutes": (
            None
            if started is None
            else round((float(doc.get("ended_at") or engine.now()) - float(started)) / 60)
        ),
        "started_at": None
        if started is None
        else datetime.fromtimestamp(float(started), UTC).isoformat(),
        "ended": bool(doc.get("ended_at")),
        "cost": spent,
        # Ending a room deletes its credentials, so the count from before the end stands.
        "vendors": doc.get("outside", 0)
        if state.stage == "Dissolve"
        else sum(1 for p in people(state, doc) if not engine.is_hosted(coalition, p)),
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
    given = engine.server.registry.names(coalition)
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
            label = given.get(person) or f"{name} {counts[role]}"
            kind, status = "person", "signed"
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


def needs_of(viewer: str, state: State, doc: Document, latest: dict[str, str]) -> list[Document]:
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
                "result": latest.get(need["id"]),
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


def my_side(
    engine: RoomEngine, coalition: str, viewer: str, state: State, doc: Document
) -> Document:
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
    mine_brief = doc["briefs"].get(viewer)
    closes = None
    if mine_brief is not None and not closed:
        at = float(mine_brief["opened"]) + BRIEF_SECONDS
        closes = datetime.fromtimestamp(at, tz=UTC).isoformat()
    return {
        "brief": brief,
        "asks": asks_of(engine, coalition, viewer, state, doc),
        "brief_closes": closes,
        "feed": feed[-FEED_SHOWN:],
        "for_you": {pid: item["line"] for pid, item in lines.items()},
        "tasks": [],
    }


def asks_of(
    engine: RoomEngine, coalition: str, viewer: str, state: State, doc: Document
) -> list[Document]:
    """What the viewer is asked to decide, in plain words. A task request whose commitment is
    also pending is left out: the commitment is the one decision, and the answer closes both."""
    titles = {n["id"]: n["title"] for n in doc["needs"]}
    rows = engine.server.hosts[coalition].open_consents(viewer)
    committing = {t for r in rows if r["kind"] == "commitment" for t in subject_tasks(state, r)}
    out: list[Document] = []
    for row in rows:
        tasks = subject_tasks(state, row)
        named = ", ".join(titles.get(t, "a need") for t in tasks)
        kind = row["kind"]
        if kind == "task" and set(tasks) & committing:
            continue
        if kind == "charter":
            helpers = len(doc["helpers"])
            here = len(people(state, doc))
            text = (
                "You are the only person here so far"
                if here == 1
                else (f"The {here} people here decide together")
            )
            text += (
                f", and {helpers} helper agent{'s' if helpers != 1 else ''} joined."
                if helpers
                else "."
            )
        elif kind == "commitment":
            text = f"Commit to doing: {named}."
        elif kind == "plan":
            note = doc["plan_notes"].get(row["id"], {})
            text = f"Choose the plan {note['name']}." if note.get("name") else "Choose a plan."
        elif kind == "tension_option":
            text = f"Settle a clash between plans for: {named}."
        elif kind == "task":
            text = f"Agree that this needs doing: {named}."
        else:
            text = "A decision is needed from you."
        out.append({"kind": kind, "id": row["id"], "revision": row["revision"], "summary": text})
    return out


def subject_tasks(state: State, row: Document) -> list[str]:
    subject = state.subjects.get(f"{row['kind']}:{row['id']}")
    return list(subject["tasks"]) if subject else []


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
