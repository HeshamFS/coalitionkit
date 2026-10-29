# SPDX-License-Identifier: Apache-2.0
"""``WhatsAppChannel``: the message door's ``MessageChannel`` over the WhatsApp Cloud API.

Outbound: free text only inside the 24-hour window; outside it the approved opener template is
sent (once per silence) and the text is refused with ``WindowClosed``, so the door keeps it
queued and sends it after the person replies. Inbound: ``ingest`` turns webhook messages for
this business number into door replies for the bound viewer; an unbound sender can only try
invitation codes, a bounded number of times.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from coalitionkit_surfaces.message import Reply

from .bindings import Bindings
from .client import WhatsAppClient
from .config import FUTURE_SLACK, WhatsAppConfig
from .errors import NotBound, RateLimited, WhatsAppError, WindowClosed
from .limits import RateLimiter, ServiceWindow
from .memory import CapacityExhausted, ExpiringMap

log = logging.getLogger("coalitionkit.channels.whatsapp")

UNKNOWN_LINE = "This number is not linked. Send the invitation code you were given."
LINKED_LINE = "Linked. Your updates will arrive here."
LOCKED_LINE = "Too many attempts. Try again in an hour."
OBJECT = "whatsapp_business_account"
PRODUCT = "whatsapp"
FULL = "idempotency memory full: send refused"


class StaleWebhook(Exception):
    """Every message in the payload is older than the allowed age (or stamped in the future)."""


@dataclass
class Ingest:
    replies: int = 0
    bound: list[str] = field(default_factory=lambda: list[str]())
    unknown: int = 0
    duplicates: int = 0
    stale: int = 0


class WhatsAppChannel:
    def __init__(
        self,
        config: WhatsAppConfig,
        client: WhatsAppClient,
        bindings: Bindings,
        *,
        wall: Callable[[], float] = time.time,
        mono: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config, self.client, self.bindings, self._wall = config, client, bindings, wall
        self.window = ServiceWindow(config.window_seconds, wall)
        self._limiter = RateLimiter(config.max_per_minute, mono)
        self._inbox: deque[Reply] = deque()
        cap = config.memory_capacity
        # Inbound ids: kept for as long as a replay could still be accepted.
        self._seen = ExpiringMap[None](config.max_webhook_age + FUTURE_SLACK, cap, wall)
        # Outbound ids and their counters: kept for the door's retry lifetime.
        self._delivered = ExpiringMap[None](config.delivery_memory_seconds, cap, wall)
        self._generation = ExpiringMap[int](config.delivery_memory_seconds, cap, wall)
        self._lock = threading.RLock()

    # -- MessageChannel ------------------------------------------------------------------------

    def send(self, viewer: str, text: str) -> None:
        """Send ``text``. A repeat of the same text is a new message once the earlier one has
        gone out; a retry after a failure reuses the failed message's id."""
        stem = viewer + ":" + hashlib.sha256(text.encode()).hexdigest()
        with self._lock:
            number = self._generation.get(stem) or 0
            if not self._generation.has_room(1) and stem not in self._generation:
                raise WhatsAppError(FULL)
            self.send_once(viewer, text, f"{stem}:{number}")
            self._generation.put(stem, number + 1)

    def send_once(self, viewer: str, text: str, message_id: str) -> None:
        """Send under a door message id: a second call with the same id sends nothing."""
        with self._lock:
            if message_id in self._delivered:
                return
            if not self._delivered.has_room(1):
                raise WhatsAppError(FULL)
            wa_id = self.bindings.wa_id_of(viewer)
            if wa_id is None:
                raise NotBound
            self._send_to(wa_id, text)
            self._delivered.put(message_id, None)

    def receive(self) -> list[Reply]:
        with self._lock:
            replies = list(self._inbox)
            self._inbox.clear()
            return replies

    # -- send rules ----------------------------------------------------------------------------

    def _send_to(self, wa_id: str, text: str) -> None:
        if not self.window.is_open(wa_id):
            if not self.window.opener_pending(wa_id) and self._limiter.allow(wa_id):
                self.client.send_opener(wa_id)
                self.window.mark_opener(wa_id)
            raise WindowClosed
        if not self._limiter.allow(wa_id):
            raise RateLimited
        self.client.send_text(wa_id, text)

    # -- inbound -------------------------------------------------------------------------------

    def ingest(self, payload: dict[str, Any]) -> Ingest:
        """Process one verified webhook payload. Only text messages sent to this business
        number count. Raises ``StaleWebhook`` when every such message is too old, and
        ``CapacityExhausted`` (before changing anything) when the replay memory is full."""
        found = _text_messages(payload, self.config.phone_number_id)
        result = Ingest()
        now = self._wall()
        with self._lock:
            # Reserve for the distinct, currently acceptable ids not yet remembered: a repeated
            # id in one batch, a duplicate and a stale message take no room.
            fresh = {
                m[1]
                for m in found
                if -FUTURE_SLACK <= now - m[2] <= self.config.max_webhook_age
                and m[1] not in self._seen
            }
            if not self._seen.has_room(len(fresh)):
                raise CapacityExhausted
            for wa_id, message_id, stamp, body in found:
                if not -FUTURE_SLACK <= now - stamp <= self.config.max_webhook_age:
                    result.stale += 1
                elif message_id in self._seen:
                    result.duplicates += 1
                else:
                    self._seen.put(message_id, None)
                    self._accept(wa_id, stamp, body, result)
        if found and result.stale == len(found):
            raise StaleWebhook
        self.client.usage.received += len(found) - result.stale - result.duplicates
        return result

    def _accept(self, wa_id: str, stamp: float, body: str, result: Ingest) -> None:
        viewer = self.bindings.viewer_of(wa_id)
        if viewer is not None:
            self.window.inbound(wa_id, stamp)
            self._inbox.append(Reply(viewer, body))
            result.replies += 1
            return
        outcome = self.bindings.redeem(wa_id, body)
        line = {"bound": LINKED_LINE, "rejected": UNKNOWN_LINE, "locked": LOCKED_LINE}.get(
            outcome.status
        )
        if outcome.status == "bound" and outcome.viewer is not None:
            self.window.inbound(wa_id, stamp)
            result.bound.append(outcome.viewer)
        else:
            result.unknown += 1
        if line is None:
            return
        try:
            if self._limiter.allow(wa_id):
                self.client.send_text(wa_id, line)
        except WhatsAppError:
            log.warning("whatsapp fixed line not sent")


