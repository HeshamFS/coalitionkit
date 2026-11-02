# SPDX-License-Identifier: Apache-2.0
"""The web-started Gardener progresses without a harness driving the host."""

import asyncio
import json
import os
import time
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from a2a.types import Message, Role, SendMessageRequest
from fastapi.testclient import TestClient
from google.protobuf.json_format import MessageToDict
from pydantic import SecretStr
from test_genesis import server_for
from test_pack_genesis import pack_client

from coalitionkit_edges.a2a.wire import EXTENSION_URI, envelope_part
from coalitionkit_mcp.gateway import build_envelope
from coalitionkit_models import ModelGateway
from coalitionkit_models.settings import Settings as ModelSettings
from coalitionkit_runtime.steward import FakeSteward
from coalitionkit_server import create_server
from coalitionkit_server.adapter import Document
from coalitionkit_server.genesis import draft_goal

__all__ = ["pack_client"]


def events(client: TestClient, cid: str, kind: str) -> list[Document]:
    return [e for e in server_for(client).store.read(cid) if e["type"] == "coalition." + kind]


def wait_for(client: TestClient, cid: str, kind: str, count: int = 1) -> list[Document]:
    until = time.monotonic() + 8
    while time.monotonic() < until:
        found = events(client, cid, kind)
        if len(found) >= count:
            return found
        time.sleep(0.05)
    raise AssertionError(f"Expected {count} {kind}: {server_for(client).store.read(cid)}")


def begin(client: TestClient, pack: str = "pack-beta") -> Document:
    ref = {"name": pack, "version": "0.2.0" if pack == "pack-beta" else "1.0.0"}
    response = client.post(
        "/v1/genesis/draft", json={"goal": "Two members need a result tomorrow", "pack": ref}
    )
    assert response.status_code == 200, response.text
    draft = response.json()["draft"]
    draft["needs"] = ["First result", "Second result"]
    draft["roles"] = [{"id": "member", "label": "member", "count": 2}]
    response = client.post(
        "/v1/genesis/start",
        json={"draft": draft},
        headers={"Authorization": "Start " + server_for(client).registry.issue_start()},
    )
    assert response.status_code == 200, response.text
    return response.json()


def consent(client: TestClient, cid: str, token: str, who: str) -> None:
    response = client.post(
        "/v1/agent/answers",
        json={"interrupt_id": f"charter:{cid}:1:{who}", "consent": True},
        headers={"Authorization": "Bearer " + token},
    )
    assert response.status_code == 200, response.text


def offer(client: TestClient, token: str, need: str, minutes: int, money: int = 0) -> None:
    response = client.post(
        "/v1/agent/offer",
        json={"need_id": need, "cost": {"minutes": minutes, "money": money, "effort": "low"}},
        headers={"Authorization": "Bearer " + token},
    )
    assert response.status_code == 200, response.text


def progress(client: TestClient) -> tuple[str, Document]:
    created = begin(client)
    cid, owner = created["coalition_id"], created["owner"]
    # Isolate host choreography from the separately tested Steward policy/model audit.
    server_for(client).hosts[cid].steward = FakeSteward()
    assert not events(client, cid, "need")
    consent(client, cid, owner["token"], "p1")
    needs = wait_for(client, cid, "need", 2)
    invite = client.post(
        "/v1/invitations",
        json={"kind": "member", "count": 1},
        headers={"Authorization": "Bearer " + owner["token"]},
    )
    secret = invite.json()["invitations"][0]["link"].split("#")[1]
    response = client.post("/v1/invitations/accept", json={"invitation": secret})
    assert response.status_code == 200, response.text
    member = response.json()
    consent(client, cid, member["token"], member["participant"])
    for need in needs:
        offer(client, owner["token"], need["payload"]["need_id"], 10)
        offer(client, member["token"], need["payload"]["need_id"], 10, 20)
    wait_for(client, cid, "propose")
    wait_for(client, cid, "tension")
    return cid, member


def test_web_driver(pack_client: TestClient) -> None:
    cid, member = progress(pack_client)
    time.sleep(1.2)
    assert len(events(pack_client, cid, "need")) == 2
    assert len(events(pack_client, cid, "propose")) == 1
    assert len(events(pack_client, cid, "tension")) == 1
    # The room can show and approve the plans: members see the proposal, not only the host.
    seen = server_for(pack_client).hosts[cid].view(member["participant"])["events"].values()
    assert any(e["type"] == "coalition.propose" for e in seen)


def test_restart(pack_client: TestClient, tmp_path: Path) -> None:
    settings = server_for(pack_client).settings.model_copy(
        update={"store": SecretStr("sqlite:///" + str(tmp_path / "restart.db"))}
    )
    with TestClient(
        create_server(settings),
        client=("127.0.0.1", 1000),
        headers={"Origin": settings.public_base_url},
    ) as client:
        cid, _ = progress(client)
    with TestClient(
        create_server(settings),
        client=("127.0.0.1", 1000),
        headers={"Origin": settings.public_base_url},
    ) as client:
        time.sleep(1.3)
        assert len(events(client, cid, "need")) == 2
        assert len(events(client, cid, "propose")) == 1
        assert len(events(client, cid, "tension")) == 1


