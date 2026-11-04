# SPDX-License-Identifier: Apache-2.0
"""An agent from outside takes a seat through the door code and does not hold the room up."""

import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from google.protobuf.json_format import MessageToDict
from room_rig import RoomModel, bearer, engine_of, events, serve, server_of, until, view_of
from test_room_engine import (
    BRIEF,
    NEEDS,
    open_brief,  # pyright: ignore[reportUnknownVariableType]
    seated_room,  # pyright: ignore[reportUnknownVariableType]
)

from coalitionkit_mcp.gateway import build_envelope, default_scope
from coalitionkit_server.cards import member_card
from coalitionkit_server.mcp_port import MCPPort


def card_body() -> dict[str, object]:
    url = "http://127.0.0.1:8999/.well-known/agent-card.json"
    card = member_card("http://127.0.0.1:8999", Ed25519PrivateKey.generate())
    return {"card_url": url, "card": MessageToDict(card)}


def test_a_card_takes_a_seat_and_the_host_holds_no_keys(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, _ = seated_room(tmp_path, client, seats=3)
        code = room["door"]["code"]
        joined = client.post("/v1/door/join", json={"code": code, **card_body()})
        assert joined.status_code == 200, joined.text
        body = joined.json()
        assert body["role"] and body["host_key"] and body["token"]
        engine = engine_of(client)
        assert not engine.is_hosted(body["coalition_id"], body["participant"])
        # It joins for itself over A2A: the host never joined on its behalf, and the seat counts
        # as filled once that join arrives.
        assert client.get(f"/v1/door/{code}").json()["filled"] == 2
        joins = [e["sender"] for e in events(client, body["coalition_id"], "join")]
        assert len(joins) == 2


def test_a_refused_card_does_not_spend_a_seat(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, _ = seated_room(tmp_path, client, seats=3)
        code = room["door"]["code"]
        before = client.get(f"/v1/door/{code}").json()["filled"]
        body = card_body()
        body["card"] = {"name": "unsigned"}
        refused = client.post("/v1/door/join", json={"code": code, **body})
        assert refused.status_code == 400
        assert client.get(f"/v1/door/{code}").json()["filled"] == before


def test_a_seat_whose_own_agent_offered_closes_its_brief(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, (member,) = seated_room(tmp_path, client)
        cid, engine = open_brief(client, room, member)
        who = member["participant"]
        assert not engine.read(cid)["briefs"][who]["closed"]
        need = events(client, cid, "need")[0]["payload"]["need_id"]
        # By hand in the web room the questions stay open: the person can still answer them.
        offered = client.post(
            "/v1/agent/offer",
            json={"need_id": need, "cost": {"minutes": 10, "money": 0, "effort": "low"}},
            headers=bearer(member["token"]),
        )
        assert offered.status_code == 200, offered.text
        assert not engine.read(cid)["briefs"][who]["closed"]
        server = server_of(client)
        person = server.registry.hosted_for(cid, who)
        payload = {
            "offer_id": "01M6JWEPH2SBS0PW033FBCTH78",
            "target": {"kind": "need", "id": need},
            "capacity": 1,
            "cost": {"minutes": 10, "money": 0, "effort": "low"},
            "valid_until": "2099-01-01T00:00:00Z",
        }
        over_mcp = build_envelope(person, cid, "coalition.offer", payload)
        reply = client.portal.call(MCPPort(server).accept, over_mcp, person.card_url)  # type: ignore[union-attr]
        assert "error" not in reply
        until(lambda: engine.read(cid)["briefs"][who]["closed"], what="the brief to close")


def test_mcp_actions_the_room_must_see_go_to_the_room() -> None:
    for kind in ("join", "offer", "commit", "ripple", "done", "leave", "decide"):
        assert default_scope("coalition." + kind) == {"audience": "coalition"}
    assert default_scope("coalition.answer") == {"audience": "host"}


def test_a_hidden_offer_is_refused_so_it_cannot_hide_a_plan(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, (member,) = seated_room(tmp_path, client)
        cid, who = room["coalition_id"], member["participant"]
        need = events(client, cid, "need")[0]["payload"]["need_id"]
        server = server_of(client)
        person = server.registry.hosted_for(cid, who)
        payload = {
            "offer_id": "01M6JWEPH2SBS0PW033FBCTH77",
            "target": {"kind": "need", "id": need},
            "capacity": 1,
            "cost": {"minutes": 10, "money": 0, "effort": "low"},
            "valid_until": "2099-01-01T00:00:00Z",
        }
        hidden = build_envelope(person, cid, "coalition.offer", payload, scope={"audience": "host"})
        reply = client.portal.call(server.accept, hidden, person.card_url)  # type: ignore[union-attr]
        assert reply["error"]["code"] == "schema_invalid"
        assert "audience" in reply["error"]["detail"]["message"]
        open_offer = build_envelope(person, cid, "coalition.offer", payload)
        reply = client.portal.call(server.accept, open_offer, person.card_url)  # type: ignore[union-attr]
        assert "error" not in reply


def test_an_outside_result_is_shown_and_a_bad_one_breaks_nothing(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, (member,) = seated_room(tmp_path, client)
        cid, who = room["coalition_id"], member["participant"]
        need = events(client, cid, "need")[0]["payload"]["need_id"]
        server = server_of(client)
        person = server.registry.hosted_for(cid, who)

        def publish(content: dict[str, object]) -> None:
            body = {"source": "document", "content": json.dumps(content)}
            sent = build_envelope(
                person, cid, "coalition.observe", body, scope={"audience": "coalition"}
            )
            reply = client.portal.call(server.accept, sent, person.card_url)  # type: ignore[union-attr]
            assert "error" not in reply, reply

        good: dict[str, object] = {
            "result": 1,
            "need_id": need,
            "kind": "draft",
            "title": "Lunch stop",
            "source": "model",
            "sources": [],
            "components": [],
            "data": {"subject": "Lunch stop", "body": "The bakery by the lake, at noon."},
        }
        publish(good)
        publish({"result": 1, "need_id": need})
        publish({**good, "kind": "budget", "title": "Odd shape", "data": {"nothing": "here"}})
        results = view_of(engine_of(client), cid, "p1")["results"]
        assert [r["title"] for r in results] == ["Lunch stop", "Odd shape"]
        assert "The bakery by the lake" in json.dumps(results[0]["messages"])
        assert results[1]["messages"], "another shape of data is still shown"
