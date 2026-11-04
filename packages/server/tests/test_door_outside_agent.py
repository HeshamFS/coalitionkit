# SPDX-License-Identifier: Apache-2.0
"""An agent from outside takes a seat through the door code and does not hold the room up."""

from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from google.protobuf.json_format import MessageToDict
from room_rig import RoomModel, bearer, engine_of, events, serve, sign, until
from test_room_engine import BRIEF, NEEDS, open_brief, seated_room

from coalitionkit_server.cards import member_card


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
        offered = client.post(
            "/v1/agent/offer",
            json={"need_id": need, "cost": {"minutes": 10, "money": 0, "effort": "low"}},
            headers=bearer(member["token"]),
        )
        assert offered.status_code == 200, offered.text
        until(lambda: engine.read(cid)["briefs"][who]["closed"], what="the brief to close")
        assert sign(client, cid, room["owner"]["token"], "p1") == 0
