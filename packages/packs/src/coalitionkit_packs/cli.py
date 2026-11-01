# SPDX-License-Identifier: Apache-2.0
"""Pack validation, signing, evaluation and isolated connectors.

Exit 0 ok, 1 failed, 2 bad usage.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from contextlib import ExitStack
from pathlib import Path
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from coalitionkit_contracts import SignatureError
from coalitionkit_contracts.owner import jwk_to_public_key
from coalitionkit_surfaces import load_catalog

from .errors import PackError
from .files import take_snapshot
from .loader import inspect_pack
from .signing import sign_pack, verify_pack, verify_pack_embedded


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="coalitionkit-pack", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    connectors = sub.add_parser("connectors", help="print or isolate pack connectors")
    connectors.add_argument("directory", type=Path)
    connectors.add_argument("--host", required=True)
    connectors.add_argument("--coalition", required=True)
    connectors.add_argument("--run", action="store_true")
    connectors.add_argument("--image", default="python:3.15-slim")
    evaluate = sub.add_parser("eval", help="run scripted pack scenarios on a host")
    evaluate.add_argument("directory", type=Path)
    evaluate.add_argument("--live", action="store_true")
    evaluate.add_argument("--require-live", action="store_true")
    evaluate.add_argument("--json", action="store_true")
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
    if args.command == "connectors":
        return run_connectors(args)
    if args.command == "eval":
        runner = importlib.import_module("coalitionkit_acceptance.pack_evals")
        return runner.command(
            directory,
            live=args.live or args.require_live,
            require_live=args.require_live,
            as_json=args.json,
        )
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


def connector_environment() -> dict[str, str]:
    """The container launcher gets no ambient host configuration or credentials."""
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP"}
    return {key: value for key, value in os.environ.items() if key.upper() in allowed}


def connector_command(
    image: str, folder: Path, name: str, command: list[str], invitation: str
) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--user=65534:65534",
        "--pids-limit=64",
        "--memory=256m",
        "--cpus=1",
        "--mount",
        f"type=bind,source={folder},target=/pack,readonly",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=32m,mode=1777",
        "--workdir",
        f"/pack/connectors/{name}",
        "--entrypoint",
        "/usr/bin/env",
        image,
        "-i",
        "PATH=/usr/local/bin:/usr/bin:/bin",
        "HOME=/tmp",
        "TMPDIR=/tmp",
        *command,
        invitation,
    ]


def run_connectors(args: argparse.Namespace) -> int:
    pack = inspect_pack(args.directory)
    for connector in pack.manifest.connectors or []:
        print(
            json.dumps(
                {
                    "name": connector.name,
                    "command": connector.command,
                    "cwd": f"connectors/{connector.name}",
                }
            )
        )
    if not args.run:
        return 0
    env = connector_environment()
    probe = subprocess.run(["docker", "info"], env=env, capture_output=True, check=False)
    if probe.returncode:
        raise ValueError("connector isolation unavailable: Docker engine is required")
    # The operator credential is used only by this parent, never passed to the child.
    token = os.environ.get("COALITIONKIT_ADMIN_TOKEN", "")
    processes: list[tuple[str, subprocess.Popen[bytes]]] = []
    with ExitStack() as directories:
        try:
            for connector in pack.manifest.connectors or []:
                request = Request(
                    args.host.rstrip("/") + "/admin/coalitions/" + args.coalition + "/connectors",
                    data=json.dumps(
                        {
                            "pack": {"name": pack.name, "version": pack.manifest.version},
                            "connector": connector.name,
                        }
                    ).encode(),
                    headers={
                        "Authorization": "Bearer " + token,
                        "Content-Type": "application/json",
                    },
                )
                with urlopen(request, timeout=30) as response:
                    invitation = json.load(response)["invitation"]
                temporary = directories.enter_context(tempfile.TemporaryDirectory())
                folder = Path(temporary) / "pack"
                # The bounded snapshot rejects links, junctions and escaping paths.
                for relative, data in take_snapshot(pack.root).files.items():
                    target = folder / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                work = folder / "connectors" / connector.name
                work.mkdir(parents=True, exist_ok=True)
                process = subprocess.Popen(
                    connector_command(
                        args.image, folder, connector.name, connector.command, invitation
                    ),
                    env=env,
                    cwd=work,
                )
                processes.append((connector.name, process))
            failed = False
            for name, process in processes:
                code = process.wait()
                if code:
                    print(f"connector {name} refused or exited: {code}", file=sys.stderr)
                    failed = True
            return int(failed)
        finally:
            for _, process in processes:
                if process.poll() is None:
                    process.terminate()
                    process.wait()


if __name__ == "__main__":
    sys.exit(main())
