# SPDX-License-Identifier: Apache-2.0
"""Live tests against the real Meta Model API. Neutral prompts, synthetic data only.

They run only with COALITIONKIT_LIVE=1 and COALITIONKIT_META_API_KEY (see conftest.py). The
key is read from the environment and never stored anywhere.
"""

from __future__ import annotations

import base64
import os
import struct
import subprocess
import tempfile
import time
import zlib
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict

from coalitionkit_models import (
    CostMeter,
    MediaClient,
    ModelGateway,
    Settings,
    load_price_table,
    validate_wav,
)

pytestmark = pytest.mark.live
USER: Any = [{"role": "user", "content": "Reply with the single word: ready"}]
CO = "live-test"
_SHARED: dict[str, bytes] = {}


def _settings(**kw: Any) -> Settings:
    key = os.environ.get("COALITIONKIT_META_API_KEY", "")
    return Settings(_env_file=None, meta_api_key=key, **kw)  # pyright: ignore[reportCallIssue]


def _log(
    rows: list[dict[str, object]],
    test: str,
    model: str,
    started: float,
    meter: CostMeter,
    note: str,
) -> None:
    records = [r for r in meter.records if r.coalition_id == CO]
    rows.append(
        {
            "test": test,
            "model": model,
            "latency": time.perf_counter() - started,
            "prompt": sum(r.prompt_tokens for r in records),
            "completion": sum(r.completion_tokens for r in records),
            "reasoning": sum(r.reasoning_tokens for r in records),
            "cost": meter.total(CO),
            "note": note,
        }
    )


@pytest.fixture
async def make_gateway() -> AsyncIterator[Callable[..., tuple[ModelGateway, CostMeter]]]:
    opened: list[ModelGateway] = []

    def make(**kw: Any) -> tuple[ModelGateway, CostMeter]:
        meter = CostMeter(load_price_table())
        gateway = ModelGateway(_settings(**kw), meter=meter)
        opened.append(gateway)
        return gateway, meter

    yield make
    for gateway in opened:
        await gateway.aclose()


async def test_chat_muse_spark_13(
    live_rows: list[dict[str, object]], make_gateway: Callable[..., Any]
) -> None:
    gateway, meter = make_gateway()
    started = time.perf_counter()
    result = await gateway.complete("hosted_agent", USER, coalition_id=CO)
    assert "ready" in result.text.lower()
    _log(live_rows, "chat hosted_agent (minimal)", result.model, started, meter, "one word")


async def test_chat_composer_low_effort(
    live_rows: list[dict[str, object]], make_gateway: Callable[..., Any]
) -> None:
    gateway, meter = make_gateway()
    started = time.perf_counter()
    result = await gateway.complete("composer", USER, coalition_id=CO)
    assert "ready" in result.text.lower()
    _log(live_rows, "chat composer (low)", result.model, started, meter, "one word")


async def test_chat_contributor_tier(
    live_rows: list[dict[str, object]], make_gateway: Callable[..., Any]
) -> None:
    gateway, meter = make_gateway(composer_model="muse-spark-1.3-contributor")
    started = time.perf_counter()
    result = await gateway.complete("composer", USER, coalition_id=CO)
    assert "ready" in result.text.lower()
    _log(live_rows, "chat contributor tier", result.model, started, meter, "synthetic prompt")


async def test_chat_muse_wonder_through_the_gateway(
    live_rows: list[dict[str, object]], make_gateway: Callable[..., Any]
) -> None:
    gateway, meter = make_gateway()
    started = time.perf_counter()
    result = await gateway.complete("gardener", USER, coalition_id=CO)
    assert "ready" in result.text.lower()
    _log(live_rows, "chat gardener = Muse Wonder", result.model, started, meter, "chat completions")


async def test_steward_route_on_the_meta_key(
    live_rows: list[dict[str, object]], make_gateway: Callable[..., Any]
) -> None:
    gateway, meter = make_gateway(steward_provider="meta")
    started = time.perf_counter()
    result = await gateway.complete("steward", USER, coalition_id=CO, temperature=0, max_tokens=400)
    assert result.model == "muse-spark-1.3"
    assert result.text.strip()
    _log(live_rows, "steward on Meta route", result.model, started, meter, "legacy opts as sent")


async def test_tool_call(
    live_rows: list[dict[str, object]], make_gateway: Callable[..., Any]
) -> None:
    gateway, meter = make_gateway()
    tools = [
        {
            "type": "function",
            "function": {
                "name": "lookup_value",
                "description": "Look up the stored value for a key. Use it; never guess values.",
                "parameters": {
                    "type": "object",
                    "properties": {"key": {"type": "string"}},
                    "required": ["key"],
                },
            },
        }
    ]
    messages: Any = [{"role": "user", "content": "What is the stored value for the key alpha?"}]
    started = time.perf_counter()
    result = await gateway.complete(
        "hosted_agent", messages, coalition_id=CO, tools=tools, tool_choice="auto"
    )
    assert result.tool_calls, result.text
    call = result.tool_calls[0]
    assert call.name == "lookup_value"
    assert str(call.arguments.get("key", "")).lower() == "alpha"
    _log(live_rows, "tool call", result.model, started, meter, f"args={call.arguments}")


