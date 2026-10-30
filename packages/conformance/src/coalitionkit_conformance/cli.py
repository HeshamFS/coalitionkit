# SPDX-License-Identifier: Apache-2.0
"""Command line entry point. JSON on stdout; the readable table on stderr."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from .operator import ReferenceOperator
from .report import exit_code
from .runner import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Coalition Protocol conformance probes")
    parser.add_argument("--target", required=True, help="Signed agent card URL")
    parser.add_argument("--level", choices=["member", "vault", "host", "surface"], required=True)
    parser.add_argument("--invite", action="append", default=[], help="Operator invitation code")
    parser.add_argument("--invites-file", type=Path, help="UTF-8 file, one invitation per line")
    parser.add_argument(
        "--redeem-url", help="Operator endpoint accepting invitation and inline card"
    )
    parser.add_argument("--operator", choices=["reference"])
    parser.add_argument("--admin-token-file", type=Path)
    parser.add_argument("--key", type=Path, help="Unencrypted Ed25519 PKCS8 PEM report signing key")
    parser.add_argument("--timeout", type=float, default=20, help="HTTP timeout in seconds")
    args = parser.parse_args(argv)
    try:
        if bool(args.operator) != bool(args.admin_token_file):
            raise ValueError(
                "--operator reference and --admin-token-file must be supplied together"
            )
        operator = (
            ReferenceOperator(
                args.target, args.admin_token_file.read_text(encoding="utf-8"), args.timeout
            )
            if args.operator
            else None
        )
        invites: list[str] = list(args.invite)
        if args.invites_file:
            invites.extend(
                s.strip()
                for s in args.invites_file.read_text(encoding="utf-8").splitlines()
                if s.strip()
            )
        key = None
        if args.key:
            loaded = load_pem_private_key(args.key.read_bytes(), password=None)
            if not isinstance(loaded, Ed25519PrivateKey):
                raise ValueError("--key must contain an Ed25519 private key")
            key = loaded
        if args.timeout <= 0:
            raise ValueError("--timeout must be positive")
        report = asyncio.run(
            run(
                args.target,
                args.level,
                invites,
                redeem_url=args.redeem_url,
                key=key,
                timeout=args.timeout,
                operator=operator,
            )
        )
    except (OSError, ValueError) as exc:
        print(f"conformance: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    print("ID    STATUS   TITLE", file=sys.stderr)
    for test in report["tests"]:
        print(f"{test['id']}  {test['status']:<8} {test['title']}", file=sys.stderr)
        if test.get("reason"):
            print("  " + test["reason"], file=sys.stderr)
    return exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
