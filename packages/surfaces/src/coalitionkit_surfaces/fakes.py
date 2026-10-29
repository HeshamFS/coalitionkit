# SPDX-License-Identifier: Apache-2.0
"""Test doubles for the ports: a manual clock, a token table and a signer holding both keys."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_contracts import new_ulid, sign_consent, sign_envelope

from .frames import Document


@dataclass
class FakeClock:
    now: float = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@dataclass
class FakeViewerAuth:
    tokens: dict[str, str] = field(default_factory=lambda: dict[str, str]())

    def viewer_for(self, token: str) -> str | None:
        return self.tokens.get(token)


@dataclass
class FakeOwnerSigner:
    """Builds a ``coalition.decide`` the way a person's device would: owner key signs consent."""

    coalition_id: str
    participant: str
    card_url: str
    agent_key: Ed25519PrivateKey
    agent_kid: str
    owner_key: Ed25519PrivateKey
    owner_kid: str
    decided_at: Callable[[], str] = lambda: "2026-10-28T12:00:00+00:00"
    sign_consent_with_agent_key: bool = False
    calls: list[tuple[Document, str, bool]] = field(
        default_factory=lambda: list[tuple[Document, str, bool]]()
    )

    def sign_decision(self, subject: Document, choice: str, consent: bool) -> Document:
        self.calls.append((subject, choice, consent))
        body: Document = {
            "subject": dict(subject),
            "choice": choice,
            "consent": consent,
            "decided_at": self.decided_at(),
        }
        key, kid = (
            (self.agent_key, self.agent_kid)
            if self.sign_consent_with_agent_key
            else (self.owner_key, self.owner_kid)
        )
        body["consent_sig"] = sign_consent(
            self.coalition_id, body, key, kid, participant=self.participant
        )
        envelope: Document = {
            "ext_version": "0.1",
            "coalition_id": self.coalition_id,
            "event_id": new_ulid(),
            "type": "coalition.decide",
            "sender": self.card_url,
            "on_behalf_of": self.participant,
            "scope": {"audience": "coalition"},
            "payload": body,
        }
        envelope["sig"] = sign_envelope(envelope, self.agent_key, self.agent_kid)
        return envelope
