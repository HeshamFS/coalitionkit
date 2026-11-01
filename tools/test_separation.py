# SPDX-License-Identifier: Apache-2.0
"""The guards that keep packs out of the kit, on throwaway repositories."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from separation import (
    SeparationError,
    check_domain,
    check_freeze,
    frozen_changes,
    pack_names,
)


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    write(tmp_path, "tools/discipline-denylist.txt", "# words\nwidgetry\n")
    write(tmp_path, "packages/kit/a.py", "x = 1\n")
    write(tmp_path, "apps/web/src/a.ts", "export const x = 1;\n")
    write(tmp_path, "spec/a.md", "the kit\n")
    write(tmp_path, "packs/demo-pack/pack.yaml", "name: demo-pack\nversion: 1.0.0\n")
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "add", ".")
    git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
    return tmp_path


def test_pack_names_come_from_folders_and_manifests(repo: Path) -> None:
    assert pack_names(repo / "packs") == ["demo-pack"]


def test_clean_kit_passes(repo: Path) -> None:
    assert "kit free" in check_domain(repo)


@pytest.mark.parametrize("where", ["packages/kit/b.py", "apps/web/src/b.ts", "spec/b.md"])
def test_domain_word_in_the_kit_fails(repo: Path, where: str) -> None:
    write(repo, where, "talks about widgetry\n")
    with pytest.raises(SeparationError, match="widgetry"):
        check_domain(repo)


def test_pack_name_in_the_kit_fails(repo: Path) -> None:
    write(repo, "apps/web/src/b.ts", "const p = 'demo-pack';\n")
    with pytest.raises(SeparationError, match="demo-pack"):
        check_domain(repo)


def test_words_inside_packs_and_docs_are_fine(repo: Path) -> None:
    write(repo, "packs/demo-pack/vocabulary.yaml", "task: widgetry\n")
    write(repo, "docs/notes.md", "widgetry demo-pack\n")
    assert "kit free" in check_domain(repo)


def test_frozen_changes_allow_only_packs_docs_and_denylist() -> None:
    changed = [
        "packs/demo-pack/pack.yaml",
        "docs/x.md",
        "tools/discipline-denylist.txt",
        "apps/web/src/a.ts",
        "packages/kit/a.py",
        "spec/a.md",
    ]
    assert frozen_changes(changed) == ["apps/web/src/a.ts", "packages/kit/a.py", "spec/a.md"]


def test_freeze_not_applied_before_the_tag(repo: Path) -> None:
    assert "not frozen" in check_freeze(repo)


def test_a_neutral_web_change_on_a_pack_branch_is_refused(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    git(repo, "tag", "core-freeze-2")
    git(repo, "checkout", "-q", "-b", "pack/demo-pack")
    monkeypatch.delenv("GITHUB_HEAD_REF", raising=False)
    monkeypatch.setenv("CK_BRANCH", "pack/demo-pack")
    write(repo, "packs/demo-pack/views.yaml", "{}\n")
    assert "leaves the kit unchanged" in check_freeze(repo)
    write(repo, "apps/web/src/a.ts", "export const x = 2;\n")
    with pytest.raises(SeparationError, match=r"apps/web/src/a\.ts"):
        check_freeze(repo)


def test_kit_branches_are_not_frozen(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    git(repo, "tag", "core-freeze-2")
    monkeypatch.setenv("CK_BRANCH", "feat/next-kit")
    write(repo, "packages/kit/a.py", "x = 2\n")
    assert "not a pack branch" in check_freeze(repo)
