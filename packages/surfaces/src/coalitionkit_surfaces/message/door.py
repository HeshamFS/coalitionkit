# SPDX-License-Identifier: Apache-2.0
"""The message door: renders one viewer's tree to a channel, sends deltas, parses replies.

A reply is parsed to exactly one numbered option or answered with a fixed help line; no model
reads free text. An ``answer`` option becomes a typed answer. A ``confirm`` option can only
open the trusted confirm step (see ``ConfirmGate``): this module holds no key and never builds
a ``coalition.decide``.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from ..catalog import Catalog, validate_surface
from .channel import MessageChannel
from .confirm import ConfirmGate, Ticket
from .doors import Doors
from .render import INVALID_VIEW, Option, Rendered, Section, render_tree
from .split import DEFAULT_LIMIT, split_blocks

Document = dict[str, Any]

HELP = "Reply with one option number, for example 1. Other replies are not understood."
NOTHING_OPEN = "Nothing is waiting for a reply."
STALE = "This request changed. Wait for the new message."
MIN_INTERVAL = 30.0
_REPLY = re.compile(r"(?:option\s*)?#?\s*(\d{1,3})\s*[.)]?", re.IGNORECASE)
_MAX_REPLY = 40


class TreeSource(Protocol):
    """Where a viewer's own tree comes from: ``(components, data_model)``, already limited to
    that viewer's scope."""

    def tree(self, viewer: str) -> tuple[list[Document], Any]: ...


@dataclass(frozen=True)
class TypedAnswer:
    viewer: str
    component_id: str
    option_id: str
    label: str


@dataclass(frozen=True)
class ReplyOutcome:
    kind: Literal["answer", "confirm", "rejected", "stale"]
    viewer: str
    answer: TypedAnswer | None = None
    ticket: Ticket | None = None


def parse_reply(text: str, options: list[Option]) -> Option | None:
    """The one option the reply names, or ``None``. Plain ``2``, ``2.``, ``#2`` and ``option 2``
    count; so do other scripts' digits. Anything else does not."""
    if len(text) > _MAX_REPLY:
        return None
    found = _REPLY.fullmatch(text.strip())
    if found is None:
        return None
    number = int(found.group(1))
    return next((o for o in options if o.number == number), None)


def headline(section: Section) -> str:
    first = section.text.split("\n", 1)[0]
    return first if len(first) <= 60 else first[:57] + "..."


def delta_lines(before: Rendered, after: Rendered) -> list[str]:
    """One short line per affected item: new, changed or removed."""
    old = {s.key: s for s in before.sections}
    new = {s.key: s for s in after.sections}
    lines = [f"New: {headline(s)}" for k, s in new.items() if k not in old]
    lines += [f"Changed: {headline(s)}" for k, s in new.items() if k in old and old[k] != s]
    lines += [f"Removed: {headline(s)}" for k, s in old.items() if k not in new]
    return lines


