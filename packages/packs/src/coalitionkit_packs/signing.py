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
from .files import MAX_FILES

FORMAT = "coalitionkit-pack/v0"
SIG_FILE = "pack.sig"


@dataclass(frozen=True)
class PackSignature:
    kid: str
    pinned: bool  # True when the key came from the caller's trusted keys


def _fail(message: str) -> PackError:
    return PackError([Problem("signature", SIG_FILE, message)])


def pack_payload(root: Path) -> bytes:
    """The canonical bytes that are signed for the folder ``root``."""
    files: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise _fail(f"{rel} is a symbolic link")
        if path.is_dir() or rel == SIG_FILE:
            continue
        if len(files) >= MAX_FILES:
            raise _fail(f"more than {MAX_FILES} files")
        files[rel] = sha256_hex(path.read_bytes())
    return canonicalize({"format": FORMAT, "files": files})


def sign_pack(root: Path, private_key: Ed25519PrivateKey, kid: str) -> Path:
    """Write ``pack.sig`` for the folder and return its path."""
    document = {
        "format": FORMAT,
        "kid": kid,
        "public_key": public_key_to_jwk(private_key.public_key(), kid),
        "sig": sign_detached(pack_payload(root), private_key, kid),
    }
    target = root / SIG_FILE
    target.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    return target


def _read_sig(root: Path) -> dict[str, Any]:
    path = root / SIG_FILE
    if not path.is_file():
        raise _fail("the pack is not signed")
    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise _fail(f"not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or data.get("format") != FORMAT:  # pyright: ignore[reportUnknownMemberType]
        raise _fail("unknown signature format")
    if not isinstance(data.get("kid"), str) or not isinstance(data.get("sig"), str):  # pyright: ignore[reportUnknownMemberType]
        raise _fail("signature file needs kid and sig")
    return data  # pyright: ignore[reportUnknownVariableType]


def verify_pack(root: Path, trusted_keys: Mapping[str, Ed25519PublicKey]) -> PackSignature:
    """Verify the folder against a key the caller trusts, chosen by the signature's ``kid``."""
    data = _read_sig(root)
    kid: str = data["kid"]
    key = trusted_keys.get(kid)
    if key is None:
        raise _fail(f"no trusted key for kid {kid!r}")
    _verify(root, data, key, kid)
    return PackSignature(kid, pinned=True)


def verify_pack_embedded(root: Path) -> PackSignature:
    """Check integrity against the public key inside ``pack.sig``.

    This proves the files are those the key holder signed, not who the author is: the caller
    must compare the ``kid`` with a key it already trusts. A pack never loads on this alone.
    """
    data = _read_sig(root)
    try:
        key = jwk_to_public_key(data.get("public_key") or {})
    except SignatureError as exc:
        raise _fail(str(exc)) from exc
    _verify(root, data, key, data["kid"])
    return PackSignature(data["kid"], pinned=False)


def _verify(root: Path, data: dict[str, Any], key: Ed25519PublicKey, kid: str) -> None:
    try:
        verify_detached(data["sig"], pack_payload(root), key, expected_kid=kid)
    except SignatureError as exc:
        raise _fail(str(exc)) from exc
