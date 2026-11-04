# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportPrivateUsage=false
"""Richer results: catalog parts made for each kind, and a picture the room's agent drew."""

from __future__ import annotations

import json
import struct
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from room_rig import BRIEF, RoomModel, bearer, engine_of, events, serve, server_of, until, view_of
from test_room_work import SHAPES, approve_commitments, laid, to_decided

from coalitionkit_server.room import fixed, image, media_store, needs, results
from coalitionkit_steward.policy import core_policies

DETAIL = "Somewhere all of us can reach."
PICTURE_NEEDS = {
    "needs": [
        {"title": "Find a venue", "kind": "place", "detail": DETAIL},
        {"title": "Share the costs", "kind": "budget", "detail": "Who pays what."},
        {"title": "Make a poster", "kind": "image", "detail": "A poster for the door."},
    ],
    "slots": [],
}


def png(width: int, height: int) -> bytes:
    """The first bytes of a PNG: enough for the host to read its size and type."""
    ihdr = struct.pack(">II", width, height) + b"\x08\x06\x00\x00\x00"
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + ihdr + b"\x00" * 64


class FakeMedia:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def generate_image(self, prompt: str, size: str = "1024x1024", **_: Any) -> bytes:
        self.prompts.append(prompt)
        return png(640, 480)


def facts() -> dict[str, Any]:
    reading = {"label": "Mira: Find a place", "amount": 50, "provenance": "signed", "ref": "e1"}
    return {
        "budget": {
            "currency": "EUR",
            "amount": 300,
            "rows": [
                {"label": "Hall", "amount": 200, "who": "all", "provenance": "estimate"},
                {"label": "Food", "amount": 100, "who": "", "provenance": "estimate"},
            ],
            "how_shared": "equally",
            "suggested": [],
            "time": [reading],
            "time_total": 50,
            "total": 300,
        },
        "list": {"items": [{"label": "Chairs", "who": "anyone", "provenance": "estimate"}]},
        "schedule": {
            "items": [
                {
                    "title": "Meet",
                    "start": "2026-11-05T10:00:00+00:00",
                    "end": "2026-11-05T11:00:00+00:00",
                    "where": "To be confirmed",
                }
            ],
            "steps": ["Meet", "Talk"],
        },
        "image": {
            "hash": "a" * 64,
            "alt": "A poster",
            "prompt": "A poster",
            "width": 1024,
            "height": 1024,
        },
        "draft": {"subject": "Hello", "body": "Come along. " * 9},
        "place": {"options": [], "chosen": None},
    }


def test_every_fixed_tree_passes_the_catalog_with_its_data_model(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel()) as client:
        engine = engine_of(client)
        for kind, data in facts().items():
            tree = fixed.fixed_tree(kind, "Title", "Detail", data)
            model = fixed.surface_model(kind, data)
            assert results.tree_errors(engine, tree, {"e1"}, model) == [], kind
            assert {n["component"] for n in tree} <= results.WHITELIST, kind
        image_tree = fixed.fixed_tree("image", "T", "D", facts()["image"])
        picture = next(n for n in image_tree if n["component"] == "Image")
        assert picture["src"] == {"path": fixed.IMAGE_SRC}
        model = fixed.surface_model("image", facts()["image"])
        assert model["image"]["src"] == "/v1/room/media/" + "a" * 64
        assert model["width"] == "1024", "numbers in a data model are strings"
        missing = fixed.fixed_tree("image", "T", "D", {"hash": None, "alt": "A", "why": "No key"})
        assert not any(n["component"] == "Image" for n in missing)


def nodes(*parts: tuple[str, str, dict[str, Any]]) -> list[results.Node]:
    return [results.Node(id=i, component=c, props=json.dumps(p)) for i, c, p in parts]


def test_the_composer_may_use_rich_parts_and_code_still_checks_them(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel()) as client:
        engine = engine_of(client)
        data = facts()["budget"]
        model = fixed.surface_model("budget", data)
        split = {"items": [{"label": "Hall", "payer": "all", "amount": "200 EUR", "kind": "x"}]}
        good = results.parse_tree(
            nodes(
                ("root", "Column", {"children": ["c", "t"]}),
                ("c", "CostSplit", split),
                (
                    "t",
                    "Table",
                    {"columns": [{"key": "label", "label": "Item"}], "rows": {"path": "/rows"}},
                ),
            )
        )
        assert isinstance(good, list) and results.tree_errors(engine, good, set(), model) == []
        raw = {"items": [{"label": "Hall", "payer": "all", "amount": 200, "kind": "x"}]}
        bare = results.parse_tree(nodes(("root", "CostSplit", raw)))
        assert isinstance(bare, list) and results.tree_errors(engine, bare, set(), model)
        literal = results.parse_tree(nodes(("root", "Image", {"alt": "x", "src": "http://x"})))
        assert isinstance(literal, list) and results.tree_errors(engine, literal, set(), model)
        assert results.parse_tree(nodes(("root", "ConsentCard", {}))) == (
            "component ConsentCard is not allowed"
        )
        listed = results.parse_tree(
            nodes(("root", "Checklist", {"items": [{"text": "Chairs · anyone", "done": False}]}))
        )
        assert isinstance(listed, list)
        assert results.covers(listed, "list", facts()["list"]) is None
        assert results.covers(listed, "image", facts()["image"]) == (
            "the layout leaves out the picture"
        )
        cards = results.parse_tree(
            nodes(
                ("root", "Card", {"title": "Items", "fields": [{"label": "Chairs", "value": "x"}]})
            )
        )
        assert isinstance(cards, list)
        assert results.covers(cards, "list", facts()["list"]) == "show the list in a Checklist"


