# SPDX-License-Identifier: Apache-2.0
# pyright: reportAttributeAccessIssue=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportMissingParameterType=false
"""A minted device takes a seat: the Mint on the host, the owner's hold, offers, readings."""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import wave
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from room_flow import briefs_open, decide_plan, reply_brief
from room_rig import (
    BRIEF,
    RoomModel,
    bearer,
    engine_of,
    events,
    join,
    serve,
    server_of,
    sign,
    start_room,
    until,
    view_of,
)

from coalitionkit_models import CostMeter, ModelGateway, load_price_table
from coalitionkit_models.gateway import ChatMessage, RawCompletion, Usage
from coalitionkit_models.media import Transcript
from coalitionkit_models.sam import Box, Segment
from coalitionkit_models.settings import Route
from coalitionkit_models.settings import Settings as ModelSettings
from coalitionkit_server.room import device_mint
from coalitionkit_server.room.devices import hub

NEEDS: dict[str, Any] = {
    "needs": [
        {"title": "Book the shared unit", "kind": "schedule", "detail": "One slot on the unit."},
        {"title": "Share the costs", "kind": "budget", "detail": "Who pays what."},
        {"title": "Write the note", "kind": "draft", "detail": "A short note to send."},
    ],
    "slots": ["Mon 01 Jan, 09:00 UTC", "Mon 01 Jan, 11:00 UTC"],
}
RESOURCE = {
    "template": "resource",
    "name": "Shared unit",
    "windows": [{"start": 540, "end": 600}],
    "duration": 30,
    "limit": 2,
    "prerequisites": [],
}
DISPLAY = {
    "template": "device",
    "name": "Display unit",
    "fields": [{"id": "field_1", "unit": "count", "threshold": 50.0}],
    "interval_seconds": 60,
}


