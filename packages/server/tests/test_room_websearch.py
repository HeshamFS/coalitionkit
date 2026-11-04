# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportPrivateUsage=false
"""Agents search the web: public words out, real URLs back, private values never sent."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from room_rig import (
    BRIEF,
    NEEDS,
    RoomModel,
    engine_of,
    events,
    serve,
    server_of,
    start_room,
    until,
    view_of,
)
from test_room_work import SHAPES, approve_commitments, laid, to_decided

from coalitionkit_models import SearchHit, SearchRun
from coalitionkit_server.room import makers, websearch

HITS = (
    SearchHit("Riverside Hall", "https://example.org/riverside-hall", "Seats forty.", "fake"),
    SearchHit("Old Mill Rooms", "https://example.net/mill", "Two rooms to rent.", "fake"),
    SearchHit("Park Pavilion", "https://example.com/pavilion", "Covered space.", "fake"),
)
CANARY = "CANARY-7f3a"


class FakeSearch:
    name = "fake"

    def __init__(self) -> None:
        self.queries: list[str] = []

    async def search(
        self, query: str, *, limit: int, coalition_id: str | None = None, participant: str = ""
    ) -> SearchRun:
        self.queries.append(query)
        return SearchRun(HITS[:limit], (query,), 1234, (100, 50))


def made(user: str) -> dict[str, Any]:
    asked = json.loads(user)
    found = asked["facts"].get("found_on_the_web")
    if asked["kind"] != "place" or not found:
        return SHAPES[asked["kind"]]
    places = [
        {"name": h["title"], "why_it_fits": "It has room for all.", "check_first": "Is it free",
         "url": h["url"]}
        for h in found[:2]
    ]  # fmt: skip
    places.append(
        {"name": "Invented Place", "why_it_fits": "Made up.", "check_first": "Nothing",
         "url": "https://invented.example/nowhere"}
    )  # fmt: skip
    return {"places": places}


def test_a_place_result_names_real_places_with_their_urls(tmp_path: Path) -> None:
    fake = FakeSearch()
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF, made=made, laid=laid)) as client:
        server_of(client)._web_search = fake  # pyright: ignore[reportAttributeAccessIssue]
        cid, engine, people = to_decided(client)
        approve_commitments(client, cid, people)
        results = lambda: [  # noqa: E731
            json.loads(e["payload"]["content"])
            for e in events(client, cid, "observe")
            if '"result": 1' in e["payload"]["content"]
        ]
        until(lambda: len(results()) == 3, 40, "three results")
        place = next(r for r in results() if r["kind"] == "place")
        options = place["data"]["options"]
        assert [o["url"] for o in options] == [HITS[0].url, HITS[1].url], "invented URL dropped"
        assert {o["provenance"] for o in options} == {"search"}
        assert [w["url"] for w in place["data"]["web"]] == [h.url for h in HITS]
        assert len(fake.queries) == 1, "one search for the need"
        assert fake.queries[0].startswith("Find a venue: ")
        view = view_of(engine, cid, "p1")
        shown = next(r for r in view["results"] if r["kind"] == "place")
        assert [link["url"] for link in shown["links"]] == [h.url for h in HITS]
        searched = view["search"]
        assert len(searched) == 1 and searched[0]["count"] == 3
        assert searched[0]["first"] == "Riverside Hall" and searched[0]["stopped"] is None
        assert any(a["label"].startswith("Searched the web:") for a in view["activity"])


def test_a_query_holding_a_private_value_is_refused_and_never_sent(tmp_path: Path) -> None:
    fake = FakeSearch()
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        server = server_of(client)
        server._web_search = fake  # pyright: ignore[reportAttributeAccessIssue]
        engine = engine_of(client)
        cid = start_room(client)["coalition_id"]
        owner = engine.owner(cid)
        assert owner is not None
        engine.vault_put(cid, owner, "_room_notes", [{"at": "now", "text": CANARY}])
        seen: list[dict[str, Any]] = []

        async def record(activity: dict[str, Any]) -> None:
            seen.append(activity)

        async def go() -> tuple[Any, Any, Any]:
            leak = await websearch.search(
                engine, cid, owner, f"a hall near {CANARY}", seats=[owner], on_activity=record
            )
            street = await websearch.search(
                engine, cid, owner, "a hall near 12 Mill Road", seats=[owner], on_activity=record
            )
            phone = await websearch.search(
                engine, cid, owner, "call +49 170 1234567 for a hall", seats=[owner]
            )
            return leak, street, phone

        assert asyncio.run(go()) == ([], [], [])
        assert fake.queries == [], "nothing left the host"
        stops = [s["stopped"] for s in view_of(engine, cid, owner)["search"]]
        assert stops == [
            "it holds something a person said privately",
            "it holds a street address",
            "the Steward's policy no-contact-details-in-room matched",
        ]
        assert [a["status"] for a in seen] == ["failed", "failed"]
        assert all(a["tool"] == "search:web" and CANARY not in json.dumps(a) for a in seen)
        assert CANARY not in json.dumps(view_of(engine, cid, owner)["search"])
        assert CANARY not in json.dumps(view_of(engine, cid, owner)["activity"])


def test_the_query_is_built_from_public_words_only() -> None:
    facts = {
        "need": {"id": "n1", "title": "Find a venue", "detail": "Somewhere all can reach."},
        "goal": "A games night for six people in the old town",
    }
    query = websearch.query_for(facts)
    assert query == "Find a venue: A games night for six people in the old town"
    assert websearch.screen(query, [], "c", "p1") is None
    assert websearch.screen("Hauptstraße 5 hall", [], "c", "p1") == "it holds a street address"
    assert websearch.screen("mail me at a@b.org", [], "c", "p1") is not None
    assert websearch.wants_fact({"need": {"title": "Find a shop for paint", "detail": ""}})
    assert not websearch.wants_fact({"need": {"title": "Write the invitation", "detail": ""}})


def test_links_from_an_outside_agent_are_checked_before_they_show() -> None:
    data = {"web": [{"title": "Ok", "url": "https://example.org"}, {"url": "javascript:x"}, 3]}
    assert websearch.shown_links(data) == [{"title": "Ok", "url": "https://example.org"}]
    assert websearch.shown_links({"web": "no"}) == [] and websearch.shown_links(None) == []


def test_when_the_maker_fails_the_found_pages_still_stand() -> None:
    found = websearch.links(list(HITS))
    made = makers.places_by_rules(found)
    assert made is not None and made["by_rules"] is True
    assert [i["url"] for i in made["ideas"]] == [h.url for h in HITS]
    assert {i["provenance"] for i in made["ideas"]} == {"search"}
    assert makers.places_by_rules(found[:1]) is None
