# SPDX-License-Identifier: Apache-2.0
"""Work: commitments, results, done, and the end of the room.

Once a plan is decided each assignee's agent asks for a commitment (``commit``); a person signs
it through the normal consent path, a helper signs only its own with its own owner key. When the
commitment is approved the assignee's agent makes the result (a ``coalition.observe`` with source
``document``) and a helper then reports ``done`` itself. A person's ``done`` only ever follows
their own click on ``/v1/room/done``. When the charter's deadline passes the room dissolves.
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from coalitionkit_contracts import new_ulid
from coalitionkit_runtime.lifecycle import State

from ..adapter import Document
from . import makers, results
from .seats import read_state, sign_asks

if TYPE_CHECKING:
    from .engine import RoomEngine


MONEY = re.compile(
    r"\b(money|costs?|pay|paid|price|prices|euros?|eur|dollars?|usd|afford|spend|fees?|expenses?)\b"
    r"|[€$£]",
    re.I,
)


def result_events(state: State) -> list[tuple[Document, Document]]:
    """(event, content) for every result in the log, oldest first."""
    found: list[tuple[Document, Document]] = []
    for event in sorted(state.events.values(), key=lambda e: e["seq"]):
        if event["type"] != "coalition.observe" or event["payload"].get("source") != "document":
            continue
        try:
            content: Any = json.loads(event["payload"]["content"])
        except ValueError:
            continue
        if isinstance(content, dict) and cast(Document, content).get("result") == 1:
            found.append((event, cast(Document, content)))
    return found


def active_commitment(state: State, task: str) -> Document | None:
    """The task's pending or approved commitment, if any."""
    for subject in state.subjects.values():
        if (
            subject["kind"] == "commitment"
            and subject["tasks"] == [task]
            and subject.get("status") in {"pending", "approved"}
        ):
            return subject
    return None


def offer_events(state: State) -> dict[tuple[str, str], str]:
    """(owner, need) -> the event id of that person's offer on it (the cheapest of several)."""
    by_offer = {
        str(e["payload"]["offer_id"]): str(e["event_id"])
        for e in state.events.values()
        if e["type"] == "coalition.offer"
    }
    best: dict[tuple[str, str], tuple[int, str]] = {}
    for offer_id, offer in state.offers.items():
        key = (str(offer["owner"]), str(offer["target"]["id"]))
        minutes = int(offer["cost"]["minutes"])
        if offer_id in by_offer and (key not in best or minutes < best[key][0]):
            best[key] = (minutes, by_offer[offer_id])
    return {k: v[1] for k, v in best.items()}


def facts_for(
    engine: RoomEngine, coalition: str, state: State, doc: Document, task: str
) -> Document:
    """The public facts a result may be made from: the goal, the plan, the offers, the times."""
    from .view import seats_of

    labels = {s["seat"]: s["label"] for s in seats_of(engine, coalition, "", state, doc)}
    needs = {n["id"]: n for n in doc["needs"]}
    refs = offer_events(state)
    plan: list[Document] = []
    for tid, t in state.tasks.items():
        who = t.get("assignee")
        if not who or tid not in needs or (t["status"] in {"withdrawn", "done"} and tid != task):
            continue
        minutes = [
            int(o["cost"]["minutes"])
            for o in state.offers.values()
            if o["owner"] == who and o["target"]["id"] == tid
        ]
        plan.append(
            {
                "title": needs[tid]["title"],
                "who": labels.get(who, who),
                "minutes": min(minutes) if minutes else 0,
                "offer_event": refs.get((who, tid)),
            }
        )
    slots = {s["id"]: s["label"] for s in doc["slots"]}
    compared: Document = doc["compare"] or {}
    shared: list[str] = list(compared.get("slots") or [])
    return {
        "goal": state.charter["goal"],
        "need": {k: needs[task][k] for k in ("id", "title", "kind", "detail")},
        "plan": plan,
        "people": [
            s["label"] for s in seats_of(engine, coalition, "", state, doc) if s["kind"] == "person"
        ],
        "amount": makers.stated_amount(str(state.charter["goal"])),
        "common": [{"id": s, "label": slots.get(s, s)} for s in shared],
        "now": datetime.fromtimestamp(engine.now(), UTC).isoformat(),
        "money": bool(
            MONEY.search(f"{state.charter['goal']} {needs[task]['title']} {needs[task]['detail']}")
        ),
    }


async def ask_commitments(engine: RoomEngine, coalition: str, state: State) -> None:
    """Each assignee's agent asks for its commitment; nobody is committed by this."""
    for task, t in state.tasks.items():
        who = t.get("assignee")
        if t["status"] != "decided" or not who or not engine.is_hosted(coalition, who):
            continue
        if active_commitment(state, task) is not None:
            continue
        payload: Document = {"commitment_id": new_ulid(), "task_id": task, "status": "pending"}
        sent = await engine.submit(coalition, who, "commit", payload, {"audience": "coalition"})
        if sent is not None:
            engine.note(coalition, "committing", "Asked for a commitment", seat=who, need=task)


