# SPDX-License-Identifier: Apache-2.0
"""WhatsApp bindings on the host's own database (SQLite or Postgres), in their own tables."""

from coalitionkit_runtime import EventStore

ATTEMPT_WINDOW = 3600.0
TABLES = (
    "CREATE TABLE IF NOT EXISTS whatsapp_invites "
    "(digest TEXT PRIMARY KEY, viewer TEXT NOT NULL, expires_at DOUBLE PRECISION NOT NULL)",
    "CREATE TABLE IF NOT EXISTS whatsapp_bindings "
    "(wa_id TEXT PRIMARY KEY, viewer TEXT NOT NULL UNIQUE)",
    "CREATE TABLE IF NOT EXISTS whatsapp_attempts "
    "(wa_id TEXT NOT NULL, at DOUBLE PRECISION NOT NULL)",
)


class SqlBindingStore:
    """``BindingStore`` on the host's own database (SQLite or Postgres), in its own tables.
    Only SHA-256 digests of invitation codes are stored."""

    def __init__(self, store: EventStore) -> None:
        self.store = store
        with store.transaction("") as tx:
            for statement in TABLES:
                tx.execute(statement)

    def add_invite(self, code_digest: str, viewer: str, expires_at: float) -> None:
        with self.store.transaction("") as tx:
            tx.execute(
                "INSERT INTO whatsapp_invites VALUES (?, ?, ?)", (code_digest, viewer, expires_at)
            )

    def take_invite(self, code_digest: str) -> tuple[str, float] | None:
        with self.store.transaction("") as tx:
            row = tx.execute(
                "SELECT viewer, expires_at FROM whatsapp_invites WHERE digest = ?", (code_digest,)
            ).fetchone()
            if row is None:
                return None
            tx.execute("DELETE FROM whatsapp_invites WHERE digest = ?", (code_digest,))
        return str(row[0]), float(row[1])

    def bind(self, wa_id: str, viewer: str) -> bool:
        with self.store.transaction("") as tx:
            taken = tx.execute("SELECT 1 FROM whatsapp_bindings WHERE wa_id = ?", (wa_id,))
            if taken.fetchone() is not None:
                return False
            tx.execute("DELETE FROM whatsapp_bindings WHERE viewer = ?", (viewer,))
            tx.execute("INSERT INTO whatsapp_bindings VALUES (?, ?)", (wa_id, viewer))
        return True

    def viewer_of(self, wa_id: str) -> str | None:
        with self.store.transaction("") as tx:
            row = tx.execute(
                "SELECT viewer FROM whatsapp_bindings WHERE wa_id = ?", (wa_id,)
            ).fetchone()
        return None if row is None else str(row[0])

    def wa_id_of(self, viewer: str) -> str | None:
        with self.store.transaction("") as tx:
            row = tx.execute(
                "SELECT wa_id FROM whatsapp_bindings WHERE viewer = ?", (viewer,)
            ).fetchone()
        return None if row is None else str(row[0])

    def note_failure(self, wa_id: str, at: float) -> None:
        with self.store.transaction("") as tx:
            tx.execute("DELETE FROM whatsapp_attempts WHERE at < ?", (at - ATTEMPT_WINDOW,))
            tx.execute("INSERT INTO whatsapp_attempts VALUES (?, ?)", (wa_id, at))

    def failures_since(self, wa_id: str, since: float) -> int:
        with self.store.transaction("") as tx:
            row = tx.execute(
                "SELECT COUNT(*) FROM whatsapp_attempts WHERE wa_id = ? AND at >= ?",
                (wa_id, since),
            ).fetchone()
        return int(row[0])

    def viewers(self) -> list[str]:
        with self.store.transaction("") as tx:
            rows = tx.execute("SELECT viewer FROM whatsapp_bindings ORDER BY viewer").fetchall()
        return [str(row[0]) for row in rows]
