# SPDX-License-Identifier: Apache-2.0
"""Transactional storage ports; the coalition row serializes writers."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from threading import RLock
from typing import Any, Protocol

from .pool import ConnectionPool

Document = dict[str, Any]


class Transaction(Protocol):
    def execute(self, sql: str, args: Sequence[Any] = ()) -> Any: ...


class EventStore(Protocol):
    def transaction(self, coalition_id: str) -> Any: ...
    def read(self, coalition_id: str, since: int = 0) -> list[Document]: ...
    def create(self, coalition_id: str, host: str, created_at: str) -> None: ...
    def redactions(self, coalition_id: str) -> dict[str, tuple[str, ...]]: ...


DDL = (
    "CREATE TABLE IF NOT EXISTS pinned_cards (coalition_id TEXT NOT NULL, card_url TEXT NOT NULL, "
    "public_key TEXT NOT NULL, kid TEXT NOT NULL, participant TEXT NOT NULL, "
    "PRIMARY KEY (coalition_id, card_url))",
    "CREATE TABLE IF NOT EXISTS invitations (coalition_id TEXT NOT NULL, "
    "participant TEXT NOT NULL, "
    "card_url TEXT NOT NULL, PRIMARY KEY (coalition_id, participant))",
    "CREATE TABLE IF NOT EXISTS coalitions (id TEXT PRIMARY KEY, host TEXT NOT NULL, "
    "created_at TEXT NOT NULL, seq BIGINT NOT NULL DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS events (coalition_id TEXT NOT NULL, seq BIGINT NOT NULL, "
    "event_id TEXT NOT NULL, sender TEXT NOT NULL, digest TEXT NOT NULL, "
    "body TEXT NOT NULL, delivery TEXT NOT NULL, "
    "PRIMARY KEY (coalition_id, seq), UNIQUE (coalition_id, event_id))",
    "CREATE TABLE IF NOT EXISTS receipts (coalition_id TEXT NOT NULL, event_id TEXT NOT NULL, "
    "body TEXT NOT NULL, PRIMARY KEY (coalition_id, event_id))",
    "CREATE TABLE IF NOT EXISTS consents (coalition_id TEXT NOT NULL, kind TEXT NOT NULL, "
    "subject_id TEXT NOT NULL, revision BIGINT NOT NULL, decider TEXT NOT NULL, "
    "status TEXT NOT NULL, answer TEXT, PRIMARY KEY "
    "(coalition_id, kind, subject_id, revision, decider))",
)


class SQLTransaction:
    def __init__(self, connection: Any, postgres: bool = False) -> None:
        self.connection = connection
        self.postgres = postgres

    def execute(self, sql: str, args: Sequence[Any] = ()) -> Any:
        return self.connection.execute(sql.replace("?", "%s") if self.postgres else sql, args)


class SQLiteStore:
    def __init__(self, path: str = ":memory:") -> None:
        self.connection = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.connection.execute("PRAGMA busy_timeout = 30000")
        self._lock = RLock()
        for statement in DDL:
            self.connection.execute(statement)
        self.connection.executescript(
            "CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events "
            "BEGIN SELECT RAISE(ABORT, 'append-only'); END;"
            "CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events "
            "BEGIN SELECT RAISE(ABORT, 'append-only'); END;"
        )

    @contextmanager
    def transaction(self, coalition_id: str) -> Generator[SQLTransaction]:
        with self._lock:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                yield SQLTransaction(self.connection)
                self.connection.commit()
            except BaseException:
                self.connection.rollback()
                raise

    def create(self, coalition_id: str, host: str, created_at: str) -> None:
        with self.transaction(coalition_id) as tx:
            tx.execute(
                "INSERT INTO coalitions (id, host, created_at) VALUES (?, ?, ?)",
                (coalition_id, host, created_at),
            )

    def read(self, coalition_id: str, since: int = 0) -> list[Document]:
        with self._lock:
            return read_events(SQLTransaction(self.connection), coalition_id, since)

    def redactions(self, coalition_id: str) -> dict[str, tuple[str, ...]]:
        with self._lock:
            return read_redactions(SQLTransaction(self.connection, False), coalition_id)

    def close(self) -> None:
        self.connection.close()


class PostgresStore:
    def __init__(self, url: str) -> None:
        self.pool = ConnectionPool(url)
        with self.pool.connection() as connection:
            for statement in DDL:
                connection.execute(statement)
            connection.execute(
                "CREATE OR REPLACE FUNCTION coalition_events_immutable() RETURNS trigger "
                "LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'append-only'; END $$"
            )
            connection.execute(
                "CREATE OR REPLACE TRIGGER events_immutable BEFORE UPDATE OR DELETE ON events "
                "FOR EACH ROW EXECUTE FUNCTION coalition_events_immutable()"
            )

    @contextmanager
    def transaction(self, coalition_id: str) -> Generator[SQLTransaction]:
        with self.pool.connection() as connection, connection.transaction():
            tx = SQLTransaction(connection, True)
            tx.execute("SELECT seq FROM coalitions WHERE id = ? FOR UPDATE", (coalition_id,))
            yield tx

    def create(self, coalition_id: str, host: str, created_at: str) -> None:
        with self.transaction(coalition_id) as tx:
            tx.execute(
                "INSERT INTO coalitions (id, host, created_at) VALUES (?, ?, ?)",
                (coalition_id, host, created_at),
            )

    def read(self, coalition_id: str, since: int = 0) -> list[Document]:
        with self.pool.connection() as connection:
            return read_events(SQLTransaction(connection, True), coalition_id, since)

    def redactions(self, coalition_id: str) -> dict[str, tuple[str, ...]]:
        with self.pool.connection() as connection:
            return read_redactions(SQLTransaction(connection, True), coalition_id)

    def close(self) -> None:
        self.pool.close()


def read_events(tx: Transaction, coalition_id: str, since: int = 0) -> list[Document]:
    rows = tx.execute(
        "SELECT body FROM events WHERE coalition_id = ? AND seq > ? ORDER BY seq",
        (coalition_id, since),
    ).fetchall()
    return [json.loads(row[0]) for row in rows]


def read_redactions(tx: Transaction, coalition_id: str) -> dict[str, tuple[str, ...]]:
    rows = tx.execute(
        "SELECT event_id, delivery FROM events WHERE coalition_id = ?", (coalition_id,)
    ).fetchall()
    return {row[0]: tuple(json.loads(row[1])) for row in rows}
