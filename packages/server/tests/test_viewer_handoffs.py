# SPDX-License-Identifier: Apache-2.0
import asyncio

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from test_genesis import client, server_for, start

from coalitionkit_contracts import new_ulid
from coalitionkit_mcp.gateway import build_envelope
from coalitionkit_runtime.steward import FakeSteward, Verdict
from coalitionkit_surfaces import SurfaceHub
from coalitionkit_surfaces.frames import encode
from coalitionkit_vault.psi import Context, Requester, Responder

__all__ = ["client"]


@pytest.mark.parametrize("count_only", [False, True])
def test_hosted_result_is_private(client: TestClient, count_only: bool) -> None:
    created = start(client)
    server = server_for(client)
    cid = created["coalition_id"]
    server.registry.redeem(server.registry.issue(cid, "p2"), server.ports, None, None)
    hub: SurfaceHub = server.surfaces[cid].state.hub
    before = server.store.read(cid)
    steward = FakeSteward()
    server.hosts[cid].steward = steward
    key_a, key_b = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    context = Context(
        cid, "private-match", "p1", "p2", "count" if count_only else "overlap", new_ulid()
    )
    requester = Requester(
        context,
        ["only-a", "overlap-secret"],
        key_a,
        key_b.public_key(),
        on_result=server.vault_result_sink(cid, "p1", context.match_id),
    )
    responder = Responder(
        context,
        ["only-b", "overlap-secret"],
        key_b,
        key_a.public_key(),
        count_trusted=["p1"],
    )
    with pytest.raises(ValueError):
        server.vault_result_sink(cid, "not-hosted", context.match_id)
    result = requester.finish(responder.respond(requester.request(responder.setup())))
    assert result == (1 if count_only else ["overlap-secret"])
    own = "".join(encode(frame) for frame in hub.agent_session("p1").start())
    assert "vault_result" in own and "private-match" in own
    assert ("overlap-secret" in own) is (not count_only)
    assert "only-a" not in own and "only-b" not in own
    for viewer in ("p2", "steward"):
        other = "".join(encode(frame) for frame in hub.agent_session(viewer).start())
        feed = "".join(encode(frame) for frame in hub.feed_session(viewer).start())
        for secret in ("private-match", "overlap-secret", "only-a", "only-b", "vault_result"):
            assert secret not in other and secret not in feed
    assert server.store.read(cid) == before
    assert steward.calls == []


def test_dispatch_view_as(client: TestClient) -> None:
    created = start(client)
    assert client.get("/v1/view-as?participant=p1").status_code == 401
    response = client.get(
        "/v1/view-as?participant=p1",
        headers={"Authorization": "Bearer " + created["owner"]["token"]},
    )
    assert response.status_code == 200
    assert response.json()["messages"][0]["createSurface"]


def test_sender_refusal_handoff(client: TestClient) -> None:
    created = start(client)
    server = server_for(client)
    cid = created["coalition_id"]
    host = server.hosts[cid]
    host.steward = FakeSteward(Verdict("block", "test-policy"))
    person = server.registry.hosted_for(cid, "p1")
    event = build_envelope(
        person,
        cid,
        "coalition.leave",
        {"reason": "REFUSED-SECRET"},
        scope={"audience": "coalition"},
    )
    response = asyncio.run(server.accept(event, person.card_url))
    assert response["error"]["code"] == "steward_blocked"
    hub: SurfaceHub = server.surfaces[cid].state.hub
    own = "".join(encode(frame) for frame in hub.feed_session("p1").start())
    assert "steward_blocked" in own and "test-policy" in own
    assert "REFUSED-SECRET" not in own
    assert hub.refusals.get("p2", []) == []
