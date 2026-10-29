# SPDX-License-Identifier: Apache-2.0
"""A confined, size-bounded snapshot of a pack folder, read once.

Everything downstream (signature check, parsing) works on the snapshot's bytes and never
reopens a file, so what is verified is exactly what is parsed. The walk refuses symbolic links,
directory junctions and any other reparse point, and every file must resolve inside the
resolved pack root.
"""

from __future__ import annotations

import json
import os
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from .errors import PackError, Problem, Report

MAX_FILE_BYTES = 256 * 1024
MAX_FILES = 500
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MANIFEST = "pack.yaml"
SIG_FILE = "pack.sig"
_REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)


def is_link_like(path: Path) -> bool:
    """True for a symbolic link, a junction or any other Windows reparse point."""
    if path.is_symlink():
        return True
    try:
        attrs = getattr(os.lstat(path), "st_file_attributes", 0)
    except OSError:
        return True
    return bool(attrs & _REPARSE)


def bad_relative_path(rel: str) -> str | None:
    """Why ``rel`` cannot name a file inside a pack, or None when it can."""
    if not rel or "\\" in rel or "\x00" in rel:
        return "not a plain relative POSIX path"
    win = PureWindowsPath(rel)
    posix = PurePosixPath(rel)
    if win.drive or win.root or posix.is_absolute() or ":" in rel:
        return "absolute or drive-qualified"
    if ".." in posix.parts or not posix.parts or "." in posix.parts:
        return "contains . or .. segments"
    return None


def _refuse(where: str, message: str) -> PackError:
    return PackError([Problem("path_escape", where, message)])


@dataclass(frozen=True)
class Snapshot:
    """Every file of a pack folder as bytes, keyed by POSIX relative path."""

    root: Path
    files: Mapping[str, bytes]

    def get(self, rel: str, where: str, report: Report) -> bytes | None:
        reason = bad_relative_path(rel)
        if reason is not None:
            report.add("path_escape", where, f"{rel!r} is {reason}")
            return None
        data = self.files.get(PurePosixPath(rel).as_posix())
        if data is None:
            report.add("missing_file", where, f"{rel!r} is not a file in the pack")
        return data

    def text(self, rel: str, where: str, report: Report) -> str | None:
        data = self.get(rel, where, report)
        if data is None:
            return None
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError as exc:
            report.add("unreadable", where, str(exc))
            return None

    def yaml(self, rel: str, where: str, report: Report) -> Any:
        text = self.text(rel, where, report)
        if text is None:
            return None
        try:
            return YAML(typ="safe", pure=True).load(text)  # pyright: ignore[reportUnknownMemberType]
        except YAMLError as exc:
            report.add("yaml", where, f"not valid YAML: {exc}")
            return None

    def json(self, rel: str, where: str, report: Report) -> Any:
        text = self.text(rel, where, report)
        if text is None:
            return None
        try:
            return json.loads(text)
        except ValueError as exc:
            report.add("json", where, f"not valid JSON: {exc}")
            return None


def take_snapshot(root: Path | str) -> Snapshot:
    """Read the whole pack folder once. Raises PackError for links, escapes and size limits."""
    base = Path(root)
    if not base.is_dir():
        raise PackError([Problem("manifest", str(base), "not a pack folder")])
    if is_link_like(base):
        raise _refuse(str(base), "the pack folder is a link or reparse point")
    resolved = base.resolve(strict=True)
    files: dict[str, bytes] = {}
    total = 0
    stack: list[Path] = [resolved]
    while stack:
        folder = stack.pop()
        for entry in sorted(folder.iterdir()):
            rel = entry.relative_to(resolved).as_posix()
            if is_link_like(entry):
                raise _refuse(rel, "symbolic links, junctions and reparse points are refused")
            real = entry.resolve(strict=True)
            if not real.is_relative_to(resolved):
                raise _refuse(rel, "resolves outside the pack folder")
            if entry.is_dir():
                stack.append(entry)
                continue
            if not entry.is_file():
                raise _refuse(rel, "not a regular file")
            if len(files) >= MAX_FILES:
                raise PackError([Problem("file_too_large", rel, f"over {MAX_FILES} files")])
            with entry.open("rb") as handle:
                # A hard link is a regular file with a second name, possibly outside the pack;
                # checked on the open handle so the file cannot be swapped after the check.
                if os.fstat(handle.fileno()).st_nlink > 1:
                    raise _refuse(rel, "hard links are refused")
                data = handle.read(MAX_FILE_BYTES + 1)
            total += len(data)
            if len(data) > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                raise PackError([Problem("file_too_large", rel, "over the size limit")])
            files[rel] = data
    return Snapshot(resolved, files)
