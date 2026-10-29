# SPDX-License-Identifier: Apache-2.0
"""The channel port: send text to a person, receive their replies. No transport lives here."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Reply:
    viewer: str
    text: str


@dataclass(frozen=True)
class Sent:
    viewer: str
    text: str
    at: float


class MessageChannel(Protocol):
    """A text channel to one person per ``viewer`` id. Real adapters live outside the core."""

    def send(self, viewer: str, text: str) -> None: ...

    def receive(self) -> list[Reply]:
        """Replies that arrived since the last call, oldest first."""
        ...


@dataclass
class InMemoryChannel:
    """The test double: keeps what was sent (with the time) and a queue of replies to deliver."""

    now: Callable[[], float] = time.perf_counter
    sent: list[Sent] = field(default_factory=lambda: list[Sent]())
    _inbox: deque[Reply] = field(default_factory=lambda: deque[Reply]())

    def send(self, viewer: str, text: str) -> None:
        self.sent.append(Sent(viewer, text, self.now()))

    def receive(self) -> list[Reply]:
        replies = list(self._inbox)
        self._inbox.clear()
        return replies

    def push(self, viewer: str, text: str) -> None:
        """A person's reply arrives."""
        self._inbox.append(Reply(viewer, text))

    def texts_to(self, viewer: str) -> list[str]:
        return [item.text for item in self.sent if item.viewer == viewer]
