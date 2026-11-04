# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportMissingParameterType=false, reportUnknownParameterType=false
"""A pack's public question: asked of every seat, published to the room, used in its search."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from room_flow import briefs_open, reply_brief
from room_rig import BRIEF, NEEDS, RoomModel, engine_of, server_of, until, view_of
from sets_rig import pack_room, serve_pack

from coalitionkit_models import SearchHit
from coalitionkit_server.room import public, websearch

PUBLIC = """public:
  - id: city
    label: City
    question: { text: "Which city are you in?", kind: text }
    search: true
"""


def said(client: Any, cid: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for e in server_of(client).store.read(cid):
        if e["type"] == "coalition.observe" and e["payload"]["content"].startswith("City: "):
            out[e["on_behalf_of"]] = e["payload"]["content"]
            assert e["scope"] == {"audience": "coalition"} and e["payload"]["source"] == "chat"
    return out


def test_a_public_answer_is_published_once_and_searched_per_seat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = RoomModel(needs=NEEDS, brief=BRIEF)
    with serve_pack(tmp_path, model, PUBLIC) as client:
        room, (a, b) = pack_room(client)
        cid, engine = room["coalition_id"], engine_of(client)
        who = ["p1", a["participant"], b["participant"]]
        briefs_open(engine, cid, who)
        asked = [q["id"] for q in view_of(engine, cid, "p1")["mine"]["brief"]]
        assert asked[-1] == "pub-city", "asked beside the agent's own questions"
        reply_brief(client, room["owner"]["token"], {"pub-city": "Lisbon"})
        reply_brief(client, a["token"], {"pub-city": "  Osaka \n"})
        until(lambda: len(said(client, cid)) == 2, 20, "two answers published")
        assert said(client, cid) == {"p1": "City: Lisbon", a["participant"]: "City: Osaka"}
        assert public.search_places(engine, cid) == {"p1": "Lisbon", a["participant"]: "Osaka"}
        # Published answers are not private: a query holding a city may leave the host.
        assert "Lisbon" not in websearch.private_values(engine, cid, who)
        # Each seat searches its own city once; the hits are kept together for the result.
        queries: list[tuple[str, str]] = []

        async def fake_search(engine_, coalition, seat, query, **kw):
            queries.append((seat, query))
            city = "Lisbon" if "Lisbon" in query else "Osaka"
            return [SearchHit(f"Old market of {city}", f"https://example.org/{city}", "s", "meta")]

        monkeypatch.setattr(websearch, "search", fake_search)
        monkeypatch.setattr(websearch, "provider", lambda engine_: object())
        need = {"id": "n-stop", "title": "A must-see stop in each city", "kind": "place"}
        facts = {"need": need, "goal": "A one-hour world tour"}
        mine = asyncio.run(websearch.for_need(engine, cid, "p1", facts, mine_only=True))
        assert [h.title for h in mine or []] == ["Old market of Lisbon (Lisbon)"]
        both = asyncio.run(websearch.for_need(engine, cid, a["participant"], facts))
        assert sorted(h.url for h in both or []) == [
            "https://example.org/Lisbon",
            "https://example.org/Osaka",
        ]
        assert queries == [
            ("p1", "A must-see stop in each city in Lisbon: A one-hour world tour"),
            (a["participant"], "A must-see stop in each city in Osaka: A one-hour world tour"),
        ], "once per city, by the seat in that city"
        assert b["participant"] not in public.search_places(engine, cid)


def test_a_seat_over_mcp_gives_its_answer_through_its_vault(tmp_path: Path) -> None:
    model = RoomModel(needs=NEEDS, brief=BRIEF)
    with serve_pack(tmp_path, model, PUBLIC) as client:
        room, (a, _b) = pack_room(client)
        cid, engine = room["coalition_id"], engine_of(client)
        server_of(client).registry.vault_values(cid, a["participant"], {"public:city": "Quito"})
        engine.wake(cid)
        until(lambda: a["participant"] in said(client, cid), 20, "the vault answer published")
        assert said(client, cid)[a["participant"]] == "City: Quito"


def test_the_loader_refuses_a_public_question_it_cannot_publish() -> None:
    from coalitionkit_packs import PublicQuestion

    with pytest.raises(ValueError, match="text or choice"):
        PublicQuestion.model_validate(
            {"id": "when", "label": "When", "question": {"text": "When?", "kind": "slots"}}
        )
    ok = PublicQuestion.model_validate(
        {"id": "city", "label": "City", "question": {"text": "Which city?", "kind": "text"}}
    )
    assert ok.search is False
