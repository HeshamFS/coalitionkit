# SPDX-License-Identifier: Apache-2.0
"""The server mounts the WhatsApp door when configured, per coalition, on its own database."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from message_support import message_world
from wa_server_support import settings
from wa_support import VERIFY, WA_ID

from coalitionkit_channels.whatsapp import Bindings
from coalitionkit_runtime import SQLiteStore
from coalitionkit_server import create_server
from coalitionkit_server.whatsapp import SqlBindingStore

__all__ = ["message_world"]

CHARTER = json.loads((Path(__file__).parent / "fixtures" / "charter.json").read_text())
ADMIN = {"Authorization": "Bearer admin-test"}
HANDSHAKE = {"hub.mode": "subscribe", "hub.verify_token": VERIFY, "hub.challenge": "42"}


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


def test_the_server_lifespan_owns_the_delivery_timer(tmp_path: Path) -> None:
    app = create_server(settings(tmp_path, whatsapp=True))
    mount = app.state.whatsapp
    assert not mount.running
    with TestClient(app):
        assert mount.running
    assert not mount.running


def test_confirm_link_base_defaults_to_the_web_confirm_route(tmp_path: Path) -> None:
    assert (
        settings(tmp_path, whatsapp=False).effective_confirm_base == "http://127.0.0.1:8000/confirm"
    )
    custom = settings(tmp_path, whatsapp=False, confirm_link_base="https://app.example/confirm/")
    assert custom.effective_confirm_base == "https://app.example/confirm"