def _text_messages(
    payload: dict[str, Any], phone_number_id: str
) -> list[tuple[str, str, float, str]]:
    """``(from, id, timestamp, body)`` of each text message in a messages webhook addressed to
    ``phone_number_id``. Another object, product or business number, and anything that is not a
    well-formed text message (statuses, media, reactions), is skipped."""
    out: list[tuple[str, str, float, str]] = []
    if payload.get("object") != OBJECT:
        return out
    for entry in _items(payload.get("entry")):
        for change in _items(entry.get("changes")):
            values = _items([change.get("value")])
            if change.get("field") != "messages" or not values:
                continue
            value = values[0]
            meta = _items([value.get("metadata")])
            if (
                value.get("messaging_product") != PRODUCT
                or not meta
                or meta[0].get("phone_number_id") != phone_number_id
            ):
                continue
            for message in _items(value.get("messages")):
                parsed = _parse(message)
                if parsed is not None:
                    out.append(parsed)
    return out


def _parse(message: dict[str, Any]) -> tuple[str, str, float, str] | None:
    texts = _items([message.get("text")])
    sender, mid, stamp = message.get("from"), message.get("id"), message.get("timestamp")
    if message.get("type") != "text" or not texts:
        return None
    body = texts[0].get("body")
    if not (isinstance(sender, str) and isinstance(mid, str) and isinstance(body, str)):
        return None
    try:
        return sender, mid, float(str(stamp)), body
    except ValueError:
        return None


def _items(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]  # pyright: ignore[reportUnknownVariableType]
