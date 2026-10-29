# SPDX-License-Identifier: Apache-2.0
"""Acceptance test 3, fourth surface: the message door over a text channel (in-memory double).

Four members; needs arrive with different scopes. After each accepted event the door brings
every member up to date. Measured: time from the host's accepted event to each message handed to
the channel. Checked: every member's messages carry only that member's own scope, and a text
reply never becomes a signed decision.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from coalitionkit_runtime import SQLiteStore
from coalitionkit_surfaces import load_catalog
from coalitionkit_surfaces.message import (
    ConfirmGate,
    HostTreeSource,
    InMemoryChannel,
    MessageDoor,
    host_is_open,
    load_doors,
)

from .arena import NOW, PUBLIC, Arena, accepted
from .metrics import Recorder

Document = dict[str, Any]

SPEC_CATALOG = Path(__file__).resolve().parents[4] / "spec" / "catalog" / "coalitionkit-v0_9.json"
MEMBERS = ("p1", "p2", "p3", "p4")
#: Which members each kind of need is scoped to ("all" is the whole Coalition).
SCOPES: dict[str, list[str] | None] = {
    "all": None,
    "p1": ["p1"],
    "p2p3": ["p2", "p3"],
    "p4": ["p4"],
}
EVENTS = 60
DEADLINE = "2026-10-29T12:00:00Z"


@dataclass
class MessageDoorResult:
    recorder: Recorder
    #: (viewer, marker) pairs where a member saw a marker outside its scope.
    leaks: list[tuple[str, str]] = field(default_factory=lambda: list[tuple[str, str]]())
    #: Number of markers each member should see and did see.
    expected: dict[str, int] = field(default_factory=lambda: dict[str, int]())
    seen: dict[str, int] = field(default_factory=lambda: dict[str, int]())
    decisions_from_replies: int = 0
    tickets: int = 0
    max_message_length: int = 0


def _marker(index: int, kind: str) -> str:
    return f"Need {index:03d} scope {kind}"


def _audience(kind: str) -> list[str]:
    scope = SCOPES[kind]
    return list(MEMBERS) if scope is None else scope


def _scope_doc(kind: str) -> Document:
    scope = SCOPES[kind]
    return PUBLIC if scope is None else {"audience": "participants", "participants": scope}


def _emit_need(arena: Arena, index: int, kind: str) -> None:
    body: Document = {
        "description": _marker(index, kind),
        "requirements": [],
        "window": {"start": NOW, "end": DEADLINE},
    }
    accepted(arena.host.host_emit("need", body, _scope_doc(kind)))


def run_message_door(events: int = EVENTS, limit: int = 1000) -> MessageDoorResult:
    recorder = Recorder("doors_message")
    result = MessageDoorResult(recorder)
    store = SQLiteStore()
    arena = Arena.open(store, deciders=["p1", "p2"])
    try:
        for name in MEMBERS:
            arena.enroll(name)
        channel = InMemoryChannel(now=time.perf_counter)
        gate = ConfirmGate(host_is_open(arena.host))
        door = MessageDoor(
            channel,
            HostTreeSource(arena.host),
            load_catalog(SPEC_CATALOG),
            load_doors(SPEC_CATALOG),
            gate,
            limit=limit,
            min_interval=0.0,
        )
        for name in MEMBERS:
            door.sync(name)  # the first, full view of each member (not timed)
        kinds = list(SCOPES)
        for index in range(events):
            kind = kinds[index % len(kinds)]
            _emit_need(arena, index, kind)
            started = time.perf_counter()  # the host has accepted the event
            for name in MEMBERS:
                first = len(channel.sent)
                door.sync(name)
                for item in channel.sent[first:]:
                    recorder.sample("delivery_s", item.at - started)
                    recorder.count("messages")
        _check_scope(channel, events, kinds, result)
        _consent_flow(arena, channel, door, result)
        result.max_message_length = max((len(m.text) for m in channel.sent), default=0)
        recorder.count("max_message_length", result.max_message_length)
        recorder.count("scope_leaks", len(result.leaks))
        recorder.count("decisions_from_replies", result.decisions_from_replies)
    finally:
        arena.close()
    return result


_MARKER = re.compile(r"Need (\d{3}) scope (\w+)")


def _check_scope(
    channel: InMemoryChannel, events: int, kinds: list[str], result: MessageDoorResult
) -> None:
    for name in MEMBERS:
        text = "\n".join(channel.texts_to(name))
        found = {(int(i), k) for i, k in _MARKER.findall(text)}
        wanted = {(i, kinds[i % len(kinds)]) for i in range(events)}
        wanted = {(i, k) for i, k in wanted if name in _audience(k)}
        result.expected[name] = len(wanted)
        result.seen[name] = len(found & wanted)
        result.leaks += [(name, _marker(i, k)) for i, k in sorted(found - wanted)]


def _consent_flow(
    arena: Arena, channel: InMemoryChannel, door: MessageDoor, result: MessageDoorResult
) -> None:
    """A plan waits for p1's decision; a text reply opens the confirm step and signs nothing."""
    task = arena.need()
    arena.propose({task: "p1"})
    door.sync("p1")
    before = len(arena.events())
    channel.push("p1", "1")
    for outcome in door.poll():
        result.tickets += 1 if outcome.kind == "confirm" else 0
    after = arena.events()
    result.decisions_from_replies = sum(
        1
        for event in after[before:]
        if event["type"] == "coalition.decide" and event["on_behalf_of"] == "p1"
    )


