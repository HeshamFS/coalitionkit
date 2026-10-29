# SPDX-License-Identifier: Apache-2.0
"""Shared test helpers: canary secrets, a recording fake of the Cloud API, a wired channel."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx
from pydantic import SecretStr

from coalitionkit_channels.whatsapp import (
    Bindings,
    WhatsAppChannel,
    WhatsAppClient,
    WhatsAppConfig,
    sign,
)

# Canaries: if one of these shows up in a log line, repr or exception, a secret leaked.
TOKEN = "canary-token-7f3a91"
APP_SECRET = "canary-app-secret-c25d08"
VERIFY = "canary-verify-b46e17"
CANARIES = (TOKEN, APP_SECRET, VERIFY)
PHONE_ID = "1000000000001"
WA_ID = "15550000001"
OTHER_WA = "15550000002"
NOW = 1_800_000_000.0

Handler = Callable[[httpx.Request], httpx.Response]


def config(**extra: Any) -> WhatsAppConfig:
    return WhatsAppConfig(
        token=SecretStr(TOKEN),
        phone_number_id=PHONE_ID,
        app_secret=SecretStr(APP_SECRET),
        verify_token=SecretStr(VERIFY),
        **extra,
    )


def accepted(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"messages": [{"id": "wamid.test"}]}, request=request)


@dataclass
class Clock:
    now: float = NOW

    def __call__(self) -> float:
        return self.now


@dataclass
class Fake:
    """Records every request; answers with ``script`` (a list of handlers) then ``accepted``."""

    script: list[Handler] = field(default_factory=lambda: list[Handler]())
    requests: list[httpx.Request] = field(default_factory=lambda: list[httpx.Request]())

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.script.pop(0)(request) if self.script else accepted(request)

    def bodies(self) -> list[dict[str, Any]]:
        return [json.loads(r.content) for r in self.requests]

    def kinds(self) -> list[str]:
        return [str(b["type"]) for b in self.bodies()]


@dataclass
class Rig:
    channel: WhatsAppChannel
    fake: Fake
    clock: Clock
    bindings: Bindings
    sleeps: list[float]


def rig(*, bound: bool = True, window_open: bool = True, **extra: Any) -> Rig:
    fake, clock, sleeps = Fake(), Clock(), list[float]()
    cfg = config(**extra)
    client = WhatsAppClient(
        cfg, http=httpx.Client(transport=httpx.MockTransport(fake)), sleep=sleeps.append
    )
    bindings = Bindings(clock=clock)
    channel = WhatsAppChannel(cfg, client, bindings, wall=clock, mono=clock)
    if bound:
        bindings.redeem(WA_ID, bindings.invite("p1"))
    if window_open:
        channel.window.inbound(WA_ID)
    return Rig(channel, fake, clock, bindings, sleeps)


def text_payload(
    sender: str, body: str, message_id: str, stamp: float = NOW, phone_id: str = PHONE_ID
) -> dict[str, Any]:
    message = {
        "from": sender,
        "id": message_id,
        "timestamp": str(int(stamp)),
        "type": "text",
        "text": {"body": body},
    }
    metadata = {"display_phone_number": "15550001111", "phone_number_id": phone_id}
    value = {
        "messaging_product": "whatsapp",
        "metadata": metadata,
        "contacts": [{"profile": {"name": "Sender"}, "wa_id": sender}],
        "messages": [message],
    }
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": "1", "changes": [{"field": "messages", "value": value}]}],
    }


def signed(payload: dict[str, Any]) -> tuple[bytes, dict[str, str]]:
    body = json.dumps(payload).encode()
    return body, {"X-Hub-Signature-256": sign(body, APP_SECRET), "Content-Type": "application/json"}