class Shape(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    sides: int


async def test_strict_json_schema(
    live_rows: list[dict[str, object]], make_gateway: Callable[..., Any]
) -> None:
    gateway, meter = make_gateway()
    messages: Any = [{"role": "user", "content": "Describe a triangle: its name and sides."}]
    started = time.perf_counter()
    result = await gateway.complete(
        "hosted_agent", messages, coalition_id=CO, response_schema=Shape
    )
    assert isinstance(result.parsed, Shape)
    assert result.parsed.sides == 3
    _log(live_rows, "strict json_schema", result.model, started, meter, result.text.strip()[:60])


def _png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    row = b"\x00" + bytes(rgb) * width
    raw = zlib.compress(row * height)

    def chunk(kind: bytes, body: bytes) -> bytes:
        crc = zlib.crc32(kind + body) & 0xFFFFFFFF
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", crc)

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", raw) + chunk(b"IEND", b"")


async def test_vision_input(
    live_rows: list[dict[str, object]], make_gateway: Callable[..., Any]
) -> None:
    gateway, meter = make_gateway()
    url = "data:image/png;base64," + base64.b64encode(_png(96, 96, (255, 0, 0))).decode("ascii")
    messages: Any = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What single colour fills this image? One word."},
                {"type": "image_url", "image_url": {"url": url}},
            ],
        }
    ]
    started = time.perf_counter()
    result = await gateway.complete("hosted_agent", messages, coalition_id=CO)
    assert "red" in result.text.lower()
    _log(live_rows, "vision input", result.model, started, meter, "96x96 red PNG")


async def test_image_generation(live_rows: list[dict[str, object]]) -> None:
    meter = CostMeter(load_price_table())
    client = MediaClient(_settings(), meter=meter)
    started = time.perf_counter()
    try:
        data = await client.generate_image(
            "five solid blue circles of different sizes on a plain white background",
            "1024x1024",
            coalition_id=CO,
        )
    finally:
        await client.aclose()
    assert len(data) > 1000
    _SHARED["image"] = data
    head = data[:4] + data[8:12]
    _log(live_rows, "image generation", "muse-image-1.0", started, meter, f"{len(data)} B {head!r}")


async def test_sam_on_the_generated_image(live_rows: list[dict[str, object]]) -> None:
    image = _SHARED.get("image")
    if image is None:
        pytest.skip("needs the image from test_image_generation in the same run")
    meter = CostMeter(load_price_table())
    client = MediaClient(_settings(), meter=meter)
    started = time.perf_counter()
    try:
        segments = await client.segment(image, "circle", coalition_id=CO)
    finally:
        await client.aclose()
    assert len(segments) >= 3
    assert all(s.box.x2 > s.box.x1 and s.box.y2 > s.box.y1 for s in segments)
    assert all(s.mask_kind in ("lossless", "one_bit") for s in segments)
    kinds = sorted({s.mask_kind for s in segments})
    _log(live_rows, "SAM segment", "sam-3.1", started, meter, f"{len(segments)} circles {kinds}")


SENTENCE = "The quick brown fox jumps over the lazy dog near the old stone bridge."


def _synthesise_wav(path: Path) -> None:
    script = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$f = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo("
        "16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, "
        "[System.Speech.AudioFormat.AudioChannel]::Mono); "
        f"$s.SetOutputToWaveFile('{path}', $f); $s.Speak('{SENTENCE}'); $s.Dispose()"
    )
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        check=True,
        timeout=60,
    )


@pytest.mark.parametrize("mode", ["PUSH_TO_TALK", "ENDPOINTING", "DIARIZATION"])
async def test_transcription_of_a_synthesised_wav(
    live_rows: list[dict[str, object]], mode: Any
) -> None:
    if os.name != "nt":
        pytest.skip("needs Windows System.Speech to synthesise the WAV")
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "speech.wav"
        _synthesise_wav(path)
        audio = path.read_bytes()
    info = validate_wav(audio)
    meter = CostMeter(load_price_table())
    client = MediaClient(_settings(), meter=meter)
    started = time.perf_counter()
    try:
        transcript = await client.transcribe(audio, mode, coalition_id=CO)
    finally:
        await client.aclose()
    words = transcript.text.lower().replace(".", "").split()
    assert {"quick", "fox", "bridge"} <= set(words), transcript.text
    assert transcript.audio_ms > 0
    note = f"{info.duration_ms} ms audio, {len(transcript.turns)} turn(s)"
    _log(live_rows, f"transcription {mode}", "muse-voice-transcribe-1.0", started, meter, note)
