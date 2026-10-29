# SPDX-License-Identifier: Apache-2.0
"""A member's keys and its signed Agent Card with the CoalitionKit extension."""

from __future__ import annotations

from dataclasses import dataclass, field

from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_contracts import public_key_to_jwk
from coalitionkit_edges.a2a import (
    ENVELOPE_MEDIA_TYPE,
    card_key_entry,
    coalition_extension,
    sign_card,
)
from coalitionkit_edges.a2a.server import CARD_PATH, RPC_PATH


@dataclass
class MemberIdentity:
    """One participant: the agent key signs envelopes and the card, the owner key signs consent."""

    name: str
    base_url: str
    agent_key: Ed25519PrivateKey = field(default_factory=Ed25519PrivateKey.generate)
    owner_key: Ed25519PrivateKey = field(default_factory=Ed25519PrivateKey.generate)

    @property
    def agent_kid(self) -> str:
        return f"{self.name}-agent-1"

    @property
    def owner_kid(self) -> str:
        return f"{self.name}-owner-1"

    @property
    def card_url(self) -> str:
        return self.base_url.rstrip("/") + CARD_PATH

    def owner_jwk(self) -> dict[str, str]:
        return public_key_to_jwk(self.owner_key.public_key(), self.owner_kid)

    def build_card(self, framework: str, model: str) -> AgentCard:
        """The member's card: JSON-RPC at 1.0, the extension declared, signed with the agent key."""
        key = card_key_entry(self.agent_key.public_key(), self.agent_kid)
        params = {"roles": ["member"], "vault": "local", "surfaces": [], "keys": [key]}
        card = AgentCard(
            name=f"{self.name} member agent",
            description=f"A Coalition member agent built on {framework}, model {model}",
            version="0.1.0",
            supported_interfaces=[
                AgentInterface(
                    url=self.base_url.rstrip("/") + RPC_PATH,
                    protocol_binding="JSONRPC",
                    protocol_version="1.0",
                )
            ],
            capabilities=AgentCapabilities(
                streaming=False,
                extensions=[coalition_extension(params, "Takes part in multi-party Coalitions")],
            ),
            default_input_modes=[ENVELOPE_MEDIA_TYPE],
            default_output_modes=["text/plain"],
            skills=[
                AgentSkill(
                    id="coalition-member",
                    name="Coalition member",
                    description="Joins Coalitions, offers, answers its vault and commits",
                    tags=["coalition", framework],
                )
            ],
        )
        return sign_card(card, self.agent_key, self.agent_kid)