class MintModel:
    """The Mint's scripted transport: the config, the attacks, and what a frame shows."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config, self.shown = config, "42"

    async def create(
        self, route: Route, messages: Sequence[ChatMessage], opts: Mapping[str, Any]
    ) -> RawCompletion:
        system = str(messages[0]["content"])
        if "Fill the fixed" in system:
            reply: Any = self.config
        elif "adversarial" in system:
            reply = {"cases": [{"tool": "write", "arguments_json": "{}"}]}
        else:
            reply = {"records": [{"label": "field_1", "value": self.shown, "confidence": 0.99}]}
        return RawCompletion(json.dumps(reply), Usage(100, 40), "stop")


class Media:
    async def segment(self, image: bytes | str, phrase: str, *, coalition_id: str | None = None):
        assert isinstance(image, bytes)
        with Image.open(io.BytesIO(image)) as frame:
            w, h = frame.width, frame.height
        return (Segment(Box(0, 0, w, h, w, h), "", 0),)

    async def transcribe(self, wav_bytes: bytes, *, coalition_id: str | None = None) -> Transcript:
        return Transcript("Open from nine to ten. Slots of thirty minutes. Limit two.", ())


def media_files(tmp_path: Path) -> tuple[bytes, bytes]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg and ffprobe are required")
    frame = tmp_path / "frame.png"
    Image.new("RGB", (320, 180), "white").save(frame)
    video = tmp_path / "input.mp4"
    subprocess.run(
        [
            *(ffmpeg, "-nostdin", "-v", "error", "-loop", "1", "-i", str(frame), "-t", "1"),
            *("-r", "1", "-pix_fmt", "yuv420p", str(video)),
        ],
        check=True,
        timeout=30,
    )
    voice = io.BytesIO()
    with wave.open(voice, "wb") as audio:
        audio.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        audio.writeframes(b"\0\0" * 16000)
    return video.read_bytes(), voice.getvalue()


def frame_png(value: str) -> bytes:
    image = Image.new("RGB", (320, 120), "white")
    ImageDraw.Draw(image).text((20, 40), f"Field 1: {value}", fill="black")
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def offers(user: str) -> dict[str, Any]:
    ids = [n["id"] for n in json.loads(user)["needs"]]
    return {
        "offers": [{"need_id": i, "minutes": 40, "money": 0, "effort": "medium"} for i in ids],
        "note": "Offered a little on each.",
    }


def two_seated(client: TestClient, config: dict[str, Any]) -> tuple[str, Any, dict[str, Any]]:
    room = start_room(client, seats=3)
    cid, engine = room["coalition_id"], engine_of(client)
    member = join(client, room)
    sign(client, cid, room["owner"]["token"], "p1")
    sign(client, cid, member["token"], member["participant"])
    until(lambda: len(events(client, cid, "need")) >= 3, what="needs")
    h = hub(engine)
    h.script = MintModel(config)
    h.gateway = ModelGateway(
        ModelSettings(), transport=h.script, meter=CostMeter(load_price_table())
    )
    h.media = Media()
    return cid, engine, {"p1": room["owner"], member["participant"]: member}


def begin(client: TestClient, cid: str, people: dict[str, Any]) -> None:
    """The owner begins; the people seated sign the revised charter, as on their screens."""
    client.post("/v1/room/begin", json={}, headers=bearer(people["p1"]["token"]))
    for who, person in people.items():
        sign(client, cid, person["token"], who)


def mint_one(
    client: TestClient, tmp_path: Path, cid: str, owner: str, label: str, template: str
) -> str:
    video, voice = media_files(tmp_path)
    need = events(client, cid, "need")[0]["payload"]["need_id"]
    sent = client.post(
        "/v1/room/mint",
        files={"video": ("v.mp4", video, "video/mp4"), "voice": ("n.wav", voice, "audio/wav")},
        data={"label": label, "needs": need, "template": template},
        headers=bearer(owner),
    )
    assert sent.status_code == 202, sent.text
    pid = sent.json()["device"]
    engine = engine_of(client)
    until(lambda: engine.read(cid)["devices"][pid]["state"] != "minting", 60, "the Mint")
    entry = engine.read(cid)["devices"][pid]
    assert entry["state"] == "approve", entry
    return pid


def test_a_minted_resource_is_approved_by_hold_offers_on_a_hold_and_confirms(
    tmp_path: Path,
) -> None:
    scripted = RoomModel(needs=NEEDS, brief=BRIEF, offers=offers)
    with serve(tmp_path, scripted) as client:
        cid, engine, people = two_seated(client, RESOURCE)
        owner, member = people["p1"]["token"], next(v for k, v in people.items() if k != "p1")
        pid = mint_one(client, tmp_path, cid, owner, "Shared unit", "resource")
        seen = {d["id"]: d for d in view_of(engine, cid, "p1")["devices"]}[pid]
        assert seen["state"] == "approve" and seen["can_approve"], seen
        assert seen["attacks"]["passed"] == seen["attacks"]["total"] > 0
        assert seen["needs"][0]["title"] == "Book the shared unit"
        assert [s["state"] for s in seen["stages"]][:5] == ["done"] * 5
        others = view_of(engine, cid, member["participant"])["devices"][0]
        assert not others["can_approve"], "only its owner may approve it"
        refused = client.post(
            "/v1/room/mint/approve", json={"device": pid}, headers=bearer(member["token"])
        )
        assert refused.status_code == 403
        assert pid not in server_of(client).hosts[cid].state.members
        approved = client.post("/v1/room/mint/approve", json={"device": pid}, headers=bearer(owner))
        assert approved.status_code == 200, approved.text
        host = server_of(client).hosts[cid]
        assert pid in host.state.members
        seat = next(s for s in view_of(engine, cid, "p1")["seats"] if s["seat"] == pid)
        assert seat["kind"] == "device" and seat["label"] == "Shared unit"
        card = json.loads(
            (device_mint.mint_root(engine) / cid / pid / "agent-card.json").read_text()
        )
        assert card["name"] == "Shared unit" and card.get("signatures"), "the owner signed it"

        begin(client, cid, people)
        assert pid not in host.state.charter["deciders"], "a device never decides"
        briefs_open(engine, cid, list(people))
        for person in people.values():
            reply_brief(client, person["token"], {"q1": None, "q2": 2, "q3": None})
        until(lambda: engine.read(cid)["offers_done"], 60, "offers")
        mine = [e for e in events(client, cid, "offer") if e["on_behalf_of"] == pid]
        assert len(mine) == 1 and mine[0]["payload"]["cost"] == {
            "minutes": 30,
            "money": 0,
            "effort": "low",
        }
        assert engine.read(cid)["devices"][pid]["hold"]["state"] == "held"
        assert "nonce" not in json.dumps(view_of(engine, cid, member["participant"]))
        until(lambda: events(client, cid, "propose"), 60, "plans")
        until(lambda: host.open_consents("p1"), 20, "an ask")
        decide_plan(client, cid, people)
        need = mine[0]["payload"]["target"]["id"]
        until(lambda: host.state.tasks[need]["status"] in {"decided", "committed", "done"}, 30)
        assert host.state.tasks[need]["assignee"] == pid, "the cheapest offer is the device's"
        until(lambda: host.state.tasks[need]["status"] == "done", 40, "the device to finish")
        assert engine.read(cid)["devices"][pid]["hold"]["state"] == "confirmed"
        result = [
            json.loads(e["payload"]["content"])
            for e in events(client, cid, "observe")
            if e["on_behalf_of"] == pid and e["payload"]["source"] == "document"
        ]
        assert result and result[0]["data"]["items"][0]["start"] == "09:00"


def test_a_display_device_publishes_readings_and_a_crossing_ripples(tmp_path: Path) -> None:
    scripted = RoomModel(needs=NEEDS, brief=BRIEF, offers=offers)
    with serve(tmp_path, scripted) as client:
        cid, engine, people = two_seated(client, DISPLAY)
        owner = people["p1"]["token"]
        pid = mint_one(client, tmp_path, cid, owner, "Display unit", "device")
        assert (
            client.post(
                "/v1/room/mint/approve", json={"device": pid}, headers=bearer(owner)
            ).status_code
            == 200
        )
        begin(client, cid, people)
        briefs_open(engine, cid, list(people))
        for person in people.values():
            reply_brief(client, person["token"], {"q1": None, "q2": 2, "q3": None})
        until(lambda: engine.read(cid)["offers_done"], 60, "offers")
        assert not [e for e in events(client, cid, "offer") if e["on_behalf_of"] == pid]

        frame = {"frame": ("f.png", frame_png("42"), "image/png")}
        read = client.post(
            "/v1/room/mint/frame", files=frame, data={"device": pid}, headers=bearer(owner)
        )
        assert read.status_code == 200, read.text
        assert read.json()["reading"][0]["value"] == 42.0 and not read.json()["rippled"]
        shown = view_of(engine, cid, people[next(iter(people.keys() - {"p1"}))]["participant"])
        assert shown["devices"][0]["reading"][0]["over"] is False
        observed = [e for e in events(client, cid, "observe") if e["payload"]["source"] == "device"]
        assert len(observed) == 1 and observed[0]["on_behalf_of"] == pid

        hub(engine).script.shown = "61"
        over = {"frame": ("f.png", frame_png("61"), "image/png")}
        read = client.post(
            "/v1/room/mint/frame", files=over, data={"device": pid}, headers=bearer(owner)
        )
        assert read.status_code == 200, read.text
        assert read.json()["rippled"], "crossing the threshold ripples the needs that name it"
        ripple = [e for e in events(client, cid, "ripple") if e["on_behalf_of"] == pid]
        assert len(ripple) == 1 and "above its limit of 50" in ripple[0]["payload"]["change"]
        not_owner = people[next(iter(people.keys() - {"p1"}))]["token"]
        refused = client.post(
            "/v1/room/mint/frame", files=over, data={"device": pid}, headers=bearer(not_owner)
        )
        assert refused.status_code == 403
