# SPDX-License-Identifier: Apache-2.0
"""The server mounts the WhatsApp door when configured, per coalition, on its own database."""

import json
import time
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from message_support import MsgWorld, message_world
from pydantic import SecretStr
from wa_support import APP_SECRET, PHONE_ID, VERIFY, WA_ID, Fake, signed, text_payload

from coalitionkit_channels.whatsapp import UNKNOWN_LINE, Bindings
from coalitionkit_runtime import SQLiteStore
from coalitionkit_server import Settings, create_server
from coalitionkit_server.whatsapp import SqlBindingStore, mount_whatsapp

__all__ = ["message_world"]

CHARTER = json.loads((Path(__file__).parent / "fixtures" / "charter.json").read_text())
ADMIN = {"Authorization": "Bearer admin-test"}
HANDSHAKE = {"hub.mode": "subscribe", "hub.verify_token": VERIFY, "hub.challenge": "42"}


def settings(tmp_path: Path, *, whatsapp: bool) -> Settings:
    extra: dict[str, Any] = {}
    if whatsapp:
        extra = {
            "whatsapp_token": SecretStr("t"),
            "whatsapp_phone_number_id": PHONE_ID,
            "whatsapp_app_secret": SecretStr(APP_SECRET),
            "whatsapp_verify_token": SecretStr(VERIFY),
        }
    return Settings(
        _env_file=None,  # pyright: ignore[reportCallIssue]
        store=SecretStr(f"sqlite:///{tmp_path / 'host.db'}"),
        host_key_file=tmp_path / "keys" / "host.key",
        admin_token=SecretStr("admin-test"),
        **extra,
    )


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("TOKEN", "PHONE_NUMBER_ID", "APP_SECRET", "VERIFY_TOKEN"):
        monkeypatch.delenv(f"COALITIONKIT_WHATSAPP_{name}", raising=False)


def test_create_server_has_no_whatsapp_routes_without_settings(tmp_path: Path) -> None:
    app = create_server(settings(tmp_path, whatsapp=False))
    client = TestClient(app)
    assert client.get("/webhooks/whatsapp", params=HANDSHAKE).status_code == 404
    body = {"coalition": "c", "participant": "p1"}
    assert client.post("/admin/whatsapp/invitations", json=body, headers=ADMIN).status_code == 404
    app.state.server.close()


def test_create_server_mounts_the_door_when_configured(tmp_path: Path) -> None:
    app = create_server(settings(tmp_path, whatsapp=True))
    client = TestClient(app)
    assert client.get("/webhooks/whatsapp", params=HANDSHAKE).text == "42"
    body = {"coalition": "nope", "participant": "p1"}
    assert client.post("/admin/whatsapp/invitations", json=body).status_code == 401
    assert client.post("/admin/whatsapp/invitations", json=body, headers=ADMIN).status_code == 404
    created = client.post("/admin/coalitions", json=CHARTER, headers=ADMIN).json()
    unjoined = {"coalition": created["coalition_id"], "participant": "p1"}
    # p1 has not joined, so there is no view to deliver: no invitation either.
    assert (
        client.post("/admin/whatsapp/invitations", json=unjoined, headers=ADMIN).status_code == 404
    )
    assert app.state.whatsapp.door_for(created["coalition_id"]) is not None
    assert app.state.whatsapp.door_for("other") is None
    app.state.server.close()


def test_binding_then_reply_opens_only_the_confirm_step(
    message_world: MsgWorld, tmp_path: Path
) -> None:
    world = message_world
    world.propose(world.need("Task for p1"), ["p1"])
    fake = Fake()
    app = FastAPI()
    coalition = world.host.coalition_id

    def admin(request: Request) -> None:
        if request.headers.get("authorization") != "Bearer admin-test":
            raise HTTPException(401)

    mount = mount_whatsapp(
        app,
        settings(tmp_path, whatsapp=True),
        world.host.store,
        {coalition: world.host},
        admin,
        http=httpx.Client(transport=httpx.MockTransport(fake)),
    )
    assert mount is not None
    client = TestClient(app)
    invite = client.post(
        "/admin/whatsapp/invitations",
        json={"coalition": coalition, "participant": "p1"},
        headers=ADMIN,
    )
    code = invite.json()["code"]

    def say(text: str, mid: str) -> None:
        body, headers = signed(text_payload(WA_ID, text, mid, time.time()))
        assert client.post("/webhooks/whatsapp", content=body, headers=headers).status_code == 200

    say("hi", "w0")  # not a code: the fixed line only
    assert fake.bodies()[-1]["text"]["body"] == UNKNOWN_LINE
    say(code, "w1")  # binds and delivers the first view
    assert mount.bindings.viewer_of(WA_ID) == f"{coalition}/p1"
    sent = [b["text"]["body"] for b in fake.bodies()]
    assert any("Task for p1" in text for text in sent)
    log_before = len(world.host.store.read(coalition))
    say("1", "w2")  # the one option: opens the confirm step
    assert "not your decision" in fake.bodies()[-1]["text"]["body"]
    assert [o.kind for o in mount.outcomes] == ["confirm"]
    assert len(world.host.store.read(coalition)) == log_before  # nothing signed or appended
    assert world.host.open_consents("p1")


def test_bindings_survive_a_restart_on_the_same_database(tmp_path: Path) -> None:
    path = str(tmp_path / "bindings.db")
    first = SQLiteStore(path)
    bindings = Bindings(SqlBindingStore(first))
    code = bindings.invite("c1/p1")
    spare = bindings.invite("c1/p2")
    assert bindings.redeem(WA_ID, code).status == "bound"
    first.close()

    second = SQLiteStore(path)
    again = Bindings(SqlBindingStore(second))
    assert again.viewer_of(WA_ID) == "c1/p1" and again.wa_id_of("c1/p1") == WA_ID
    # The burned code stays burned; the unused one still works after the restart.
    assert again.redeem("15550000009", code).status == "rejected"
    assert again.redeem("15550000009", spare).status == "bound"
    # Failed attempts persist too: three failures lock the sender across a restart.
    for _ in range(3):
        again.redeem("15550000010", "nothing")
    second.close()
    last = SQLiteStore(path)
    third = Bindings(SqlBindingStore(last))
    assert third.redeem("15550000010", third.invite("c1/p3")).status == "locked"
    last.close()