# -- live: a model reads the messages and answers with an option number ----------------------------

LIVE_SYSTEM = (
    "You are a member reading a text message on your phone. Follow the reply instruction in the "
    "message. Answer with the reply only, nothing else."
)
#: (options, the slot the message asks for, whether the prompt is a consent request)
LIVE_SHAPES = [
    (2, 2, False),
    (3, 1, False),
    (3, 3, False),
    (4, 2, False),
    (5, 4, False),
    (6, 5, False),
    (2, 1, True),
    (4, 4, False),
]


def _column(*children: str) -> Document:
    return {"id": "root", "component": "Column", "children": list(children)}


class PromptSource:
    """One neutral question with numbered slots, as a tree for the door."""

    def __init__(self, count: int, wanted: int, consent: bool = False) -> None:
        self.count, self.wanted, self.consent = count, wanted, consent

    def tree(self, viewer: str) -> tuple[list[Document], Any]:
        if self.consent:
            ask: Document = {
                "id": "ask",
                "component": "ConsentCard",
                "summary": "A plan for member 1",
                "consequence": "Saying yes binds you to it.",
                "decision_deadline": DEADLINE,
                "subject": {"kind": "plan", "id": "plan1", "revision": 1},
            }
            text = "Reply with the number that opens the confirm step."
            note: Document = {"id": "note", "component": "Text", "text": text}
            return [_column("ask", "note"), ask, note], {}
        options = [{"id": f"s{k}", "label": f"Slot {k}"} for k in range(1, self.count + 1)]
        pick: Document = {"id": "pick", "component": "ChoicePicker", "options": options}
        text = f"Reply with the number of the option for Slot {self.wanted}."
        note = {"id": "note", "component": "Text", "text": text}
        return [_column("note", "pick"), note, pick], {}


@dataclass
class LivePromptResult:
    prompts: int = 0
    parsed: int = 0
    correct: int = 0
    replies: list[str] = field(default_factory=lambda: list[str]())


async def run_live_prompts(gateway: Any, recorder: Recorder) -> LivePromptResult:
    """Each prompt goes through a fresh door and an in-memory channel; the model sees exactly the
    text a person would, and its reply goes back through the same channel."""
    catalog, doors = load_catalog(SPEC_CATALOG), load_doors(SPEC_CATALOG)
    result = LivePromptResult()
    for index, (count, wanted, consent) in enumerate(LIVE_SHAPES):
        channel = InMemoryChannel()
        gate = ConfirmGate(lambda _viewer, _subject: True)
        door = MessageDoor(channel, PromptSource(count, wanted, consent), catalog, doors, gate)
        door.sync("p1")
        messages = [
            {"role": "system", "content": LIVE_SYSTEM},
            {"role": "user", "content": "\n".join(channel.texts_to("p1"))},
        ]
        done = await gateway.complete(
            "hosted_agent",
            messages,
            coalition_id=f"message-{index}",
            participant="p1",
            max_tokens=500,
            reasoning_effort="minimal",
        )
        result.prompts += 1
        result.replies.append(done.text.strip()[:40])
        channel.push("p1", done.text)
        [outcome] = door.poll()
        if outcome.kind in {"answer", "confirm"}:
            result.parsed += 1
            got = outcome.answer.option_id if outcome.answer else "confirm"
            result.correct += 1 if got == ("confirm" if consent else f"s{wanted}") else 0
    recorder.count("live_prompts", result.prompts)
    recorder.count("live_replies_parsed", result.parsed)
    recorder.count("live_replies_correct", result.correct)
    return result
