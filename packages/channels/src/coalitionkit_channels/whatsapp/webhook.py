# SPDX-License-Identifier: Apache-2.0
"""The webhook routes: ``GET`` verify handshake and ``POST`` signed deliveries."""

from __future__ import annotations

import asyncio
import hmac
import json
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import APIRouter, Query, Request
from starlette.responses import JSONResponse, PlainTextResponse, Response

from . import signature
from .channel import Ingest, StaleWebhook, WhatsAppChannel

PATH = "/webhooks/whatsapp"
MAX_BODY = 1_000_000


def create_router(
    channel: WhatsAppChannel, on_ingest: Callable[[Ingest], None] | None = None
) -> APIRouter:
    router = APIRouter()
    config = channel.config

    @router.get(PATH)
    def verify(  # pyright: ignore[reportUnusedFunction]
        mode: Annotated[str, Query(alias="hub.mode")] = "",
        token: Annotated[str, Query(alias="hub.verify_token")] = "",
        challenge: Annotated[str, Query(alias="hub.challenge")] = "",
    ) -> Response:
        expected = config.verify_token.get_secret_value().encode()
        if mode != "subscribe" or not hmac.compare_digest(token.encode(), expected):
            return PlainTextResponse("forbidden", 403)
        return PlainTextResponse(challenge)

    @router.post(PATH)
    async def deliver(request: Request) -> Response:  # pyright: ignore[reportUnusedFunction]
        body = await request.body()
        if len(body) > MAX_BODY:
            return JSONResponse({"detail": "too large"}, 413)
        header = request.headers.get("x-hub-signature-256")
        if not signature.verify(body, header, config.app_secret.get_secret_value()):
            return JSONResponse({"detail": "bad signature"}, 401)
        try:
            payload: Any = json.loads(body)
        except ValueError:
            return JSONResponse({"detail": "bad body"}, 400)
        if not isinstance(payload, dict):
            return JSONResponse({"detail": "bad body"}, 400)
        try:
            result = await asyncio.to_thread(channel.ingest, payload)  # pyright: ignore[reportUnknownArgumentType]
        except StaleWebhook:
            return JSONResponse({"detail": "stale"}, 400)
        if on_ingest is not None:
            await asyncio.to_thread(on_ingest, result)
        return JSONResponse({"status": "ok"})

    return router
