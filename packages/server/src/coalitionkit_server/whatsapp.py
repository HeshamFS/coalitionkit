# SPDX-License-Identifier: Apache-2.0
"""Mounts the WhatsApp message-door transport when it is configured. Nothing else in the
server names WhatsApp.

One ``MessageDoor`` per coalition, built from that host's own projection; a person is linked to
one ``coalition/participant`` viewer by a single-use invitation code. A reply can only open the
door's confirm step (a one-time code for the trusted confirm page); nothing here signs.
"""

import logging
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from coalitionkit_channels.whatsapp import (
    Bindings,
    Ingest,
    WhatsAppChannel,
    WhatsAppClient,
    WhatsAppConfig,
    WhatsAppError,
    create_router,
)
from coalitionkit_runtime import CoalitionHost, EventStore
from coalitionkit_surfaces import load_catalog
from coalitionkit_surfaces.catalog import Catalog
from coalitionkit_surfaces.message import (
    ConfirmGate,
    Doors,
    HostTreeSource,
    MessageDoor,
    ReplyOutcome,
    host_is_open,
    load_doors,
)

from .settings import Settings

log = logging.getLogger("coalitionkit.server.whatsapp")
SEP = "/"
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


def viewer_key(coalition: str, participant: str) -> str:
    return coalition + SEP + participant


class ScopedChannel:
    """One coalition's door sends through the shared channel under ``coalition/participant``.
    Replies are read once by the mount, not per door."""

    def __init__(self, channel: WhatsAppChannel, coalition: str) -> None:
        self.channel, self.coalition = channel, coalition

    def send(self, viewer: str, text: str) -> None:
        self.channel.send(viewer_key(self.coalition, viewer), text)

    def receive(self) -> list[Any]:
        return []


class WhatsAppInvite(BaseModel):
    coalition: str
    participant: str


@dataclass
class WhatsAppMount:
    channel: WhatsAppChannel
    bindings: Bindings
    hosts: dict[str, CoalitionHost]
    catalog: Catalog
    doors: Doors
    link_base: str | None
    outcomes: deque[ReplyOutcome] = field(default_factory=lambda: deque[ReplyOutcome](maxlen=1000))
    _doors: dict[str, MessageDoor] = field(default_factory=lambda: dict[str, MessageDoor]())
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def door_for(self, coalition: str) -> MessageDoor | None:
        host = self.hosts.get(coalition)
        if host is None:
            return None
        if coalition not in self._doors:
            self._doors[coalition] = MessageDoor(
                ScopedChannel(self.channel, coalition),
                HostTreeSource(host),
                self.catalog,
                self.doors,
                ConfirmGate(host_is_open(host)),
                link_base=self.link_base,
            )
        return self._doors[coalition]

    def on_ingest(self, result: Ingest) -> None:
        """After a verified delivery: greet newly linked people, then let each coalition's door
        read the replies. Outcomes (answers, opened confirm steps) wait in ``outcomes``."""
        with self._lock:
            for key in result.bound:
                self._sync(key)
            for reply in self.channel.receive():
                self._reply(reply.viewer, reply.text)

    def _split(self, key: str) -> tuple[MessageDoor, str] | None:
        coalition, _, participant = key.partition(SEP)
        door = self.door_for(coalition)
        return None if door is None else (door, participant)

    def _reply(self, key: str, text: str) -> None:
        target = self._split(key)
        if target is None:
            return
        door, participant = target
        try:
            self.outcomes.append(door.handle_reply(participant, text))
        except WhatsAppError:
            log.warning("whatsapp reply not answered")
        self._sync(key)

    def _sync(self, key: str) -> None:
        target = self._split(key)
        if target is None:
            return
        try:
            target[0].sync(target[1])
        except WhatsAppError, KeyError, ValueError:
            log.warning("whatsapp sync deferred")


def mount_whatsapp(
    app: FastAPI,
    settings: Settings,
    store: EventStore,
    hosts: dict[str, CoalitionHost],
    check_admin: Callable[[Request], None],
    *,
    http: httpx.Client | None = None,
) -> WhatsAppMount | None:
    """Mount the webhook and the invitation route, or return ``None`` when not configured."""
    if not settings.whatsapp_configured:
        return None
    assert settings.whatsapp_token and settings.whatsapp_app_secret
    assert settings.whatsapp_verify_token and settings.whatsapp_phone_number_id
    config = WhatsAppConfig.load(
        token=settings.whatsapp_token,
        phone_number_id=settings.whatsapp_phone_number_id,
        app_secret=settings.whatsapp_app_secret,
        verify_token=settings.whatsapp_verify_token,
    )
    path: Path = settings.catalog_file
    bindings = Bindings(SqlBindingStore(store))
    channel = WhatsAppChannel(config, WhatsAppClient(config, http=http), bindings)
    mount = WhatsAppMount(
        channel, bindings, hosts, load_catalog(path), load_doors(path), settings.confirm_link_base
    )
    app.include_router(create_router(channel, mount.on_ingest))

    @app.post("/admin/whatsapp/invitations")
    def invite(request: Request, body: WhatsAppInvite) -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
        check_admin(request)
        host = hosts.get(body.coalition)
        if host is None or body.participant not in host.state.members or SEP in body.coalition:
            raise HTTPException(404)
        return {"code": bindings.invite(viewer_key(body.coalition, body.participant))}

    app.state.whatsapp = mount
    return mount
