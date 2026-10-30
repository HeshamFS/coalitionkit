# SPDX-License-Identifier: Apache-2.0
"""Live: send the approved ``hello_world`` template from the test number (one message)."""

from __future__ import annotations

import os
import time

import pytest
from pydantic import SecretStr

from coalitionkit_channels.whatsapp import WhatsAppClient, WhatsAppConfig

pytestmark = pytest.mark.live


def test_hello_world_template_returns_a_message_id() -> None:
    if os.environ.get("COALITIONKIT_LIVE") != "1":
        pytest.skip("COALITIONKIT_LIVE is not 1")
    token = os.environ.get("COALITIONKIT_WHATSAPP_TOKEN")
    phone = os.environ.get("COALITIONKIT_WHATSAPP_PHONE_NUMBER_ID")
    recipient = os.environ.get("COALITIONKIT_WHATSAPP_TEST_RECIPIENT")
    if not (token and phone):
        pytest.skip("no key: COALITIONKIT_WHATSAPP_TOKEN / _PHONE_NUMBER_ID not set")
    if not recipient:
        pytest.skip("COALITIONKIT_WHATSAPP_TEST_RECIPIENT is not set")
    config = WhatsAppConfig(
        token=SecretStr(token),
        phone_number_id=phone,
        app_secret=SecretStr("unused-in-this-test"),
        verify_token=SecretStr("unused-in-this-test"),
    )
    client = WhatsAppClient(config)
    started = time.perf_counter()
    message_id = client.send_opener(recipient)
    elapsed = time.perf_counter() - started
    client.close()
    assert message_id.startswith("wamid.")
    print(f"live whatsapp template sent: 1 message, {elapsed:.2f}s, usage={client.usage}")
