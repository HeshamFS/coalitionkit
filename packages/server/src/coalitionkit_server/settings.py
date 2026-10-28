# SPDX-License-Identifier: Apache-2.0
"""Environment configuration and private key storage."""

import os
import subprocess
from pathlib import Path
from typing import Literal

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME")
    return (Path(base) if base else Path.home() / ".local" / "share") / "coalitionkit"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COALITIONKIT_", extra="ignore")

    store: SecretStr = Field(
        default_factory=lambda: SecretStr(f"sqlite:///{data_dir() / 'host.db'}")
    )
    host_key_file: Path = Field(default_factory=lambda: data_dir() / "host.key")
    public_base_url: str = "http://127.0.0.1:8000"
    bind_host: str = "127.0.0.1"
    bind_port: int = Field(default=8000, ge=1, le=65535)
    surfaces: set[Literal["mcp", "feed", "agent"]] = {"mcp", "feed", "agent"}
    admin_token: SecretStr | None = None

    @field_validator("public_base_url")
    @classmethod
    def url(cls, value: str) -> str:
        from urllib.parse import urlsplit

        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username:
            raise ValueError("public_base_url must be an HTTP origin without credentials")
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ValueError("public_base_url must be an origin")
        return value.rstrip("/")


def load_key(path: Path) -> Ed25519PrivateKey:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, "wb") as stream:
                # Restrict the empty file before writing secret bytes. Do not change the
                # permissions of a caller-supplied parent directory.
                if os.name == "nt":
                    identity = subprocess.check_output(["whoami"], text=True).strip()
                    subprocess.run(
                        ["icacls", str(path), "/inheritance:r", "/grant:r", f"{identity}:F"],
                        check=True,
                        capture_output=True,
                    )
                stream.write(Ed25519PrivateKey.generate().private_bytes_raw())
    if os.name != "nt" and path.stat().st_mode & 0o077:
        raise ValueError("host key permissions must be 0600")
    return Ed25519PrivateKey.from_private_bytes(path.read_bytes())
