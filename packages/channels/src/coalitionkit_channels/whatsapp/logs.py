# SPDX-License-Identifier: Apache-2.0
"""Keeps the webhook verify token out of access logs.

Meta's handshake puts ``hub.verify_token`` in the URL query, and uvicorn's access log prints the
URL. ``install_log_redaction`` hides that value on the access logger (the server CLI also runs
uvicorn with ``access_log=False``; any other launcher should do the same or keep this filter).
"""

from __future__ import annotations

import logging
import re

_TOKEN = re.compile(r"(hub(?:\.|%2E)verify_token=)[^&\s\"']*", re.IGNORECASE)
REDACTED = "[redacted]"
LOGGERS = ("uvicorn.access", "httpx", "httpx2", "httpcore")


class RedactVerifyToken(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        text = record.getMessage()
        if "verify_token" in text.lower():
            record.msg, record.args = _TOKEN.sub(r"\1" + REDACTED, text), None
        return True


def redact(text: str) -> str:
    return _TOKEN.sub(r"\1" + REDACTED, text)


def install_log_redaction() -> None:
    """Idempotent: one filter instance per logger."""
    for name in LOGGERS:
        logger = logging.getLogger(name)
        if not any(isinstance(f, RedactVerifyToken) for f in logger.filters):
            logger.addFilter(RedactVerifyToken())
