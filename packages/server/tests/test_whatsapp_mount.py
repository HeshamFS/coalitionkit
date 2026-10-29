# SPDX-License-Identifier: Apache-2.0
"""The server mounts the WhatsApp door only when all four settings are present."""

from typing import Any, cast

from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from pydantic import SecretStr

from coalitionkit_server.settings import Settings
from coalitionkit_server.whatsapp import mount_whatsapp
from coalitionkit_surfaces.message import MessageChannel, MessageDoor


class StubDoor:
    def __init__(self) -> None:
        self.synced: list[str] = []

    def sync(self, viewer: str) -> int:
        self.synced.append(viewer)
        return 0

    def poll(self) -> list[Any]:
        return []


def make(channel: MessageChannel) -> MessageDoor:
    return cast(MessageDoor, StubDoor())


def deny(request: Request) -> None:
    if request.headers.get("authorization") != "Bearer ok":
        raise HTTPException(401)


def settings(**extra: Any) -> Settings:
    return Settings(_env_file=None, **extra)  # pyright: ignore[reportCallIssue]


def full() -> Settings:
    return settings(
        whatsapp_token=SecretStr("t"),
        whatsapp_phone_number_id="1",
        whatsapp_app_secret=SecretStr("s"),
        whatsapp_verify_token=SecretStr("v"),
    )


def test_not_mounted_without_settings(monkeypatch: Any) -> None:
    for name in ("TOKEN", "PHONE_NUMBER_ID", "APP_SECRET", "VERIFY_TOKEN"):
        monkeypatch.delenv(f"COALITIONKIT_WHATSAPP_{name}", raising=False)
    app = FastAPI()
    assert mount_whatsapp(app, settings(), make, deny) is None
    assert TestClient(app).get("/webhooks/whatsapp").status_code == 404


def test_partial_settings_do_not_mount() -> None:
    app = FastAPI()
    partial = settings(whatsapp_token=SecretStr("t"))
    assert mount_whatsapp(app, partial, make, deny) is None


def test_mounted_when_configured_and_invitations_need_admin() -> None:
    app = FastAPI()
    assert mount_whatsapp(app, full(), make, deny) is not None
    c = TestClient(app)
    handshake = {"hub.mode": "subscribe", "hub.verify_token": "v", "hub.challenge": "42"}
    assert c.get("/webhooks/whatsapp", params=handshake).text == "42"
    assert c.post("/admin/whatsapp/invitations", json={"viewer": "p1"}).status_code == 401
    ok = c.post(
        "/admin/whatsapp/invitations", json={"viewer": "p1"}, headers={"Authorization": "Bearer ok"}
    )
    assert ok.status_code == 200 and ok.json()["code"]
