# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Phone inputs against the real Meta models: real speech to words, a real image to an answer.

The room around them is scripted (needs, brief); the transcriber, the vision reading and the image
are real calls. Reads COALITIONKIT_META_API_KEY from the environment only and runs with
COALITIONKIT_LIVE=1. Run with ``-s``: each test prints one ``OUTCOME`` line with the measured time,
tokens and cost.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from room_flow import briefs_open, full_room
from room_rig import BRIEF, NEEDS, RoomModel, bearer, engine_of, serve, server_of

from coalitionkit_models import ModelGateway
from coalitionkit_models.gateway import ChatMessage, OpenAITransport, RawCompletion
from coalitionkit_models.media import MediaClient
from coalitionkit_models.settings import Route
from coalitionkit_models.settings import Settings as ModelSettings
from coalitionkit_server.adapter import Document

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("COALITIONKIT_LIVE") != "1"
        or not os.environ.get("COALITIONKIT_META_API_KEY", "").strip(),
        reason="no key",
    ),
]
SPOKEN = "I cannot do the second one on Saturday"
SHELF = (
    "A plain wooden shelf against a white wall holding exactly three cardboard boxes side by "
    "side, labelled A, B and C in large black letters, photographed straight on"
)
COUNT: Document = {
    "id": "q1",
    "ask": "How many boxes are on the shelf?",
    "why": "So your agent knows what is there.",
    "kind": "amount",
    "component": "Slider",
    "options": [],
    "low": 0,
    "high": 10,
    "step": 1,
    "unit": "boxes",
    "status": "open",
    "answer": None,
    "messages": [],
}


class LiveReading(RoomModel):
    """The scripted room, with the reading prompts sent to the real model."""

    def __init__(self, **kw: Any) -> None:
        super().__init__(**kw)
        self.real = OpenAITransport(ModelSettings())

    async def create(
        self, route: Route, messages: Sequence[ChatMessage], opts: Mapping[str, Any]
    ) -> RawCompletion:
        system = str(messages[0]["content"])
        if "took a photo" in system or "answers one of your questions" in system:
            return await self.real.create(route, messages, opts)
        return await super().create(route, messages, opts)


def speech(text: str, folder: Path) -> bytes:
    path = folder / "say.wav"
    script = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$f = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo("
        "16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, "
        "[System.Speech.AudioFormat.AudioChannel]::Mono); "
        f"$s.SetOutputToWaveFile('{path}', $f); $s.Speak('{text}'); $s.Dispose()"
    )
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        check=True,
        timeout=60,
    )
    return path.read_bytes()


def metered(client: TestClient, cid: str, since: int) -> str:
    """The real calls only: the meter's records after ``since`` (the scripted room came first)."""
    meter = server_of(client).gateway.meter
    assert meter is not None
    rows = [r for r in meter.records[since:] if r.coalition_id == cid]
    tokens = (sum(r.prompt_tokens for r in rows), sum(r.completion_tokens for r in rows))
    cost = sum(r.cost_micro_usd for r in rows) / 1_000_000
    models = sorted({r.model for r in rows})
    return f"calls={len(rows)} models={models} tokens={tokens} cost_usd={cost:.5f}"


def mark(client: TestClient) -> int:
    meter = server_of(client).gateway.meter
    assert meter is not None
    return len(meter.records)


def live_room(client: TestClient) -> tuple[str, Document]:
    gateway: ModelGateway = server_of(client).gateway
    server_of(client).media = MediaClient(gateway.settings, meter=gateway.meter)
    room, (member,) = full_room(client, seats=2)
    cid = room["coalition_id"]
    briefs_open(engine_of(client), cid, ["p1", member["participant"]])
    return cid, room["owner"]


@pytest.mark.skipif(os.name != "nt", reason="needs Windows System.Speech to make the speech")
def test_real_speech_becomes_the_words_said(tmp_path: Path) -> None:
    model = LiveReading(needs=NEEDS, brief=BRIEF)
    with serve(tmp_path, model) as client, tempfile.TemporaryDirectory() as folder:
        cid, owner = live_room(client)
        audio = speech(SPOKEN, Path(folder))
        since = mark(client)
        started = time.perf_counter()
        reply = client.post(
            "/v1/room/voice",
            content=audio,
            headers={**bearer(owner["token"]), "Content-Type": "audio/wav"},
        )
        wall = round((time.perf_counter() - started) * 1000)
        assert reply.status_code == 200, reply.text
        body = reply.json()
        words = set(body["text"].lower().replace(".", "").replace(",", "").split())
        assert {"second", "saturday"} <= words, body["text"]
        print(f"\nOUTCOME voice text={body['text']!r} ms={body['ms']} wall_ms={wall}")
        amount = client.post(
            "/v1/room/voice",
            content=speech("About four hours", Path(folder)),
            params={"question_id": "q2"},
            headers={**bearer(owner["token"]), "Content-Type": "audio/wav"},
        ).json()
        assert amount["answer"] == 4, amount
        print(f"OUTCOME voice-answer {amount} {metered(client, cid, since)}")


async def made(settings: ModelSettings, meter: Any, cid: str) -> bytes:
    client = MediaClient(settings, meter=meter)
    try:
        return await client.generate_image(SHELF, coalition_id=cid)
    finally:
        await client.aclose()


def test_a_real_image_answers_a_brief_question(tmp_path: Path) -> None:
    model = LiveReading(needs=NEEDS, brief=BRIEF)
    with serve(tmp_path, model) as client:
        cid, owner = live_room(client)
        engine = engine_of(client)
        record = engine.vault(cid, "p1")["_room_brief"]
        record["questions"][0] = COUNT
        engine.vault_put(cid, "p1", "_room_brief", record)
        media = server_of(client).media
        assert media is not None
        since = mark(client)
        started = time.perf_counter()
        image = asyncio.run(made(media.settings, media.meter, cid))
        made_ms = round((time.perf_counter() - started) * 1000)
        Path(os.environ.get("INPUTS_SHOTS", str(tmp_path)), "shelf.webp").write_bytes(image)
        reply = client.post(
            "/v1/room/photo",
            files={"image": ("shelf.webp", image, "image/webp")},
            data={"question_id": "q1"},
            headers=bearer(owner["token"]),
        )
        assert reply.status_code == 200, reply.text
        body = reply.json()
        assert body["answer"] == 3, body
        said = client.post(
            "/v1/room/photo?purpose=say",
            content=image,
            headers={**bearer(owner["token"]), "Content-Type": "image/webp"},
        ).json()
        assert said["answer"] and said["description"], said
        cost = metered(client, cid, since)
        print(f"OUTCOME photo image_ms={made_ms} answer={body} say={said} {cost}")
