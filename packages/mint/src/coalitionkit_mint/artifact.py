# SPDX-License-Identifier: Apache-2.0
"""Data-only artifacts, owner consent and local persistence."""

import hashlib
import json
import sqlite3
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from coalitionkit_contracts import canonicalize, public_key_to_jwk
from coalitionkit_contracts.signing import verify_detached

from .schema import Config, parse_config

VERSION = "1.0.0"


def digest(value: Any) -> str:
    return hashlib.sha256(canonicalize(value)).hexdigest()


@contextmanager
def connect(folder: Path) -> Generator[sqlite3.Connection]:
    db = sqlite3.connect(folder / "store.sqlite", timeout=10)
    db.execute("PRAGMA busy_timeout=10000")
    try:
        with db:
            yield db
    finally:
        db.close()


def generate(folder: Path, config: Config, owner: Ed25519PublicKey, owner_id: str) -> str:
    folder.mkdir(parents=True, exist_ok=False)
    data = config.model_dump(mode="json")
    manifest = {
        "artifact_id": uuid.uuid4().hex,
        "template": config.template,
        "version": VERSION,
        "config_hash": digest(data),
        "owner": public_key_to_jwk(owner, "owner"),
        "owner_id": owner_id,
    }
    (folder / "config.json").write_text(json.dumps(data), encoding="utf-8", newline="\n")
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8", newline="\n")
    with connect(folder) as db:
        db.executescript("""
            CREATE TABLE lifecycle (state TEXT NOT NULL, proof TEXT);
            INSERT INTO lifecycle VALUES ('pending', NULL);
            CREATE TABLE bookings (id TEXT PRIMARY KEY, start INTEGER, end INTEGER, state TEXT,
                                   nonce TEXT, revision INTEGER);
            CREATE TABLE reader_errors (field TEXT, error TEXT, observed REAL);
            CREATE TABLE readings (field TEXT, value REAL, observed REAL, confidence REAL);
            CREATE TABLE hold_requests (nonce TEXT PRIMARY KEY, arguments TEXT, expires REAL);
            CREATE TABLE consumed_proofs (signature TEXT PRIMARY KEY);
        """)
    return digest(manifest)


def load(folder: Path) -> tuple[Config, dict[str, Any], str]:
    manifest: dict[str, Any] = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    config = parse_config((folder / "config.json").read_text(encoding="utf-8"))
    if (
        manifest["version"] != VERSION
        or manifest["template"] != config.template
        or manifest["config_hash"] != digest(config.model_dump(mode="json"))
    ):
        raise ValueError("artifact integrity failure")
    return config, manifest, digest(manifest)


def consent_payload(manifest_hash: str, action: str, arguments: dict[str, Any]) -> bytes:
    return canonicalize({"manifest_hash": manifest_hash, "action": action, "arguments": arguments})


def verify_consent(
    key: Ed25519PublicKey,
    manifest_hash: str,
    action: str,
    arguments: dict[str, Any],
    signature: str,
) -> None:
    verify_detached(
        signature, consent_payload(manifest_hash, action, arguments), key, expected_kid="owner"
    )
