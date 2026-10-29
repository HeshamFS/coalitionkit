# SPDX-License-Identifier: Apache-2.0
"""``X-Hub-Signature-256``: HMAC-SHA256 of the raw request body, keyed with the app secret.

Meta's webhook guide: the header is ``sha256=<hex digest>`` over the payload as received.
"""

from __future__ import annotations

import hashlib
import hmac

PREFIX = "sha256="


def sign(body: bytes, app_secret: str) -> str:
    """The header value for ``body`` (used by tests and local tools)."""
    return PREFIX + hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()


def verify(body: bytes, header: str | None, app_secret: str) -> bool:
    """True only for a well-formed header that matches; compared in constant time."""
    if not header or not header.startswith(PREFIX):
        return False
    expected = sign(body, app_secret)
    return hmac.compare_digest(expected.encode(), header.encode("utf-8", "replace"))
