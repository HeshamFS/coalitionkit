# SPDX-License-Identifier: Apache-2.0
"""Who a WhatsApp id is. A person binds by sending a single-use invitation code in any message,
with a bounded number of failed attempts per sender. Codes are stored as SHA-256 digests.

Persistence is behind ``BindingStore``; the server supplies one on its own database, and
``MemoryStore`` is the in-process default for tests.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, Protocol

INVITE_SECONDS = 24 * 60 * 60.0
CODE_BYTES = 12  # 96 bits; token_urlsafe(12) is 16 characters
CODE_LENGTH = 16
MAX_FAILED = 3
ATTEMPT_WINDOW = 3600.0
_CANDIDATE = re.compile(rf"[A-Za-z0-9_-]{{{CODE_LENGTH}}}")
_MAX_CANDIDATES = 5


def digest(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


class BindingStore(Protocol):
    """Durable state. ``take_invite`` removes and returns in one step (single use)."""

    def add_invite(self, code_digest: str, viewer: str, expires_at: float) -> None: ...
    def take_invite(self, code_digest: str) -> tuple[str, float] | None: ...
    def bind(self, wa_id: str, viewer: str) -> bool:
        """Link them (dropping the viewer's earlier id); False if ``wa_id`` is already linked."""
        ...

    def viewer_of(self, wa_id: str) -> str | None: ...
    def wa_id_of(self, viewer: str) -> str | None: ...
    def viewers(self) -> list[str]:
        """Every linked viewer."""
        ...

    def note_failure(self, wa_id: str, at: float) -> None: ...
    def failures_since(self, wa_id: str, since: float) -> int: ...


class MemoryStore:
    def __init__(self) -> None:
        self._invites: dict[str, tuple[str, float]] = {}
        self._by_wa: dict[str, str] = {}
        self._by_viewer: dict[str, str] = {}
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def add_invite(self, code_digest: str, viewer: str, expires_at: float) -> None:
        with self._lock:
            self._invites[code_digest] = (viewer, expires_at)

    def take_invite(self, code_digest: str) -> tuple[str, float] | None:
        with self._lock:
            return self._invites.pop(code_digest, None)

    def bind(self, wa_id: str, viewer: str) -> bool:
        with self._lock:
            if wa_id in self._by_wa:
                return False
            old = self._by_viewer.pop(viewer, None)
            if old is not None:
                self._by_wa.pop(old, None)
            self._by_wa[wa_id], self._by_viewer[viewer] = viewer, wa_id
            return True

    def viewer_of(self, wa_id: str) -> str | None:
        with self._lock:
            return self._by_wa.get(wa_id)

    def wa_id_of(self, viewer: str) -> str | None:
        with self._lock:
            return self._by_viewer.get(viewer)

    def viewers(self) -> list[str]:
        with self._lock:
            return sorted(self._by_viewer)

    def note_failure(self, wa_id: str, at: float) -> None:
        with self._lock:
            self._failures.setdefault(wa_id, []).append(at)

    def failures_since(self, wa_id: str, since: float) -> int:
        with self._lock:
            kept = [t for t in self._failures.get(wa_id, []) if t >= since]
            self._failures[wa_id] = kept
            return len(kept)


Status = Literal["bound", "rejected", "locked", "silent"]


@dataclass(frozen=True)
class Redemption:
    """``rejected``: a failed attempt (counted). ``locked``: the attempt limit was just reached,
    send the lock line once. ``silent``: locked earlier in this window, send nothing."""

    status: Status
    viewer: str | None = None


class Bindings:
    def __init__(
        self,
        store: BindingStore | None = None,
        *,
        clock: Callable[[], float] = time.time,
        ttl: float = INVITE_SECONDS,
    ) -> None:
        self.store: BindingStore = store or MemoryStore()
        self._clock, self._ttl = clock, ttl
        self._lock = threading.Lock()

    def invite(self, viewer: str) -> str:
        """A fresh code for this viewer (shown once to the owner, out of band)."""
        code = secrets.token_urlsafe(CODE_BYTES)
        self.store.add_invite(digest(code), viewer, self._clock() + self._ttl)
        return code

    def redeem(self, wa_id: str, text: str) -> Redemption:
        """Look for a code in ``text`` from an unbound sender. At most ``MAX_FAILED`` failed
        attempts per hour; past that nothing is tried, even for a valid code."""
        with self._lock:
            now = self._clock()
            failed = self.store.failures_since(wa_id, now - ATTEMPT_WINDOW)
            if failed > MAX_FAILED:
                return Redemption("silent")
            if failed == MAX_FAILED:
                self.store.note_failure(wa_id, now)
                return Redemption("locked")
            viewer = self._try(wa_id, text, now)
            if viewer is not None:
                return Redemption("bound", viewer)
            self.store.note_failure(wa_id, now)
            return Redemption("rejected")

    def _try(self, wa_id: str, text: str, now: float) -> str | None:
        if self.store.viewer_of(wa_id) is not None:
            return None
        for candidate in _CANDIDATE.findall(text)[:_MAX_CANDIDATES]:
            invite = self.store.take_invite(digest(candidate))
            if invite is not None and invite[1] > now and self.store.bind(wa_id, invite[0]):
                return invite[0]
        return None

    def viewer_of(self, wa_id: str) -> str | None:
        return self.store.viewer_of(wa_id)

    def wa_id_of(self, viewer: str) -> str | None:
        return self.store.wa_id_of(viewer)

    def viewers(self) -> list[str]:
        return self.store.viewers()
