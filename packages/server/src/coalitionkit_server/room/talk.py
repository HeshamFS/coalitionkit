# SPDX-License-Identifier: Apache-2.0
"""Talk: the agents speak to each other before the room plans, and again after a change.

Between Compare and Plans the room opens a Talk stage of at most ``room_talk_rounds`` rounds. In
a round each hosted seat's agent, one after another, reads the public thread and the offers and
either sends one ``coalition.say`` or passes; it may then revise its own offers through the same
path a change uses. Agents a person brought over MCP get a bounded wait to say their line. The
plans wait until the stage is over. A round in which nobody spoke ends the talk.

What an agent reads is public (the thread, the offers, the needs, the shared times) plus its own
vault. Before a line leaves, code checks its closed shape and that it holds none of that seat's own
private answers; a held line is written down as a stop. The Steward reviews every line that
leaves, as it does any member message. A sentence a person types for the others while the room
is still before its plans is kept as a whisper; their agent says it in the next round.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from coalitionkit_runtime.lifecycle import State

from ..adapter import Document
from .brief import given
from .model import ask
from .seats import people, read_state
from .talk_rules import Line, TalkReply, checked, leaked, private_values, whispered

if TYPE_CHECKING:
    from .engine import RoomEngine

WHISPERS = "_room_whispers"
MAX_REVISE = 2
THREAD_SHOWN = 24
PRIVATE_STOP = "talk-private-value"
PRIVATE_EXPLAIN = "The line held one of its person's private answers, so it was not said."

SYSTEM = (
    "You are one person's agent in a small group room, and the agents are talking before the "
    "room makes its plans. Read the thread and the offers, then either say one short useful "
    "thing or pass (speak false). Useful is: a question to one seat, a trade (I take this if "
    "you take that), a caveat the others should know before the plans, or agreeing or "
    "disagreeing with a line in the thread. Never greet, never repeat a line already said, "
    "never invent a fact. 'to' is 'room' or one seat id from seats; 're' is the number of the "
    "thread line you answer, or 0. Never state any value from told_by_your_person (no hours, "
    "amounts, times or answers): those are private, so speak of fit only in general words. If "
    "your_person_asked_you_to_say is not empty, say that for them, faithfully and briefly. In "
    "revise list the ids of needs whose offer you want to change because of what was said, "
    "for example a trade you accept or a need another seat fits better; else leave it empty. "
    "At most 280 characters."
)


# --- where the talk stands ------------------------------------------------------------------
def session_key(doc: Document) -> str:
    """One talk before the first plans, and one after each change."""
    change = doc.get("change")
    if not change:
        return "start"
    digest = hashlib.sha256(json.dumps(change, sort_keys=True).encode()).hexdigest()
    return "change:" + digest[:12]


def rounds_of(engine: RoomEngine) -> int:
    return int(engine.server.settings.room_talk_rounds)


def settled(engine: RoomEngine, doc: Document) -> bool:
    """True when the plans need not wait for talk: it is off, or this session is over."""
    return rounds_of(engine) == 0 or doc.get("talk_done") == session_key(doc)


def listening(engine: RoomEngine, doc: Document) -> bool:
    """A sentence for the others is kept for the agent to say, not sent as a chat line."""
    return bool(doc["begun"] and doc["briefs_done"]) and not settled(engine, doc)


def head_seq(state: State) -> int:
    return max((int(e.get("seq", 0)) for e in state.events.values()), default=0)


def say_events(state: State, viewer: str | None = None) -> list[Document]:
    found = [
        e
        for e in state.events.values()
        if e["type"] == "coalition.say" and (viewer is None or state.visible(e, viewer))
    ]
    return sorted(found, key=lambda e: int(e.get("seq", 0)))


# --- whispers -------------------------------------------------------------------------------
def whisper(engine: RoomEngine, coalition: str, who: str, text: str) -> Document:
    """Keep a sentence for the seat's own agent to say in the next round."""
    words = whispered(text)
    with engine.lock:
        kept = list(engine.vault(coalition, who).get(WHISPERS, []))
        at = datetime.fromtimestamp(engine.now(), UTC).isoformat()
        kept.append({"at": at, "text": words, "said": False})
        engine.vault_put(coalition, who, WHISPERS, kept[-10:])
    engine.feed_add(coalition, who, f"Your agent will say this in the talk: {words}")
    engine.wake(coalition)
    return {
        "route": "talk",
        "reply": "Your agent will say this to the others in the next round of talk.",
    }


