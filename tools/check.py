# SPDX-License-Identifier: Apache-2.0
"""The one checks command: `uv run python tools/check.py`.

Runs, in order: ruff check, ruff format --check, pyright, lint-imports, schema
meta-validation, pytest and the agnostic-core rule. Stops at the first failure with a
non-zero exit code.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "spec" / "schemas"
DENYLIST = ROOT / "tools" / "discipline-denylist.txt"
SCHEMA_ID_BASE = "https://coalitionkit.dev/schemas/coalition/v0/"
SKIP_DIRS = {
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "node_modules",
    "dist",
    "build",
}
BINARY_SUFFIXES = {".pyc", ".png", ".jpg", ".gif", ".ico", ".whl", ".zip", ".gz", ".so", ".pyd"}


class CheckError(Exception):
    """A check failed; the message says what to fix."""


def run(args: list[str]) -> None:
    """Run a command with an argument list (no shell). Raise CheckError on a non-zero exit."""
    print(f"$ {' '.join(args)}", flush=True)
    result = subprocess.run(args, cwd=ROOT, check=False)
    if result.returncode != 0:
        raise CheckError(f"command exited with code {result.returncode}")


def py(*module_args: str) -> list[str]:
    return [sys.executable, "-m", *module_args]


def ruff_check() -> None:
    run(py("ruff", "check", "."))


def ruff_format() -> None:
    run(py("ruff", "format", "--check", "."))


def pyright() -> None:
    run(py("pyright"))


def import_linter() -> None:
    code = "from importlinter.cli import lint_imports_command; lint_imports_command()"
    run([sys.executable, "-c", code])


def schemas() -> None:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError

    files = sorted(SCHEMAS.rglob("*.json"))
    if not files:
        raise CheckError(f"no schema files under {SCHEMAS}")
    problems: list[str] = []
    for path in files:
        name = path.relative_to(ROOT).as_posix()
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
        except (json.JSONDecodeError, SchemaError) as exc:
            problems.append(f"{name}: {exc}")
            continue
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            problems.append(f"{name}: $schema must be JSON Schema 2020-12")
        if not str(schema.get("$id", "")).startswith(SCHEMA_ID_BASE):
            problems.append(f"{name}: $id must start with {SCHEMA_ID_BASE}")
        elif schema["$id"] != SCHEMA_ID_BASE + path.name:
            problems.append(f"{name}: $id must end with the file name")
    if problems:
        raise CheckError("schema problems:\n  " + "\n  ".join(problems))
    print(f"{len(files)} schema files are valid JSON Schema 2020-12", flush=True)


def pytest() -> None:
    run(py("pytest", "-q"))


def denylist_words() -> list[str]:
    words: list[str] = []
    for line in DENYLIST.read_text(encoding="utf-8").splitlines():
        word = line.strip()
        if word and not word.startswith("#"):
            words.append(word)
    if not words:
        raise CheckError(f"{DENYLIST} lists no words")
    return words


def agnostic_core() -> None:
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(w) for w in denylist_words()) + r")\b", re.IGNORECASE
    )
    hits: list[str] = []
    scanned = 0
    for path in sorted((ROOT / "packages").rglob("*")):
        rel = path.relative_to(ROOT / "packages")
        if (
            not path.is_file()
            or SKIP_DIRS.intersection(rel.parts)
            or any(part.endswith(".egg-info") for part in rel.parts)
            or path.suffix in BINARY_SUFFIXES
        ):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        scanned += 1
        for number, line in enumerate(text.splitlines(), start=1):
            for match in pattern.finditer(line):
                hits.append(f"{path.relative_to(ROOT).as_posix()}:{number}: {match.group(0)!r}")
    if hits:
        raise CheckError(
            "domain words found under packages/ (the core must stay domain-agnostic):\n  "
            + "\n  ".join(hits)
        )
    print(f"agnostic core: {scanned} files under packages/ are free of denylisted words")


def separation() -> None:
    """Domain words and pack names stay out of the kit; validate installed packs."""
    from separation import SeparationError, check_domain, check_packs

    tests = ("tools/test_separation.py",)
    run(py("pytest", "-q", "-p", "no:cacheprovider", "-o", "pythonpath=tools", *tests))
    try:
        for step in (check_domain, check_packs):
            print(step(), flush=True)
    except SeparationError as exc:
        raise CheckError(str(exc)) from None


STEPS: list[tuple[str, Callable[[], None]]] = [
    ("ruff check", ruff_check),
    ("ruff format --check", ruff_format),
    ("pyright", pyright),
    ("lint-imports", import_linter),
    ("schema meta-validation", schemas),
    ("pytest", pytest),
    ("agnostic-core rule", agnostic_core),
    ("separation of packs and kit", separation),
]


def main() -> int:
    for number, (name, step) in enumerate(STEPS, start=1):
        print(f"\n[{number}/{len(STEPS)}] {name}", flush=True)
        try:
            step()
        except CheckError as exc:
            print(f"\nFAILED: {name}: {exc}", file=sys.stderr)
            return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
