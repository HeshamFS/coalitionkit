# SPDX-License-Identifier: Apache-2.0
"""Bounded checked connections; a failed transaction is never retried by the pool."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from queue import Empty, LifoQueue
from threading import RLock
from time import monotonic
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import psycopg


class StoreUnavailable(Exception):
    """Retry the same submission bytes and event ID after a transport failure."""


class ConnectionPool:
    def __init__(self, url: str, size: int = 4) -> None:
        self.url = url
        self._slots: LifoQueue[psycopg.Connection | None] = LifoQueue(size)
        for _ in range(size):
            self._slots.put(None)
        self._lock = RLock()
        self._retry_at = 0.0
        self._delay = 0.1
        self._closed = False

    def _connect(self) -> psycopg.Connection:
        import psycopg

        with self._lock:
            if self._closed or monotonic() < self._retry_at:
                raise StoreUnavailable("store reconnect pending")
            try:
                connection = psycopg.connect(self.url, autocommit=True, connect_timeout=2)
            except psycopg.OperationalError as exc:
                self._retry_at = monotonic() + self._delay
                self._delay = min(self._delay * 2, 2.0)
                raise StoreUnavailable("store connection unavailable") from exc
            self._delay, self._retry_at = 0.1, 0.0
            return connection

    @contextmanager
    def connection(self) -> Generator[psycopg.Connection]:
        import psycopg

        try:
            connection = self._slots.get(timeout=2)
        except Empty as exc:
            raise StoreUnavailable("store pool busy") from exc
        try:
            if self._closed:
                raise StoreUnavailable("store pool closed")
            if connection is not None:
                try:
                    connection.execute("SELECT 1")
                except psycopg.OperationalError, psycopg.InterfaceError:
                    connection.close()
                    connection = None
            if connection is None:
                connection = self._connect()
            try:
                yield connection
            except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
                # COMMIT may have succeeded. Only the caller can replay the same event ID.
                connection.close()
                connection = None
                raise StoreUnavailable("store transaction interrupted") from exc
        finally:
            with self._lock:
                if self._closed and connection is not None:
                    connection.close()
                    connection = None
                self._slots.put(connection)

    def close(self) -> None:
        with self._lock:
            self._closed = True
            while True:
                try:
                    connection = self._slots.get_nowait()
                except Empty:
                    break
                if connection is not None:
                    connection.close()
