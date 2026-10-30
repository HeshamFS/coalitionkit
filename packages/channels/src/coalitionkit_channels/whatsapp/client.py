# SPDX-License-Identifier: Apache-2.0
"""The Cloud API send call: one POST to ``/{version}/{phone-number-id}/messages``.

Retries 429 and 5xx (and refused connections) with exponential backoff. Meta documents no
idempotency header for this call, so de-duplication is done by the caller (see ``channel``).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from .config import OPENER_LANGUAGE, OPENER_TEMPLATE, WhatsAppConfig
from .errors import WhatsAppError

log = logging.getLogger("coalitionkit.channels.whatsapp")

Kind = Literal["text", "template"]


@dataclass
class Usage:
    """Counts only. Never a number, a text or an id."""

    text: int = 0
    template: int = 0
    retries: int = 0
    failures: int = 0
    received: int = 0


def text_body(to: str, text: str) -> dict[str, Any]:
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    }


def template_body(to: str) -> dict[str, Any]:
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "template",
        "template": {"name": OPENER_TEMPLATE, "language": {"code": OPENER_LANGUAGE}},
    }


class WhatsAppClient:
    def __init__(
        self,
        config: WhatsAppConfig,
        *,
        http: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._config, self._sleep = config, sleep
        self._http = http or httpx.Client(timeout=15.0)
        self.usage = Usage()

    def send_text(self, to: str, text: str) -> str:
        return self._post("text", text_body(to, text))

    def send_opener(self, to: str) -> str:
        return self._post("template", template_body(to))

    def close(self) -> None:
        self._http.close()

    def _post(self, kind: Kind, body: dict[str, Any]) -> str:
        cfg = self._config
        headers = {"Authorization": "Bearer " + cfg.token.get_secret_value()}
        status: int | None = None
        for attempt in range(1, cfg.max_attempts + 1):
            try:
                response = self._http.post(cfg.messages_url, json=body, headers=headers)
                status = response.status_code
            except httpx.ConnectError:
                status = None
            except httpx.HTTPError:
                self.usage.failures += 1
                raise WhatsAppError("send failed: transport error") from None
            else:
                if status < 400:
                    return self._accepted(kind, response, attempt)
                if status != 429 and status < 500:
                    self.usage.failures += 1
                    log.warning("whatsapp send refused kind=%s status=%d", kind, status)
                    raise WhatsAppError("send refused", status)
            if attempt < cfg.max_attempts:
                self.usage.retries += 1
                self._sleep(cfg.backoff_seconds * 2 ** (attempt - 1))
        self.usage.failures += 1
        log.warning("whatsapp send gave up kind=%s attempts=%d", kind, cfg.max_attempts)
        raise WhatsAppError("send failed after retries", status)

    def _accepted(self, kind: Kind, response: httpx.Response, attempts: int) -> str:
        try:
            message_id = str(response.json()["messages"][0]["id"])
        except ValueError, KeyError, IndexError, TypeError:
            self.usage.failures += 1
            raise WhatsAppError("unexpected response shape", response.status_code) from None
        if kind == "text":
            self.usage.text += 1
        else:
            self.usage.template += 1
        log.info("whatsapp sent kind=%s attempts=%d", kind, attempts)
        return message_id
