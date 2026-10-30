# SPDX-License-Identifier: Apache-2.0
"""Admin emission uses the ordinary signed, validated host path."""

import httpx
import pytest
from test_server import CHARTER, Running
from test_server import running as running
from test_server import settings as settings

from coalitionkit_contracts import verify_envelope, verify_receipt
from coalitionkit_server.adapter import Document


async def test_host_events_authentication_and_refusal(running: Running) -> None:
    async with httpx.AsyncClient(base_url=running.base) as http:
        auth = {"Authorization": "Bearer admin-test"}
        created = (await http.post("/admin/coalitions", json=CHARTER, headers=auth)).json()
        path = f"/admin/coalitions/{created['coalition_id']}/host-events"
        body: Document = {"type": "need", "payload": {}}
        member = (
            await http.post(
                "/invitations/redeem", json={"invitation": created["invitations"][0]["invitation"]}
            )
        ).json()
        for headers in ({}, {"Authorization": "Bearer " + member["token"]}):
            assert (await http.post(path, json=body, headers=headers)).status_code == 401
        reply = await http.post(path, json=body, headers=auth)
        assert reply.status_code == 200
        refusal = reply.json()
        assert refusal["type"] == "coalition.error"
        assert refusal["payload"]["code"] == "schema_invalid"
        verify_envelope(refusal, running.state.key.public_key())
        assert (await http.post(path, json={"type": 1}, headers=auth)).status_code == 422
        assert (
            await http.post("/admin/coalitions/missing/host-events", json=body, headers=auth)
        ).status_code == 404
        reply = await http.post(
            path,
            json={"type": "charter", "payload": CHARTER, "scope": {"audience": "coalition"}},
            headers=auth,
        )
        result = reply.json()
        assert result["accepted"]["payload"]["revision"] == 2
        verify_envelope(result["accepted"], running.state.key.public_key())
        verify_receipt(
            result["receipt"], running.state.key.public_key(), accepted=result["accepted"]
        )


@pytest.mark.parametrize("scope", [None, {"audience": "host"}])
async def test_host_event_default_scope(running: Running, scope: dict[str, str] | None) -> None:
    async with httpx.AsyncClient(base_url=running.base) as http:
        auth = {"Authorization": "Bearer admin-test"}
        created = (await http.post("/admin/coalitions", json=CHARTER, headers=auth)).json()
        body = {"type": "charter", "payload": CHARTER, "scope": scope}
        response = await http.post(
            f"/admin/coalitions/{created['coalition_id']}/host-events", json=body, headers=auth
        )
        assert response.json()["accepted"]["scope"] == {"audience": "host"}
