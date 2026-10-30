# SPDX-License-Identifier: Apache-2.0
"""Operator enrollment adapter and signed protocol messages; no server internals."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from a2a.types import AgentCapabilities, AgentCard, AgentInterface
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from google.protobuf.json_format import MessageToDict

from coalitionkit_contracts import (
    new_ulid,
    public_key_to_jwk,
    sign_consent,
    sign_envelope,
    sign_owner_proof,
)
from coalitionkit_edges.a2a.client import MemberClient
from coalitionkit_edges.a2a.identity import CardKey, coalition_extension, sign_card

Document = dict[str, Any]


@dataclass
class Participant:
    client: MemberClient
    key: Ed25519PrivateKey
    owner: Ed25519PrivateKey
    coalition: str
    participant: str
    card_url: str
    token: str = ""

    def event(self, kind: str, payload: Document, scope: Document | None = None) -> Document:
        event: Document = {
            "ext_version": "0.1",
            "coalition_id": self.coalition,
            "event_id": new_ulid(),
            "type": "coalition." + kind,
            "sender": self.card_url,
            "on_behalf_of": self.participant,
            "scope": scope or {"audience": "coalition"},
            "payload": payload,
        }
        event["sig"] = sign_envelope(event, self.key, "agent")
        return event

    def decision(
        self,
        revision: int = 1,
        *,
        kind: str = "charter",
        identifier: str | None = None,
        consent: bool = True,
        choice: str | None = None,
    ) -> Document:
        identifier = identifier or self.coalition
        body: Document = {
            "subject": {"kind": kind, "id": identifier, "revision": revision},
            "choice": choice or identifier,
            "consent": consent,
            "decided_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
        body["consent_sig"] = sign_consent(
            self.coalition, body, self.owner, "owner", participant=self.participant
        )
        return self.event("decide", body)

    async def view(self, http: httpx.AsyncClient, url: str) -> Document:
        async with http.stream(
            "GET", url, headers={"Authorization": "Bearer " + self.token}
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    frame = json.loads(line[6:])
                    if frame.get("type") == "STATE_SNAPSHOT":
                        snapshot: Document = frame["snapshot"]
                        return snapshot
        raise ValueError("feed ended without a state snapshot")

    def join(self) -> Document:
        jwk = public_key_to_jwk(self.owner.public_key(), "owner")
        return self.event(
            "join",
            {
                "card_url": self.card_url,
                "owner_key": jwk,
                "owner_proof": sign_owner_proof(
                    self.coalition, self.participant, self.card_url, jwk, self.owner
                ),
                "roles_requested": ["member"],
                "surfaces": [],
                "vault": "local",
            },
        )


def probe_card(url: str, key: Ed25519PrivateKey) -> AgentCard:
    return sign_card(
        AgentCard(
            name="Conformance participant",
            description="Protocol probe",
            version="0.1.0",
            supported_interfaces=[
                AgentInterface(url=url, protocol_binding="JSONRPC", protocol_version="1.0")
            ],
            capabilities=AgentCapabilities(
                extensions=[
                    coalition_extension(
                        {
                            "keys": [public_key_to_jwk(key.public_key(), "agent")],
                            "roles": ["member"],
                            "surfaces": [],
                            "vault": "local",
                        },
                        "Coalition protocol",
                    )
                ]
            ),
            default_input_modes=["application/json"],
            default_output_modes=["application/json"],
        ),
        key,
        "agent",
    )


async def enroll(
    http: httpx.AsyncClient, target: str, host: CardKey, invite: str, redeem_url: str
) -> Participant:
    key, owner = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    # The operator endpoint admits the inline signed card. This URL is an identity,
    # not a callback; tests requiring inbound delivery remain explicitly unavailable.
    url = "https://conformance.invalid/" + new_ulid()
    response = await http.post(
        redeem_url,
        json={
            "invitation": invite,
            "card_url": url,
            "card": MessageToDict(probe_card(url, key)),
        },
    )
    response.raise_for_status()
    body: Document = response.json()
    client = await MemberClient.connect(http, target, body["token"], host.public_key, host.kid)
    return Participant(
        client, key, owner, body["coalition_id"], body["participant"], url, body["token"]
    )
