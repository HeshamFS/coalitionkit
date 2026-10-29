# SPDX-License-Identifier: Apache-2.0
"""WhatsApp Cloud API settings and the pinned Graph API version."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, SecretStr

# One place for the Graph API version. v26.0 is the newest version Meta's WhatsApp Cloud API
# docs name (send-messages guide, example endpoint https://graph.facebook.com/v26.0/<PHONE_NUMBER_ID>/messages;
# Graph API v26.0 release post, 2026-07-29).
GRAPH_API_VERSION = "v26.0"
GRAPH_BASE = "https://graph.facebook.com"

# The template Meta provisions on every test number; the only message allowed outside the window.
OPENER_TEMPLATE = "hello_world"
OPENER_LANGUAGE = "en_US"

WINDOW_SECONDS = 24 * 60 * 60.0


class WhatsAppConfig(BaseModel):
    """Everything the adapter needs. Secrets are ``SecretStr``: repr and errors never show them."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    token: SecretStr
    phone_number_id: str
    app_secret: SecretStr
    verify_token: SecretStr
    max_attempts: int = 4
    backoff_seconds: float = 0.5
    max_per_minute: int = 20
    max_webhook_age: float = 600.0
    window_seconds: float = WINDOW_SECONDS

    @property
    def messages_url(self) -> str:
        return f"{GRAPH_BASE}/{GRAPH_API_VERSION}/{self.phone_number_id}/messages"
