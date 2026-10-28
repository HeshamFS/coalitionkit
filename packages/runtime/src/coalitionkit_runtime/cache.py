# SPDX-License-Identifier: Apache-2.0
"""Transaction-scoped incremental folds and consent synchronization."""

from __future__ import annotations

import json
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from threading import RLock

from .consents import ConsentLedger
from .lifecycle import State
from .store import Document, EventStore, Transaction


class HostCache:
    def __init__(self, store: EventStore, coalition_id: str) -> None:
        self.store, self.coalition_id = store, coalition_id
        self.lock = RLock()
        self.reset()

    def reset(self) -> None:
        self.state = State(self.coalition_id)
        self.sequence = 0
        self.durable_sequence = 0
        self.requests: dict[str, tuple[object, ...]] = {}
        self.redactions: dict[str, tuple[str, ...]] = {}
        self.expired_at: str | None = None

    @contextmanager
    def transaction(self) -> Generator[Transaction]:
        with self.lock:
            requests = self.requests
            try:
                with self.store.transaction(self.coalition_id) as tx:
                    yield tx
                self.durable_sequence = self.sequence
            except BaseException:
                if self.sequence > self.durable_sequence:
                    # An appended event may have rolled back or lost its commit reply.
                    self.reset()
                else:
                    # Validation refusals do not discard the already committed fold.
                    self.requests = requests
                raise

    def refresh(self, tx: Transaction, now: str) -> State:
        row = tx.execute("SELECT seq FROM coalitions WHERE id = ?", (self.coalition_id,)).fetchone()
        head = row[0] if row else 0
        if head < self.sequence or (
            self.expired_at
            and datetime.fromisoformat(now) < datetime.fromisoformat(self.expired_at)
        ):
            self.reset()
        rows = tx.execute(
            "SELECT body, delivery FROM events WHERE coalition_id = ? AND seq > ? ORDER BY seq",
            (self.coalition_id, self.sequence),
        ).fetchall()
        events = [(json.loads(body), tuple(json.loads(paths))) for body, paths in rows]
        if (
            events
            and self.expired_at
            and datetime.fromisoformat(events[0][0]["ts"]) < datetime.fromisoformat(self.expired_at)
        ):
            self.reset()
            return self.refresh(tx, now)
        for event, paths in events:
            self.apply(event, paths)
        self.durable_sequence = head
        before = self.fingerprints()
        self.state.expire(now)
        if before != self.fingerprints():
            self.expired_at = now
        self.sync(tx)
        return self.state

    def apply(self, event: Document, paths: tuple[str, ...]) -> None:
        self.sequence = event["seq"]
        self.state.apply(event)
        self.redactions[event["event_id"]] = paths

    def fingerprints(self) -> dict[str, tuple[object, ...]]:
        return {
            key: (s["revision"], s.get("status"), tuple(s["deciders"]))
            for key, s in self.state.subjects.items()
        }

    def sync(self, tx: Transaction) -> None:
        current = self.fingerprints()
        ledger = ConsentLedger(tx, self.coalition_id)
        for key, fingerprint in current.items():
            if self.requests.get(key) != fingerprint:
                subject = self.state.subjects[key]
                ledger.request(subject, subject["deciders"])
        self.requests = current
