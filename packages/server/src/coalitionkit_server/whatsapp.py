# SPDX-License-Identifier: Apache-2.0
"""Mounts the WhatsApp message-door transport when it is configured. Nothing else in the
server names WhatsApp."""

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx
from fastapi import FastAPI, Request
from pydantic import BaseModel

from coalitionkit_channels.whatsapp import (
    Bindings,
    Ingest,
    WhatsAppChannel,
    WhatsAppClient,
    WhatsAppConfig,
    create_router,
)
from coalitionkit_surfaces.message import MessageChannel, MessageDoor, ReplyOutcome

from .settings import Settings

DoorFactory = Callable[[MessageChannel], MessageDoor]


class WhatsAppInvite(BaseModel):
    viewer: str


@dataclass
class WhatsAppMount:
    channel: WhatsAppChannel
    door: MessageDoor
    bindings: Bindings
    outcomes: deque[ReplyOutcome] = field(default_factory=lambda: deque[ReplyOutcome](maxlen=1000))

    def on_ingest(self, result: Ingest) -> None:
        """After a verified delivery: greet newly linked viewers, then let the door read the
        replies. Typed answers wait in ``outcomes`` for the host-side consumer."""
        for viewer in result.bound:
            self.door.sync(viewer)
        self.outcomes.extend(self.door.poll())


def mount_whatsapp(
    app: FastAPI,
    settings: Settings,
    make_door: DoorFactory,
    check_admin: Callable[[Request], None],
    *,
    http: httpx.Client | None = None,
) -> WhatsAppMount | None:
    """Mount the webhook and the invitation route, or return ``None`` when not configured."""
    if not settings.whatsapp_configured:
        return None
    assert settings.whatsapp_token and settings.whatsapp_app_secret
    assert settings.whatsapp_verify_token and settings.whatsapp_phone_number_id
    config = WhatsAppConfig(
        token=settings.whatsapp_token,
        phone_number_id=settings.whatsapp_phone_number_id,
        app_secret=settings.whatsapp_app_secret,
        verify_token=settings.whatsapp_verify_token,
    )
    bindings = Bindings()
    channel = WhatsAppChannel(config, WhatsAppClient(config, http=http), bindings)
    mount = WhatsAppMount(channel, make_door(channel), bindings)
    app.include_router(create_router(channel, mount.on_ingest))

    @app.post("/admin/whatsapp/invitations")
    def invite(request: Request, body: WhatsAppInvite) -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
        check_admin(request)
        return {"code": bindings.invite(body.viewer)}

    app.state.whatsapp = mount
    return mount