def test_a_layout_may_not_say_the_budget_was_agreed() -> None:
    said = [{"id": "root", "component": "Text", "text": "A budget totalling 120 euro is agreed."}]
    assert results.claims_agreement(said, facts()["budget"])
    plain = [{"id": "root", "component": "Text", "text": "A proposal to share 120 euro."}]
    assert results.claims_agreement(plain, facts()["budget"]) is None


def test_the_composer_is_told_which_part_each_kind_prefers() -> None:
    for part in ("CostSplit", "Checklist", "Timeline", "Gantt", "budget shows", "a list in"):
        assert part in results.LAYOUT_SYSTEM


def test_a_picture_is_kept_only_when_the_goal_asks_for_one() -> None:
    reply = needs.NeedsReply(
        needs=[
            needs.NeedItem(title="Make a poster", kind="image", detail="For the door."),
            needs.NeedItem(title="Plan the day", kind="image", detail="Steps."),
        ],
        slots=[],
    )
    kept = needs.checked(reply, "Three friends plan a picnic")
    assert kept is not None and [n.kind for n in kept] == ["image", "draft"]
    assert needs.kind_of("Make a poster for the fair") == "image"


def test_a_prompt_the_policies_hold_never_reaches_the_image_model() -> None:
    stops: list[tuple[Any, ...]] = []
    media = FakeMedia()
    engine = SimpleNamespace(
        policies=core_policies(),
        record_stop=lambda *a, **_: stops.append(a),  # pyright: ignore[reportUnknownArgumentType]
        server=SimpleNamespace(media=media),
    )
    goal = "Make a poster; questions to someone@example.org or +44 20 7946 0958"
    held = {"goal": goal, "need": {"title": "Make a poster", "detail": "For the door."}}
    assert image.held_by(engine, "c1", "p1", image.prompt_for(held))  # pyright: ignore[reportArgumentType]
    import asyncio

    data, source = asyncio.run(image.make_image(engine, "c1", "p1", "n1", held))  # pyright: ignore[reportArgumentType]
    assert source == "rules" and data["hash"] is None and "Steward" in data["why"]
    assert media.prompts == [] and len(stops) == 1


def test_a_picture_is_kept_by_its_hash_and_its_size_is_read() -> None:
    assert media_store.size_of(png(640, 480)) == (640, 480)
    webp = b"RIFF\x00\x00\x00\x00WEBPVP8X" + b"\x00" * 8 + (639).to_bytes(3, "little")
    assert media_store.size_of(webp + (479).to_bytes(3, "little")) == (640, 480)
    assert media_store.size_of(b"nothing") is None


def picture_model(activities: list[dict[str, Any]]) -> RoomModel:
    def made(user: str) -> dict[str, Any]:
        return SHAPES[json.loads(user)["kind"]]

    del activities
    return RoomModel(needs=PICTURE_NEEDS, brief=BRIEF, made=made, laid=laid)


@pytest.mark.parametrize("wired", [True, False])
def test_an_image_need_gives_a_served_picture_from_public_facts(
    tmp_path: Path, wired: bool
) -> None:
    activities: list[dict[str, Any]] = []
    with serve(tmp_path, picture_model(activities)) as client:
        server = server_of(client)
        media = FakeMedia()
        server.media = media  # pyright: ignore[reportAttributeAccessIssue]
        if wired:

            async def sink(activity: dict[str, Any]) -> None:
                activities.append(activity)

            engine_of(client).activity_sink = lambda _c: sink  # pyright: ignore[reportAttributeAccessIssue]
        cid, engine, people = to_decided(client)
        approve_commitments(client, cid, people)
        found = lambda: [  # noqa: E731
            json.loads(e["payload"]["content"])
            for e in events(client, cid, "observe")
            if '"kind": "image"' in e["payload"]["content"]
        ]
        content = until(found, 40, "the picture")[0]
        data = content["data"]
        assert content["source"] == "model" and content["title"] == "Make a poster"
        assert set(data) == {"hash", "alt", "prompt", "width", "height"}
        assert (data["width"], data["height"]) == (640, 480)
        assert media.prompts == [data["prompt"]] and "Make a poster" in data["prompt"]
        for who in people:
            for value in engine.vault(cid, who).values():
                if isinstance(value, str) and len(value) > 3:
                    assert value not in data["prompt"], "no vault value leaves in a prompt"
        token = bearer(next(iter(people.values()))["token"])
        served = client.get(f"/v1/room/media/{data['hash']}", headers=token)
        assert served.status_code == 200 and served.content == png(640, 480)
        assert served.headers["content-type"] == "image/png"
        assert client.get(f"/v1/room/media/{data['hash']}").status_code in {401, 403}
        assert client.get("/v1/room/media/" + "b" * 64, headers=token).status_code == 404
        assert client.get("/v1/room/media/..%2Fhost.key", headers=token).status_code == 404
        shown = next(r for r in view_of(engine, cid, "p1")["results"] if r["kind"] == "image")
        model = next(m for m in shown["messages"] if "updateDataModel" in m)
        assert model["updateDataModel"]["value"]["image"]["src"].endswith(data["hash"])
        assert any(n["component"] == "Image" for n in shown["tree"])
        line = next(a for a in engine.read(cid)["activity"] if a["label"].startswith("Drawing"))
        assert line["state"] == "done" and line["source"] == "model"
        if wired:
            assert [a["status"] for a in activities] == ["started", "done"]
            assert {a["tool"] for a in activities} == {"media:image"}
            assert set(activities[-1]) == {
                *("seat", "agent", "tool", "args", "result", "status", "ms", "refs")
            }
        assert isinstance(client, TestClient)
