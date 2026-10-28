# SPDX-License-Identifier: Apache-2.0
"""A verdict signed with Ed25519 and bound to the subject's event_id and revision."""

from __future__ import annotations

from typing import Annotated, Literal

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from coalitionkit_contracts import SignatureError, canonicalize, sign_detached, verify_detached

Action = Literal["allow", "redact", "block", "quarantine", "escalate"]
_Ulid = Annotated[str, StringConstraints(pattern=r"^[0-9A-HJKMNP-TV-Z]{26}$")]


class VerdictError(Exception):
    """The verdict does not verify, or is about a different subject or revision."""


class VerdictBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    #: Domain separator: a verdict signature can never be replayed as an envelope signature.
    kind: Literal["steward_verdict"] = "steward_verdict"
    coalition_id: _Ulid
    event_id: _Ulid
    revision: Annotated[int, Field(ge=1, le=2**53 - 1)]
    subject_kind: Literal["message", "artifact"]
    action: Action
    policy_id: str
    redact: list[str]
    explain: str
    model_audited: bool
    issued_at: str


class SignedVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    body: VerdictBody
    sig: str


def _payload(body: VerdictBody) -> bytes:
    return canonicalize(body.model_dump(mode="json"))


def sign_verdict(body: VerdictBody, private_key: Ed25519PrivateKey, kid: str) -> SignedVerdict:
    return SignedVerdict(body=body, sig=sign_detached(_payload(body), private_key, kid))


def verify_verdict(
    signed: SignedVerdict,
    public_key: Ed25519PublicKey,
    *,
    event_id: str,
    revision: int,
    expected_kid: str | None = None,
) -> VerdictBody:
    """Check the signature and that it covers this event and revision. Raises VerdictError."""
    try:
        verify_detached(signed.sig, _payload(signed.body), public_key, expected_kid=expected_kid)
    except SignatureError as exc:
        raise VerdictError(f"bad signature: {exc}") from exc
    if signed.body.event_id != event_id or signed.body.revision != revision:
        raise VerdictError(
            f"verdict covers {signed.body.event_id} r{signed.body.revision}, "
            f"not {event_id} r{revision}"
        )
    return signed.body
