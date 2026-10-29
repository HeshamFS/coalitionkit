# SPDX-License-Identifier: Apache-2.0
"""``WhatsAppChannel``: the message door's ``MessageChannel`` over the WhatsApp Cloud API.

Outbound: free text only inside the 24-hour window; outside it the approved opener template is
sent (once per silence) and the text is refused with ``WindowClosed``, so the door keeps it
queued and sends it after the person replies. Inbound: ``ingest`` turns webhook messages into
door replies for the bound viewer; an unbound sender can only redeem an invitation code.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import OrderedDict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from coalitionkit_surfaces.message import Reply

from .bindings import Bindings
from .client import WhatsAppClient
from .config import WhatsAppConfig
from .errors import NotBound, RateLimited, WhatsAppError, WindowClosed
from .limits import RateLimiter, ServiceWindow

log = logging.getLogger("coalitionkit.channels.whatsapp")

UNKNOWN_LINE = "This number is not linked. Send the invitation code you were given."
LINKED_LINE = "Linked. Your updates will arrive here."
_MEMORY = 10_000
_CODE_MAX = 200


class StaleWebhook(Exception):
    """Every message in the payload is older than the allowed age."""


@dataclass
class Ingest:
    replies: int = 0
    bound: list[str] = field(default_factory=lambda: list[str]())
    unknown: int = 0
    duplicates: int = 0
    stale: int = 0


def _remember(seen: OrderedDict[str, None], key: str) -> bool:
    """Record ``key``; False when it was already there. Memory is bounded."""
    if key in seen:
        return False
    seen[key] = None
    if len(seen) > _MEMORY:
        seen.popitem(last=False)
    return True


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
        self._seen: OrderedDict[str, None] = OrderedDict()
        self._delivered: OrderedDict[str, None] = OrderedDict()
        self._generation: dict[str, int] = {}
        self._lock = threading.RLock()

    # -- MessageChannel ------------------------------------------------------------------------

    def send(self, viewer: str, text: str) -> None:
        """Send ``text``. A repeat of the same text is a new message once the earlier one has
        gone out; a retry after a failure reuses the failed message's id."""
        stem = viewer + ":" + hashlib.sha256(text.encode()).hexdigest()
        with self._lock:
            message_id = f"{stem}:{self._generation.get(stem, 0)}"
            self.send_once(viewer, text, message_id)
            self._generation[stem] = self._generation.get(stem, 0) + 1

    def send_once(self, viewer: str, text: str, message_id: str) -> None:
        """Send under a door message id: a second call with the same id sends nothing."""
        with self._lock:
            if message_id in self._delivered:
                return
            wa_id = self.bindings.wa_id_of(viewer)
            if wa_id is None:
                raise NotBound
            self._send_to(wa_id, text)
            _remember(self._delivered, message_id)

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
        """Process one verified webhook payload. Raises ``StaleWebhook`` when it carries
        messages and every one is too old."""
        found = list(_text_messages(payload))
        result = Ingest()
        now = self._wall()
        with self._lock:
            for wa_id, message_id, stamp, body in found:
                if now - stamp > self.config.max_webhook_age:
                    result.stale += 1
                elif not _remember(self._seen, message_id):
                    result.duplicates += 1
                else:
                    self._accept(wa_id, stamp, body, result)
        if found and result.stale == len(found):
            raise StaleWebhook
        self.client.usage.received += len(found) - result.stale - result.duplicates
        return result

    def _accept(self, wa_id: str, stamp: float, body: str, result: Ingest) -> None:
        self.window.inbound(wa_id, stamp)
        viewer = self.bindings.viewer_of(wa_id)
        if viewer is not None:
            self._inbox.append(Reply(viewer, body))
            result.replies += 1
            return
        viewer = self.bindings.redeem(wa_id, body[:_CODE_MAX])
        line = UNKNOWN_LINE if viewer is None else LINKED_LINE
        if viewer is None:
            result.unknown += 1
        else:
            result.bound.append(viewer)
        try:
            if self._limiter.allow(wa_id):
                self.client.send_text(wa_id, line)
        except WhatsAppError:
            log.warning("whatsapp fixed line not sent")


def _text_messages(payload: dict[str, Any]) -> list[tuple[str, str, float, str]]:
    """``(from, id, timestamp, body)`` of each text message in a messages webhook; anything
    that is not a well-formed text message (statuses, media, reactions) is skipped."""
    out: list[tuple[str, str, float, str]] = []
    for entry in _items(payload.get("entry")):
        for change in _items(entry.get("changes")):
            values = _items([change.get("value")])
            if change.get("field") != "messages" or not values:
                continue
            for message in _items(values[0].get("messages")):
                text = message.get("text")
                sender, mid, stamp = (
                    message.get("from"),
                    message.get("id"),
                    message.get("timestamp"),
                )
                if message.get("type") != "text" or not isinstance(text, dict):
                    continue
                body = text.get("body")  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
                if isinstance(sender, str) and isinstance(mid, str) and isinstance(body, str):
                    try:
                        out.append((sender, mid, float(str(stamp)), body))
                    except ValueError:
                        continue
    return out


def _items(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]  # pyright: ignore[reportUnknownVariableType]