class MessageDoor:
    def __init__(
        self,
        channel: MessageChannel,
        source: TreeSource,
        catalog: Catalog,
        doors: Doors,
        gate: ConfirmGate,
        *,
        clock: Callable[[], float] = time.monotonic,
        limit: int = DEFAULT_LIMIT,
        min_interval: float = MIN_INTERVAL,
        link_base: str | None = None,
    ) -> None:
        self.channel, self.source, self.catalog, self.doors = channel, source, catalog, doors
        self.gate, self.clock, self.limit = gate, clock, limit
        self.min_interval, self.link_base = min_interval, link_base
        split_blocks(["x"], limit)  # refuses a limit that is too small, at once
        self._sent: dict[str, Rendered] = {}
        self._last_send: dict[str, float] = {}
        self._pending: set[str] = set()
        self._queue: dict[str, list[str]] = {}
        self._target: dict[str, Rendered] = {}

    # -- state to the person -------------------------------------------------------------------

    def _render(self, viewer: str) -> Rendered:
        components, data = self.source.tree(viewer)
        errors = validate_surface(self.catalog, self.catalog.catalog_id, components, data)
        if errors:
            return Rendered([Section("root", INVALID_VIEW)], [])
        return render_tree(components, data, self.doors)

    def _deliver(self, viewer: str, blocks: list[str]) -> int:
        """Send one-off texts (help lines, confirm codes). No view state hangs on them."""
        messages = split_blocks([b for b in blocks if b], self.limit)
        for text in messages:
            self.channel.send(viewer, text)
        return len(messages)

    def _drain(self, viewer: str) -> int:
        """Hand the queued parts to the channel one by one. A part leaves the queue only after
        its send returned, so a failure keeps the unsent rest; the view counts as sent (and
        the waiting time starts) only when the last part is out."""
        queue = self._queue[viewer]
        sent = 0
        while queue:
            self.channel.send(viewer, queue[0])
            queue.pop(0)
            sent += 1
        self._sent[viewer] = self._target.pop(viewer)
        self._last_send[viewer] = self.clock()
        self._pending.discard(viewer)
        del self._queue[viewer]
        return sent

    def sync(self, viewer: str) -> int:
        """Bring this person up to date. The first call sends the full view; later calls send one
        short line per changed item, and only when this viewer's own view changed. Returns the
        number of messages handed to the channel.

        If the channel raises, nothing is lost: the unsent parts stay queued and the next
        ``sync`` or ``flush`` sends exactly those (parts already delivered are not repeated)."""
        if viewer in self._queue:
            return self._drain(viewer)
        current = self._render(viewer)
        previous = self._sent.get(viewer)
        if previous is None:
            blocks = [s.text for s in current.sections] + [current.options_block()]
        elif previous == current:
            self._pending.discard(viewer)
            return 0
        elif self.clock() - self._last_send.get(viewer, 0.0) < self.min_interval:
            self._pending.add(viewer)  # sent later against the last state actually sent
            return 0
        else:
            lines = delta_lines(previous, current)
            moved = previous.options != current.options
            block = current.options_block() if moved else ""
            blocks = ["\n".join(lines), block or ("" if not moved else NOTHING_OPEN)]
        self._queue[viewer] = split_blocks([b for b in blocks if b], self.limit)
        self._target[viewer] = current
        return self._drain(viewer)

    def flush(self) -> int:
        """Send the held deltas of viewers whose waiting time has passed, and finish any
        message a failed send left behind."""
        return sum(self.sync(viewer) for viewer in sorted(self._pending | set(self._queue)))

    # -- replies ---------------------------------------------------------------------------------

    def poll(self) -> list[ReplyOutcome]:
        return [self.handle_reply(r.viewer, r.text) for r in self.channel.receive()]

    def handle_reply(self, viewer: str, text: str) -> ReplyOutcome:
        shown = self._sent.get(viewer)
        options = shown.options if shown is not None else []
        option = parse_reply(text, options)
        if option is None:
            self._deliver(viewer, [HELP if options else NOTHING_OPEN])
            return ReplyOutcome("rejected", viewer)
        if option.kind == "answer":
            answer = TypedAnswer(viewer, option.component_id, option.option_id, option.label)
            self._deliver(viewer, [f"Received: {option.label}"])
            return ReplyOutcome("answer", viewer, answer=answer)
        ticket = (
            self.gate.issue(viewer, option.subject, option.option_id) if option.subject else None
        )
        if ticket is None:
            self._deliver(viewer, [STALE])
            return ReplyOutcome("stale", viewer)
        self._deliver(viewer, [self._confirm_text(ticket)])
        return ReplyOutcome("confirm", viewer, ticket=ticket)

    def _confirm_text(self, ticket: Ticket) -> str:
        minutes = max(1, round(self.gate.ttl / 60))
        where = f"{self.link_base.rstrip('/')}/{ticket.code}" if self.link_base else ""
        way = f"open {where} or enter the code {ticket.code}" if where else f"enter {ticket.code}"
        return (
            f"To go on, {way} on the trusted confirm page. It works once and expires in "
            f"{minutes} min. Your reply here is not your decision."
        )
