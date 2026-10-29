# SPDX-License-Identifier: Apache-2.0
"""The trusted confirm step a text reply can open. A reply never becomes a decision.

A ticket is a one-time, short-lived code bound to one person, one subject ``{kind, id,
revision}`` and, for a tension, one chosen option. The trusted confirm page redeems it and then
asks the person for the owner-signed decision. If the subject moved on to a newer revision (or
was answered or expired) the ticket is void.
"""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

Document = dict[str, Any]

TICKET_SECONDS = 300.0


class ConfirmVoid(Exception):
    """The confirm step cannot go ahead. ``code`` is one of the fixed values below."""

    UNKNOWN = "unknown_code"
    EXPIRED = "expired"
    USED = "already_used"
    STALE = "stale_subject"
    WRONG_VIEWER = "not_your_code"

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Ticket:
    code: str
    viewer: str
    subject: Document
    choice: str
    expires_at: float


def new_code() -> str:
    return secrets.token_urlsafe(9)


class ConfirmGate:
    """Issues and redeems tickets. It holds no key and builds no decision."""

    def __init__(
        self,
        is_open: Callable[[str, Document], bool],
        *,
        clock: Callable[[], float] = time.monotonic,
        ttl: float = TICKET_SECONDS,
        make_code: Callable[[], str] = new_code,
    ) -> None:
        """``is_open(viewer, subject)`` is true while the subject, at exactly that revision,
        still waits for this person's decision."""
        self._is_open, self._clock, self.ttl, self._make_code = is_open, clock, ttl, make_code
        self._tickets: dict[str, Ticket] = {}
        self._used: set[str] = set()

    def issue(self, viewer: str, subject: Document, choice: str) -> Ticket | None:
        """A ticket, or ``None`` when the subject is no longer open at that revision."""
        if not self._is_open(viewer, subject):
            return None
        ticket = Ticket(self._make_code(), viewer, dict(subject), choice, self._clock() + self.ttl)
        self._tickets[ticket.code] = ticket
        return ticket

    def redeem(self, code: str, viewer: str) -> Ticket:
        """Use the ticket once. Raises ``ConfirmVoid`` unless it is known, unused, unexpired,
        this person's and still at the subject's current revision."""
        ticket = self._tickets.get(code)
        if ticket is None:
            raise ConfirmVoid(ConfirmVoid.UNKNOWN)
        if code in self._used:
            raise ConfirmVoid(ConfirmVoid.USED)
        if ticket.viewer != viewer:
            raise ConfirmVoid(ConfirmVoid.WRONG_VIEWER)
        if self._clock() >= ticket.expires_at:
            raise ConfirmVoid(ConfirmVoid.EXPIRED)
        if not self._is_open(viewer, ticket.subject):
            raise ConfirmVoid(ConfirmVoid.STALE)
        self._used.add(code)
        return ticket
