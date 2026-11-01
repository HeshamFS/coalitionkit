# SPDX-License-Identifier: Apache-2.0
import json
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from test_genesis import client, server_for, start
from test_pack_genesis import pack_client

from coalitionkit_contracts import verify_envelope
from coalitionkit_runtime.steward import FakeSteward
from coalitionkit_server.packs import private_extension
from coalitionkit_surfaces.frames import encode

__all__ = ["client", "pack_client"]


def test_vault_isolation(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    created = start(client)
    server = server_for(client)
    cid = created["coalition_id"]
    headers = {"Authorization": "Bearer " + created["owner"]["token"]}
    invite = client.post("/v1/invitations", json={"kind": "member", "count": 1}, headers=headers)
    secret = invite.json()["invitations"][0]["link"].split("#")[1]
    joined = client.post("/v1/invitations/accept", json={"invitation": secret}).json()
    other = {"Authorization": "Bearer " + joined["token"]}
    host = server.hosts[cid]
    steward = FakeSteward()
    host.steward = steward
    before = server.store.read(cid)
    canary = "PRIVATE-VAULT-CANARY"
    result = client.post("/v1/agent/vault", json={"values": {"secret": canary}}, headers=headers)
    assert result.status_code == 200, result.text
    assert result.json() == {"keys": ["secret"]}
    assert server.registry.vault_values(cid, "p1") == {"secret": canary}
    assert client.get("/v1/agent/vault", headers=headers).json() == {"keys": ["secret"]}
    assert client.get("/v1/agent/vault", headers=other).json() == {"keys": []}
    for method in ("get", "post"):
        assert getattr(client, method)("/v1/agent/vault").status_code == 401
    assert client.get("/v1/agent/vault?participant=p1", headers=other).status_code == 403
    assert (
        client.post(
            "/v1/agent/vault",
            headers=other,
            json={"participant": "p1", "values": {"secret": "bad"}},
        ).status_code
        == 403
    )
    assert (
        client.post("/v1/agent/vault", headers=other, json={"values": {"other": "own"}}).status_code
        == 200
    )
    assert server.registry.vault_values(cid, "p1")["secret"] == canary
    hub = server.surfaces[cid].state.hub
    for viewer in ("p1", joined["participant"], "steward"):
        assert canary not in json.dumps(host.view(viewer))
        assert canary not in "".join(encode(f) for f in hub.feed_session(viewer).start())
        assert canary not in "".join(encode(f) for f in hub.agent_session(viewer).start())
    assert server.store.read(cid) == before and steward.calls == []
    assert "PRIVATE-VAULT-CANARY" not in caplog.text
    assert "PRIVATE-OFFER-CANARY" not in caplog.text
    with server.store.transaction(cid) as tx:
        rows = tx.execute("SELECT hosted FROM server_credentials").fetchall()
        assert canary not in str(rows)
        tx.execute("UPDATE server_credentials SET hosted = '' WHERE participant = 'p1'")
    for path in ("offer", "vault"):
        assert client.post("/v1/agent/" + path, headers=headers, json={}).status_code == 409
    assert client.get("/v1/agent/vault", headers=headers).status_code == 409


def test_offer(pack_client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    client = pack_client
    server = server_for(client)
    ref = {"name": "pack-alpha", "version": "1.0.0"}
    key = (ref["name"], ref["version"])
    pack = server.packs[key]
    server.packs[key] = replace(
        pack,
        schemas={
            **pack.schemas,
            "offer": {
                "type": "object",
                "properties": {
                    "count": {"type": "integer"},
                    "secret": {"type": "string", "x-private": True},
                },
                "additionalProperties": False,
            },
        },
    )
    draft = client.post("/v1/genesis/draft", json={"goal": "Agree", "pack": ref}).json()["draft"]
    draft["roles"] = draft["roles"][:1]
    result = client.post(
        "/v1/genesis/start",
        json={"draft": draft},
        headers={"Authorization": "Start " + server.registry.issue_start()},
    )
    assert result.status_code == 200, result.text
    created = result.json()
    cid = created["coalition_id"]
    host = server.hosts[cid]
    headers = {"Authorization": "Bearer " + created["owner"]["token"]}
    hub = server.surfaces[cid].state.hub
    for request in host.open_consents("p1"):
        subject = request
        interrupt = f"{subject['kind']}:{subject['id']}:{subject['revision']}:p1"
        response = client.post(
            "/v1/agent/answers", json={"interrupt_id": interrupt, "consent": True}, headers=headers
        )
        assert response.status_code == 200, response.text
    need = next(iter(host.state.tasks))
    body = {"need_id": need, "ext": {"count": 2}}
    response = client.post("/v1/agent/offer", json=body, headers=headers)
    assert response.status_code == 200, response.text
    event = next(e for e in server.store.read(cid) if e["seq"] == response.json()["seq"])
    assert event["on_behalf_of"] == "p1"
    person = server.registry.hosted_for(cid, "p1")
    assert verify_envelope(event, person.agent_key.public_key()) == person.agent_kid
    assert event["sender"] == server.registry.hosted_for(cid, "p1").card_url
    assert event["payload"]["offer_id"] == response.json()["offer_id"]
    before = server.store.read(cid)
    steward = FakeSteward()
    host.steward = steward
    for ext, error in [
        ({"count": "bad"}, "schema_invalid"),
        ({"secret": "PRIVATE-OFFER-CANARY"}, "private_extension"),
    ]:
        response = client.post("/v1/agent/offer", json={**body, "ext": ext}, headers=headers)
        assert response.status_code == 422 and response.json()["error"] == error
    assert server.store.read(cid) == before and steward.calls == []
    assert "PRIVATE-VAULT-CANARY" not in caplog.text
    assert "PRIVATE-OFFER-CANARY" not in caplog.text
    assert "PRIVATE-OFFER-CANARY" not in json.dumps(host.view("p1"))
    assert "PRIVATE-OFFER-CANARY" not in str(hub.refusals)


def test_private_annotations_in_nested_references() -> None:
    schema = {
        "properties": {"rows": {"type": "array", "items": {"$ref": "#/$defs/row"}}},
        "$defs": {
            "row": {"anyOf": [{"type": "object"}, {"properties": {"secret": {"x-private": True}}}]}
        },
    }
    assert private_extension(schema, {"rows": [{"secret": "canary"}]})
    assert not private_extension(schema, {"rows": [{"public": "value"}]})
    assert not private_extension(schema, {"secret": "unrelated"})
