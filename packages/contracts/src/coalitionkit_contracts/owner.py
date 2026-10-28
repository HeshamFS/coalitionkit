# SPDX-License-Identifier: Apache-2.0
"""The owner key bound to a participant at join (``owner_key`` and ``owner_proof``, ADR 018).

``owner_proof`` is a compact JWS (detached payload) made with the OWNER key over the JCS form of
``{coalition_id, participant, card_url, owner_key}``. The host pins the key it verifies there.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
from collections.abc import Mapping
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .canonical import canonicalize, envelope_dict
from .envelope import Envelope
from .signing import SignatureError, sign_detached, verify_detached


def public_key_to_jwk(key: Ed25519PublicKey, kid: str) -> dict[str, str]:
    """An Ed25519 public key as the JWK shape of ``common.json#/$defs/ed25519_jwk``."""
    x = base64.urlsafe_b64encode(key.public_bytes_raw()).rstrip(b"=").decode("ascii")
    return {"kty": "OKP", "crv": "Ed25519", "x": x, "kid": kid}


def jwk_to_public_key(jwk: Mapping[str, Any]) -> Ed25519PublicKey:
    """The public key in an Ed25519 JWK. Raises SignatureError when it is not one."""
    if (
        jwk.get("kty") != "OKP"
        or jwk.get("crv") != "Ed25519"
        or not isinstance(jwk.get("kid"), str)
    ):
        raise SignatureError("owner_key must be an Ed25519 JWK with a kid")
    x = jwk.get("x")
    if not isinstance(x, str):
        raise SignatureError("owner_key has no x")
    try:
        raw = base64.b64decode(x + "=" * (-len(x) % 4), altchars=b"-_", validate=True)
        return Ed25519PublicKey.from_public_bytes(raw)
    except (binascii.Error, ValueError) as exc:
        raise SignatureError("owner_key x is not a valid Ed25519 key") from exc


class OwnerKeyConflictError(ValueError):
    """The owner key is already pinned to another participant (wire error ``not_authorized``)."""


def jwk_thumbprint(jwk: Mapping[str, Any]) -> str:
    """RFC 7638 SHA-256 thumbprint (base64url, no padding) of an Ed25519 (OKP) JWK."""
    jwk_to_public_key(jwk)
    members = {"crv": jwk["crv"], "kty": jwk["kty"], "x": jwk["x"]}
    digest = hashlib.sha256(canonicalize(members)).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def check_owner_key_unique(
    pinned: Mapping[str, str], participant: str, owner_key_thumbprint: str
) -> None:
    """Raise when this owner key is already pinned to a different participant.

    ``pinned`` maps participant ID to the thumbprint of its pinned owner key, for one Coalition.
    """
    for other, thumbprint in pinned.items():
        if other != participant and thumbprint == owner_key_thumbprint:
            raise OwnerKeyConflictError(f"owner key is already pinned to participant {other}")


def owner_proof_payload(
    coalition_id: str, participant: str, card_url: str, owner_key: Mapping[str, Any]
) -> bytes:
    return canonicalize(
        {
            "coalition_id": coalition_id,
            "participant": participant,
            "card_url": card_url,
            "owner_key": dict(owner_key),
        }
    )


def sign_owner_proof(
    coalition_id: str,
    participant: str,
    card_url: str,
    owner_key: Mapping[str, Any],
    owner_private_key: Ed25519PrivateKey,
) -> str:
    """The ``owner_proof`` for a join; the JWS kid is the JWK's kid."""
    payload = owner_proof_payload(coalition_id, participant, card_url, owner_key)
    return sign_detached(payload, owner_private_key, str(owner_key["kid"]))


def verify_owner_proof(
    join: Envelope | Mapping[str, Any], *, agent_public_key: Ed25519PublicKey | None = None
) -> Ed25519PublicKey:
    """Check a ``coalition.join`` envelope's owner proof and return the key to pin.

    The proof must verify under the key it carries, bind this Coalition, participant (the
    envelope's ``on_behalf_of``) and card, and the owner key must not be the agent's own key.
    Raises SignatureError on any failure.
    """
    data = envelope_dict(join)
    body: Any = data.get("payload")
    if data.get("type") != "coalition.join" or not isinstance(body, Mapping):
        raise SignatureError("not a coalition.join envelope")
    payload: Mapping[str, Any] = body  # pyright: ignore[reportUnknownVariableType]
    jwk: Any = payload.get("owner_key")
    if not isinstance(jwk, Mapping):
        raise SignatureError("join has no owner_key")
    owner_jwk: Mapping[str, Any] = jwk  # pyright: ignore[reportUnknownVariableType]
    key = jwk_to_public_key(owner_jwk)
    signed = owner_proof_payload(
        str(data.get("coalition_id")),
        str(data.get("on_behalf_of")),
        str(payload.get("card_url")),
        owner_jwk,
    )
    verify_detached(payload.get("owner_proof"), signed, key, expected_kid=str(owner_jwk["kid"]))
    if (
        agent_public_key is not None
        and key.public_bytes_raw() == agent_public_key.public_bytes_raw()
    ):
        raise SignatureError("the owner key must differ from the agent key")
    return key
