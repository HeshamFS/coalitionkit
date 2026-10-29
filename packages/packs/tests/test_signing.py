# SPDX-License-Identifier: Apache-2.0
"""Author signatures: a pack that fails verification never loads."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from packs_support import CORE_CATALOG, CORE_VERSION, copy_pack, core_catalog, new_key, rewrite

from coalitionkit_contracts.owner import public_key_to_jwk
from coalitionkit_packs import (
    Pack,
    PackError,
    load_pack,
    sign_pack,
    verify_pack,
    verify_pack_embedded,
)
from coalitionkit_packs.cli import main


def load(root: Path, keys: dict[str, Ed25519PublicKey]) -> Pack:
    return load_pack(
        root, trusted_keys=keys, core_catalog=core_catalog(), core_version=CORE_VERSION
    )


def test_signed_pack_loads(tmp_path: Path) -> None:
    key = new_key()
    root = copy_pack("pack-alpha", tmp_path)
    sign_pack(root, key, "author-1")
    pack = load(root, {"author-1": key.public_key()})
    assert pack.signature is not None and pack.signature.kid == "author-1"
    assert verify_pack(root, {"author-1": key.public_key()}).pinned
    assert not verify_pack_embedded(root).pinned


def test_unsigned_pack_never_loads(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    with pytest.raises(PackError) as caught:
        load(root, {"author-1": new_key().public_key()})
    assert caught.value.rules() == {"signature"}


@pytest.mark.parametrize("change", ["edit", "add", "remove"])
def test_any_change_breaks_the_signature(tmp_path: Path, change: str) -> None:
    key = new_key()
    root = copy_pack("pack-alpha", tmp_path)
    sign_pack(root, key, "k")
    if change == "edit":
        rewrite(root / "vocabulary.yaml", "task: step", "task: stage")
    elif change == "add":
        (root / "extra.txt").write_text("x", encoding="utf-8")
    else:
        (root / "skills" / "SKILL.md").unlink()
    with pytest.raises(PackError) as caught:
        load(root, {"k": key.public_key()})
    assert caught.value.rules() == {"signature"}
    with pytest.raises(PackError):
        verify_pack_embedded(root)


def test_wrong_or_unknown_key_is_refused(tmp_path: Path) -> None:
    key = new_key()
    root = copy_pack("pack-beta", tmp_path)
    sign_pack(root, key, "k")
    for keys in ({"k": new_key().public_key()}, {"other": key.public_key()}, {}):
        with pytest.raises(PackError):
            load(root, keys)


def test_resigned_by_someone_else_does_not_load(tmp_path: Path) -> None:
    root = copy_pack("pack-beta", tmp_path)
    sign_pack(root, new_key(), "k")  # an attacker re-signs under the same kid
    with pytest.raises(PackError):
        load(root, {"k": new_key().public_key()})


def test_invalid_pack_does_not_load_even_when_signed(tmp_path: Path) -> None:
    key = new_key()
    root = copy_pack("pack-beta", tmp_path)
    rewrite(root / "views.yaml", "[ReviewBoard, Card]", "[Nowhere]")
    sign_pack(root, key, "k")
    with pytest.raises(PackError) as caught:
        load(root, {"k": key.public_key()})
    assert "unknown_component" in caught.value.rules()


def test_cli_validate_sign_verify(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    key = new_key()
    pem = tmp_path / "key.pem"
    pem.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    jwk = tmp_path / "pub.json"
    jwk.write_text(json.dumps(public_key_to_jwk(key.public_key(), "k")), encoding="utf-8")
    root = copy_pack("pack-alpha", tmp_path)
    cat = str(CORE_CATALOG)
    assert main(["validate", str(root), "--catalog", cat, "--core-version", CORE_VERSION]) == 0
    assert main(["verify", str(root)]) == 1  # unsigned
    assert main(["sign", str(root), "--key", str(pem), "--kid", "k"]) == 0
    assert main(["verify", str(root)]) == 0
    assert main(["verify", str(root), "--trusted-key", str(jwk)]) == 0
    rewrite(root / "vocabulary.yaml", "task: step", "task: stage")
    assert main(["verify", str(root), "--trusted-key", str(jwk)]) == 1
    assert main(["validate", str(root), "--core-version", CORE_VERSION]) == 1  # no core catalog
    err = capsys.readouterr().err
    assert "[signature]" in err and "[core_catalog_missing]" in err
    assert main(["sign", str(root), "--key", str(tmp_path / "none"), "--kid", "k"]) == 2
