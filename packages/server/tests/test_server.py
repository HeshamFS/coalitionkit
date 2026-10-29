# SPDX-License-Identifier: Apache-2.0
"""Protocol clients use real TCP ports and the composed application's lifespan."""

import json
import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import httpx2
import pytest
import uvicorn
from a2a.client.errors import A2AClientError
from mcp import Client
from mcp.client.session import ClientRequestContext
from mcp.client.streamable_http import streamable_http_client
from mcp_types import ElicitRequestParams, ElicitResult
from pydantic import SecretStr

from coalitionkit_contracts import public_key_to_jwk, sign_owner_proof, verify_consent
from coalitionkit_edges.a2a import MemberClient, ReceivedError
from coalitionkit_mcp.gateway import build_envelope
from coalitionkit_server import Settings, create_server
from coalitionkit_server.app import Server

Document = dict[str, Any]
CHARTER = json.loads((Path(__file__).parent / "fixtures" / "charter.json").read_text())


class Running:
    def __init__(self, settings: Settings) -> None:
        self.app = create_server(settings)
        self.state: Server = self.app.state.server
        self.base = settings.public_base_url
        self.worker = uvicorn.Server(
            uvicorn.Config(
                self.app,
                host="127.0.0.1",
                port=settings.bind_port,
                log_level="warning",
                access_log=False,
            )
        )
        self.thread = threading.Thread(target=self.worker.run, daemon=True)

    def __enter__(self) -> Running:
        self.thread.start()
        until = time.monotonic() + 20
        while not self.worker.started:
            if not self.thread.is_alive() or time.monotonic() > until:
                raise RuntimeError("server failed to start")
            time.sleep(0.02)
        return self

    def __exit__(self, *args: object) -> None:
        self.worker.should_exit = True
        self.thread.join(15)
        assert not self.thread.is_alive()

    def enroll(self) -> Document:
        with httpx.Client(base_url=self.base) as http:
            created = http.post(
                "/admin/coalitions", json=CHARTER, headers={"Authorization": "Bearer admin-test"}
            )
            assert created.status_code == 200, created.text
            invitation = created.json()["invitations"][0]["invitation"]
            redeemed = http.post("/invitations/redeem", json={"invitation": invitation})
            assert redeemed.status_code == 200, redeemed.text
            assert (
                http.post("/invitations/redeem", json={"invitation": invitation}).status_code == 400
            )
            return redeemed.json()

    def join(self, enrollment: Document) -> Document:
        coalition = enrollment["coalition_id"]
        person = self.state.registry.hosted_for(coalition, enrollment["participant"])
        jwk = public_key_to_jwk(person.owner_key.public_key(), person.owner_kid)
        body = {
            "card_url": person.card_url,
            "owner_key": jwk,
            "owner_proof": sign_owner_proof(
                coalition, person.participant, person.card_url, jwk, person.owner_key
            ),
            "roles_requested": ["member"],
            "surfaces": ["web"],
            "vault": "hosted",
        }
        return build_envelope(
            person, coalition, "coalition.join", body, scope={"audience": "coalition"}
        )


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = int(sock.getsockname()[1])
    return Settings(
        store=SecretStr(f"sqlite:///{tmp_path / 'host.db'}"),
        host_key_file=tmp_path / "keys" / "host.key",
        bind_port=port,
        public_base_url=f"http://127.0.0.1:{port}",
        admin_token=SecretStr("admin-test"),
    )


@pytest.fixture
def running(settings: Settings) -> Iterator[Running]:
    with Running(settings) as server:
        yield server


async def send(server: Running, enrollment: Document, event: Document) -> None:
    async with httpx.AsyncClient() as http:
        client = await MemberClient.connect(
            http,
            server.state.signer.card_url,
            enrollment["token"],
            server.state.key.public_key(),
            "host",
        )
        try:
            await client.send(event)
        finally:
            await client.close()


async def test_a2a_invitation_required(running: Running) -> None:
    enrolled = running.enroll()
    event = running.join(enrolled)
    await send(running, enrolled, event)
    host = running.state.hosts[enrolled["coalition_id"]]
    assert "p1" in host.state.members
    with pytest.raises(A2AClientError, match="401"):
        await send(running, {**enrolled, "token": "uninvited"}, event)
    # A valid credential cannot enroll another participant or reuse the invitation.
    person = running.state.registry.hosted_for(host.coalition_id, "p1")
    second = build_envelope(person, host.coalition_id, "coalition.join", event["payload"])
    with pytest.raises(ReceivedError):
        await send(running, enrolled, second)
    with httpx.Client(base_url=running.base) as http:
        issued = http.post(
            f"/admin/coalitions/{host.coalition_id}/invitations",
            json={"participant": "p2"},
            headers={"Authorization": "Bearer admin-test"},
        ).json()["invitation"]
        card = http.get(enrolled["card_url"]).json()
        card.pop("signatures")
        refused = http.post(
            "/invitations/redeem",
            json={
                "invitation": issued,
                "card_url": "https://p2.example/card",
                "card": card,
            },
        )
        assert refused.status_code == 400
        # Card verification fails before the invitation is consumed.
        assert http.post("/invitations/redeem", json={"invitation": issued}).status_code == 200


