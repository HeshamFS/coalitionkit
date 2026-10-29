# SPDX-License-Identifier: Apache-2.0
"""No secret in any log line, repr or exception (canary tokens)."""

from __future__ import annotations

import logging

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from wa_support import CANARIES, WA_ID, config, rig, signed, text_payload

from coalitionkit_channels.whatsapp import ConfigError, WhatsAppConfig, WhatsAppError, create_router


def clean(text: str) -> bool:
    return not any(c in text for c in CANARIES)


def test_config_repr_and_dump_hide_secrets() -> None:
    cfg = config()
    assert clean(repr(cfg)) and clean(str(cfg)) and clean(str(cfg.model_dump()))


def test_failures_and_logs_carry_no_secret() -> None:
    r = rig(max_attempts=2)
    leak = CANARIES[0]
    r.fake.script = [
        lambda q: httpx.Response(500, text=f"token {leak}", request=q),
        lambda q: httpx.Response(500, text=f"token {leak}", request=q),
    ]
    logger = logging.getLogger("coalitionkit")
    logger.setLevel(logging.DEBUG)
    with pytest.raises(WhatsAppError) as caught:
        r.channel.send("p1", "hi")
    assert clean(str(caught.value)) and clean(repr(caught.value))
    assert caught.value.__cause__ is None


def test_logs_during_normal_traffic_are_clean(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    r = rig()
    r.channel.send("p1", "a message the owner would not want in logs")
    app = FastAPI()
    app.include_router(create_router(r.channel))
    body, headers = signed(text_payload(WA_ID, "reply body", "m-log"))
    TestClient(app).post("/webhooks/whatsapp", content=body, headers=headers)
    TestClient(app).post(
        "/webhooks/whatsapp", content=body, headers={"X-Hub-Signature-256": "sha256=00"}
    )
    assert caplog.records
    for record in caplog.records:
        line = record.getMessage()
        assert clean(line)
        assert "owner would not want" not in line and "reply body" not in line
        assert WA_ID not in line


def test_transport_error_hides_url_and_headers() -> None:
    r = rig()

    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout talking to " + str(request.url), request=request)

    r.fake.script = [boom]
    with pytest.raises(WhatsAppError) as caught:
        r.channel.send("p1", "hi")
    assert clean(str(caught.value)) and "graph.facebook" not in str(caught.value)


def test_invalid_config_error_never_echoes_a_value() -> None:
    for bad in ({"max_attempts": CANARIES[0]}, {"unexpected": CANARIES[1]}, {"token": 5}):
        values = {
            "token": SecretStr(CANARIES[0]),
            "phone_number_id": "1",
            "app_secret": SecretStr(CANARIES[1]),
            "verify_token": SecretStr(CANARIES[2]),
            **bad,
        }
        with pytest.raises(ValidationError) as caught:
            WhatsAppConfig(**values)  # pyright: ignore[reportArgumentType]
        assert clean(str(caught.value)) and clean(repr(caught.value))
        with pytest.raises(ConfigError) as clean_error:
            WhatsAppConfig.load(**values)
        assert clean(str(clean_error.value)) and clean_error.value.__cause__ is None
        assert clean_error.value.__context__ is None


def test_handshake_logs_never_contain_the_verify_token(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    r = rig()
    app = FastAPI()
    app.include_router(create_router(r.channel))
    params = {"hub.mode": "subscribe", "hub.verify_token": CANARIES[2], "hub.challenge": "7"}
    assert TestClient(app).get("/webhooks/whatsapp", params=params).text == "7"
    # What uvicorn's access log would print for the same request. Capture on that logger itself,
    # since other tests may have switched off its propagation.
    seen: list[logging.LogRecord] = []

    class Grab(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            seen.append(record)

    access = logging.getLogger("uvicorn.access")
    grab, old = Grab(), access.level
    access.addHandler(grab)
    access.setLevel(logging.INFO)
    url = f"/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token={CANARIES[2]}&hub.challenge=7"
    try:
        access.info('%s - "%s %s HTTP/%s" %d', "127.0.0.1:5", "GET", url, "1.1", 200)
    finally:
        access.removeHandler(grab)
        access.setLevel(old)
    assert len(seen) == 1 and "hub.verify_token=[redacted]" in seen[0].getMessage()
    for record in [*caplog.records, *seen]:
        assert clean(record.getMessage()) and clean(str(record.args))
