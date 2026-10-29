# SPDX-License-Identifier: Apache-2.0
"""Keeps the webhook verify token out of access logs.

Meta's handshake puts ``hub.verify_token`` in the URL query, and uvicorn's access log prints the
URL. ``install_log_redaction`` hides that value on the access logger (the server CLI also runs
uvicorn with ``access_log=False``; any other launcher should do the same or keep this filter).
"""

from __future__ import annotations

import logging
import re
from urllib.parse import unquote_plus

_PAIR = re.compile(r"([^\s&?#\"'=]+)=([^&\s\"']*)")
SECRET_PARAM = "hub.verify_token"
REDACTED = "[redacted]"
LOGGERS = ("uvicorn.access", "httpx", "httpx2", "httpcore")


def _name(raw: str) -> str:
    """The parameter name as the server reads it: percent-decoded (also when encoded twice)."""
    for _ in range(3):
        decoded = unquote_plus(raw)
        if decoded == raw:
            break
        raw = decoded
    return raw.lower()


def _hide(found: re.Match[str]) -> str:
    if _name(found.group(1)) == SECRET_PARAM:
        return found.group(1) + "=" + REDACTED
    return found.group(0)


def redact(text: str) -> str:
    """Hide the value of ``hub.verify_token`` however the name is spelled (case, %-encoding)."""
    return _PAIR.sub(_hide, text)


class RedactVerifyToken(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        text = record.getMessage()
        hidden = redact(text)
        if hidden != text:
            record.msg, record.args = hidden, None
        return True


def install_log_redaction() -> None:
    """Idempotent: one filter instance per logger."""
    for name in LOGGERS:
        logger = logging.getLogger(name)
        if not any(isinstance(f, RedactVerifyToken) for f in logger.filters):
            logger.addFilter(RedactVerifyToken())