async def test_mcp_view_and_elicited_consent(running: Running) -> None:
    enrolled = running.enroll()
    await send(running, enrolled, running.join(enrolled))
    other = running.enroll()
    await send(running, other, running.join(other))
    asked: list[str] = []

    async def answer(context: ClientRequestContext, params: ElicitRequestParams) -> ElicitResult:
        asked.append(str(getattr(params, "message", "")))
        return ElicitResult(action="accept", content={"consent": True})

    async with (
        httpx2.AsyncClient(headers={"Authorization": "Bearer " + enrolled["token"]}) as http,
        Client(
            streamable_http_client(running.base + "/mcp", http_client=http),
            elicitation_callback=answer,
        ) as client,
    ):
        view = await client.call_tool("my_view", {"coalition_id": enrolled["coalition_id"]})
        assert not view.is_error, view
        forbidden = await client.call_tool("my_view", {"coalition_id": other["coalition_id"]})
        assert forbidden.is_error
        result = await client.call_tool(
            "accept_charter", {"coalition_id": enrolled["coalition_id"]}
        )
        assert not result.is_error, result
    assert len(asked) == 1
    event = running.state.store.read(enrolled["coalition_id"])[-1]
    person = running.state.registry.hosted_for(enrolled["coalition_id"], "p1")
    assert event["type"] == "coalition.decide"
    verify_consent(
        enrolled["coalition_id"], event["payload"], person.owner_key.public_key(), participant="p1"
    )


async def test_feed_snapshot_then_accepted_delta(running: Running) -> None:
    enrolled = running.enroll()
    await send(running, enrolled, running.join(enrolled))
    frames: list[str] = []
    async with (
        httpx.AsyncClient(timeout=10) as http,
        http.stream(
            "GET",
            running.base + "/v1/feed",
            headers={"Authorization": "Bearer " + enrolled["token"]},
        ) as response,
    ):
        assert response.status_code == 200
        async for line in response.aiter_lines():
            if not line.startswith("data: "):
                continue
            frame = json.loads(line[6:])
            frames.append(frame["type"])
            if frame["type"] == "STATE_SNAPSHOT":
                person = running.state.registry.hosted_for(enrolled["coalition_id"], "p1")
                event = build_envelope(
                    person,
                    enrolled["coalition_id"],
                    "coalition.observe",
                    {"source": "chat", "content": "updated"},
                    scope={"audience": "coalition"},
                )
                await send(running, enrolled, event)
            if frame["type"] == "STATE_DELTA":
                assert "updated" in json.dumps(frame)
                break
    assert frames[:2] == ["RUN_STARTED", "STATE_SNAPSHOT"]
    assert "STATE_DELTA" in frames


async def test_restart_preserves_members_log_and_credentials(settings: Settings) -> None:
    with Running(settings) as first:
        enrolled = first.enroll()
        await send(first, enrolled, first.join(enrolled))
        before = first.state.store.read(enrolled["coalition_id"])
        key = first.state.key.public_key().public_bytes_raw()
    with Running(settings) as second:
        host = second.state.hosts[enrolled["coalition_id"]]
        assert "p1" in host.state.members
        assert second.state.store.read(host.coalition_id) == before
        assert second.state.key.public_key().public_bytes_raw() == key
        with httpx.Client() as http:
            response = http.get(second.base + "/healthz")
            assert response.json()["store"] == "ok"
            steward = response.json()["steward"]
            assert set(steward) == {"provider", "model", "fallback"}
            assert steward["fallback"] == (steward["provider"] == "meta")
            assert "admin-test" not in response.text
        person = second.state.registry.hosted_for(host.coalition_id, "p1")
        await send(
            second,
            enrolled,
            build_envelope(
                person,
                host.coalition_id,
                "coalition.observe",
                {"source": "chat", "content": "resumed"},
            ),
        )
        assert len(second.state.store.read(host.coalition_id)) == len(before) + 1


def _adapter(members: frozenset[str] | None) -> tuple[Any, Any, Any]:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from coalitionkit_models import FakeModel, ModelGateway, ScriptedResponse, Settings
    from coalitionkit_server.audit import AuditLoop, StewardAdapter
    from coalitionkit_steward import Steward

    allow = '{"action": "allow", "policy_id": null, "reason": "ok", "redact": []}'
    fake = FakeModel([ScriptedResponse(allow)] * 4)
    gateway = ModelGateway(Settings(_env_file=None), transport=fake)  # pyright: ignore[reportCallIssue]
    steward = Steward(gateway, signing_key=Ed25519PrivateKey.generate(), kid="host")
    runner = AuditLoop()
    adapter = StewardAdapter(steward, runner, None if members is None else lambda _: members)
    return adapter, fake, runner


