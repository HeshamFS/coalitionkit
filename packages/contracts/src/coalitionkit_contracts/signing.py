# SPDX-License-Identifier: Apache-2.0
"""Compact JWS (EdDSA / Ed25519) over an envelope, with the payload detached.

The signed bytes are the JCS form of the envelope without ``sig``, ``seq``, ``ts`` and
``prev_hash``. The token is ``<protected>..<signature>``: RFC 7515 Appendix F, the middle part
is empty because the verifier rebuilds it from the envelope. Keys are always passed in; nothing
here fetches a key.
"""

from __future__ import annotations

import base64
import binascii
import json
from collections.abc import Mapping
from typing import Any

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .canonical import canonicalize, envelope_dict
from .envelope import UNSIGNED_FIELDS, Envelope

ALG = "EdDSA"
TYP = "JOSE"


class SignatureError(Exception):
    """The signature is malformed or does not verify."""


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    try:
        return base64.b64decode(text + "=" * (-len(text) % 4), altchars=b"-_", validate=True)
    except (binascii.Error, ValueError) as exc:
        raise SignatureError("invalid base64url") from exc


def signing_payload(envelope: Envelope | Mapping[str, Any]) -> bytes:
    """The JCS bytes that are signed."""
    data = {k: v for k, v in envelope_dict(envelope).items() if k not in UNSIGNED_FIELDS}
    return canonicalize(data)


def protected_header(kid: str) -> str:
    """The base64url protected header: alg, typ ``JOSE`` and kid, in JCS form."""
    return _b64(rfc8785.dumps({"alg": ALG, "typ": TYP, "kid": kid}))


def sign_envelope(
    envelope: Envelope | Mapping[str, Any], private_key: Ed25519PrivateKey, kid: str
) -> str:
    """Sign an envelope and return the compact JWS to put in ``sig``."""
    header = protected_header(kid)
    signing_input = f"{header}.{_b64(signing_payload(envelope))}".encode("ascii")
    return f"{header}..{_b64(private_key.sign(signing_input))}"


def verify_envelope(
    envelope: Envelope | Mapping[str, Any],
    public_key: Ed25519PublicKey,
    *,
    expected_kid: str | None = None,
) -> str:
    """Verify ``envelope['sig']`` against ``public_key`` only. Returns the ``kid``.

    Raises SignatureError on any failure.
    """
    sig = envelope_dict(envelope).get("sig")
    if not isinstance(sig, str):
        raise SignatureError("envelope has no sig")
    parts = sig.split(".")
    if len(parts) != 3 or parts[1] != "":
        raise SignatureError("sig must be a compact JWS with a detached payload")
    header_b64, _, signature_b64 = parts
    try:
        header: Any = json.loads(_unb64(header_b64))
    except ValueError as exc:
        raise SignatureError("protected header is not JSON") from exc
    if not isinstance(header, dict) or set(header) != {"alg", "typ", "kid"}:  # pyright: ignore[reportUnknownArgumentType]
        raise SignatureError("protected header must hold exactly alg, typ and kid")
    if header["alg"] != ALG or header["typ"] != TYP or not isinstance(header["kid"], str):
        raise SignatureError("unsupported protected header")
    kid: str = header["kid"]
    if expected_kid is not None and kid != expected_kid:
        raise SignatureError("kid does not match the expected key")
    signing_input = f"{header_b64}.{_b64(signing_payload(envelope))}".encode("ascii")
    try:
        public_key.verify(_unb64(signature_b64), signing_input)
    except InvalidSignature as exc:
        raise SignatureError("signature does not verify") from exc
    return kid


def is_valid_signature(
    envelope: Envelope | Mapping[str, Any],
    public_key: Ed25519PublicKey,
    *,
    expected_kid: str | None = None,
) -> bool:
    try:
        verify_envelope(envelope, public_key, expected_kid=expected_kid)
    except SignatureError:
        return False
    return True
