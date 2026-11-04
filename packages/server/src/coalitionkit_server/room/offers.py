# SPDX-License-Identifier: Apache-2.0
"""Offers: each seat's agent offers what its person said they can give.

A hosted seat's agent reads the needs and its own brief, and sends real ``coalition.offer``
events signed with its own key. The model may only choose among the room's needs and fill
numbers; code clamps them to what the person said (hours, money) and builds the payload from
closed fields. Whatever prose the model adds goes to that seat's own feed and nowhere else. A
helper offers on the one need it serves. A person who brought their own agent is not driven:
the room gives it a short grace and moves on.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from coalitionkit_contracts import new_ulid, validate_payload
from coalitionkit_runtime.lifecycle import State

from ..adapter import Document
from . import websearch
from .brief import given
from .model import ask
from .offer_rules import (
    HELPER_MINUTES,
    OfferItem,
    OffersReply,
    checked,
    cover_items,
    feed_text,
    limits,
    rule_offers,
)
from .seats import people, read_state

if TYPE_CHECKING:
    from .engine import RoomEngine

GRACE_S = 60.0  # how long a person's own (not hosted) agent has to offer
NOTE_MAX = 300

OFFER_SYSTEM = (
    "You are one person's agent in a small group room. An offer says: I could do this need, "
    "and it would take me about this long. Offers are alternatives, not a bill; the room "
    "picks among everyone's offers. Offer on every need this person could do, with your own "
    "honest estimate in minutes for each one, different from need to need and never above "
    "the most they said they would give to any one job. Set the effort from fit: low for "
    "what they prefer, medium for the rest, high for what they would rather not do. Money is "
    "the amount this person would pay out of their own pocket for the job, a whole number "
    "no larger than the most they would pay, and usually 0. Money in the goal is the "
    "group's shared budget; it is not a cost of any one offer. Write the note in plain "
    "words, never quote a limit or its value, and never say a cost is zero because of a limit."
)


async def send_offer(
    engine: RoomEngine,
    coalition: str,
    who: str,
    state: State,
    item: OfferItem,
    *,
    offer_id: str | None = None,
    valid_until: str | None = None,
) -> str | None:
    """One signed offer from this seat's own agent, closed fields only; None if it was held."""
    payload: Document = {
        "offer_id": offer_id or new_ulid(),
        "target": {"kind": "need", "id": item.need_id},
        "capacity": 1,
        "cost": {"minutes": item.minutes, "money": item.money, "effort": item.effort},
        "valid_until": valid_until or state.tasks[item.need_id]["window"]["end"],
    }
    validate_payload("coalition.offer", payload)
    sent = await engine.submit(coalition, who, "offer", payload, {"audience": "coalition"})
    return str(sent["event_id"]) if sent else None


def titles(needs: list[Document]) -> dict[str, str]:
    return {n["id"]: n["title"] for n in needs}


async def person_offers(engine: RoomEngine, coalition: str, who: str, state: State) -> None:
    doc = engine.read(coalition)
    needs = [n for n in doc["needs"] if n["id"] in state.tasks]
    told = given(engine, coalition, who)
    lim = limits(told)
    entry = engine.start_activity(coalition, "offering", "Choosing what to offer", seat=who)
    reply = None
    if not lim.silent:
        reply = await ask(
            engine,
            coalition,
            "hosted_agent",
            OFFER_SYSTEM,
            {
                "goal": state.charter["goal"],
                "person": engine.name_of(coalition, who),
                "needs": [{k: n[k] for k in ("id", "title", "kind", "detail")} for n in needs],
                "told_by_the_person": told,
                "most_minutes_for_any_one_job": lim.cap,
                "most_money_they_would_pay_themselves": lim.money,
            },
            OffersReply,
            verb="offering",
            label="Reading your answers to choose offers",
            seat=who,
            only=who,
        )
    items = checked(reply, needs, lim)
    source = "model" if items else "rules"
    if items is None:
        items = rule_offers(needs, lim)
    for item in items:
        await send_offer(engine, coalition, who, state, item)
    goal = str(state.charter["goal"])
    await websearch.at_offer(engine, coalition, who, goal, needs, {i.need_id for i in items})
    names = titles(needs)
    engine.end_activity(
        coalition,
        entry,
        state="done",
        source=source,
        label=f"Offered on {len(items)} of {len(needs)} needs" if items else "Made no offer",
    )
    engine.feed_add(coalition, who, feed_text(items, names, lim, source))
    engine.update(coalition, lambda d: d["offers"].__setitem__(who, {"count": len(items)}))


async def helper_offer(engine: RoomEngine, coalition: str, pid: str, state: State) -> None:
    info = engine.read(coalition)["helpers"][pid]
    if info.get("kind") == "device" or info["need_id"] not in state.tasks:
        return
    item = OfferItem(need_id=info["need_id"], minutes=HELPER_MINUTES, money=0, effort="low")
    await send_offer(engine, coalition, pid, state, item)
    engine.note(coalition, "offering", "Offered on the need it serves", seat=pid)
    engine.update(coalition, lambda d: d["offers"].__setitem__(pid, {"count": 1}))


