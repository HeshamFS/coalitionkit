# SPDX-License-Identifier: Apache-2.0
"""Owner-signed consent: ``consent_sig`` on ``coalition.decide`` (ADR 018).

The signature is a compact JWS (detached payload) by the OWNER key over the JCS form of
``{coalition_id, participant, subject, choice, consent, decided_at}``. The agent's envelope
signature alone never makes a decision count: ``verify_decision`` needs both keys.
``participant`` is the envelope's ``on_behalf_of``, so a consent cannot be replayed as
another participant's.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .canonical import canonicalize, envelope_dict
from .envelope import Envelope
from .signing import SignatureError, sign_detached, verify_detached, verify_envelope

CONSENT_FIELDS: tuple[str, ...] = (
    "coalition_id",
    "participant",
    "subject",
    "choice",
    "consent",
    "decided_at",
)


def consent_payload(coalition_id: str, decide: Mapping[str, Any], *, participant: str) -> bytes:
    """The JCS bytes the owner signs. ``decide`` is a ``coalition.decide`` payload."""
    if not participant:
        raise SignatureError("consent has no participant")
    data: dict[str, Any] = {"coalition_id": coalition_id, "participant": participant}
    for field in CONSENT_FIELDS[2:]:
        if field not in decide:
            raise SignatureError(f"decision has no {field}")
        data[field] = decide[field]
    return canonicalize(data)


def sign_consent(
    coalition_id: str,
    decide: Mapping[str, Any],
    owner_key: Ed25519PrivateKey,
    kid: str,
    *,
    participant: str,
) -> str:
    """The ``consent_sig`` value for a decision (any ``consent_sig`` already in it is ignored)."""
    return sign_detached(
        consent_payload(coalition_id, decide, participant=participant), owner_key, kid
    )


def verify_consent(
    coalition_id: str,
    decide: Mapping[str, Any],
    owner_public_key: Ed25519PublicKey,
    *,
    participant: str,
    expected_kid: str | None = None,
) -> str:
    """Verify ``decide['consent_sig']`` against the pinned OWNER key only. Returns the kid."""
    return verify_detached(
        decide.get("consent_sig"),
        consent_payload(coalition_id, decide, participant=participant),
        owner_public_key,
        expected_kid=expected_kid,
    )


def verify_decision(
    envelope: Envelope | Mapping[str, Any],
    agent_public_key: Ed25519PublicKey,
    owner_public_key: Ed25519PublicKey,
) -> None:
    """A decision counts only when the agent signed the envelope AND the owner signed the consent.

    Raises SignatureError otherwise.
    """
    data = envelope_dict(envelope)
    if data.get("type") != "coalition.decide":
        raise SignatureError("not a coalition.decide envelope")
    verify_envelope(data, agent_public_key)
    payload: Any = data.get("payload")
    if not isinstance(payload, Mapping):
        raise SignatureError("decision has no payload")
    participant = data.get("on_behalf_of")
    if not isinstance(participant, str) or not participant:
        raise SignatureError("decision has no on_behalf_of")
    verify_consent(
        str(data.get("coalition_id")),
        payload,  # pyright: ignore[reportUnknownArgumentType]
        owner_public_key,
        participant=participant,
    )
