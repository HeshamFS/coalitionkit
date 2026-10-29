# SPDX-License-Identifier: Apache-2.0
"""Who a WhatsApp id is. A binding is made only by a single-use invitation code the person
sends as their first message. Codes are stored as SHA-256 digests."""

from __future__ import annotations

import hashlib
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

INVITE_SECONDS = 24 * 60 * 60.0


def _digest(code: str) -> str:
    return hashlib.sha256(code.strip().encode()).hexdigest()


@dataclass(frozen=True)
class _Invite:
    viewer: str
    expires_at: float


class Bindings:
    """In-memory store; the interface is what a durable one would copy."""

    def __init__(
        self, *, clock: Callable[[], float] = time.monotonic, ttl: float = INVITE_SECONDS
    ) -> None:
        self._clock, self._ttl = clock, ttl
        self._invites: dict[str, _Invite] = {}
        self._by_wa: dict[str, str] = {}
        self._by_viewer: dict[str, str] = {}
        self._lock = threading.Lock()

    def invite(self, viewer: str) -> str:
        """A fresh code for this viewer (shown once to the owner, out of band)."""
        code = secrets.token_urlsafe(9)
        with self._lock:
            self._invites[_digest(code)] = _Invite(viewer, self._clock() + self._ttl)
        return code

    def redeem(self, wa_id: str, code: str) -> str | None:
        """Bind ``wa_id`` to the code's viewer and burn the code, or return ``None``. An id that
        is already bound cannot be rebound, and a viewer keeps one id."""
        with self._lock:
            if wa_id in self._by_wa:
                return None
            invite = self._invites.pop(_digest(code), None)
            if invite is None or invite.expires_at <= self._clock():
                return None
            old = self._by_viewer.pop(invite.viewer, None)
            if old is not None:
                self._by_wa.pop(old, None)
            self._by_wa[wa_id] = invite.viewer
            self._by_viewer[invite.viewer] = wa_id
            return invite.viewer

    def viewer_of(self, wa_id: str) -> str | None:
        with self._lock:
            return self._by_wa.get(wa_id)

    def wa_id_of(self, viewer: str) -> str | None:
        with self._lock:
            return self._by_viewer.get(viewer)
