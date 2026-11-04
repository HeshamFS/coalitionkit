# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""Phone inputs: a spoken clip or a photo becomes words the person confirms, and nothing else."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from inputs_rig import PNG, ReadingModel, media, reading, wav
from room_flow import briefs_open, full_room
from room_rig import BRIEF, BRIEF_TEXT, NEEDS, bearer, engine_of, events, serve, server_of, view_of

from coalitionkit_server.room import inputs
from coalitionkit_server.room.inputs_read import rule_answer

HEARD = "I cannot do the second one on Saturday"


def brief_room(client: TestClient, heard: str = HEARD, sent: list[bytes] | None = None):
    server_of(client).media = media(heard, sent)
    room, (member,) = full_room(client, seats=2)
    cid, engine = room["coalition_id"], engine_of(client)
    briefs_open(engine, cid, ["p1", member["participant"]])
    return cid, engine, room["owner"], member


def post_voice(
    client: TestClient, token: str, audio: bytes, **params: str
) -> Any:  # raw body, as the web sends it
    return client.post(
        "/v1/room/voice",
        content=audio,
        params=params,
        headers={**bearer(token), "Content-Type": "audio/wav"},
    )


def no_reader(_s: str, _u: str, _i: bool) -> dict[str, Any] | None:
    return None


def stored(tmp_path: Path) -> bytes:
    return b"".join(p.read_bytes() for p in tmp_path.glob("host.db*"))


def test_a_clip_becomes_words_for_the_speaker_only_and_the_audio_is_not_kept(
    tmp_path: Path,
) -> None:
    sent: list[bytes] = []
    with serve(tmp_path, ReadingModel(no_reader, needs=NEEDS, brief=BRIEF)) as client:
        cid, engine, owner, member = brief_room(client, sent=sent)
        before = len(server_of(client).store.read(cid))
        audio = wav(1.5)
        reply = post_voice(client, owner["token"], audio)
        assert reply.status_code == 200, reply.text
        body = reply.json()
        assert body["text"] == HEARD and body["source"] == "model" and body["ms"] >= 0
        assert audio in sent[0], "the clip went to the transcriber as it was"
        assert len(server_of(client).store.read(cid)) == before, "hearing words is no event"
        mine = view_of(engine, cid, "p1")["mine"]["inputs"]
        assert mine == [{"kind": "voice", "text": HEARD, "ms": body["ms"]}]
        other = view_of(engine, cid, member["participant"])
        assert other["mine"]["inputs"] == [] and HEARD not in json.dumps(other)
        assert audio[44:2000] not in stored(tmp_path), "the audio never reaches the store"
        multipart = client.post(
            "/v1/room/voice",
            files={"audio": ("clip.wav", audio, "audio/wav")},
            headers=bearer(owner["token"]),
        )
        assert multipart.status_code == 200 and multipart.json()["text"] == HEARD


def test_a_clip_is_refused_when_it_is_not_a_short_mono_wav(tmp_path: Path) -> None:
    with serve(tmp_path, ReadingModel(no_reader, needs=NEEDS, brief=BRIEF)) as client:
        _cid, _engine, owner, _member = brief_room(client)
        token = owner["token"]
        assert post_voice(client, token, wav(21)).status_code == 413
        assert post_voice(client, token, wav(1, channels=2)).status_code == 422
        assert post_voice(client, token, wav(1, rate=44_100)).status_code == 422
        assert post_voice(client, token, b"not audio").status_code == 422
        assert post_voice(client, token, b"").status_code == 422
        assert post_voice(client, token, b"x" * (3 * 1024 * 1024)).status_code == 413
        assert client.post("/v1/room/voice", content=wav(1)).status_code == 401
        assert post_voice(client, token, wav(1), question_id="q9").status_code == 404


def test_spoken_words_answer_a_closed_question_after_the_person_confirms(tmp_path: Path) -> None:
    def reader(system: str, user: str, image: bool) -> dict[str, Any] | None:
        data = json.loads(user)
        assert not image and "by speaking" in system and data["kind"] == "amount"
        assert data["words"] == "about four hours"
        return reading(number=4, has_number=True)

    with serve(tmp_path, ReadingModel(reader, needs=NEEDS, brief=BRIEF)) as client:
        server_of(client).media = media("about four hours")
        room, (member,) = full_room(client, seats=2)
        cid, engine = room["coalition_id"], engine_of(client)
        briefs_open(engine, cid, ["p1", member["participant"]])
        token = room["owner"]["token"]
        body = post_voice(client, token, wav(1), question_id="q2").json()
        assert body["answer"] == 4 and body["words"] == "4 hours"
        assert body["answer_source"] == "model" and body["question_id"] == "q2"
        record = engine.vault(cid, "p1")["_room_brief"]["questions"][1]
        assert record["status"] == "open", "nothing is answered until the person confirms"
        confirm = client.post(
            "/v1/room/brief",
            json={"question_id": "q2", "value": body["answer"]},
            headers=bearer(token),
        )
        assert confirm.status_code == 200
        assert engine.vault(cid, "p1")["_room_brief"]["questions"][1]["answer"] == 4
        assert post_voice(client, token, wav(1), question_id="q2").status_code == 409


def test_words_answer_by_rules_when_the_model_cannot(tmp_path: Path) -> None:
    with serve(tmp_path, ReadingModel(no_reader, needs=NEEDS, brief=BRIEF_TEXT)) as client:
        _cid, _engine, owner, _member = brief_room(client, heard="The venue please")
        body = post_voice(client, owner["token"], wav(1), question_id="q1").json()
        assert body["answer"] == "o1" and body["words"] == "The venue"
        assert body["answer_source"] == "rules"
        text = post_voice(client, owner["token"], wav(1), question_id="q3").json()
        assert text["answer"] == "The venue please" and text["answer_source"] == "rules"
    question: dict[str, Any] = {"kind": "amount", "options": [], "low": 0, "high": 10}
    assert rule_answer(question, "maybe 40 or 6") == 6
    assert rule_answer(question, "no idea") is None


