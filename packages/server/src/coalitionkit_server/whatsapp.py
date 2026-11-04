# SPDX-License-Identifier: Apache-2.0
"""Mounts the WhatsApp message-door transport when it is configured. Nothing else in the
server names WhatsApp.

One ``MessageDoor`` per coalition, built from that host's own projection; a person is linked to
one ``coalition/participant`` viewer by a single-use invitation code. A reply can only open the
door's confirm step (a one-time code for the trusted confirm page); nothing here signs. A pump
owned by the server lifespan listens to committed host events and retries deferred updates.
"""

import logging
import threading
import time
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
from coalitionkit_runtime import CoalitionHost, EventStore, SubscriberDropped, Subscription
from coalitionkit_surfaces import ConsentRequest, load_catalog
from coalitionkit_surfaces.catalog import Catalog
from coalitionkit_surfaces.hub import latest_seq
from coalitionkit_surfaces.message import (
    ConfirmGate,
    ConfirmVoid,
    Doors,
    HostTreeSource,
    MessageDoor,
    ReplyOutcome,
    Ticket,
    host_is_open,
    load_doors,
)

from .settings import Settings
from .whatsapp_store import SqlBindingStore

__all__ = ["SqlBindingStore", "WhatsAppMount", "mount_whatsapp"]

log = logging.getLogger("coalitionkit.server.whatsapp")
SEP = "/"
TICK = 0.5  # how often the pump looks for committed host events
RETRY = 15.0  # how often it retries deferred updates (rate limit, closed 24-hour window)
VOID_STATUS = {
    ConfirmVoid.UNKNOWN: 404,
    ConfirmVoid.EXPIRED: 410,
    ConfirmVoid.USED: 409,
    ConfirmVoid.STALE: 409,
    ConfirmVoid.WRONG_VIEWER: 403,
}


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


class RedeemBody(BaseModel):
    code: str


@dataclass
class WhatsAppMount:
    channel: WhatsAppChannel
    bindings: Bindings
    hosts: dict[str, CoalitionHost]
    catalog: Catalog
    doors: Doors
    link_base: str | None
    clock: Callable[[], float] = time.monotonic
    gate_ttl: float = 300.0
    outcomes: deque[ReplyOutcome] = field(default_factory=lambda: deque[ReplyOutcome](maxlen=1000))
    _doors: dict[str, MessageDoor] = field(default_factory=lambda: dict[str, MessageDoor]())
    _gates: dict[str, ConfirmGate] = field(default_factory=lambda: dict[str, ConfirmGate]())
    _subs: dict[str, Subscription] = field(default_factory=lambda: dict[str, Subscription]())
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _stop: threading.Event = field(default_factory=threading.Event)
    _thread: threading.Thread | None = None

    def door_for(self, coalition: str) -> MessageDoor | None:
        host = self.hosts.get(coalition)
        if host is None:
            return None
        with self._lock:
            if coalition not in self._doors:
                gate = ConfirmGate(host_is_open(host), clock=self.clock, ttl=self.gate_ttl)
                self._gates[coalition] = gate
                # Subscribe before the first view so no commit between the two is missed.
                self._subs[coalition] = host.bus.subscribe(coalition, latest_seq(host))
                self._doors[coalition] = MessageDoor(
                    ScopedChannel(self.channel, coalition),
                    HostTreeSource(host),
                    self.catalog,
                    self.doors,
                    gate,
                    clock=self.clock,
                    link_base=self.link_base,
                )
            return self._doors[coalition]

    def gate_for(self, coalition: str) -> ConfirmGate | None:
        """The one gate shared by this coalition's door and the confirm endpoint."""
        return self._gates.get(coalition) if self.door_for(coalition) else None

    # -- inbound -------------------------------------------------------------------------------

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
        except (WhatsAppError, KeyError, ValueError):
            log.warning("whatsapp sync deferred")

    # -- outbound: committed host events and the retry timer -----------------------------------

    def pump_once(self, retry: bool = False) -> None:
        """Sync linked viewers of every coalition that committed events since the last look
        (and, when ``retry``, of every coalition: deferred updates are tried again)."""
        with self._lock:
            if retry:
                for key in self.bindings.viewers():
                    self.door_for(key.partition(SEP)[0])
            for coalition in list(self._subs):
                if self._woke(coalition) or retry:
                    self._sync_coalition(coalition)

    def _woke(self, coalition: str) -> bool:
        sub, host = self._subs[coalition], self.hosts.get(coalition)
        if host is None or not sub.wake.is_set():
            return False
        try:
            sub.read(host.store)  # advances the cursor and clears the wake
        except SubscriberDropped:
            host.bus.unsubscribe(sub)
            self._subs[coalition] = host.bus.subscribe(coalition, latest_seq(host))
        return True

    def _sync_coalition(self, coalition: str) -> None:
        for key in self.bindings.viewers():
            if key.startswith(coalition + SEP):
                self._sync(key)

    def start(self, tick: float = TICK, retry: float = RETRY) -> None:
        """Run the pump on a thread (the server lifespan calls this)."""
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, args=(tick, retry), name="whatsapp-pump", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(10)
            self._thread = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run(self, tick: float, retry: float) -> None:
        last = float("-inf")
        while not self._stop.wait(tick):
            due = time.monotonic() - last >= retry
            if due:
                last = time.monotonic()
            try:
                self.pump_once(retry=due)
            except Exception:  # keep the pump alive; the next tick tries again
                log.warning("whatsapp pump tick failed")

    # -- the confirm handoff -------------------------------------------------------------------

    def redeem(self, coalition: str, participant: str, code: str) -> dict[str, Any]:
        """Use a confirm code for this signed-in person and return the consent request for the
        trusted shell (the same shape as an interrupt on the agent stream). Signing happens only
        through the existing answer flow."""
        gate, host = self.gate_for(coalition), self.hosts.get(coalition)
        if gate is None or host is None:
            raise HTTPException(404, ConfirmVoid.UNKNOWN)
        try:
            ticket = gate.redeem(code, participant)
        except ConfirmVoid as void:
            raise HTTPException(VOID_STATUS.get(void.code, 400), void.code) from None
        return consent_request(host, ticket, participant)