def pending_whisper(engine: RoomEngine, coalition: str, who: str) -> str:
    kept = engine.vault(coalition, who).get(WHISPERS, [])
    return next((str(w["text"]) for w in kept if not w["said"]), "")


def whisper_said(engine: RoomEngine, coalition: str, who: str) -> None:
    with engine.lock:
        kept = [{**w, "said": True} for w in engine.vault(coalition, who).get(WHISPERS, [])]
        engine.vault_put(coalition, who, WHISPERS, kept)


# --- one turn -------------------------------------------------------------------------------
def labels_of(
    engine: RoomEngine, coalition: str, who: str, state: State, doc: Document
) -> dict[str, str]:
    from .view import seats_of

    return {s["seat"]: s["label"] for s in seats_of(engine, coalition, who, state, doc)}


def thread_of(state: State, labels: dict[str, str]) -> list[Document]:
    return [
        {
            "n": n,
            "id": e["event_id"],
            "from": labels.get(e["on_behalf_of"], e["on_behalf_of"]),
            "to": "room" if e["payload"]["to"] == "room" else labels.get(e["payload"]["to"], "?"),
            "intent": e["payload"]["intent"],
            "text": e["payload"]["text"],
        }
        for n, e in enumerate(say_events(state), start=1)
    ]


def public_offers(state: State, doc: Document, labels: dict[str, str], who: str) -> list[Document]:
    titles = {n["id"]: n["title"] for n in doc["needs"]}
    return [
        {
            "need_id": o["target"]["id"],
            "need": titles.get(o["target"]["id"], "a need"),
            "by": labels.get(str(o["owner"]), "a seat"),
            "yours": str(o["owner"]) == who,
            "minutes": o["cost"]["minutes"],
            "effort": o["cost"]["effort"],
        }
        for o in state.offers.values()
        if o["target"]["id"] in titles
    ]


def public_words(state: State, doc: Document) -> str:
    cmp: Document = doc.get("compare") or {}
    shared: dict[str, str] = {str(s["id"]): str(s["label"]) for s in doc["slots"]}
    raw: list[object] = list(cmp.get("slots") or [])
    ids = [str(s) for s in raw]
    common = [shared.get(s, s) for s in ids]
    goal = str(state.charter.get("goal", ""))
    return " ".join([goal, *(n["title"] for n in doc["needs"]), *common])


async def speak(
    engine: RoomEngine, coalition: str, who: str, state: State, talk: Document
) -> Document:
    """One seat's turn. Returns {said: event id or None, revised: [need ids]}."""
    doc = engine.read(coalition)
    labels = labels_of(engine, coalition, who, state, doc)
    thread = thread_of(state, labels)
    others = {p for p in people(state, doc) if p != who}
    live = [n for n in doc["needs"] if n["id"] in state.tasks]
    told = given(engine, coalition, who)
    asked_to = pending_whisper(engine, coalition, who)
    reply = await ask(
        engine,
        coalition,
        "hosted_agent",
        SYSTEM,
        {
            "goal": state.charter["goal"],
            "you": labels.get(who, "you"),
            "round": talk["round"],
            "seats": [{"id": p, "name": labels.get(p, p)} for p in others],
            "needs": [{"id": n["id"], "title": n["title"], "kind": n["kind"]} for n in live],
            "offers": public_offers(state, doc, labels, who),
            "thread": thread[-THREAD_SHOWN:],
            "told_by_your_person": told,
            "your_person_asked_you_to_say": asked_to,
        },
        TalkReply,
        verb="saying",
        label="Reading the talk and the offers",
        seat=who,
    )
    line = checked(reply, others, thread)
    if line is None and asked_to:
        line = Line(to="room", intent="caveat", text=asked_to, re=None)
    said = await send_line(engine, coalition, who, line, (told, asked_to), state, doc, labels)
    revised: list[str] = []
    wanted = [i for i in (reply.revise if reply else []) if i in {n["id"] for n in live}]
    if wanted and thread:
        revised = await revise(engine, coalition, who, wanted[:MAX_REVISE], thread, state)
    return {"said": said, "revised": revised}


