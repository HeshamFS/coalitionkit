# SPDX-License-Identifier: Apache-2.0
"""Neutral media generated only inside each test's temporary directory."""

import io
import os
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any

import pytest
from PIL import Image, ImageDraw

from coalitionkit_models.gateway import FakeModel, ModelGateway, ScriptedResponse
from coalitionkit_models.media import Transcript
from coalitionkit_models.meter import CostMeter
from coalitionkit_models.prices import load_price_table
from coalitionkit_models.sam import Box, Segment
from coalitionkit_models.settings import Settings


@pytest.fixture(autouse=True)
def live_gate(request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("live"):
        if not os.environ.get("COALITIONKIT_META_API_KEY"):
            pytest.skip("no key")
        if os.environ.get("COALITIONKIT_LIVE") != "1":
            pytest.skip("COALITIONKIT_LIVE is not 1")


class ScriptedMedia:
    async def segment(
        self, image: bytes | str, phrase: str, *, coalition_id: str | None = None
    ) -> tuple[Segment, ...]:
        assert isinstance(image, bytes)
        with Image.open(io.BytesIO(image)) as frame:
            return (
                Segment(Box(0, 0, frame.width, frame.height, frame.width, frame.height), "", 0),
            )

    async def transcribe(self, wav_bytes: bytes, *, coalition_id: str | None = None) -> Transcript:
        return Transcript(
            "Open from minute 540 to 600. Duration 30. Limit 2. No prerequisites.", ()
        )


@pytest.fixture
def config(request: pytest.FixtureRequest) -> dict[str, Any]:
    if request.param == "device":
        return {
            "template": "device",
            "name": "Device A",
            "fields": [{"id": "field_1", "unit": "count", "threshold": 50.0}],
            "interval_seconds": 2,
        }
    return {
        "template": "resource",
        "name": "Resource A",
        "windows": [{"start": 540, "end": 600}],
        "duration": 30,
        "limit": 2,
        "prerequisites": [],
    }


@pytest.fixture
def media_files(tmp_path: Path, config: dict[str, Any]) -> tuple[Path, Path, Path]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg and ffprobe are required")
    image = Image.new("RGB", (640, 360), "white")
    draw = ImageDraw.Draw(image)
    if config["template"] == "device":
        draw.rectangle((20, 20, 620, 200), outline="black", width=5)
        draw.text((40, 60), "Field 1: 42", fill="black", font_size=48)
    else:
        for row, text in enumerate(
            ("Resource A", "Slot 1: 09:00 - 09:30", "Slot 2: 09:30 - 10:00")
        ):
            draw.rectangle((10, 10 + row * 100, 630, 100 + row * 100), outline="black")
            draw.text((25, 30 + row * 100), text, fill="black", font_size=32)
    frame = tmp_path / "frame.png"
    image.save(frame)
    video = tmp_path / "input.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-nostdin",
            "-v",
            "error",
            "-loop",
            "1",
            "-i",
            str(frame),
            "-t",
            "1",
            "-r",
            "1",
            "-pix_fmt",
            "yuv420p",
            str(video),
        ],
        check=True,
        timeout=15,
    )
    voice = tmp_path / "voice.wav"
    with wave.open(str(voice), "wb") as audio:
        audio.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        audio.writeframes(b"\0\0" * 16000)
    return video, voice, frame


@pytest.fixture
def scripted(config: dict[str, Any]) -> tuple[ModelGateway, ScriptedMedia, FakeModel]:
    import json

    fake = FakeModel(
        [
            ScriptedResponse('{"records":[{"label":"field_1","value":"42","confidence":0.99}]}'),
            ScriptedResponse(json.dumps(config)),
            ScriptedResponse('{"cases":[{"tool":"write","arguments_json":"{}"}]}'),
        ]
    )
    return (
        ModelGateway(Settings(), transport=fake, meter=CostMeter(load_price_table())),
        ScriptedMedia(),
        fake,
    )


def synthesize(voice: Path, template: str) -> None:
    if os.name != "nt":
        pytest.skip("System.Speech voice synthesis requires Windows")
    sentence = (
        "The display has field_1 in count units. Alarm above 50. Read every 2 seconds."
        if template == "device"
        else "Resource A opens at 9 and closes at 10. Slots last 30 minutes. "
        "The limit is 2 holds. There are no prerequisites."
    )
    script = voice.parent / "voice.ps1"
    script.write_text(
        "# SPDX-License-Identifier: Apache-2.0\n"
        "$ErrorActionPreference = 'Stop'\nAdd-Type -AssemblyName System.Speech\n"
        "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer\n"
        "$format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, "
        "[System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, "
        "[System.Speech.AudioFormat.AudioChannel]::Mono)\n"
        "$speaker.SetOutputToWaveFile($args[0], $format)\n"
        "$speaker.Speak($args[1])\n$speaker.Dispose()\n",
        encoding="utf-8",
    )
    try:
        subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-File",
                str(script),
                str(voice),
                sentence,
            ],
            check=True,
            timeout=20,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        pytest.skip("System.Speech unavailable: " + type(exc).__name__)
