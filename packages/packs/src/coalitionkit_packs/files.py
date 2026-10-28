# SPDX-License-Identifier: Apache-2.0
"""Reading files that belong to a pack: confined to the pack folder, size-limited, safe YAML."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from .errors import Report

MAX_FILE_BYTES = 256 * 1024
MAX_FILES = 500
MANIFEST = "pack.yaml"


def resolve(root: Path, rel: str, where: str, report: Report) -> Path | None:
    """The file ``rel`` inside ``root``, or None after recording why it is refused."""
    posix = PurePosixPath(rel)
    if "\\" in rel or posix.is_absolute() or ".." in posix.parts or not posix.parts:
        report.add("path_escape", where, f"{rel!r} points outside the pack folder")
        return None
    candidate = root.joinpath(*posix.parts)
    current = root
    for part in posix.parts:
        current = current / part
        if current.is_symlink():
            report.add("path_escape", where, f"{rel!r} goes through a symbolic link")
            return None
    if not candidate.is_file():
        report.add("missing_file", where, f"{rel!r} is not a file in the pack")
        return None
    if candidate.stat().st_size > MAX_FILE_BYTES:
        report.add("file_too_large", where, f"{rel!r} is over {MAX_FILE_BYTES} bytes")
        return None
    return candidate


def read_text(path: Path, where: str, report: Report) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        report.add("unreadable", where, str(exc))
        return None


def load_yaml_text(text: str, where: str, report: Report) -> Any:
    try:
        return YAML(typ="safe", pure=True).load(text)  # pyright: ignore[reportUnknownMemberType]
    except YAMLError as exc:
        report.add("yaml", where, f"not valid YAML: {exc}")
        return None


def load_yaml_file(root: Path, rel: str, where: str, report: Report) -> Any:
    path = resolve(root, rel, where, report)
    text = read_text(path, where, report) if path else None
    return load_yaml_text(text, where, report) if text is not None else None


def load_json_file(root: Path, rel: str, where: str, report: Report) -> Any:
    path = resolve(root, rel, where, report)
    text = read_text(path, where, report) if path else None
    if text is None:
        return None
    try:
        return json.loads(text)
    except ValueError as exc:
        report.add("json", where, f"not valid JSON: {exc}")
        return None
