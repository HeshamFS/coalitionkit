# SPDX-License-Identifier: Apache-2.0
"""Regression tests for the review findings: confinement, one-read loading, fail-closed catalog."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from packs_support import CORE_VERSION, copy_pack, core_catalog, new_key

from coalitionkit_contracts import Membership, Scope
from coalitionkit_packs import (
    PackError,
    ScopeWidenError,
    check_not_wider,
    inspect_pack,
    load_pack,
    sign_pack,
    verify_pack_embedded,
)
from coalitionkit_packs.files import Snapshot
from coalitionkit_packs.signing import PackSignature, verify_snapshot

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="directory junctions")


def make_junction(link: Path, target: Path) -> None:
    done = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        check=False,
    )
    if done.returncode != 0:
        pytest.skip("cannot create a junction here")


def outside_folder(tmp_path: Path) -> Path:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "views.yaml").write_text("components: {}\n", encoding="utf-8")
    return outside


# 1. confinement ---------------------------------------------------------------------------


@windows_only
def test_junction_inside_pack_is_refused(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    make_junction(root / "linked", outside_folder(tmp_path))
    with pytest.raises(PackError) as caught:
        inspect_pack(root, core_catalog=core_catalog(), core_version=CORE_VERSION)
    assert caught.value.rules() == {"path_escape"}


@windows_only
def test_manifest_path_through_a_junction_is_refused(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    (root / "views.yaml").unlink()
    make_junction(root / "views.yaml", outside_folder(tmp_path))  # a junction named like a file
    with pytest.raises(PackError) as caught:
        inspect_pack(root, core_catalog=core_catalog(), core_version=CORE_VERSION)
    assert "path_escape" in caught.value.rules()


@windows_only
def test_signing_and_verifying_refuse_junctions(tmp_path: Path) -> None:
    root = copy_pack("pack-beta", tmp_path)
    key = new_key()
    sign_pack(root, key, "k")
    make_junction(root / "linked", outside_folder(tmp_path))
    with pytest.raises(PackError):
        verify_pack_embedded(root)
    with pytest.raises(PackError):
        sign_pack(root, key, "k")


@windows_only
def test_pack_folder_itself_may_not_be_a_junction(tmp_path: Path) -> None:
    real = copy_pack("pack-beta", tmp_path)
    link = tmp_path / "link"
    make_junction(link, real)
    with pytest.raises(PackError) as caught:
        inspect_pack(link, core_catalog=core_catalog(), core_version=CORE_VERSION)
    assert caught.value.rules() == {"path_escape"}


def test_signing_refuses_symlinks(tmp_path: Path) -> None:
    root = copy_pack("pack-beta", tmp_path)
    target = tmp_path / "elsewhere.txt"
    target.write_text("x", encoding="utf-8")
    try:
        (root / "extra.txt").symlink_to(target)
    except OSError:
        pytest.skip("symbolic links are not available here")
    with pytest.raises(PackError):
        sign_pack(root, new_key(), "k")


# 2. verify-then-reread --------------------------------------------------------------------


def test_load_parses_the_bytes_it_verified(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    key = new_key()
    root = copy_pack("pack-alpha", tmp_path)
    sign_pack(root, key, "k")

    def verify_then_swap(snap: Snapshot, keys: Mapping[str, Ed25519PublicKey]) -> PackSignature:
        signature = verify_snapshot(snap, keys)
        (root / "vocabulary.yaml").write_text("task: swapped\n", encoding="utf-8")
        (root / "views.yaml").write_text("components: {Card: {}}\n", encoding="utf-8")
        return signature

    monkeypatch.setattr("coalitionkit_packs.loader.verify_snapshot", verify_then_swap)
    pack = load_pack(
        root,
        trusted_keys={"k": key.public_key()},
        core_catalog=core_catalog(),
        core_version=CORE_VERSION,
    )
    assert pack.vocabulary["task"] == "step"
    assert "StepList" in pack.components


def test_oversized_file_is_refused(tmp_path: Path) -> None:
    root = copy_pack("pack-beta", tmp_path)
    (root / "big.txt").write_bytes(b"x" * (256 * 1024 + 1))
    with pytest.raises(PackError) as caught:
        inspect_pack(root, core_catalog=core_catalog(), core_version=CORE_VERSION)
    assert caught.value.rules() == {"file_too_large"}


# 3. fail closed without a core catalog ----------------------------------------------------


def test_views_without_a_core_catalog_are_refused(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    with pytest.raises(PackError) as caught:
        inspect_pack(root, core_version=CORE_VERSION)
    assert caught.value.rules() == {"core_catalog_missing"}


def test_load_without_a_core_catalog_is_refused(tmp_path: Path) -> None:
    key = new_key()
    root = copy_pack("pack-alpha", tmp_path)
    sign_pack(root, key, "k")
    with pytest.raises(PackError) as caught:
        load_pack(root, trusted_keys={"k": key.public_key()}, core_version=CORE_VERSION)
    assert caught.value.rules() == {"core_catalog_missing"}


# 4. scope audience conversions ------------------------------------------------------------


def test_self_is_not_narrower_than_a_list_without_proof() -> None:
    base = Scope(audience="participants", participants=["p1"])
    with pytest.raises(ScopeWidenError):
        check_not_wider(base, Scope(audience="self"))
    roles = Scope(audience="roles", roles=["r"])
    with pytest.raises(ScopeWidenError):
        check_not_wider(roles, Scope(audience="self"))
    with pytest.raises(ScopeWidenError):
        check_not_wider(roles, Scope(audience="participants", participants=["p1"]))


def test_resolved_sets_decide_self_conversions() -> None:
    members = Membership(frozenset({"p1", "p2"}), {"r": frozenset({"p1"})})
    base = Scope(audience="participants", participants=["p1"])
    check_not_wider(base, Scope(audience="self"), owner="p1", membership=members)
    with pytest.raises(ScopeWidenError):
        check_not_wider(base, Scope(audience="self"), owner="p2", membership=members)
    by_role = Scope(audience="roles", roles=["r"])
    check_not_wider(
        by_role, Scope(audience="participants", participants=["p1"]), owner="p2", membership=members
    )
    with pytest.raises(ScopeWidenError):
        check_not_wider(
            by_role,
            Scope(audience="participants", participants=["p2"]),
            owner="p1",
            membership=members,
        )


def test_provable_conversions_still_pass() -> None:
    check_not_wider(Scope(audience="coalition"), Scope(audience="self"))
    check_not_wider(Scope(audience="roles", roles=["a"]), Scope(audience="host"))
    check_not_wider(Scope(audience="self"), Scope(audience="self"))


def test_hard_link_to_a_file_outside_the_pack_is_refused(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    outside = tmp_path / "outside-secret.yaml"
    outside.write_text("secret: value", encoding="utf-8")
    os.link(outside, root / "extra.yaml")
    with pytest.raises(PackError) as caught:
        inspect_pack(root, core_catalog=core_catalog(), core_version=CORE_VERSION)
    assert caught.value.rules() == {"path_escape"}
