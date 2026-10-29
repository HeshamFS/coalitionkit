# SPDX-License-Identifier: Apache-2.0
"""Fault injection around an event store: dropped connections, lost commits, lost replies."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from threading import Lock
from typing import Any, Literal

from coalitionkit_runtime import EventStore
from coalitionkit_runtime.store import Document

Where = Literal["before", "inside", "after"]


class InjectedFault(ConnectionError):
    """The injected stand-in for a database connection that dropped."""


class FaultyStore:
    """Wraps a store. ``arm`` schedules faults for the next transactions.

    * ``before``: the connection is gone before the transaction opens; nothing was written.
    * ``inside``: it drops after the work but before the commit; the work rolls back.
    * ``after``: the commit succeeded but the caller never hears of it (the reply is lost).
    """

    def __init__(self, inner: EventStore) -> None:
        self.inner = inner
        self._lock = Lock()
        self._plan: list[Where] = []
        self.fired: list[Where] = []

    def arm(self, *plan: Where) -> None:
        with self._lock:
            self._plan.extend(plan)

    def _next(self) -> Where | None:
        with self._lock:
            return self._plan.pop(0) if self._plan else None

    @contextmanager
    def transaction(self, coalition_id: str) -> Generator[Any]:
        fault = self._next()
        if fault == "before":
            self.fired.append(fault)
            raise InjectedFault("connection dropped before the transaction")
        with self.inner.transaction(coalition_id) as tx:
            yield tx
            if fault == "inside":
                self.fired.append(fault)
                raise InjectedFault("connection dropped before the commit")
        if fault == "after":
            self.fired.append(fault)
            raise InjectedFault("connection dropped after the commit")

    def read(self, coalition_id: str, since: int = 0) -> list[Document]:
        return self.inner.read(coalition_id, since)

    def create(self, coalition_id: str, host: str, created_at: str) -> None:
        self.inner.create(coalition_id, host, created_at)

    def redactions(self, coalition_id: str) -> dict[str, tuple[str, ...]]:
        return self.inner.redactions(coalition_id)

    def close(self) -> None:
        close = getattr(self.inner, "close", None)
        if callable(close):
            close()
