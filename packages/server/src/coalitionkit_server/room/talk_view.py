# SPDX-License-Identifier: Apache-2.0
"""``room.talk``: the thread the agents said, and where the Talk stage stands, for one viewer.

The thread comes from the log, limited to what this viewer's projection may see. ``mine`` holds
only this viewer's own whisper that their agent has not said yet.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from coalitionkit_runtime.lifecycle import State

from ..adapter import Document
from .talk import (
    HIDDEN,
    listening,
    pending_whisper,
    rounds_of,
    said_text,
    say_events,
    session_key,
    settled,
)

if TYPE_CHECKING:
    from .engine import RoomEngine


def stage_of(event: Document, marks: list[tuple[int, str]]) -> str:
    """``start`` for a line before the first plans, ``change`` for one said after a change."""
    seq = int(event.get("seq", 0))
    return "change" if any(seq > at for at, _ in marks) else "start"


def talk_of(
    engine: RoomEngine, coalition: str, viewer: str, state: State, doc: Document
) -> Document:
    talk: Document = doc.get("talk") or {}
    current = talk.get("key") == session_key(doc)
    is_open = bool(talk) and current and not settled(engine, doc)
    ripples = [
        (int(e.get("seq", 0)), e["event_id"])
        for e in state.events.values()
        if e["type"] == "coalition.ripple"
    ]
    waiting = [
        p
        for p in doc.get("mcp_seats", [])
        if is_open and talk.get("phase") == "waiting" and p in state.members
    ]
    return {
        "open": is_open,
        "round": int(talk.get("round", 0)) if talk else 0,
        "rounds": rounds_of(engine),
        "stage": None if not talk else ("change" if talk["key"] != "start" else "start"),
        "waiting_for": waiting,
        "thread": [
            {
                "seq": int(e.get("seq", 0)),
                "id": e["event_id"],
                "from": e["on_behalf_of"],
                "to": e["payload"]["to"],
                "intent": e["payload"]["intent"],
                "text": said_text(e, viewer),
                "redacted": said_text(e, viewer) == HIDDEN,
                "re": e["payload"].get("re"),
                "stage": stage_of(e, ripples),
            }
            for e in say_events(state, viewer)
        ],
        "revised": list(doc.get("talk_revised", [])),
        "mine": {
            "whisper": pending_whisper(engine, coalition, viewer) or None,
            "listening": listening(engine, doc),
        },
    }
