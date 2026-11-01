# SPDX-License-Identifier: Apache-2.0
"""Genesis reader and host lifecycle contract tests."""

import json
import os
from collections.abc import Generator, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from coalitionkit_contracts import new_ulid, public_key_to_jwk
from coalitionkit_models import FakeModel, ModelGateway, ScriptedResponse
from coalitionkit_models.settings import Settings as ModelSettings
from coalitionkit_models.structured import response_format
from coalitionkit_runtime import Acknowledgement
from coalitionkit_server import Settings, create_server
from coalitionkit_server.adapter import Document
from coalitionkit_server.app import Server
from coalitionkit_server.genesis import DraftResponse, ModelDraft, draft_goal, read_goal
from coalitionkit_server.registry import digest

NOW = datetime(2030, 1, 7, 12, tzinfo=UTC)  # Monday


@pytest.mark.parametrize(
    "sentence,roles,deadline,needs",
    [
        (
            "Nine of us need a shared room tonight",
            [("member", 9)],
            "2030-01-07T23:59:59Z",
            ["a shared room"],
        ),
        (
            "3 labs and a courier need a delivery by Friday",
            [("lab", 3), ("courier", 1)],
            "2030-01-11T23:59:59Z",
            ["a delivery"],
        ),
        ("Two teams want to finish in 3 days", [("team", 2)], "2030-01-10T12:00:00Z", ["finish"]),
        ("We need a room", [("member", 1)], None, ["a room"]),
        ("Build something together", [("member", 1)], None, []),
        (
            "4 volunteers need transport today",
            [("volunteer", 4)],
            "2030-01-07T23:59:59Z",
            ["transport"],
        ),
        (
            "Five people need supplies tomorrow",
            [("member", 5)],
            "2030-01-08T23:59:59Z",
            ["supplies"],
        ),
        (
            "6 reviewers want feedback in two hours",
            [("reviewer", 6)],
            "2030-01-07T14:00:00Z",
            ["feedback"],
        ),
        (
            "A courier needs a route by 2030-02-01",
            [("courier", 1)],
            "2030-02-01T23:59:59Z",
            ["a route"],
        ),
        ("Twelve members need agreement", [("member", 12)], None, ["agreement"]),
        ("3 people want to organize", [("member", 3)], None, ["organize"]),
        ("A team needs space in 1 day", [("team", 1)], "2030-01-08T12:00:00Z", ["space"]),
        ("We need 3 boxes", [("member", 1)], None, ["3 boxes"]),
    ],
)
def test_reader(
    sentence: str, roles: list[tuple[str, int]], deadline: str | None, needs: list[str]
) -> None:
    result = read_goal(sentence, NOW)
    assert [(r.id, r.count) for r in result.draft.roles] == roles
    assert result.draft.model_dump(mode="json")["deadline"] == deadline
    assert result.draft.needs == needs
    assert result.draft.pack is None and result.source == "reader"
    for reading in result.reading:
        assert sentence[slice(*reading.span)]


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.delenv("COALITIONKIT_META_API_KEY", raising=False)
    settings = Settings(
        store=SecretStr("sqlite:///:memory:"),
        host_key_file=tmp_path / "host.key",
        genesis="local",
        public_base_url="http://127.0.0.1:8000",
    )
    app = create_server(settings)
    with TestClient(
        app, client=("127.0.0.1", 12345), headers={"Origin": settings.public_base_url}
    ) as http:
        yield http


def server_for(client: TestClient) -> Server:
    return cast(FastAPI, client.app).state.server


def start(client: TestClient) -> Document:
    code = server_for(client).registry.issue_start()
    draft = client.post("/v1/genesis/draft", json={"goal": "Three members need a room"}).json()[
        "draft"
    ]
    result = client.post(
        "/v1/genesis/start", json={"draft": draft}, headers={"Authorization": "Start " + code}
    )
    assert result.status_code == 200, result.text
    host = public_key_to_jwk(server_for(client).key.public_key(), "host")
    assert result.json()["host_key"] == host  # pinned by the browser at join
    return result.json()


