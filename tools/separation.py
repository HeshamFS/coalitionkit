# SPDX-License-Identifier: Apache-2.0
"""Keep Discipline Packs out of the kit (docs/packs/plan.md, section 7).

1. Domain words: no word from the denylist and no pack name under ``packages/``, ``apps/`` or
   ``spec/``. Packs add their own domain words to the denylist, so the scan covers them.
2. Freeze: after the ``core-freeze-3.2`` tag (the kit release packs build on), a ``pack/*``
   branch may change only ``packs/``, ``docs/`` and the denylist.
3. Packs: every folder in ``packs/`` validates with the loader, and its scripted evals pass.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DENYLIST = ROOT / "tools" / "discipline-denylist.txt"
PACKS = ROOT / "packs"
KIT_DIRS = ("packages", "apps", "spec")
FREEZE_TAG = "core-freeze-3.2"
PACK_BRANCH = "pack/"
PACK_BRANCH_MAY_CHANGE = ("packs/", "docs/", "tools/discipline-denylist.txt")
SKIP_DIRS = {
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    "test-results",
    "playwright-report",
}
BINARY = {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".woff", ".woff2", ".zip"}


class SeparationError(Exception):
    """A pack reached into the kit, or the kit reached into a pack."""


def denylist(path: Path = DENYLIST) -> list[str]:
    words = [w.strip() for w in path.read_text(encoding="utf-8").splitlines()]
    return [w for w in words if w and not w.startswith("#")]


def pack_names(packs: Path = PACKS) -> list[str]:
    """Folder names of the installed packs, and the ``name`` each ``pack.yaml`` declares."""
    names: set[str] = set()
    if not packs.is_dir():
        return []
    for folder in sorted(p for p in packs.iterdir() if p.is_dir()):
        names.add(folder.name)
        manifest = folder / "pack.yaml"
        if manifest.is_file():
            text = manifest.read_text("utf-8")
            match = re.search(r"^name:\s*([a-z0-9][a-z0-9-]*)\s*$", text, re.M)
            if match:
                names.add(match.group(1))
    return sorted(names)


def kit_files(root: Path = ROOT) -> Iterable[Path]:
    for top in KIT_DIRS:
        base = root / top
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            rel = path.relative_to(root).parts
            if path.is_file() and not SKIP_DIRS.intersection(rel) and path.suffix not in BINARY:
                yield path


def domain_hits(terms: list[str], root: Path = ROOT) -> list[str]:
    if not terms:
        return []
    pattern = re.compile(r"\b(" + "|".join(re.escape(t) for t in terms) + r")\b", re.IGNORECASE)
    hits: list[str] = []
    for path in kit_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            for match in pattern.finditer(line):
                hits.append(f"{path.relative_to(root).as_posix()}:{number}: {match.group(0)!r}")
    return hits


def check_domain(root: Path = ROOT) -> str:
    terms = denylist(root / "tools" / "discipline-denylist.txt") + pack_names(root / "packs")
    hits = domain_hits(terms, root)
    if hits:
        raise SeparationError(
            "domain words or pack names found in the kit (packages/, apps/, spec/):\n  "
            + "\n  ".join(hits[:50])
        )
    return f"kit free of {len(terms)} domain words and pack names"


def git(*args: str, root: Path = ROOT) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def current_branch(root: Path = ROOT) -> str:
    return (
        os.environ.get("GITHUB_HEAD_REF")
        or os.environ.get("CK_BRANCH")
        or git("rev-parse", "--abbrev-ref", "HEAD", root=root)
    )


def frozen_changes(changed: Iterable[str]) -> list[str]:
    """Paths a pack branch may not change."""
    return sorted(p for p in changed if not p.startswith(PACK_BRANCH_MAY_CHANGE))


def check_freeze(root: Path = ROOT) -> str:
    if not git("rev-parse", "-q", "--verify", f"refs/tags/{FREEZE_TAG}", root=root):
        return f"no {FREEZE_TAG} tag yet: the kit is not frozen"
    branch = current_branch(root)
    if not branch.startswith(PACK_BRANCH):
        return f"branch {branch!r} is not a pack branch: freeze check not applied"
    changed = git("diff", "--name-only", f"{FREEZE_TAG}...HEAD", root=root).splitlines()
    changed += git("diff", "--name-only", "HEAD", root=root).splitlines()
    bad = frozen_changes(changed)
    if bad:
        raise SeparationError(
            f"a pack branch changed the kit after {FREEZE_TAG}:\n  " + "\n  ".join(bad)
        )
    return f"pack branch {branch!r} leaves the kit unchanged since {FREEZE_TAG}"


def pack_command(*args: str) -> list[str]:
    return [sys.executable, "-m", "coalitionkit_packs.cli", *args]


def has_eval_command(root: Path = ROOT) -> bool:
    cli = root / "packages" / "packs" / "src" / "coalitionkit_packs" / "cli.py"
    return cli.is_file() and '"eval"' in cli.read_text(encoding="utf-8")


def check_packs(root: Path = ROOT) -> str:
    folders = sorted(p for p in (root / "packs").glob("*") if (p / "pack.yaml").is_file())
    if not folders:
        return "no packs installed under packs/"
    for folder in folders:
        for args in (
            (("validate", str(folder)),)
            + ((("eval", str(folder)),) if has_eval_command(root) else ())
            + ((("accept", str(folder)),) if (folder / "acceptance.yaml").is_file() else ())
        ):
            print(f"$ coalitionkit-pack {' '.join(args)}", flush=True)
            result = subprocess.run(pack_command(*args), cwd=root, check=False)
            if result.returncode != 0:
                raise SeparationError(f"pack {folder.name}: {args[0]} failed")
    return f"{len(folders)} packs validated" + (" and evaluated" if has_eval_command(root) else "")
