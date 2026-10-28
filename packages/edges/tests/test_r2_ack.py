# SPDX-License-Identifier: Apache-2.0
"""R2 acknowledgement forms cross the real A2A connection unchanged."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from coalitionkit_edges.a2a import EdgeCallError, FakeHost

if TYPE_CHECKING:
    from conftest import Rig, Signed


@pytest.mark.parametrize("form", ["projection", "receipt_only", "forged", "wrong_hash"])
async def test_acknowledgement_forms(
    rig: Rig, signed: Signed, monkeypatch: pytest.MonkeyPatch, form: str
) -> None:
    original = FakeHost.accept

    async def respond(host: FakeHost, envelope: dict[str, Any], sender: str) -> dict[str, Any]:
        reply = await original(host, envelope, sender)
        event = reply["accepted"]
        if form == "receipt_only":
            reply["accepted"] = None
            return reply
        source = {
            name: event[name] for name in ("event_id", "seq", "type", "on_behalf_of", "prev_hash")
        }
        source["hash"] = reply["receipt"]["payload"]["head_hash"]
        if form == "wrong_hash":
            source["hash"] = "0" * 64
        projected = host.signer.envelope(
            event["coalition_id"], "coalition.projection", {"source": source, "payload": {}}
        )
        if form == "forged":
            projected["payload"]["payload"]["forged"] = True
        reply["accepted"] = projected
        return reply

    monkeypatch.setattr(FakeHost, "accept", respond)
    if form in {"forged", "wrong_hash"}:
        with pytest.raises(EdgeCallError, match="does not verify"):
            await rig.client.send(signed())
    else:
        ack = await rig.client.send(signed())
        if form == "receipt_only":
            assert ack.accepted is None
        else:
            assert ack.accepted is not None
            assert ack.accepted["type"] == "coalition.projection"
        assert ack.receipt["type"] == "coalition.receipt"
