# SPDX-License-Identifier: Apache-2.0
"""Fixtures: a host app under uvicorn on a real port, a member identity and a connected client."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
import pytest
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from examples import make_envelope

from coalitionkit_contracts import new_ulid, public_key_to_jwk, sign_envelope
from coalitionkit_edges.a2a import (
    ENVELOPE_MEDIA_TYPE,
    CredentialRegistry,
    FakeHost,
    HostSigner,
    MemberClient,
    card_key_entry,
    coalition_extension,
    create_host_app,
    sign_card,
)
from coalitionkit_edges.a2a.testing import RunningServer, free_port

MEMBER_URL = "https://agents.example.org/p2/card.json"
TOKEN = "member-token-1"
HOST_KID = "host-key-1"


@dataclass
class Member:
    card_url: str
    key: Ed25519PrivateKey
    kid: str
    owner_key: Ed25519PrivateKey
    owner_kid: str

    def owner_jwk(self) -> dict[str, str]:
        return public_key_to_jwk(self.owner_key.public_key(), self.owner_kid)


@dataclass
class Rig:
    server: RunningServer
    host: FakeHost
    signer: HostSigner
    credentials: CredentialRegistry
    http: httpx.AsyncClient
    client: MemberClient
    member: Member

    @property
    def rpc_url(self) -> str:
        return f"{self.server.base_url}/a2a"


@pytest.fixture
def member() -> Member:
    return Member(
        MEMBER_URL,
        Ed25519PrivateKey.generate(),
        "member-key-1",
        Ed25519PrivateKey.generate(),
        "owner-1",
    )


@pytest.fixture
def host_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


@pytest.fixture
async def rig(member: Member, host_key: Ed25519PrivateKey) -> AsyncIterator[Rig]:
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    signer = HostSigner(f"{base}/.well-known/agent-card.json", host_key, HOST_KID)
    credentials = CredentialRegistry()
    credentials.add(TOKEN, member.card_url)
    host = FakeHost(signer)
    app = create_host_app(host, signer, credentials, base)
    with RunningServer(app, port) as server:
        async with httpx.AsyncClient() as http:
            client = await MemberClient.connect(
                http, signer.card_url, TOKEN, host_key.public_key(), HOST_KID
            )
            yield Rig(server, host, signer, credentials, http, client, member)


Signed = Callable[..., dict[str, Any]]


@pytest.fixture
def signed(member: Member) -> Signed:
    """Build a schema-valid envelope from the member, signed with its agent key."""

    def build(message_type: str = "coalition.offer", **overrides: Any) -> dict[str, Any]:
        fields: dict[str, Any] = {"sender": member.card_url, "event_id": new_ulid(), **overrides}
        envelope = make_envelope(message_type, **fields)
        envelope["sig"] = sign_envelope(envelope, member.key, member.kid)
        return envelope

    return build


MakeCard = Callable[..., AgentCard]


@pytest.fixture
def make_card(member: Member) -> MakeCard:
    """Build a member's Agent Card. Options cover each way a card can be bad."""

    def build(
        *,
        sign: bool = True,
        publish_key: bool = True,
        not_after: datetime | None = None,
        extra_header: dict[str, Any] | None = None,
        kid: str | None = None,
    ) -> AgentCard:
        key_kid = kid or member.kid
        keys = [card_key_entry(member.key.public_key(), key_kid, not_after)] if publish_key else []
        card = AgentCard(
            name="Member agent",
            description="A member of Coalitions",
            version="0.1.0",
            supported_interfaces=[
                AgentInterface(
                    url="https://agents.example.org/p2/a2a",
                    protocol_binding="JSONRPC",
                    protocol_version="1.0",
                )
            ],
            capabilities=AgentCapabilities(
                extensions=[
                    coalition_extension(
                        {"roles": ["member"], "vault": "local", "keys": keys}, "Takes part"
                    )
                ]
            ),
            default_input_modes=[ENVELOPE_MEDIA_TYPE],
            default_output_modes=[ENVELOPE_MEDIA_TYPE],
            skills=[AgentSkill(id="member", name="Member", description="Member", tags=["x"])],
        )
        return sign_card(card, member.key, key_kid, extra_header) if sign else card

    return build
