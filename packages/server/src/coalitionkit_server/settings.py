# SPDX-License-Identifier: Apache-2.0
"""Environment configuration and private key storage."""

import os
import subprocess
from pathlib import Path
from typing import Literal

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from coalitionkit_contracts.resources import spec_path


def data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME")
    return (Path(base) if base else Path.home() / ".local" / "share") / "coalitionkit"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="COALITIONKIT_", extra="ignore", hide_input_in_errors=True
    )

    store: SecretStr = Field(
        default_factory=lambda: SecretStr(f"sqlite:///{data_dir() / 'host.db'}")
    )
    host_key_file: Path = Field(default_factory=lambda: data_dir() / "host.key")
    public_base_url: str = "http://127.0.0.1:8000"
    bind_host: str = "127.0.0.1"
    bind_port: int = Field(default=8000, ge=1, le=65535)
    surfaces: set[Literal["mcp", "feed", "agent"]] = {"mcp", "feed", "agent"}
    packs: list[Path] = Field(default_factory=list[Path])
    # Author key IDs mapped to public Ed25519 JWKs (also configurable through the environment).
    pack_trusted_keys: dict[str, dict[str, str]] = Field(default_factory=dict[str, dict[str, str]])
    genesis: Literal["off", "local", "admin"] = "off"
    # The room engine drives needs, seats and briefs in hosted rooms. Harnesses that play the
    # members themselves leave it off; `coalitionkit up` turns it on.
    room_engine: Literal["on", "off"] = "off"
    # The Talk stage before plans and after a change: rounds of agent talk (0 turns it off), and
    # how long a round waits for an agent a person brought over MCP to say its line.
    room_talk_rounds: int = Field(default=2, ge=0, le=2)
    room_talk_wait_s: float = Field(default=45.0, ge=0, le=300)
    # The standing room of a public host: with a goal set, the host forms a room from it on its
    # own clock whenever none is open, bound to the named pack and owned by the host's own seat.
    # Visitors join it; nobody else starts rooms here. It ends after the minutes, then a new one
    # forms. ``standing_room_gather_minutes`` is how long it waits for people before it begins.
    standing_room_goal: str | None = Field(default=None, min_length=1, max_length=500)
    standing_room_pack: str | None = None
    standing_room_minutes: float = Field(default=15.0, gt=0, le=1440)
    standing_room_gather_minutes: float = Field(default=5.0, ge=0, le=1440)
    standing_room_seats: int = Field(default=12, ge=2, le=64)
    # The most the models may cost one room, in US dollars; past it the room's model calls are
    # refused and the rules answer. Unset: no cap.
    room_budget_usd: float | None = Field(default=None, gt=0)
    # A file of sample rooms for the first screen. The kit ships none.
    sample_rooms: Path | None = None
    admin_token: SecretStr | None = None
    # WhatsApp message door: mounted only when all four are set.
    whatsapp_token: SecretStr | None = None
    whatsapp_phone_number_id: str | None = None
    whatsapp_app_secret: SecretStr | None = None
    whatsapp_verify_token: SecretStr | None = None
    # Where the message door's confirm link points: the web app's /confirm/<code> route.
    # Unset: the server's own public origin (the web app is served from there).
    confirm_link_base: str | None = None
    catalog_file: Path = spec_path("catalog", "coalitionkit-v0_9.json")

    @property
    def effective_confirm_base(self) -> str:
        return (self.confirm_link_base or self.public_base_url + "/confirm").rstrip("/")

    @property
    def whatsapp_configured(self) -> bool:
        return None not in (
            self.whatsapp_token,
            self.whatsapp_phone_number_id,
            self.whatsapp_app_secret,
            self.whatsapp_verify_token,
        )

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
