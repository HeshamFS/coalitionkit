# SPDX-License-Identifier: Apache-2.0
"""A line of talk a policy redacted keeps its words for its sender only."""

from __future__ import annotations

from coalitionkit_server.adapter import Document
from coalitionkit_server.room.talk import HIDDEN, said_text, thread_of


def line(redact: list[str]) -> Document:
    return {
        "event_id": "e1",
        "type": "coalition.say",
        "seq": 1,
        "on_behalf_of": "p1",
        "scope": {"audience": "coalition", "redact": redact},
        "payload": {"to": "room", "intent": "inform", "text": "a private word"},
    }


class OneLine:
    """Just enough of the room state for the thread: one line every seat may see."""

    def __init__(self, event: Document) -> None:
        self.events = {event["event_id"]: event}

    def visible(self, event: Document, viewer: str) -> bool:
        return True


def test_a_redacted_line_is_hidden_from_everyone_but_its_sender() -> None:
    hidden = line(["payload.text"])
    assert said_text(hidden, "p1") == "a private word"
    assert said_text(hidden, "p2") == HIDDEN
    assert said_text(hidden, None) == HIDDEN
    assert said_text(line([]), "p2") == "a private word"


def test_another_seats_agent_reads_only_that_the_line_was_hidden() -> None:
    state = OneLine(line(["payload.text"]))
    labels = {"p1": "Seat one", "p2": "Seat two"}
    assert [t["text"] for t in thread_of(state, labels, "p2")] == [HIDDEN]  # type: ignore[arg-type]
    assert [t["text"] for t in thread_of(state, labels, "p1")] == ["a private word"]  # type: ignore[arg-type]