def test_draft_and_codes(client: TestClient) -> None:
    for goal in ("", "   ", "x" * 501):
        assert client.post("/v1/genesis/draft", json={"goal": goal}).status_code == 422
    draft = client.post("/v1/genesis/draft", json={"goal": "We need space"}).json()["draft"]
    assert draft["goal"] == "We need space"
    server = server_for(client)
    code = server.registry.issue_start()
    expired = server.registry.issue_start()
    with server.store.transaction("") as tx:
        tx.execute(
            "UPDATE server_start_codes SET expires = ? WHERE digest = ?",
            ("2000-01-01T00:00:00+00:00", digest(expired)),
        )
        assert (
            tx.execute("SELECT digest FROM server_start_codes WHERE digest = ?", (code,)).fetchone()
            is None
        )
    for value, expected in [("wrong", 401), (expired, 401), (code, 200), (code, 401)]:
        result = client.post(
            "/v1/genesis/start", json={"draft": draft}, headers={"Authorization": "Start " + value}
        )
        assert result.status_code == expected, result.text
        if expected == 200:
            created = result.json()
            events = server.store.read(created["coalition_id"])
            assert events[0]["type"] == "coalition.charter"
            assert created["owner"]["participant"] == "p1"
            assert server.registry.lookup(created["owner"]["token"])


def test_invitations_and_dissolve(client: TestClient) -> None:
    created = start(client)
    owner = {"Authorization": "Bearer " + created["owner"]["token"]}
    invitations = client.post("/v1/invitations", json={"kind": "member", "count": 3}, headers=owner)
    assert invitations.status_code == 200, invitations.text
    first, second, third = invitations.json()["invitations"]
    secret = first["link"].split("#")[1]
    joined = client.post("/v1/invitations/accept", json={"invitation": secret})
    assert joined.status_code == 200, joined.text
    assert joined.json()["host_key"] == public_key_to_jwk(
        server_for(client).key.public_key(), "host"
    )
    member = {"Authorization": "Bearer " + joined.json()["token"]}
    assert client.post("/v1/invitations/accept", json={"invitation": secret}).status_code == 400
    assert (
        client.post(
            "/v1/invitations", json={"kind": "member", "count": 1}, headers=member
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/v1/coalition/dissolve", json={"reason": "completed"}, headers=member
        ).status_code
        == 403
    )
    assert client.delete("/v1/invitations/" + second["id"], headers=owner).status_code == 204
    assert (
        client.post(
            "/v1/invitations/accept", json={"invitation": second["link"].split("#")[1]}
        ).status_code
        == 400
    )
    server = server_for(client)
    with server.store.transaction(created["coalition_id"]) as tx:
        # Hosted state is encrypted JSON; plant a private sentinel alongside hosted keys.
        row = tx.execute(
            "SELECT hosted FROM server_credentials WHERE digest = ?",
            (digest(joined.json()["token"]),),
        ).fetchone()
        state = json.loads(server.registry.cipher.decrypt(row[0].encode()))
        state["private_limit"] = "private-sentinel-limit"
        encrypted = server.registry.cipher.encrypt(json.dumps(state).encode()).decode()
        tx.execute(
            "UPDATE server_credentials SET hosted = ? WHERE digest = ?",
            (encrypted, digest(joined.json()["token"])),
        )
    host = server.hosts[created["coalition_id"]]
    task = new_ulid()
    emitted = host.host_emit(
        "need",
        {
            "need_id": task,
            "description": "Find a shared room",
            "requirements": [],
            "window": {"start": datetime.now(UTC).isoformat(), "end": "2099-01-01T00:00:00Z"},
        },
        {"audience": "coalition"},
    )
    assert isinstance(emitted, Acknowledgement)
    result = client.post("/v1/coalition/dissolve", json={"reason": "completed"}, headers=owner)
    assert result.status_code == 200, result.text
    assert result.json()["tasks_closed"] == 1
    assert host.state.tasks[task]["status"] == "withdrawn"
    assert result.json()["tokens_revoked"] == 2
    assert result.json()["vaults_erased"] == 2
    assert result.json()["invitations_revoked"] == 1
    assert server.store.read(created["coalition_id"])[-1]["type"] == "coalition.dissolve"
    assert client.get("/v1/feed", headers=owner).status_code == 401
    assert client.get("/v1/feed", headers=member).status_code == 401
    assert (
        client.post(
            "/v1/invitations/accept", json={"invitation": third["link"].split("#")[1]}
        ).status_code
        == 400
    )
    retry = client.post("/v1/coalition/dissolve", json={"reason": "completed"}, headers=owner)
    assert retry.json() == result.json()
    with server.store.transaction("") as tx:
        assert not tx.execute("SELECT hosted FROM server_credentials").fetchall()
    assert (
        len(
            [
                e
                for e in server.store.read(created["coalition_id"])
                if e["type"] == "coalition.dissolve"
            ]
        )
        == 1
    )


