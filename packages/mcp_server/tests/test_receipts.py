# SPDX-License-Identifier: Apache-2.0
"""Receipt-only writes succeed only with a valid configured-host receipt."""

from __future__ import annotations

from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_edges.a2a.host_port import FakeHost, HostSigner
from coalitionkit_mcp.errors import CoalitionToolError
from coalitionkit_mcp.gateway import send
from coalitionkit_mcp.testing_rig import C1, hosted


class ReceiptHost(FakeHost):
    mutation: str = ""

    async def accept(
        self, envelope_json: dict[str, Any], authenticated_sender: str
    ) -> dict[str, Any]:
        reply = await super().accept(envelope_json, authenticated_sender)
        receipt = reply["receipt"]
        if self.mutation == "signature":
            receipt["payload"]["seq"] += 1
        elif self.mutation == "coalition":
            receipt = self.signer.envelope(
                "01M4XRC1J00000000000000000",
                "coalition.receipt",
                {**receipt["payload"], "coalition_id": "01M4XRC1J00000000000000000"},
            )
        elif self.mutation == "missing":
            receipt = None
        return {"accepted": None, "receipt": receipt}


def port() -> ReceiptHost:
    return ReceiptHost(
        HostSigner("https://host.example/card", Ed25519PrivateKey.generate(), "host")
    )


async def test_receipt_only_write_returns_submitted_id_and_sequence() -> None:
    host = port()
    result = await send(host, hosted("p1"), C1, "coalition.leave", {})
    assert result == {"event_id": host.accepted[0]["event_id"], "seq": 1}


@pytest.mark.parametrize("mutation", ["signature", "coalition", "missing"])
async def test_invalid_receipt_is_not_success(mutation: str) -> None:
    host = port()
    host.mutation = mutation
    with pytest.raises(CoalitionToolError, match="bad_signature"):
        await send(host, hosted("p1"), C1, "coalition.leave", {})
