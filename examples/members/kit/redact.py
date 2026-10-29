# SPDX-License-Identifier: Apache-2.0
"""Keep secrets out of anything that ends up in a scorecard."""

from __future__ import annotations

import re
from collections.abc import Iterable

REDACTED = "[redacted]"
_BEARER = re.compile(r"(?i)\bbearer\s+\S+")
_ASSIGNED = re.compile(r"(?i)\b(api[_-]?key|token|secret|authorization)\b\s*[=:]\s*\S+")
_KEYLIKE = re.compile(r"\b(?:sk|pk|key|tok)[-_][A-Za-z0-9_-]{8,}\b|\b[A-Za-z0-9_-]{32,}\b")


def describe(exc: BaseException) -> str:
    """The exception's type and nothing from its message, which may echo a credential."""
    return f"{type(exc).__name__} (message withheld)"


def scrub(text: str, secrets: Iterable[str] = (), *, patterns: bool = True) -> str:
    """Remove the given secrets and anything shaped like a key or bearer token."""
    for secret in secrets:
        if secret:
            text = text.replace(secret, REDACTED)
    if patterns:
        for pattern in (_BEARER, _ASSIGNED, _KEYLIKE):
            text = pattern.sub(REDACTED, text)
    return text