def owners_with_offers(state: State) -> set[str]:
    return {str(o["owner"]) for o in state.offers.values()}


def seeded(engine: RoomEngine, coalition: str, state: State, doc: Document) -> bool:
    """Every need is an event (or was refused), so offers have something to point at."""
    gone = engine.refused_needs(coalition)
    return all(n["id"] in state.tasks or n["id"] in gone for n in doc["needs"])


async def advance(engine: RoomEngine, coalition: str) -> None:
    """Make the offers of every hosted seat; give other agents a grace; then say who has none."""
    doc = engine.read(coalition)
    if not doc["briefs_done"] or doc["offers_done"]:
        return
    state = await read_state(engine, coalition)
    if not seeded(engine, coalition, state, doc):
        return
    now = engine.now()
    if doc["offers_open"] is None:
        engine.update(coalition, lambda d: d.__setitem__("offers_open", now))
        doc["offers_open"] = now
    had = owners_with_offers(state)
    seated = people(state, doc)
    hosted = [p for p in seated if engine.is_hosted(coalition, p)]
    todo = [p for p in hosted if p not in doc["offers"]]
    for who in todo:
        if who in had:  # offered before a restart; do not offer twice
            engine.update(coalition, lambda d, w=who: d["offers"].__setitem__(w, {"count": 0}))
    work = [person_offers(engine, coalition, who, state) for who in todo if who not in had]
    work += [
        helper_offer(engine, coalition, pid, state)
        for pid in doc["helpers"]
        if pid not in doc["offers"] and pid in state.members and pid not in had
    ]
    await asyncio.gather(*work)
    doc = engine.read(coalition)
    state = await read_state(engine, coalition)
    waiting = [p for p in seated if p not in hosted and p not in owners_with_offers(state)]
    late = now - float(doc["offers_open"]) < GRACE_S
    done = all(p in doc["offers"] for p in [*hosted, *doc["helpers"]]) and not (waiting and late)
    if done:
        await cover(engine, coalition, state, doc)
        state = await read_state(engine, coalition)
        engine.update(coalition, lambda d: d.__setitem__("offers_done", True))
        note_gaps(engine, coalition, state, doc)


def live_targets(state: State, now: str) -> set[str]:
    """Needs that have an offer still open (an offer ended on purpose does not count)."""
    at = datetime.fromisoformat(now)
    return {
        str(o["target"]["id"])
        for o in state.offers.values()
        if datetime.fromisoformat(o["valid_until"]) > at
    }


async def cover(
    engine: RoomEngine,
    coalition: str,
    state: State,
    doc: Document,
    avoid: frozenset[str] = frozenset(),
) -> None:
    """Make sure no need is left without an offer, unless every hosted person said 0 hours.

    A plan has to cover every need, and an offer only says "I could do this, about this long",
    so anyone who gave any hours can cover a bare need. These offers bind no one: the person's
    own yes on a plan is what counts, and their feed says so.
    """
    offered = live_targets(state, datetime.fromtimestamp(engine.now(), UTC).isoformat())
    gone = engine.refused_needs(coalition)
    done = {k for k, t in state.tasks.items() if t["status"] in {"done", "withdrawn"}}
    needs = [n for n in doc["needs"] if n["id"] not in gone and n["id"] not in done]
    bare = [n for n in needs if n["id"] not in offered]
    hosted = [p for p in people(state, doc) if engine.is_hosted(coalition, p) and p not in avoid]
    if not bare or not hosted:
        return
    mine = {who: limits(given(engine, coalition, who)) for who in hosted}
    taken = cover_items(needs, bare, mine)
    names = titles(doc["needs"])
    for who, items in taken.items():
        for item in items:
            await send_offer(engine, coalition, who, state, item)
        engine.note(coalition, "offering", "Covered a need nobody had offered on", seat=who)
        engine.feed_add(
            coalition,
            who,
            f"Nobody had offered on {', '.join(names[i.need_id] for i in items)}, so your agent "
            "also offered on it. Nothing binds you until you say yes to a plan.",
        )


def note_gaps(engine: RoomEngine, coalition: str, state: State, doc: Document) -> None:
    """Say plainly which needs nobody offered on; a plan cannot cover them."""
    offered = {str(o["target"]["id"]) for o in state.offers.values()}
    gone = engine.refused_needs(coalition)
    bare = [n for n in doc["needs"] if n["id"] not in offered and n["id"] not in gone]
    if not bare:
        return
    names = ", ".join(n["title"] for n in bare)
    engine.start_activity(
        coalition,
        "planning",
        f"Nobody has offered on {names}. A plan covers every need, so it waits for an offer.",
        state="failed",
    )
    engine.update(coalition, lambda d: d.__setitem__("gaps_noted", [n["id"] for n in bare]))