async def make_one(
    engine: RoomEngine, coalition: str, state: State, doc: Document, task: str, commitment: str
) -> None:
    who = str(state.tasks[task]["assignee"])
    kind = next(n["kind"] for n in doc["needs"] if n["id"] == task)
    facts = facts_for(engine, coalition, state, doc, task)
    known = set(state.events)
    title, data, tree, source = await results.make(engine, coalition, kind, who, task, facts, known)
    refs = [
        str(e)
        for e in [
            *(p["offer_event"] for p in facts["plan"]),
            state.tasks[task]["source"]["event_id"],
        ]
        if e
    ]
    content = {
        "result": 1,
        "need_id": task,
        "kind": kind,
        "title": title,
        "source": source,
        "sources": list(dict.fromkeys(refs)),
        "components": tree,
        "data": data,
    }
    sent = await engine.submit(
        coalition,
        who,
        "observe",
        {"source": "document", "content": json.dumps(content)},
        {"audience": "coalition"},
    )

    def mark(d: Document) -> None:
        d["made"][task] = {
            "commitment": commitment,
            "result": sent["event_id"] if sent else None,
            "held": sent is None,
        }

    engine.update(coalition, mark)


async def make_results(engine: RoomEngine, coalition: str, state: State, doc: Document) -> None:
    """Make the result of every committed task whose commitment has none yet."""
    todo: list[tuple[str, str]] = []
    for task, t in state.tasks.items():
        who = t.get("assignee")
        active = active_commitment(state, task)
        if t["status"] != "committed" or not who or active is None or not active["tasks"]:
            continue
        if not engine.is_hosted(coalition, who) or active.get("suspended"):
            continue
        if doc["made"].get(task, {}).get("commitment") != active["id"]:
            todo.append((task, str(active["id"])))
    await asyncio.gather(*(make_one(engine, coalition, state, doc, t, c) for t, c in todo))


async def helpers_report(engine: RoomEngine, coalition: str, state: State, doc: Document) -> None:
    """A helper reports done once its own result is in; a person's done is their own click."""
    for task, t in state.tasks.items():
        who = t.get("assignee")
        made = doc["made"].get(task)
        if (
            who is not None
            and who in doc["helpers"]
            and t["status"] == "committed"
            and made
            and made["result"]
            and not made.get("done")
        ):
            evidence = [{"kind": "result", "ref": made["result"], "verified_by": who}]
            sent = await engine.submit(
                coalition,
                who,
                "done",
                {"task_id": task, "evidence": evidence},
                {"audience": "coalition"},
            )
            engine.update(coalition, lambda d, k=task: d["made"][k].__setitem__("done", True))
            if sent is not None:
                engine.note(coalition, "making", "Reported done", seat=who, need=task)


def can_mark_done(state: State, doc: Document, who: str, task: str) -> bool:
    """Their approved commitment has a result, and the task is not done."""
    t = state.tasks.get(task)
    made = doc["made"].get(task)
    active = active_commitment(state, task)
    return bool(
        t
        and t.get("assignee") == who
        and who not in doc["helpers"]
        and t["status"] == "committed"
        and active
        and active["status"] == "approved"
        and made
        and made["result"]
        and made["commitment"] == active["id"]
    )


async def mark_done(engine: RoomEngine, coalition: str, who: str, task: str) -> Document | None:
    state = await read_state(engine, coalition)
    doc = engine.read(coalition)
    if not can_mark_done(state, doc, who, task):
        raise LookupError(task)
    evidence = [{"kind": "result", "ref": doc["made"][task]["result"], "verified_by": who}]
    return await engine.submit(
        coalition, who, "done", {"task_id": task, "evidence": evidence}, {"audience": "coalition"}
    )


async def advance(engine: RoomEngine, coalition: str) -> None:
    doc = engine.read(coalition)
    if not doc["begun"] or not doc["offers_done"]:
        return
    state = await read_state(engine, coalition)
    await ask_commitments(engine, coalition, state)
    for helper in doc["helpers"]:
        if helper in state.members:
            await sign_asks(engine, coalition, helper, {"commitment"})
    state = await read_state(engine, coalition)
    await make_results(engine, coalition, state, doc)
    doc = engine.read(coalition)
    state = await read_state(engine, coalition)
    await helpers_report(engine, coalition, state, doc)
    await finish_if_due(engine, coalition, state)


async def finish_if_due(engine: RoomEngine, coalition: str, state: State) -> None:
    """The deadline ends the room: the same dissolve the owner can ask for."""
    from ..genesis import dissolve_coalition

    deadline = datetime.fromisoformat(str(state.charter["deadline"]).replace("Z", "+00:00"))
    if state.stage == "Dissolve" or datetime.fromtimestamp(engine.now(), UTC) < deadline:
        return
    engine.note(coalition, "ending", "The deadline has come; the room ends")
    await engine.thread(dissolve_coalition, engine.server, coalition, "deadline")
