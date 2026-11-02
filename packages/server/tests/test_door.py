# SPDX-License-Identifier: Apache-2.0
"""Opening without a start link, the Door, knocks and the map."""

import re
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response
from pydantic import SecretStr

from coalitionkit_server import Settings, create_server
from coalitionkit_server.adapter import Document
from coalitionkit_server.app import Server
from coalitionkit_server.door import CODE_ALPHABET

ROOM_FIELDS = {"id", "goal", "place", "seats", "filled", "closes", "lat", "lon", "status", "sample"}


def make_client(tmp_path: Path, mode: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.delenv("COALITIONKIT_META_API_KEY", raising=False)
    settings = Settings.model_validate(
        {
            "store": SecretStr("sqlite:///:memory:"),
            "host_key_file": tmp_path / "host.key",
            "genesis": mode,
            "admin_token": "secret",
            "public_base_url": "http://127.0.0.1:8000",
        }
    )
    with TestClient(
        create_server(settings),
        client=("127.0.0.1", 12345),
        headers={"Origin": settings.public_base_url},
    ) as http:
        yield http


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    yield from make_client(tmp_path, "local", monkeypatch)


@pytest.fixture
def admin_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    yield from make_client(tmp_path, "admin", monkeypatch)


def server_for(client: TestClient) -> Server:
    return cast(FastAPI, client.app).state.server


def draft(
    roles: list[tuple[str, int]] | None = None,
    deadline: str = "2099-01-01T00:00:00Z",
    place: str | None = None,
) -> Document:
    return {
        "goal": "Share a table",
        "roles": [{"id": i, "label": i.title(), "count": n} for i, n in roles or [("member", 3)]],
        "needs": [],
        "deadline": deadline,
        "place": place,
    }


def open_room(
    client: TestClient,
    visibility: str = "code",
    roles: list[tuple[str, int]] | None = None,
    place: str | None = None,
) -> Document:
    body = {"draft": draft(roles=roles, place=place), "visibility": visibility}
    result = client.post("/v1/genesis/start", json=body)
    assert result.status_code == 200, result.text
    return result.json()


def owner_of(room: Document) -> dict[str, str]:
    return {"Authorization": "Bearer " + room["owner"]["token"]}


def join(client: TestClient, code: str, **body: str) -> Response:
    return client.post("/v1/door/join", json={"code": code, **body})


def test_start_without_code_in_local_mode(client: TestClient) -> None:
    room = open_room(client)
    assert room["owner"]["participant"] == "p1"
    door = room["door"]
    assert door["stopped"] is False and door["visibility"] == "code"
    assert door["link"] == "http://127.0.0.1:8000/join#" + door["code"]
    assert (door["seats"], door["filled"]) == (3, 1)
    assert door["knocks"] == []


def test_invalid_code_still_refused_in_local_mode(client: TestClient) -> None:
    result = client.post(
        "/v1/genesis/start", json={"draft": draft()}, headers={"Authorization": "Start nope"}
    )
    assert result.status_code == 401
    code = server_for(client).registry.issue_start()
    valid = client.post(
        "/v1/genesis/start", json={"draft": draft()}, headers={"Authorization": "Start " + code}
    )
    assert valid.status_code == 200
    reused = client.post(
        "/v1/genesis/start", json={"draft": draft()}, headers={"Authorization": "Start " + code}
    )
    assert reused.status_code == 401


def test_eleventh_start_in_a_minute_is_429(client: TestClient) -> None:
    for _ in range(10):
        open_room(client)
    result = client.post("/v1/genesis/start", json={"draft": draft()})
    assert result.status_code == 429


def test_admin_mode_still_needs_a_code(admin_client: TestClient) -> None:
    body = {"draft": draft()}
    assert admin_client.post("/v1/genesis/start", json=body).status_code == 401
    code = server_for(admin_client).registry.issue_start()
    started = admin_client.post(
        "/v1/genesis/start", json=body, headers={"Authorization": "Start " + code}
    )
    assert started.status_code == 200 and started.json()["door"]["code"]


def test_code_format_and_alphabet(client: TestClient) -> None:
    codes = {open_room(client)["door"]["code"] for _ in range(6)}
    assert len(codes) == 6
    for code in codes:
        assert re.fullmatch(r"[A-Z0-9]{3}-[A-Z0-9]{4}", code)
        assert set(code.replace("-", "")) <= set(CODE_ALPHABET)
    assert not set("ILO01") & set(CODE_ALPHABET)


def test_join_by_code_twice_gives_two_seats(client: TestClient) -> None:
    room = open_room(client)
    code = room["door"]["code"]
    seen = client.get("/v1/door/" + code)
    assert seen.json() == {
        "goal": "Share a table",
        "place": None,
        "closes_at": seen.json()["closes_at"],
        "seats": 3,
        "filled": 1,
        "roles": [{"id": "member", "label": "Member", "open": True}],
    }
    first, second = join(client, code), join(client, code.lower())
    for reply in (first, second):
        assert reply.status_code == 200, reply.text
        assert set(reply.json()) == {"coalition_id", "participant", "token", "host_key"}
    ids = {first.json()["participant"], second.json()["participant"]}
    assert len(ids) == 2 and "p1" not in ids
    assert first.json()["token"] != second.json()["token"]
    assert client.get("/v1/door/" + code).json()["filled"] == 3
    # A joined member holds no owner rights.
    token = first.json()["token"]
    assert (
        client.get("/v1/coalition/door", headers={"Authorization": "Bearer " + token}).status_code
        == 403
    )


def test_role_with_an_open_seat_is_chosen(client: TestClient) -> None:
    room = open_room(client, roles=[("lead", 1), ("scribe", 2)])
    code = room["door"]["code"]
    assert join(client, code, role="scribe").status_code == 200
    roles = {r["id"]: r["open"] for r in client.get("/v1/door/" + code).json()["roles"]}
    assert roles == {"lead": False, "scribe": True}
    # The lead seat is the opener's, so a request for it falls to the first role with a seat.
    assert join(client, code, role="lead").status_code == 200
    arrivals = client.get("/v1/coalition/door", headers=owner_of(room)).json()["arrivals"]
    assert [(a["role"], a["label"]) for a in arrivals] == [
        ("scribe", "Scribe"),
        ("scribe", "Scribe"),
        ("lead", "Lead"),
    ]
    assert join(client, code).status_code == 409


def test_full_room_is_409_and_names_no_one(client: TestClient) -> None:
    code = open_room(client, roles=[("member", 1)])["door"]["code"]
    refused = join(client, code)
    assert refused.status_code == 409
    assert "p1" not in refused.text


def test_stopped_code_is_404(client: TestClient) -> None:
    room = open_room(client)
    code = room["door"]["code"]
    stopped = client.post("/v1/coalition/door/stop", json={}, headers=owner_of(room))
    assert stopped.status_code == 200 and stopped.json()["stopped"] is True
    assert client.get("/v1/door/" + code).status_code == 404
    assert join(client, code).status_code == 404
    assert join(client, "ZZZ-ZZZZ").status_code == 404


def test_past_deadline_is_404(client: TestClient) -> None:
    room = open_room(client)
    code = room["door"]["code"]
    with server_for(client).store.transaction("") as tx:
        tx.execute("UPDATE server_doors SET closes_at = '2000-01-01T00:00:00+00:00'")
    assert client.get("/v1/door/" + code).status_code == 404
    assert join(client, code).status_code == 404


def test_join_attempts_are_limited(client: TestClient) -> None:
    for _ in range(10):
        assert join(client, "ZZZ-ZZZZ").status_code == 404
    assert join(client, "ZZZ-ZZZZ").status_code == 429


def test_arrivals_and_filled(client: TestClient) -> None:
    room = open_room(client)
    code = room["door"]["code"]
    join(client, code)
    door = client.get("/v1/coalition/door", headers=owner_of(room)).json()
    assert (door["seats"], door["filled"]) == (3, 2)
    assert [a["participant"] for a in door["arrivals"]] == ["p2", "p1"]
    assert {a["home"] for a in door["arrivals"]} == {"hosted"}
    assert all(a["at"] and a["label"] == "Member" for a in door["arrivals"])


def test_knock_yes_gives_one_use_invitation_once(client: TestClient) -> None:
    room = open_room(client, visibility="nearby")
    listed = client.get("/v1/rooms").json()["rooms"][0]["id"]
    knock = client.post(f"/v1/rooms/{listed}/knock", json={})
    assert knock.status_code == 200
    ticket = knock.json()
    waiting = f"/v1/rooms/{listed}/knocks/{ticket['knock']}?secret={ticket['secret']}"
    assert client.get(waiting).json() == {"state": "waiting"}
    owner = owner_of(room)
    assert (
        client.get("/v1/coalition/door", headers=owner).json()["knocks"][0]["id"] == ticket["knock"]
    )
    answered = client.post(
        f"/v1/coalition/door/knocks/{ticket['knock']}", json={"answer": "yes"}, headers=owner
    )
    assert answered.status_code == 200 and answered.json()["knocks"] == []
    first = client.get(waiting).json()
    assert first["state"] == "yes" and first["invitation"]
    assert client.get(waiting).json() == {"state": "yes"}
    accepted = client.post("/v1/invitations/accept", json={"invitation": first["invitation"]})
    assert accepted.status_code == 200
    assert (
        client.post("/v1/invitations/accept", json={"invitation": first["invitation"]}).status_code
        == 400
    )
    door = client.get("/v1/coalition/door", headers=owner).json()
    assert door["filled"] == 2


def test_knock_no_and_wrong_secret(client: TestClient) -> None:
    room = open_room(client, visibility="nearby")
    listed = client.get("/v1/rooms").json()["rooms"][0]["id"]
    ticket = client.post(f"/v1/rooms/{listed}/knock", json={}).json()
    base = f"/v1/rooms/{listed}/knocks/{ticket['knock']}"
    assert client.get(base + "?secret=wrong").status_code == 403
    assert client.get(base).status_code == 403
    assert (
        client.get(f"/v1/rooms/{listed}/knocks/nope?secret={ticket['secret']}").status_code == 403
    )
    owner = owner_of(room)
    client.post(
        f"/v1/coalition/door/knocks/{ticket['knock']}", json={"answer": "no"}, headers=owner
    )
    assert client.get(base + "?secret=" + ticket["secret"]).json() == {"state": "no"}
    again = client.post(
        f"/v1/coalition/door/knocks/{ticket['knock']}", json={"answer": "yes"}, headers=owner
    )
    assert again.status_code == 404


def test_knock_needs_a_listed_room(client: TestClient) -> None:
    room = open_room(client)
    assert client.post("/v1/rooms/unknown/knock", json={}).status_code == 404
    assert room["door"]["code"]
    nearby = open_room(client, visibility="nearby")
    assert nearby["door"]["visibility"] == "nearby"


def test_listed_room_shows_public_fields_only(client: TestClient) -> None:
    open_room(client)  # a code room never appears
    assert client.get("/v1/rooms").json()["rooms"] == []
    room = open_room(client, visibility="nearby", place="the square")
    listed = client.get("/v1/rooms").json()["rooms"]
    assert len(listed) == 1
    entry = listed[0]
    assert set(entry) == ROOM_FIELDS
    assert (entry["goal"], entry["place"], entry["seats"], entry["filled"]) == (
        "Share a table",
        "the square",
        3,
        1,
    )
    assert entry["sample"] is False and entry["status"] == "forming"
    assert room["coalition_id"] not in str(entry) and room["door"]["code"] not in str(entry)
    again = client.get("/v1/rooms").json()["rooms"][0]
    assert (again["id"], again["lat"], again["lon"]) == (entry["id"], entry["lat"], entry["lon"])


def test_room_leaves_the_list_when_stopped_full_or_dissolved(client: TestClient) -> None:
    stopped = open_room(client, visibility="nearby")
    client.post("/v1/coalition/door/stop", json={}, headers=owner_of(stopped))
    assert client.get("/v1/rooms").json()["rooms"] == []
    full = open_room(client, visibility="nearby", roles=[("member", 2)])
    assert len(client.get("/v1/rooms").json()["rooms"]) == 1
    assert join(client, full["door"]["code"]).status_code == 200
    assert client.get("/v1/rooms").json()["rooms"] == []
    gone = open_room(client, visibility="nearby")
    assert len(client.get("/v1/rooms").json()["rooms"]) == 1
    client.post("/v1/coalition/dissolve", json={"reason": "cancelled"}, headers=owner_of(gone))
    assert client.get("/v1/rooms").json()["rooms"] == []


def test_dissolve_erases_door_knock_and_arrival_rows(client: TestClient) -> None:
    room = open_room(client, visibility="nearby")
    listed = client.get("/v1/rooms").json()["rooms"][0]["id"]
    ticket = client.post(f"/v1/rooms/{listed}/knock", json={}).json()
    join(client, room["door"]["code"])
    server = server_for(client)
    tables = ("server_doors", "server_door_arrivals", "server_door_knocks")

    def counts() -> list[int]:
        with server.store.transaction("") as tx:
            return [tx.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables]

    assert all(counts())
    done = client.post(
        "/v1/coalition/dissolve", json={"reason": "completed"}, headers=owner_of(room)
    )
    assert done.status_code == 200 and done.json()["door_erased"] == 4
    assert counts() == [0, 0, 0]
    assert client.get("/v1/door/" + room["door"]["code"]).status_code == 404
    assert (
        client.get(
            f"/v1/rooms/{listed}/knocks/{ticket['knock']}?secret={ticket['secret']}"
        ).status_code
        == 403
    )
