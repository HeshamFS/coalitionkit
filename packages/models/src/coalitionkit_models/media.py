# SPDX-License-Identifier: Apache-2.0
"""Meta media endpoints: image generation, SAM segmentation and speech transcription.

Same settings, retries, rate limit and cost meter as the chat gateway. Calls go to the Meta
route (``Settings.media_route``) with the Meta key.
"""

from __future__ import annotations

import asyncio
import base64
import json
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

import httpx2

from ._resilience import Retrier, transient_status
from .errors import ProviderError
from .meter import SYSTEM_PARTICIPANT, CostMeter
from .sam import Segment, parse_sam_output
from .settings import Settings
from .wav import validate_wav

TranscribeMode = Literal["PUSH_TO_TALK", "ENDPOINTING", "DIARIZATION"]
_MEDIA_KEY = "media"


@dataclass(frozen=True)
class Turn:
    start_ms: int
    end_ms: int
    text: str
    speaker: str | None = None


@dataclass(frozen=True)
class Transcript:
    text: str
    turns: tuple[Turn, ...]
    audio_ms: int = 0


def image_mime(data: bytes) -> str:
    """The MIME type of image bytes, from the magic number."""
    if data.startswith(b"\x89PNG"):
        return "image/png"
    if data.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"


def _classify(exc: Exception) -> tuple[bool, int | None]:
    if isinstance(exc, httpx2.HTTPStatusError):
        status = exc.response.status_code
        return transient_status(status), status
    return isinstance(exc, httpx2.TransportError), None


def _dicts(value: Any) -> list[dict[str, Any]]:
    """The dict items of a JSON list (anything else yields an empty list)."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]  # pyright: ignore[reportUnknownVariableType]


def _int_or_zero(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError, OverflowError):
        return 0


def _response_text(body: dict[str, Any]) -> str:
    direct = body.get("output_text")
    if isinstance(direct, str):
        return direct
    parts: list[str] = []
    for item in _dicts(body.get("output")):
        for content in _dicts(item.get("content")):
            text = content.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "".join(parts)


class MediaClient:
    def __init__(
        self,
        settings: Settings,
        *,
        meter: CostMeter | None = None,
        http: httpx2.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
        rng: random.Random | None = None,
        base_delay_s: float = 0.5,
        max_delay_s: float = 8.0,
    ) -> None:
        self.settings = settings
        self.meter = meter
        self._http = http or httpx2.AsyncClient(timeout=settings.request_timeout_s)
        self._retrier = Retrier(
            settings.max_attempts,
            sleep=sleep,
            clock=clock,
            rng=rng,
            base_delay_s=base_delay_s,
            max_delay_s=max_delay_s,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _post(
        self,
        model: str,
        path: str,
        bill: Callable[[dict[str, Any] | None], None],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """POST and return the JSON object. ``bill`` runs right after the provider answered
        successfully, before the body is parsed or validated; it gets ``None`` when the body is
        not a JSON object, so unusable replies are still billed."""
        route = self.settings.media_route(model)
        url = route.base_url.rstrip("/") + path
        headers = {"Authorization": f"Bearer {self.settings.api_key(route)}"}

        async def call() -> dict[str, Any]:
            response = await self._http.post(url, headers=headers, **kwargs)
            response.raise_for_status()
            body: Any = None
            try:
                body = response.json()
            finally:
                bill(body if isinstance(body, dict) else None)  # pyright: ignore[reportUnknownArgumentType]
            if not isinstance(body, dict):
                raise ProviderError("media reply is not a JSON object")
            return body  # pyright: ignore[reportUnknownVariableType]

        return await self._retrier.run(
            _MEDIA_KEY, self.settings.media_rate_limit_per_minute, call, _classify
        )

    def _check(self, coalition_id: str | None) -> None:
        if self.meter is not None and coalition_id is not None:
            self.meter.check(coalition_id)

    def _meter(
        self, coalition_id: str | None, who: str, model: str, *, images: int = 0, audio_ms: int = 0
    ) -> None:
        if self.meter is not None:
            self.meter.record_media(
                coalition_id or "_unattributed", who, model, images=images, audio_ms=audio_ms
            )

    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        *,
        coalition_id: str | None = None,
        participant: str = SYSTEM_PARTICIPANT,
    ) -> bytes:
        """One generated image as bytes (the API returns WebP)."""
        self._check(coalition_id)
        model = self.settings.image_model
        body = await self._post(
            model,
            "/images/generations",
            lambda _: self._meter(coalition_id, participant, model, images=1),
            json={"model": model, "prompt": prompt, "size": size, "response_format": "b64_json"},
        )
        data = _dicts(body.get("data"))
        encoded = data[0].get("b64_json") if data else None
        if not isinstance(encoded, str):
            raise ProviderError("image reply has no data[0].b64_json")
        return base64.b64decode(encoded)

    async def segment(
        self,
        image: bytes | str,
        phrase: str,
        *,
        include_confidence: bool = True,
        coalition_id: str | None = None,
        participant: str = SYSTEM_PARTICIPANT,
    ) -> list[Segment]:
        """Segments of every instance of a short noun phrase in an image (bytes or URL)."""
        self._check(coalition_id)
        model = self.settings.segment_model
        if isinstance(image, bytes):
            encoded = base64.b64encode(image).decode("ascii")
            image_url = f"data:{image_mime(image)};base64,{encoded}"
        else:
            image_url = image
        content = [
            {"type": "input_text", "text": phrase},
            {"type": "input_image", "image_url": image_url},
        ]
        payload: dict[str, Any] = {
            "model": model,
            "input": [{"type": "message", "role": "user", "content": content}],
        }
        if include_confidence:
            payload["metadata"] = {"include_confidence": "true"}
        body = await self._post(
            model,
            "/responses",
            lambda _: self._meter(coalition_id, participant, model, images=1),
            json=payload,
        )
        return parse_sam_output(_response_text(body))

    async def transcribe(
        self,
        wav_bytes: bytes,
        mode: TranscribeMode = "PUSH_TO_TALK",
        *,
        language_bias: list[str] | None = None,
        keywords: list[str] | None = None,
        coalition_id: str | None = None,
        participant: str = SYSTEM_PARTICIPANT,
    ) -> Transcript:
        """Transcribe a mono 16-bit PCM WAV (16 or 24 kHz). Validated before anything is sent."""
        wav_ms = validate_wav(wav_bytes).duration_ms
        self._check(coalition_id)
        model = self.settings.transcribe_model
        request: dict[str, Any] = {"model": model, "audioEncoding": "WAV", "mode": mode}
        if language_bias:
            request["languageBias"] = language_bias
        if keywords:
            request["keywords"] = keywords
        files = {
            "request": (None, json.dumps(request), "application/json"),
            "audio": ("audio.wav", wav_bytes, "audio/wav"),
        }

        def bill(body: dict[str, Any] | None) -> None:
            # Never less than the audio we sent: a missing or low reported duration is not free.
            reported = _int_or_zero(body.get("audioDurationMs")) if body else 0
            self._meter(coalition_id, participant, model, audio_ms=max(reported, wav_ms))

        body = await self._post(model, "/asr/transcribe", bill, files=files)
        turns = tuple(
            Turn(
                _int_or_zero(t.get("startMs")),
                _int_or_zero(t.get("endMs")),
                str(t.get("transcript", "")),
                t.get("speaker"),
            )
            for t in _dicts(body.get("turns"))
        )
        audio_ms = max(_int_or_zero(body.get("audioDurationMs")), wav_ms)
        return Transcript(str(body.get("transcript", "")), turns, audio_ms)