def test_a_photo_answers_a_question_and_the_image_is_not_kept(tmp_path: Path) -> None:
    def reader(system: str, user: str, image: bool) -> dict[str, Any] | None:
        assert image and "with a photo" in system
        data = json.loads(user)
        assert data["kind"] == "choice" and [o["id"] for o in data["options"]] == ["o1", "o2"]
        return reading(description="A shelf with three labelled boxes.", option_ids=["o2"])

    model = ReadingModel(reader, needs=NEEDS, brief=BRIEF)
    with serve(tmp_path, model) as client:
        cid, engine, owner, member = brief_room(client)
        before = len(server_of(client).store.read(cid))
        reply = client.post(
            "/v1/room/photo",
            files={"image": ("shelf.png", PNG, "image/png")},
            data={"question_id": "q1"},
            headers=bearer(owner["token"]),
        )
        assert reply.status_code == 200, reply.text
        body = reply.json()
        assert body["answer"] == "o2" and body["words"] == "The costs"
        assert body["description"] == "A shelf with three labelled boxes."
        assert model.images[0].startswith("data:image/png;base64,")
        assert len(server_of(client).store.read(cid)) == before
        assert b"PHOTO-BYTES-MARKER" not in stored(tmp_path)
        assert view_of(engine, cid, "p1")["mine"]["inputs"][-1]["kind"] == "photo"
        assert "three labelled" not in json.dumps(view_of(engine, cid, member["participant"]))


def test_a_photo_for_a_sentence_and_the_refusals(tmp_path: Path) -> None:
    def reader(system: str, user: str, image: bool) -> dict[str, Any] | None:
        assert image and "took a photo" in system and json.loads(user) == {"purpose": "say"}
        return reading(description="Two chairs.", text="We have two chairs.")

    with serve(tmp_path, ReadingModel(reader, needs=NEEDS, brief=BRIEF)) as client:
        _cid, _engine, owner, _member = brief_room(client)
        auth = {**bearer(owner["token"]), "Content-Type": "image/png"}
        body = client.post("/v1/room/photo?purpose=say", content=PNG, headers=auth).json()
        assert body["answer"] == "We have two chairs." and body["description"] == "Two chairs."
        assert client.post("/v1/room/photo", content=PNG, headers=auth).status_code == 422
        both = "/v1/room/photo?purpose=say&question_id=q1"
        assert client.post(both, content=PNG, headers=auth).status_code == 422
        gif = client.post("/v1/room/photo?purpose=say", content=b"GIF89a....", headers=auth)
        assert gif.status_code == 415


def test_no_key_says_so(tmp_path: Path) -> None:
    with serve(tmp_path, ReadingModel(no_reader, needs=NEEDS, brief=BRIEF)) as client:
        _cid, _engine, owner, _member = brief_room(client)
        auth = {**bearer(owner["token"]), "Content-Type": "image/png"}
        reply = client.post("/v1/room/photo?purpose=say", content=PNG, headers=auth)
        assert reply.status_code == 503


def test_a_sentence_said_by_voice_reaches_the_room_marked_as_voice(tmp_path: Path) -> None:
    with serve(tmp_path, ReadingModel(no_reader, needs=NEEDS, brief=BRIEF)) as client:
        cid, engine, owner, _member = brief_room(client)
        reply = client.post(
            "/v1/room/say",
            json={"text": "everyone: I can bring chairs", "via": "voice"},
            headers=bearer(owner["token"]),
        )
        assert reply.status_code == 200 and reply.json()["route"] == "room"
        said = [e for e in events(client, cid, "observe") if e["on_behalf_of"] == "p1"]
        assert [e["payload"]["source"] for e in said] == ["voice"]
        photo = client.post(
            "/v1/room/say",
            json={"text": "everyone: we have two chairs", "via": "photo"},
            headers=bearer(owner["token"]),
        )
        assert photo.status_code == 200
        said = [e for e in events(client, cid, "observe") if e["on_behalf_of"] == "p1"]
        assert [e["payload"]["source"] for e in said] == ["voice", "camera"]
        said_to_room = "Said something to the room"
        activity = view_of(engine, cid, "p1")["activity"]
        spoken = [a for a in activity if a["label"] == said_to_room]
        assert [a["source"] for a in spoken] == ["voice", "camera"]
        bad = client.post(
            "/v1/room/say", json={"text": "hi", "via": "fax"}, headers=bearer(owner["token"])
        )
        assert bad.status_code == 422


def test_each_call_is_reported_without_what_was_said() -> None:
    seen: list[dict[str, Any]] = []

    async def hook(activity: dict[str, Any]) -> None:
        seen.append(activity)

    async def run() -> None:
        async with inputs.reported(hook, "p1", "media:transcribe", "a spoken clip") as line:
            line["result"] = "8 words"
        with pytest.raises(RuntimeError):
            async with inputs.reported(hook, "p1", "model:vision", "a photo"):
                raise RuntimeError("boom")

    asyncio.run(run())
    assert [a["status"] for a in seen] == ["started", "done", "started", "failed"]
    assert set(seen[1]) == {"seat", "agent", "tool", "args", "result", "status", "ms", "refs"}
    assert seen[1]["result"] == "8 words" and seen[3]["result"] == "RuntimeError"
