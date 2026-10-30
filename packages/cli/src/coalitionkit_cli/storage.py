# SPDX-License-Identifier: Apache-2.0
"""Private local state and bounded reset."""

import os
import secrets
import shutil
import subprocess
from pathlib import Path

MARKER = ".coalitionkit-owner"


def prepare(path: Path, reset: bool) -> Path:
    if path.is_symlink() or path.is_junction():
        raise ValueError("data directory must not be a link")
    path = path.resolve()
    marker = path / MARKER
    if path.exists():
        if not marker.is_file() or marker.read_text() != str(path):
            raise ValueError("data directory was not created here by coalitionkit up")
        if any(p.is_symlink() or p.is_junction() for p in path.rglob("*")):
            raise ValueError("data directory contains links")
        if reset:
            shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    marker.write_text(str(path), encoding="utf-8")
    return path


def admin_token(path: Path) -> str:
    token_file = path / "admin.token"
    if not token_file.exists():
        fd = os.open(token_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            if os.name == "nt":
                identity = subprocess.check_output(["whoami"], text=True).strip()
                subprocess.run(
                    ["icacls", str(token_file), "/inheritance:r", "/grant:r", f"{identity}:F"],
                    check=True,
                    capture_output=True,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            stream.write(secrets.token_urlsafe(32))
    if os.name != "nt":
        token_file.chmod(0o600)
    return token_file.read_text(encoding="utf-8")