def test_local_guards(client: TestClient) -> None:
    for origin in ("https://foreign.example", ""):
        assert (
            client.post(
                "/v1/genesis/draft", json={"goal": "A goal"}, headers={"Origin": origin}
            ).status_code
            == 403
        )
    client.headers.pop("origin")
    assert client.post("/v1/genesis/draft", json={"goal": "A goal"}).status_code == 403
    client.headers["origin"] = "http://127.0.0.1:8000"
    assert client.post("/v1/genesis/draft", data={"goal": "A goal"}).status_code == 403
    remote = TestClient(client.app, client=("192.0.2.1", 345), headers=dict(client.headers))
    assert remote.post("/v1/genesis/draft", json={"goal": "A goal"}).status_code == 403


def test_a_browser_same_origin_get_lists_packs(client: TestClient) -> None:
    # What a browser sends for fetch("/v1/packs") from the host's own page: no Origin header.
    client.headers.pop("origin")
    browser = {"Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "cors", "Host": "127.0.0.1:8000"}
    assert client.get("/v1/packs", headers=browser).status_code == 200
    # DNS rebinding: the browser calls the page same-origin, but the Host is not the host's own.
    rebound = {**browser, "Host": "rebound.example:8000"}
    assert client.get("/v1/packs", headers=rebound).status_code == 403
    for site in ("cross-site", "same-site", "none"):
        assert client.get("/v1/packs", headers={"Sec-Fetch-Site": site}).status_code == 403
    assert client.get("/v1/packs").status_code == 403
    no_origin_post = client.post("/v1/genesis/draft", json={"goal": "A goal"}, headers=browser)
    assert no_origin_post.status_code == 403
    remote = TestClient(client.app, client=("192.0.2.1", 345))
    assert remote.get("/v1/packs", headers=browser).status_code == 403


async def test_model_fallback_and_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COALITIONKIT_META_API_KEY", "test")
    fake = FakeModel([ValueError("failed"), ScriptedResponse("not JSON")])
    gateway = ModelGateway(ModelSettings(), transport=fake)
    assert (await draft_goal("A shared goal", gateway)).source == "reader"
    assert (await draft_goal("A shared goal", gateway)).source == "reader"
    expected = read_goal("A shared goal")
    fake.script.append(ScriptedResponse(expected.model_dump_json()))
    assert (await draft_goal("A shared goal", gateway)).source == "model"
    monkeypatch.delenv("COALITIONKIT_META_API_KEY")
    assert (await draft_goal("A shared goal", gateway)).source == "reader"
    assert len(fake.calls) == 3


def test_admin_gate(client: TestClient) -> None:
    server = server_for(client)
    server.settings.genesis = "admin"
    server.settings.admin_token = SecretStr("admin")
    assert client.post("/v1/genesis/draft", json={"goal": "A goal"}).status_code == 401
    assert (
        client.post(
            "/v1/genesis/draft", json={"goal": "A goal"}, headers={"Authorization": "Bearer admin"}
        ).status_code
        == 200
    )


def test_cleanup_failure_retry(client: TestClient) -> None:
    created = start(client)
    server = server_for(client)
    auth = {"Authorization": "Bearer " + created["owner"]["token"]}
    with patch.object(server.hosts[created["coalition_id"]], "host_emit", side_effect=RuntimeError):
        response = client.post("/v1/coalition/dissolve", json={"reason": "cancelled"}, headers=auth)
    assert response.status_code == 500
    assert response.json() == {"failed": "event", "done": {}}
    assert (
        client.post(
            "/v1/coalition/dissolve", json={"reason": "cancelled"}, headers=auth
        ).status_code
        == 200
    )


def test_genesis_asks_the_model_for_closed_objects_only() -> None:
    """Strict providers refuse a reply schema with any object that may hold other keys."""

    def objects(node: object) -> Iterator[dict[str, object]]:
        if isinstance(node, dict):
            node = cast(dict[str, object], node)
            if node.get("type") == "object":
                yield node
            for value in node.values():
                yield from objects(value)
        elif isinstance(node, list):
            for value in cast(list[object], node):
                yield from objects(value)

    schema = response_format(ModelDraft)["json_schema"]["schema"]
    found = list(objects(schema))
    assert found and all(o.get("additionalProperties") is False for o in found)
    assert "suggested" not in schema["properties"] and "vocabulary" not in schema["properties"]


async def test_model_draft_becomes_a_host_draft_response() -> None:
    goal = "Nine members need a shared room tomorrow"
    reply = {
        "draft": {
            "goal": goal,
            "roles": [{"id": "member", "label": "member", "count": 9}],
            "needs": ["a shared room"],
            "deadline": None,
            "pack": None,
            "utc_offset_minutes": None,
            "deciders": "all",
        },
        "source": "model",
        "reading": [{"span": [0, 4], "kind": "count"}, {"span": [30, 99], "kind": "need"}],
    }
    gateway = ModelGateway(
        ModelSettings(), transport=FakeModel([ScriptedResponse(json.dumps(reply))])
    )
    try:
        with patch.dict(os.environ, {"COALITIONKIT_META_API_KEY": "test-not-a-real-key"}):
            result = await draft_goal(goal, gateway)
    finally:
        await gateway.aclose()
    assert isinstance(result, DraftResponse)
    assert result.source == "model" and result.draft.roles[0].count == 9
    assert result.suggested is None and result.vocabulary == {}
    # The span past the goal is dropped; the reader fills the deadline the model left out.
    assert [r.span for r in result.reading] == [(0, 4), (32, 40)]
    assert result.draft.deadline == read_goal(goal).draft.deadline is not None


@pytest.mark.live
@pytest.mark.skipif(
    not os.environ.get("COALITIONKIT_META_API_KEY") or os.environ.get("COALITIONKIT_LIVE") != "1",
    reason="live model opt-in and key required",
)
async def test_live_genesis() -> None:
    gateway = ModelGateway(ModelSettings())
    try:
        result = await draft_goal("Nine members need a shared room tomorrow", gateway)
        assert result.source == "model"
        DraftResponse.model_validate(result.model_dump())
    finally:
        await gateway.aclose()


async def test_owner_feed_over_http(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    import httpx
    from test_server import Running

    monkeypatch.delenv("COALITIONKIT_META_API_KEY", raising=False)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    settings = Settings(
        store=SecretStr("sqlite:///:memory:"),
        host_key_file=tmp_path / "host.key",
        genesis="local",
        bind_port=port,
        public_base_url=f"http://127.0.0.1:{port}",
    )
    with Running(settings) as running:
        async with httpx.AsyncClient(
            base_url=running.base, headers={"Origin": running.base}
        ) as http:
            code = running.state.registry.issue_start()
            draft = read_goal("Two members need a shared room").draft.model_dump(mode="json")
            response = await http.post(
                "/v1/genesis/start",
                json={"draft": draft},
                headers={"Authorization": "Start " + code},
            )
            assert response.status_code == 200, response.text
            async with http.stream(
                "GET",
                "/v1/feed",
                headers={"Authorization": "Bearer " + response.json()["owner"]["token"]},
            ) as stream:
                assert stream.status_code == 200
                async for line in stream.aiter_lines():
                    if line.startswith("data: "):
                        assert json.loads(line[6:])["type"] == "RUN_STARTED"
                        break


def test_cleanup_resumes_after_erasing_vaults(client: TestClient) -> None:
    from contextlib import contextmanager
    from typing import Any

    created = start(client)
    server = server_for(client)
    original = server.store.transaction
    auth = {"Authorization": "Bearer " + created["owner"]["token"]}

    @contextmanager
    def failing_transaction(coalition: str) -> Generator[Any]:
        with original(coalition) as tx:
            execute = tx.execute

            def fail_tokens(sql: str, args: Any = ()) -> Any:
                if sql.startswith("DELETE FROM server_credentials"):
                    raise RuntimeError("storage unavailable")
                return execute(sql, args)

            with patch.object(tx, "execute", side_effect=fail_tokens):
                yield tx

    with patch.object(server.store, "transaction", side_effect=failing_transaction):
        response = client.post("/v1/coalition/dissolve", json={"reason": "cancelled"}, headers=auth)
    assert response.status_code == 500
    assert response.json()["failed"] == "tokens_revoked"
    assert response.json()["done"]["vaults_erased"] == 1
    retry = client.post("/v1/coalition/dissolve", json={"reason": "cancelled"}, headers=auth)
    assert retry.status_code == 200, retry.text
    assert retry.json()["vaults_erased"] == 1
    assert retry.json()["tokens_revoked"] == 1
    assert retry.json()["seq"] == response.json()["done"]["seq"]


async def test_model_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio
    from unittest.mock import AsyncMock

    monkeypatch.setenv("COALITIONKIT_META_API_KEY", "test")
    gateway = ModelGateway(ModelSettings(), transport=FakeModel([]))

    async def slow(*args: object, **kwargs: object) -> None:
        await asyncio.sleep(10)

    with patch.object(gateway, "complete", new=AsyncMock(side_effect=slow)) as complete:
        assert (await draft_goal("A shared goal", gateway)).source == "reader"
        complete.assert_awaited_once()


def test_business_invitation_requires_card(client: TestClient) -> None:
    created = start(client)
    owner = {"Authorization": "Bearer " + created["owner"]["token"]}
    response = client.post("/v1/invitations", json={"kind": "business", "count": 1}, headers=owner)
    secret = response.json()["invitations"][0]["link"].split("#")[1]
    assert client.post("/v1/invitations/accept", json={"invitation": secret}).status_code == 400
    assert client.post("/invitations/redeem", json={"invitation": secret}).status_code == 400


def test_refused_charter(client: TestClient) -> None:
    server = server_for(client)
    draft = read_goal("A shared goal").draft.model_dump(mode="json")
    with patch.object(server, "create", side_effect=ValueError("charter refused: invalid_state")):
        response = client.post(
            "/v1/genesis/start",
            json={"draft": draft},
            headers={"Authorization": "Start " + server.registry.issue_start()},
        )
    assert response.status_code == 422
    assert "invalid_state" in response.json()["detail"]


def test_day_words_follow_the_writers_time_zone() -> None:
    # 22:30 UTC on a Thursday: 23:30 an hour east, 17:30 five hours west,
    # and already Friday 00:30 two hours east.
    now = datetime(2026, 11, 5, 22, 30, tzinfo=UTC)
    east = read_goal("Two members need a plan by Friday", now, utc_offset_minutes=60).draft
    west = read_goal("Two members need a plan by Friday", now, utc_offset_minutes=-300).draft
    utc = read_goal("Two members need a plan by Friday", now).draft
    assert east.deadline == datetime(2026, 11, 6, 22, 59, 59, tzinfo=UTC)
    assert west.deadline == datetime(2026, 11, 7, 4, 59, 59, tzinfo=UTC)
    assert utc.deadline == datetime(2026, 11, 6, 23, 59, 59, tzinfo=UTC)
    tonight = read_goal("Two members need a plan tonight", now, utc_offset_minutes=60).draft
    assert tonight.deadline == datetime(2026, 11, 5, 22, 59, 59, tzinfo=UTC)
    past_midnight = read_goal("Two members need a plan tonight", now, utc_offset_minutes=120)
    assert past_midnight.draft.deadline == datetime(2026, 11, 6, 21, 59, 59, tzinfo=UTC)


async def test_reader_fills_needs_the_model_left_out() -> None:
    goal = "Two members need a shared room by tomorrow"
    reply = {
        "draft": {
            "goal": goal,
            "roles": [{"id": "member", "label": "member", "count": 2}],
            "needs": [],
            "deadline": None,
            "pack": None,
            "utc_offset_minutes": None,
            "deciders": "all",
        },
        "source": "model",
        "reading": [{"span": [0, 3], "kind": "count"}],
    }
    gateway = ModelGateway(
        ModelSettings(), transport=FakeModel([ScriptedResponse(json.dumps(reply))])
    )
    try:
        with patch.dict(os.environ, {"COALITIONKIT_META_API_KEY": "test-not-a-real-key"}):
            result = await draft_goal(goal, gateway)
    finally:
        await gateway.aclose()
    reader = read_goal(goal)
    assert result.source == "model" and result.draft.roles[0].count == 2
    assert result.draft.needs == reader.draft.needs == ["a shared room"]
    assert result.draft.deadline == reader.draft.deadline is not None
    kinds = sorted(r.kind for r in result.reading)
    assert kinds == ["count", "deadline", "need"]
