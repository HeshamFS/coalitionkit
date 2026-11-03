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
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

from coalitionkit_contracts import new_ulid, validate_payload
from coalitionkit_mcp.gateway import build_envelope
from coalitionkit_runtime.lifecycle import State

from ..adapter import Document
from .brief import given
from .model import ask
from .needs import tidy
from .seats import people, read_state

if TYPE_CHECKING:
    from .engine import RoomEngine

GRACE_S = 60.0  # how long a person's own (not hosted) agent has to offer
DEFAULT_MINUTES = 30  # a starting offer for someone who gave no limit
MIN_MINUTES = 5
HELPER_MINUTES = 15
NOTE_MAX = 300

SYSTEM = (
    "You are one person's agent in a small group room. Decide what to offer on the room's "
    "needs for that person, from what they told you. Offer only on needs you list by id, "
    "give minutes and money as whole numbers inside the limits they set, and set the effort "
    "(low, medium or high). Offer on no need they did not point at or cannot afford. Then "
    "write one short note to the person saying what you offered and why, in plain words."
)


class OfferItem(BaseModel):
    need_id: str
    minutes: int
    money: int
    effort: Literal["low", "medium", "high"]


class OffersReply(BaseModel):
    offers: list[OfferItem]
    note: str


@dataclass(frozen=True)
class Limits:
    minutes: int | None  # None: the person set no limit on time
    money: int  # 0 unless the person gave an amount in some other unit
    picked: tuple[str, ...]  # the words of what they chose to take on
    answered: bool  # they answered at least one question


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", text.lower()) if len(w) >= 4}


def limits(told: list[Document]) -> Limits:
    minutes: int | None = None
    money = 0
    picked: list[str] = []
    for item in told:
        if item["kind"] == "amount":
            unit = str(item["unit"]).lower()
            if "hour" in unit or unit in {"h", "hr", "hrs"}:
                minutes = int(item["answer"] * 60) + (minutes or 0)
            else:
                money += int(item["answer"])
        elif item["kind"] == "choice":
            picked.append(str(item["answer"]))
    return Limits(minutes, money, tuple(picked), bool(told))


def effort_of(minutes: int) -> Literal["low", "medium", "high"]:
    return "low" if minutes <= 30 else "medium" if minutes <= 120 else "high"


def chosen_needs(needs: list[Document], lim: Limits) -> list[Document]:
    """The needs the person pointed at; every need when they pointed at none that match."""
    wanted = [n for n in needs if any(words(p) & words(n["title"]) for p in lim.picked)]
    return wanted or needs


def rule_offers(needs: list[Document], lim: Limits) -> list[OfferItem]:
    """No model: offer on the needs they chose, inside the hours they gave. 0 hours is no offer."""
    if lim.minutes == 0:
        return []
    chosen = chosen_needs(needs, lim)
    if lim.minutes is None:
        per, count = DEFAULT_MINUTES, len(chosen)
    else:
        count = max(0, min(len(chosen), lim.minutes // MIN_MINUTES))
        per = lim.minutes // count if count else 0
    return [
        OfferItem(need_id=n["id"], minutes=per, money=0, effort=effort_of(per))
        for n in chosen[:count]
    ]


def checked(
    reply: OffersReply | None, needs: list[Document], lim: Limits
) -> list[OfferItem] | None:
    """The model's offers, clamped to the person's limits; None when none is usable."""
    if reply is None or lim.minutes == 0:
        return None
    known = {n["id"] for n in needs}
    left = lim.minutes
    out: list[OfferItem] = []
    for item in reply.offers:
        if item.need_id not in known or any(o.need_id == item.need_id for o in out):
            continue
        minutes = max(MIN_MINUTES, item.minutes)
        if left is not None:
            minutes = min(minutes, left)
            if minutes < MIN_MINUTES:
                break
            left -= minutes
        money = max(0, min(item.money, lim.money))
        out.append(
            OfferItem(need_id=item.need_id, minutes=minutes, money=money, effort=item.effort)
        )
    return out or None


async def send_offer(
    engine: RoomEngine, coalition: str, who: str, state: State, item: OfferItem
) -> str:
    """One signed offer from this seat's own agent. Closed fields only."""
    server = engine.server
    person = server.registry.hosted_for(coalition, who)
    payload: Document = {
        "offer_id": new_ulid(),
        "target": {"kind": "need", "id": item.need_id},
        "capacity": 1,
        "cost": {"minutes": item.minutes, "money": item.money, "effort": item.effort},
        "valid_until": state.tasks[item.need_id]["window"]["end"],
    }
    validate_payload("coalition.offer", payload)
    envelope = build_envelope(
        person, coalition, "coalition.offer", payload, scope={"audience": "coalition"}
    )
    reply = await engine.guard(server.ports[coalition].accept(envelope, person.card_url))
    if "error" in reply:
        raise RuntimeError("offer refused: " + str(reply["error"]["code"]))
    return str(envelope["event_id"])


def titles(needs: list[Document]) -> dict[str, str]:
    return {n["id"]: n["title"] for n in needs}


async def person_offers(engine: RoomEngine, coalition: str, who: str, state: State) -> None:
    doc = engine.read(coalition)
    needs = [n for n in doc["needs"] if n["id"] in state.tasks]
    told = given(engine, coalition, who)
    lim = limits(told)
    entry = engine.start_activity(coalition, "offering", "Choosing what to offer", seat=who)
    reply = None
    if lim.minutes != 0:
        reply = await ask(
            engine,
            coalition,
            "hosted_agent",
            SYSTEM,
            {
                "goal": state.charter["goal"],
                "needs": [{k: n[k] for k in ("id", "title", "kind", "detail")} for n in needs],
                "told_by_the_person": told,
                "limit_minutes": lim.minutes,
                "limit_money": lim.money,
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
    names = titles(needs)
    engine.end_activity(
        coalition,
        entry,
        state="done",
        source=source,
        label=f"Offered on {len(items)} of {len(needs)} needs" if items else "Made no offer",
    )
    engine.feed_add(coalition, who, feed_text(items, names, lim, source))
    if source == "model" and reply is not None and reply.note.strip():
        engine.feed_add(coalition, who, tidy(reply.note, NOTE_MAX))
    engine.update(coalition, lambda d: d["offers"].__setitem__(who, {"count": len(items)}))


def feed_text(items: list[OfferItem], names: dict[str, str], lim: Limits, source: str) -> str:
    if not items:
        why = "you gave it no hours" if lim.minutes == 0 else "nothing fit what you said"
        return f"Your agent made no offer, because {why}. You can still join a plan later."
    parts = "; ".join(f"{i.minutes} minutes on {names[i.need_id]}" for i in items)
    start = (
        "You skipped the questions, so your agent offered a starting amount: "
        if not lim.answered
        else "Your agent offered "
    )
    how = "" if source == "model" else " (fixed rules, no model)"
    return f"{start}{parts}{how}. Nothing here binds you: only your own yes on a plan does."


async def helper_offer(engine: RoomEngine, coalition: str, pid: str, state: State) -> None:
    info = engine.read(coalition)["helpers"][pid]
    if info["need_id"] not in state.tasks:
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
        engine.update(coalition, lambda d: d.__setitem__("offers_done", True))
        note_gaps(engine, coalition, state, doc)


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
