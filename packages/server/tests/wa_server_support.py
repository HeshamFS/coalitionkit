# SPDX-License-Identifier: Apache-2.0
"""Server-side WhatsApp test rig: a real host (surfaces' neutral message world), the mount on a
bare app, a recording fake of the Cloud API, fake clocks, and one linked person."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from message_support import MsgWorld
from pydantic import SecretStr
from wa_support import APP_SECRET, PHONE_ID, VERIFY, WA_ID, Clock, Fake, signed, text_payload

from coalitionkit_server import Settings
from coalitionkit_server.whatsapp import WhatsAppMount, mount_whatsapp

ADMIN = {"Authorization": "Bearer admin-test"}
TOKENS = {"tok-p1": "p1", "tok-p2": "p2"}


def settings(tmp_path: Path, *, whatsapp: bool = True, **extra: Any) -> Settings:
    if whatsapp:
        extra = {
            "whatsapp_token": SecretStr("t"),
            "whatsapp_phone_number_id": PHONE_ID,
            "whatsapp_app_secret": SecretStr(APP_SECRET),
            "whatsapp_verify_token": SecretStr(VERIFY),
            **extra,
        }
    return Settings(
        _env_file=None,  # pyright: ignore[reportCallIssue]
        store=SecretStr(f"sqlite:///{tmp_path / 'host.db'}"),
        host_key_file=tmp_path / "keys" / "host.key",
        admin_token=SecretStr("admin-test"),
        **extra,
    )


@dataclass
class Linked:
    world: MsgWorld
    client: TestClient
    mount: WhatsAppMount
    fake: Fake
    clock: Clock
    wall: Clock
    coalition: str

    def say(self, text: str, mid: str, sender: str = WA_ID) -> int:
        body, headers = signed(text_payload(sender, text, mid, self.wall.now))
        return self.client.post("/webhooks/whatsapp", content=body, headers=headers).status_code

    def texts(self) -> list[str]:
        return [b["text"]["body"] for b in self.fake.bodies() if b["type"] == "text"]

    def kinds(self) -> list[str]:
        return self.fake.kinds()

    def redeem(self, token: str, code: str) -> Any:
        return self.client.post(
            "/v1/confirm/redeem", json={"code": code}, headers={"Authorization": f"Bearer {token}"}
        )


def link(world: MsgWorld, tmp_path: Path) -> Linked:
    """Mount the transport on a bare app over ``world.host`` and link p1's phone."""
    fake, clock, wall = Fake(), Clock(), Clock()
    app = FastAPI()
    coalition = world.host.coalition_id

    def admin(request: Request) -> None:
        if request.headers.get("authorization") != "Bearer admin-test":
            raise HTTPException(401)

    def lookup(token: str) -> dict[str, Any] | None:
        who = TOKENS.get(token)
        return None if who is None else {"coalition": coalition, "participant": who}

    mount = mount_whatsapp(
        app,
        settings(tmp_path),
        world.host.store,
        {coalition: world.host},
        admin,
        lookup,
        http=httpx.Client(transport=httpx.MockTransport(fake)),
        clock=clock,
        wall=wall,
    )
    assert mount is not None
    client = TestClient(app)
    linked = Linked(world, client, mount, fake, clock, wall, coalition)
    invite = client.post(
        "/admin/whatsapp/invitations",
        json={"coalition": coalition, "participant": "p1"},
        headers=ADMIN,
    )
    assert invite.status_code == 200
    assert linked.say(invite.json()["code"], "bind-0") == 200
    return linked