async def send_line(
    engine: RoomEngine,
    coalition: str,
    who: str,
    line: Line | None,
    mine: tuple[list[Document], str],
    state: State,
    doc: Document,
    labels: dict[str, str],
) -> str | None:
    """Check the line against the seat's own private answers, then send it signed."""
    told, asked_to = mine
    if line is None:
        engine.note(coalition, "saying", "Had nothing to add", seat=who)
        return None
    target = None if line.to == "room" else line.to
    if leaked(line.text, private_values(told, public_words(state, doc)), asked_to):
        engine.record_stop(coalition, who, target, PRIVATE_STOP, PRIVATE_EXPLAIN)
        engine.feed_add(coalition, who, "Your agent kept a line back: it held one of your answers.")
        return None
    payload: Document = {"to": line.to, "intent": line.intent, "text": line.text}
    if line.re:
        payload["re"] = line.re
    sent = await engine.submit(coalition, who, "say", payload, {"audience": "coalition"}, to=target)
    if asked_to:
        whisper_said(engine, coalition, who)
    if sent is None:
        return None
    to = "the room" if target is None else labels.get(target, "a seat")
    engine.start_activity(
        coalition,
        "saying",
        f"Said to {to}: {line.text}",
        seat=who,
        state="done",
        event=str(sent["event_id"]),
    )
    engine.feed_add(coalition, who, f"Your agent said to {to}: {line.text}")
    return str(sent["event_id"])


async def revise(
    engine: RoomEngine,
    coalition: str,
    who: str,
    needs: list[str],
    thread: list[Document],
    state: State,
) -> list[str]:
    """Offer again on what the talk moved, the way a change re-offers. Never another's offer."""
    from .say import reoffer

    heard = " | ".join(f"{t['from']}: {t['text']}" for t in thread[-6:])
    change: Document = {
        "from": "",
        "text": f"What the agents said: {heard}",
        "moved": needs,
        "withdraw": False,
    }
    await reoffer(engine, coalition, who, change, state)
    at = datetime.fromtimestamp(engine.now(), UTC).isoformat()
    entry: Document = {"seat": who, "needs": needs, "at": at}
    engine.update(coalition, lambda d: d.setdefault("talk_revised", []).append(entry))
    return needs


# --- the stage ------------------------------------------------------------------------------
def ready(doc: Document) -> bool:
    cmp = doc.get("compare")
    return bool(
        doc["begun"]
        and doc["offers_done"]
        and cmp is not None
        and cmp["state"] == "done"
        and not doc["change_pending"]
    )


def save(engine: RoomEngine, coalition: str, talk: Document) -> None:
    engine.update(coalition, lambda d: d.__setitem__("talk", dict(talk)))


def opened(key: str, number: int, state: State, now: float) -> Document:
    return {
        "key": key,
        "round": number,
        "phase": "speaking",
        "spoke": [],
        "from_seq": head_seq(state),
        "since": now,
    }


async def advance(engine: RoomEngine, coalition: str) -> None:
    doc = engine.read(coalition)
    if rounds_of(engine) == 0 or not ready(doc):
        return
    key = session_key(doc)
    if doc.get("talk_done") == key:
        return
    state = await read_state(engine, coalition)
    talk: Document | None = doc.get("talk")
    if talk is None or talk["key"] != key:
        talk = opened(key, 1, state, engine.now())
        save(engine, coalition, talk)
        engine.note(coalition, "saying", "The agents are talking before the plans")
    if talk["phase"] == "speaking":
        hosted = [p for p in people(state, doc) if engine.is_hosted(coalition, p)]
        for who in hosted:
            if who in talk["spoke"]:
                continue
            await speak(engine, coalition, who, await read_state(engine, coalition), talk)
            talk["spoke"] = [*talk["spoke"], who]
            save(engine, coalition, talk)
        talk.update(phase="waiting", since=engine.now())
        save(engine, coalition, talk)
    await close_round(engine, coalition, talk, key)


async def close_round(engine: RoomEngine, coalition: str, talk: Document, key: str) -> None:
    """Wait a bounded time for agents brought over MCP, then open the next round or finish."""
    doc = engine.read(coalition)
    state = await read_state(engine, coalition)
    lines = [e for e in say_events(state) if int(e.get("seq", 0)) > int(talk["from_seq"])]
    outside = [p for p in doc.get("mcp_seats", []) if p in state.members]
    quiet = [p for p in outside if not any(e["on_behalf_of"] == p for e in lines)]
    wait = float(engine.server.settings.room_talk_wait_s)
    if quiet and engine.now() - float(talk["since"]) < wait:
        return
    if lines and talk["round"] < rounds_of(engine):
        save(engine, coalition, opened(key, talk["round"] + 1, state, engine.now()))
        engine.wake(coalition)
        return

    def finish(d: Document) -> None:
        d["talk"] = {**talk, "phase": "done"}
        d["talk_done"] = key

    engine.update(coalition, finish)
    said = len(say_events(state))
    engine.note(coalition, "saying", f"The talk is over ({said} lines); the plans come next")
    engine.wake_gardener(coalition)
