# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Rig for the phone-input tests: a WAV maker, a scripted transcriber and a model that reads."""

from __future__ import annotations

import io
import json
import wave
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import httpx2
from pydantic import SecretStr
from room_rig import RoomModel

from coalitionkit_models import CostMeter, load_price_table
from coalitionkit_models.gateway import ChatMessage, RawCompletion, Usage
from coalitionkit_models.media import MediaClient
from coalitionkit_models.settings import Route
from coalitionkit_models.settings import Settings as ModelSettings

# A tiny PNG header is enough for the type check; the scripted model never decodes it.
PNG = b"\x89PNG\r\n\x1a\n" + b"PHOTO-BYTES-MARKER" * 8


def wav(seconds: float = 1.0, rate: int = 16_000, channels: int = 1) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as writer:
        writer.setnchannels(channels)
        writer.setsampwidth(2)
        writer.setframerate(rate)
        writer.writeframes(b"\x01\x00" * int(seconds * rate) * channels)
    return out.getvalue()


def media(heard: str, sent: list[bytes] | None = None) -> MediaClient:
    """A media client whose transcriber always hears ``heard``."""

    def handle(request: httpx2.Request) -> httpx2.Response:
        if sent is not None:
            sent.append(request.content)
        return httpx2.Response(
            200, json={"transcript": heard, "turns": [], "audioDurationMs": 1000}
        )

    settings = ModelSettings(meta_api_key=SecretStr("test-key"))
    http = httpx2.AsyncClient(transport=httpx2.MockTransport(handle))
    return MediaClient(settings, meter=CostMeter(load_price_table()), http=http)


Reader = Callable[[str, str, bool], dict[str, Any] | None]


class ReadingModel(RoomModel):
    """The room's scripted model, plus the reading prompts: ``reader(system, user, has_image)``."""

    def __init__(self, reader: Reader, **kw: Any) -> None:
        super().__init__(**kw)
        self.reader = reader
        self.images: list[str] = []

    async def create(
        self, route: Route, messages: Sequence[ChatMessage], opts: Mapping[str, Any]
    ) -> RawCompletion:
        system, content = str(messages[0]["content"]), messages[-1]["content"]
        if "took a photo" in system or "answers one of your questions" in system:
            self.calls.append((route.role, list(messages)))
            image = isinstance(content, list)
            if image:
                parts: list[Any] = list(content)
                self.images.append(str(parts[1]["image_url"]["url"]))
                user = str(parts[0]["text"])
            else:
                user = str(content)
            reply = self.reader(system, user, image)
            if reply is None:
                from coalitionkit_models import MissingKeyError

                raise MissingKeyError("no key in this test")
            return RawCompletion(json.dumps(reply), Usage(300, 40), "stop")
        return await super().create(route, messages, opts)


def reading(**kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "description": "",
        "option_ids": [],
        "number": 0,
        "has_number": False,
        "text": "",
    }
    return {**base, **kw}