def consent_request(host: CoalitionHost, ticket: Ticket, participant: str) -> dict[str, Any]:
    subject = ticket.subject
    request = ConsentRequest(subject["kind"], subject["id"], int(subject["revision"]), participant)
    deadline = host.state.subject(request.kind, request.subject_id).get("decision_deadline")
    return {
        "id": request.interrupt_id,
        "message": f"Your decision is needed on a {request.kind.replace('_', ' ')}",
        "expires_at": deadline if isinstance(deadline, str) else None,
        "metadata": {"subject": request.subject},
    }


def mount_whatsapp(
    app: FastAPI,
    settings: Settings,
    store: EventStore,
    hosts: dict[str, CoalitionHost],
    check_admin: Callable[[Request], None],
    lookup: Callable[[str], dict[str, Any] | None],
    *,
    http: httpx.Client | None = None,
    clock: Callable[[], float] = time.monotonic,
    wall: Callable[[], float] = time.time,
) -> WhatsAppMount | None:
    """Mount the webhook, the invitation route and the confirm redeem route, or return ``None``
    when not configured."""
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
    bindings = Bindings(SqlBindingStore(store), clock=wall)
    channel = WhatsAppChannel(config, WhatsAppClient(config, http=http), bindings, wall=wall)
    mount = WhatsAppMount(
        channel,
        bindings,
        hosts,
        load_catalog(path),
        load_doors(path),
        settings.effective_confirm_base,
        clock=clock,
    )
    app.include_router(create_router(channel, mount.on_ingest))

    @app.post("/admin/whatsapp/invitations")
    def invite(request: Request, body: WhatsAppInvite) -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
        check_admin(request)
        host = hosts.get(body.coalition)
        if host is None or body.participant not in host.state.members or SEP in body.coalition:
            raise HTTPException(404)
        return {"code": bindings.invite(viewer_key(body.coalition, body.participant))}

    @app.post("/v1/confirm/redeem")
    def redeem(request: Request, body: RedeemBody) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        row = lookup(token) if token else None
        if row is None:
            raise HTTPException(401, "unauthenticated")
        return mount.redeem(str(row["coalition"]), str(row["participant"]), body.code)

    app.state.whatsapp = mount
    return mount
