# SPDX-License-Identifier: Apache-2.0
"""``coalitionkit-pack validate|sign|verify <dir>``. Exit 0 ok, 1 pack refused, 2 bad usage."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from coalitionkit_contracts import SignatureError
from coalitionkit_contracts.owner import jwk_to_public_key
from coalitionkit_surfaces import load_catalog

from .errors import PackError
from .loader import inspect_pack
from .signing import sign_pack, verify_pack, verify_pack_embedded


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="coalitionkit-pack", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("validate", help="check every pack rule (signature not required)")
    check.add_argument("directory", type=Path)
    check.add_argument("--catalog", type=Path, help="core catalog JSON (surfaces format)")
    check.add_argument("--core-version", help="core version to test the pack's range against")
    sign = sub.add_parser("sign", help="write pack.sig with an Ed25519 key (PKCS8 PEM)")
    sign.add_argument("directory", type=Path)
    sign.add_argument("--key", type=Path, required=True)
    sign.add_argument("--kid", required=True)
    verify = sub.add_parser("verify", help="verify pack.sig")
    verify.add_argument("directory", type=Path)
    verify.add_argument("--trusted-key", type=Path, help="Ed25519 public JWK file to pin")
    return parser


def _private_key(path: Path) -> Ed25519PrivateKey:
    key = load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("the key file is not an Ed25519 private key")
    return key


def _trusted(path: Path) -> dict[str, Ed25519PublicKey]:
    jwk = json.loads(path.read_text(encoding="utf-8"))
    return {str(jwk["kid"]): jwk_to_public_key(jwk)}


def _run(args: argparse.Namespace) -> int:
    directory: Path = args.directory
    if args.command == "validate":
        catalog = load_catalog(args.catalog) if args.catalog else None
        pack = inspect_pack(directory, core_catalog=catalog, core_version=args.core_version)
        print(f"ok: {pack.name} {pack.manifest.version} is valid")
        return 0
    if args.command == "sign":
        target = sign_pack(directory, _private_key(args.key), args.kid)
        print(f"signed: wrote {target}")
        return 0
    if args.trusted_key:
        sig = verify_pack(directory, _trusted(args.trusted_key))
        print(f"ok: signature by trusted key {sig.kid}")
    else:
        sig = verify_pack_embedded(directory)
        print(f"ok: files match key {sig.kid} (author not pinned, use --trusted-key)")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return _run(args)
    except PackError as exc:
        for problem in exc.problems:
            print(f"refused: {problem}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, SignatureError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
