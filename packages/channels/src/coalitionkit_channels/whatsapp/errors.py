# SPDX-License-Identifier: Apache-2.0
"""Errors carry a fixed reason and a status code, never a body, URL, header or token."""

from __future__ import annotations


class WhatsAppError(Exception):
    def __init__(self, reason: str, status: int | None = None) -> None:
        super().__init__(reason if status is None else f"{reason} (HTTP {status})")
        self.reason, self.status = reason, status


class WindowClosed(WhatsAppError):
    """Free text is refused outside the 24-hour window; only the opener template may go."""

    def __init__(self) -> None:
        super().__init__("outside the 24-hour window: free text refused")


class RateLimited(WhatsAppError):
    def __init__(self) -> None:
        super().__init__("per-recipient send limit reached")


class NotBound(WhatsAppError):
    def __init__(self) -> None:
        super().__init__("viewer has no linked WhatsApp id")
