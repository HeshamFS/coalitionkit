# SPDX-License-Identifier: Apache-2.0
"""Author signatures over a whole pack folder (Ed25519, JCS bytes, detached compact JWS).

``pack.sig`` is JSON: ``{format, kid, public_key, sig}``. The signed payload is the JCS form of
``{format, files}`` where ``files`` maps every other file in the folder (POSIX path) to its
SHA-256. Adding, removing or editing any file breaks the signature.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from coalitionkit_contracts import (
    SignatureError,
    canonicalize,
    sha256_hex,
    sign_detached,
    verify_detached,
)
from coalitionkit_contracts.owner import jwk_to_public_key, public_key_to_jwk

from .errors import PackError, Problem
from .files import SIG_FILE, Snapshot, take_snapshot

FORMAT = "coalitionkit-pack/v0"


@dataclass(frozen=True)
class PackSignature:
    kid: str
    pinned: bool  # True when the key came from the caller's trusted keys


def _fail(message: str) -> PackError:
    return PackError([Problem("signature", SIG_FILE, message)])


def snapshot_payload(snap: Snapshot) -> bytes:
    """The canonical bytes that are signed: the hash of every file except ``pack.sig``."""
    files = {rel: sha256_hex(data) for rel, data in sorted(snap.files.items()) if rel != SIG_FILE}
    return canonicalize({"format": FORMAT, "files": files})


def pack_payload(root: Path) -> bytes:
    return snapshot_payload(take_snapshot(root))


def sign_pack(root: Path, private_key: Ed25519PrivateKey, kid: str) -> Path:
    """Write ``pack.sig`` for the folder and return its path."""
    snap = take_snapshot(root)
    document = {
        "format": FORMAT,
        "kid": kid,
        "public_key": public_key_to_jwk(private_key.public_key(), kid),
        "sig": sign_detached(snapshot_payload(snap), private_key, kid),
    }
    target = snap.root / SIG_FILE
    target.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    return target


def _read_sig(snap: Snapshot) -> dict[str, Any]:
    raw = snap.files.get(SIG_FILE)
    if raw is None:
        raise _fail("the pack is not signed")
    try:
        data: Any = json.loads(raw.decode("utf-8"))
    except ValueError as exc:
        raise _fail(f"not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or data.get("format") != FORMAT:  # pyright: ignore[reportUnknownMemberType]
        raise _fail("unknown signature format")
    if not isinstance(data.get("kid"), str) or not isinstance(data.get("sig"), str):  # pyright: ignore[reportUnknownMemberType]
        raise _fail("signature file needs kid and sig")
    return data  # pyright: ignore[reportUnknownVariableType]


def verify_snapshot(snap: Snapshot, trusted_keys: Mapping[str, Ed25519PublicKey]) -> PackSignature:
    """Verify exactly the bytes in ``snap`` against a key the caller trusts (by ``kid``)."""
    data = _read_sig(snap)
    kid: str = data["kid"]
    key = trusted_keys.get(kid)
    if key is None:
        raise _fail(f"no trusted key for kid {kid!r}")
    _verify(snap, data, key, kid)
    return PackSignature(kid, pinned=True)


def verify_pack(root: Path, trusted_keys: Mapping[str, Ed25519PublicKey]) -> PackSignature:
    return verify_snapshot(take_snapshot(root), trusted_keys)


def verify_pack_embedded(root: Path) -> PackSignature:
    """Check integrity against the public key inside ``pack.sig``.

    This proves the files are those the key holder signed, not who the author is: the caller
    must compare the ``kid`` with a key it already trusts. A pack never loads on this alone.
    """
    snap = take_snapshot(root)
    data = _read_sig(snap)
    try:
        key = jwk_to_public_key(data.get("public_key") or {})
    except SignatureError as exc:
        raise _fail(str(exc)) from exc
    _verify(snap, data, key, data["kid"])
    return PackSignature(data["kid"], pinned=False)


def _verify(snap: Snapshot, data: dict[str, Any], key: Ed25519PublicKey, kid: str) -> None:
    try:
        verify_detached(data["sig"], snapshot_payload(snap), key, expected_kid=kid)
    except SignatureError as exc:
        raise _fail(str(exc)) from exc
