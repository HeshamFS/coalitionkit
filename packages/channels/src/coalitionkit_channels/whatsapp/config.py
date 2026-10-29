# SPDX-License-Identifier: Apache-2.0
"""WhatsApp Cloud API settings and the pinned Graph API version."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, SecretStr, ValidationError

# One place for the Graph API version. v26.0 is the newest version Meta's WhatsApp Cloud API
# docs name (send-messages guide, example endpoint https://graph.facebook.com/v26.0/<PHONE_NUMBER_ID>/messages;
# Graph API v26.0 release post, 2026-07-29).
GRAPH_API_VERSION = "v26.0"
GRAPH_BASE = "https://graph.facebook.com"

# The template Meta provisions on every test number; the only message allowed outside the window.
OPENER_TEMPLATE = "hello_world"
OPENER_LANGUAGE = "en_US"

WINDOW_SECONDS = 24 * 60 * 60.0
FUTURE_SLACK = 300.0  # a message stamped further ahead than this is refused


class ConfigError(ValueError):
    """Invalid settings. Names the fields and the kind of problem, never a value."""


class WhatsAppConfig(BaseModel):
    """Everything the adapter needs. Secrets are ``SecretStr``: repr and errors never show them."""

    # hide_input_in_errors: a validation error never echoes a value (it could be a secret).
    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)

    token: SecretStr
    phone_number_id: str
    app_secret: SecretStr
    verify_token: SecretStr
    max_attempts: int = 4
    backoff_seconds: float = 0.5
    max_per_minute: int = 20
    max_webhook_age: float = 600.0
    window_seconds: float = WINDOW_SECONDS
    # Inbound ids are remembered for the whole span in which a delivery could still be accepted
    # (max_webhook_age plus the future-timestamp slack); outbound ids for the door's retry
    # lifetime. Both are time-based; a full memory refuses new work instead of forgetting.
    delivery_memory_seconds: float = WINDOW_SECONDS
    memory_capacity: int = 100_000

    @classmethod
    def load(cls, **values: Any) -> WhatsAppConfig:
        """Build from raw values; a failure is a ConfigError with no input echoed (the
        exception chain is cut, because a ValidationError object still holds the inputs)."""
        try:
            return cls(**values)
        except ValidationError as error:
            problems = "; ".join(
                ".".join(str(part) for part in item["loc"]) + ": " + item["type"]
                for item in error.errors()
            )
        raise ConfigError("invalid WhatsApp settings (" + problems + ")")

    @property
    def messages_url(self) -> str:
        return f"{GRAPH_BASE}/{GRAPH_API_VERSION}/{self.phone_number_id}/messages"