def test_admin_not_driven(pack_client: TestClient) -> None:
    server = server_for(pack_client)
    created = server.create(
        {
            "goal": "Other driver",
            "roles": [{"id": "member"}],
            "rules": [],
            "deadline": "2099-01-01T00:00:00Z",
            "deciders": ["p1"],
        }
    )
    time.sleep(1.2)
    assert created["coalition_id"] not in server.gardener.tasks
    assert not events(pack_client, created["coalition_id"], "need")


@pytest.mark.live
@pytest.mark.skipif(
    os.environ.get("COALITIONKIT_LIVE") != "1" or not os.environ.get("COALITIONKIT_META_API_KEY"),
    reason="live model opt-in and key required",
)
def test_live_loop(pack_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # The fixture builds its server with model calls off; draft live with the caller's key,
    # then let the scripted server's loop take the model-written draft from there.
    monkeypatch.undo()

    async def live_draft() -> Document:
        gateway = ModelGateway(ModelSettings())
        try:
            result = await draft_goal(
                "Two members need one result and one review tomorrow", gateway
            )
        finally:
            await gateway.aclose()
        assert result.source == "model"
        return result.draft.model_dump(mode="json")

    draft = asyncio.run(live_draft())
    assert draft["needs"]
    draft["pack"] = {"name": "pack-beta", "version": "0.2.0"}
    draft["roles"] = [{"id": "member", "label": "member", "count": 1}]
    server = server_for(pack_client)
    response = pack_client.post(
        "/v1/genesis/start",
        json={"draft": draft},
        headers={"Authorization": "Start " + server.registry.issue_start()},
    )
    assert response.status_code == 200, response.text
    created = response.json()
    cid, owner = created["coalition_id"], created["owner"]
    server.hosts[cid].steward = FakeSteward()
    consent(pack_client, cid, owner["token"], owner["participant"])
    for need in wait_for(pack_client, cid, "need", len(draft["needs"])):
        offer(pack_client, owner["token"], need["payload"]["need_id"], 1)
    wait_for(pack_client, cid, "propose")


def test_ripple_preserves_untouched(pack_client: TestClient) -> None:
    cid, member = progress(pack_client)
    server = server_for(pack_client)
    host = server.hosts[cid]
    touched, untouched = list(host.state.tasks)
    before = deepcopy(host.state.tasks[untouched])
    person = server.registry.hosted_for(cid, member["participant"])
    envelope = build_envelope(
        person,
        cid,
        "coalition.ripple",
        {"change": "Availability changed", "invalidates": [touched]},
        scope={"audience": "coalition"},
    )
    # Exercise the signed member envelope over the public protocol transport.
    message = Message(
        message_id="ripple", context_id=cid, role=Role.ROLE_USER, parts=[envelope_part(envelope)]
    )
    response = pack_client.post(
        "/a2a",
        json={
            "jsonrpc": "2.0",
            "id": "1",
            "method": "SendMessage",
            "params": MessageToDict(SendMessageRequest(message=message)),
        },
        headers={
            "Authorization": "Bearer " + member["token"],
            "A2A-Version": "1.0",
            "A2A-Extensions": EXTENSION_URI,
        },
    )
    assert response.status_code == 200, response.text
    wait_for(pack_client, cid, "ripple")
    proposals = wait_for(pack_client, cid, "propose", 2)
    assert {a["task_id"] for p in proposals[-1]["payload"]["plans"] for a in p["assignments"]} == {
        touched
    }
    assert host.state.tasks[untouched] == before


def test_schema_refusals_once(pack_client: TestClient) -> None:
    server = server_for(pack_client)
    key = ("pack-beta", "0.2.0")
    server.packs[key] = replace(
        server.packs[key],
        schemas={
            "need": {
                "type": "object",
                "required": ["code"],
                "properties": {"code": {"type": "string"}},
            }
        },
    )
    created = begin(pack_client)
    cid = created["coalition_id"]
    consent(pack_client, cid, created["owner"]["token"], "p1")
    time.sleep(1.3)
    with server.store.transaction(cid) as tx:
        rows = tx.execute(
            "SELECT error FROM server_genesis_refusals WHERE coalition = ?", (cid,)
        ).fetchall()
    assert len(rows) == 2
    assert all(json.loads(r[0])["code"] == "schema_invalid" for r in rows)
    hub = server.surfaces[cid].state.hub
    assert len(hub.outboxes["p1"]) == 2
    # A later wake must neither retry the refused sentences nor report them again.
    server.gardener.step(cid)
    assert len(hub.outboxes["p1"]) == 2
    assert not events(pack_client, cid, "need")


def test_refusal_does_not_stop_remaining_needs(pack_client: TestClient) -> None:
    server = server_for(pack_client)
    created = begin(pack_client)
    cid = created["coalition_id"]
    # An invalid first sentence exercises the same host refusal path as required ext.
    with server.store.transaction(cid) as tx:
        tx.execute(
            "UPDATE server_genesis SET needs = ? WHERE coalition = ?",
            (json.dumps(["", "Valid result"]), cid),
        )
    consent(pack_client, cid, created["owner"]["token"], "p1")
    needs = wait_for(pack_client, cid, "need")
    assert needs[0]["payload"]["description"] == "Valid result"
    with server.store.transaction(cid) as tx:
        assert (
            len(
                tx.execute(
                    "SELECT id FROM server_genesis_refusals WHERE coalition = ?", (cid,)
                ).fetchall()
            )
            == 1
        )


async def test_demo_not_driven(pack_client: TestClient) -> None:
    from coalitionkit_cli.demo import enroll

    server = server_for(pack_client)
    cid, tokens = await enroll(server, 2)
    consent(pack_client, cid, tokens["p1"], "p1")
    time.sleep(1.2)
    assert cid not in server.gardener.tasks
    assert not events(pack_client, cid, "need")


def test_restart_resumes_before_owner_consent(pack_client: TestClient, tmp_path: Path) -> None:
    settings = server_for(pack_client).settings.model_copy(
        update={"store": SecretStr("sqlite:///" + str(tmp_path / "pending.db"))}
    )
    with TestClient(
        create_server(settings),
        client=("127.0.0.1", 1000),
        headers={"Origin": settings.public_base_url},
    ) as client:
        created = begin(client)
        cid = created["coalition_id"]
    with TestClient(
        create_server(settings),
        client=("127.0.0.1", 1000),
        headers={"Origin": settings.public_base_url},
    ) as client:
        consent(client, cid, created["owner"]["token"], "p1")
        assert len(wait_for(client, cid, "need", 2)) == 2


def test_a_failed_step_is_retried_without_new_activity(
    pack_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from coalitionkit_server import gardener_loop

    monkeypatch.setattr(gardener_loop, "RETRY_BASE_S", 0.1)
    created = begin(pack_client)
    cid, owner = created["coalition_id"], created["owner"]
    server = server_for(pack_client)
    server.hosts[cid].steward = FakeSteward()
    real_step, broken = server.gardener.step, {"on": True}

    def flaky(coalition: str) -> None:
        if broken["on"]:
            raise RuntimeError("store briefly unavailable")
        real_step(coalition)

    monkeypatch.setattr(server.gardener, "step", flaky)
    consent(pack_client, cid, owner["token"], "p1")
    time.sleep(1.5)  # the step after consent fails; no further event follows
    assert not events(pack_client, cid, "need")
    broken["on"] = False
    assert len(wait_for(pack_client, cid, "need", 2)) == 2


def test_no_plan_before_every_decider_has_joined(pack_client: TestClient) -> None:
    created = begin(pack_client)  # two seats: p1 and p2 both decide
    cid, owner = created["coalition_id"], created["owner"]
    server_for(pack_client).hosts[cid].steward = FakeSteward()
    consent(pack_client, cid, owner["token"], "p1")
    needs = wait_for(pack_client, cid, "need", 2)
    for need in needs:
        offer(pack_client, owner["token"], need["payload"]["need_id"], 10)
    time.sleep(2.5)
    assert not events(pack_client, cid, "propose")  # the second decider has not said yes yet
    invite = pack_client.post(
        "/v1/invitations",
        json={"kind": "member", "count": 1},
        headers={"Authorization": "Bearer " + owner["token"]},
    )
    secret = invite.json()["invitations"][0]["link"].split("#")[1]
    joined = pack_client.post("/v1/invitations/accept", json={"invitation": secret})
    assert joined.status_code == 200, joined.text  # still open to join: no plan has moved it on
    member = joined.json()
    consent(pack_client, cid, member["token"], member["participant"])
    assert wait_for(pack_client, cid, "propose")


def test_a_released_coalition_is_never_driven(pack_client: TestClient) -> None:
    created = begin(pack_client)
    cid, owner = created["coalition_id"], created["owner"]
    server = server_for(pack_client)
    pack_client.portal.call(server.gardener.release, cid)  # type: ignore[union-attr]
    consent(pack_client, cid, owner["token"], "p1")
    time.sleep(2.5)
    assert not events(pack_client, cid, "need")  # the caller plays the Gardener itself
    assert cid not in server.gardener.tasks
    with server.store.transaction(cid) as tx:
        assert not tx.execute("SELECT 1 FROM server_genesis WHERE coalition = ?", (cid,)).fetchall()
