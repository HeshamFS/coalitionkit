# SPDX-License-Identifier: Apache-2.0
# pyright: reportAttributeAccessIssue=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""The Mint on the host against the real Meta media models, then the device takes its seat."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageDraw
from room_rig import BRIEF, RoomModel, bearer, engine_of, serve, server_of, until, view_of
from test_room_devices import NEEDS, mint_one, two_seated

from coalitionkit_models import CostMeter, ModelGateway, load_price_table
from coalitionkit_models.media import MediaClient
from coalitionkit_models.settings import load_settings
from coalitionkit_server.room.devices import hub

pytestmark = pytest.mark.live


@pytest.fixture(autouse=True)
def live_gate() -> None:
    if not os.environ.get("COALITIONKIT_META_API_KEY"):
        pytest.skip("no key")
    if os.environ.get("COALITIONKIT_LIVE") != "1":
        pytest.skip("COALITIONKIT_LIVE is not 1")


SPEAK = "\n".join(
    [
        "Add-Type -AssemblyName System.Speech",
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer",
        "$f = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, "
        "[System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, "
        "[System.Speech.AudioFormat.AudioChannel]::Mono)",
        "$s.SetOutputToWaveFile($args[0], $f)",
        "$s.Speak($args[1])",
        "$s.Dispose()",
        "",
    ]
)


def real_media(tmp_path: Path) -> tuple[bytes, bytes]:
    """A neutral schedule board on video, and a synthesized voice note with its rules."""
    ffmpeg = shutil.which("ffmpeg")
    if os.name != "nt" or not ffmpeg:
        pytest.skip("needs Windows speech synthesis and ffmpeg")
    image = Image.new("RGB", (960, 540), "white")
    draw = ImageDraw.Draw(image)
    for row, line in enumerate(("Shared unit", "Slot 1: 09:00 - 09:30", "Slot 2: 09:30 - 10:00")):
        draw.rectangle((30, 30 + row * 150, 930, 160 + row * 150), outline="black", width=5)
        draw.text((60, 60 + row * 150), line, fill="black", font_size=56)
    frame, video, voice = tmp_path / "f.png", tmp_path / "v.mp4", tmp_path / "n.wav"
    image.save(frame)
    subprocess.run(
        [
            *(ffmpeg, "-nostdin", "-v", "error", "-loop", "1", "-i", str(frame), "-t", "2"),
            *("-r", "1", "-pix_fmt", "yuv420p", str(video)),
        ],
        check=True,
        timeout=30,
    )
    script = tmp_path / "speak.ps1"
    script.write_text(SPEAK, encoding="utf-8")
    words = (
        "Shared unit opens at 9 and closes at 10. Slots last 30 minutes. "
        "The limit is 2 holds. There are no prerequisites."
    )
    shell = ("powershell.exe", "-NoProfile", "-NonInteractive", "-File")
    subprocess.run(
        [*shell, str(script), str(voice), words],
        check=True,
        timeout=30,
    )
    return video.read_bytes(), voice.read_bytes()


def test_a_real_mint_seats_a_device_after_the_owners_hold(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        cid, engine, people = two_seated(client, {"template": "resource"})
        settings = load_settings()
        meter = CostMeter(load_price_table())
        h = hub(engine)
        h.gateway = ModelGateway(settings, meter=meter)
        h.media = MediaClient(settings, meter=meter)
        owner = people["p1"]["token"]
        media = real_media(tmp_path)
        pid = mint_one(client, tmp_path, cid, owner, "Shared unit", "resource", media)
        entry = engine.read(cid)["devices"][pid]
        print("LIVE mint", entry["elapsed"], "s", entry["cost_micro_usd"], "micro-USD")
        print("LIVE attacks", entry["attacks"], "tokens", entry["tokens"])
        approved = client.post("/v1/room/mint/approve", json={"device": pid}, headers=bearer(owner))
        assert approved.status_code == 200, approved.text
        assert pid in server_of(client).hosts[cid].state.members
        until(lambda: view_of(engine, cid, "p1")["devices"][0]["health"] == "live", 10)
        assert any(s["kind"] == "device" for s in view_of(engine_of(client), cid, "p1")["seats"])
        await_tools = engine.read(cid)["devices"][pid]["tools"]
        assert "hold_slot" in await_tools