def _proposal() -> dict[str, Any]:
    canary = "zq7canary-p3-only"
    tasks = ["01M4XRC2A00000000000000002", "01M4XRC2A00000000000000003"]
    assignments = [{"task_id": tasks[0], "assignee": "p1"}, {"task_id": tasks[1], "assignee": "p3"}]
    assignments[1]["note"] = canary
    plan = {"plan_id": "01M4XRC0Z8185GR38E1W8124GK", "revision": 1, "assignments": assignments}
    return {
        "ext_version": "0.1",
        "coalition_id": "01M4XRC000000G40R40M30E209",
        "event_id": "01M4XRC0Z8185GR38E1W8124GK",
        "type": "coalition.propose",
        "sender": "https://agents.example.org/p1/card.json",
        "on_behalf_of": "p1",
        "scope": {"audience": "coalition"},
        "payload": {"proposal_set_id": "s", "plans": [{**plan, "objective_scores": {}}]},
        "sig": "x",
    }


def test_steward_adapter_with_members_never_sends_a_non_member_assignment_to_the_model() -> None:
    adapter, fake, runner = _adapter(frozenset({"p1", "p2"}))
    try:
        verdict = adapter.review(_proposal())
    finally:
        runner.close()
    sent = json.dumps([messages for _, messages, _ in fake.calls])
    assert fake.calls and "zq7canary-p3-only" not in sent
    assert verdict.action == "allow"


def test_steward_adapter_without_members_fails_closed_and_sends_nothing() -> None:
    adapter, fake, runner = _adapter(None)
    try:
        verdict = adapter.review(_proposal())
    finally:
        runner.close()
    assert fake.calls == []
    assert (verdict.action, verdict.policy_id) == ("escalate", "steward-members-unknown")


@pytest.mark.parametrize("kind", ["observe", "offer", "ripple"])
def test_steward_adapter_receives_consented_recipients(kind: str) -> None:
    from coalitionkit_runtime.steward import ReviewContext

    adapter, fake, runner = _adapter(None)
    members = frozenset({"p1", "p2"})
    context = ReviewContext(members, members, members)
    event: Document = {**_proposal(), "type": f"coalition.{kind}", "payload": {}}
    event["scope"] = {"audience": "participants", "participants": ["p1", "p2"]}
    try:
        assert adapter.review(event, context=context).action == "allow"
        event["scope"] = {"audience": "participants", "participants": ["p1", "p2", "p3"]}
        assert adapter.review(event, context=context).action == "block"
        assert not fake.calls
    finally:
        runner.close()


def test_selftest_does_not_block_first_safe_review() -> None:
    from coalitionkit_runtime.steward import ReviewContext
    from coalitionkit_server.audit import StewardAdapter

    ready = threading.Event()
    adapter, _, runner = _adapter(frozenset({"p1", "p2"}))
    steward = adapter.steward

    def initialize() -> Any:
        assert ready.wait(5)
        return steward

    deferred = StewardAdapter(initialize, runner)
    members = frozenset({"p1", "p2"})
    context = ReviewContext(members, members, members)
    try:
        event = {**_proposal(), "type": "coalition.observe", "payload": {"content": "update"}}
        assert deferred.review(event, context=context).action == "allow"
        assert deferred.review(_proposal(), context=context).policy_id == "steward-selftest-pending"
        ready.set()
        assert deferred._ready is not None  # pyright: ignore[reportPrivateUsage]
        deferred._ready.result(timeout=5)  # pyright: ignore[reportPrivateUsage]
        assert deferred.review(_proposal(), context=context).action == "allow"
    finally:
        ready.set()
        runner.close()


def test_health_reports_store_failure(settings: Settings) -> None:
    from unittest.mock import patch

    from fastapi.testclient import TestClient

    from coalitionkit_runtime.pool import StoreUnavailable

    app = create_server(settings)
    with TestClient(app) as client:
        with patch.object(app.state.server.store, "transaction", side_effect=StoreUnavailable):
            response = client.get("/healthz")
            assert response.status_code == 503
            assert response.json()["store"] == "down"
        assert client.get("/healthz").json()["store"] == "ok"


async def test_interrupted_append_is_retryable_over_a2a(running: Running) -> None:
    from unittest.mock import patch

    from coalitionkit_runtime.pool import StoreUnavailable

    enrolled = running.enroll()
    event = running.join(enrolled)
    host = running.state.hosts[enrolled["coalition_id"]]
    with (
        patch.object(host, "accept", side_effect=StoreUnavailable),
        pytest.raises(A2AClientError, match="503"),
    ):
        await send(running, enrolled, event)
    await send(running, enrolled, event)
    await send(running, enrolled, event)
    assert sum(e["event_id"] == event["event_id"] for e in host.store.read(host.coalition_id)) == 1
