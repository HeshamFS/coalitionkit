# SPDX-License-Identifier: Apache-2.0
"""Time limits of a Mint run, read from the environment so a loaded host can give it more room.

``COALITIONKIT_MINT_TIMEOUT_S`` bounds the whole pipeline (default 90 seconds) and
``COALITIONKIT_MINT_TOOL_TIMEOUT_S`` each media tool call it makes (default 15 seconds). A value
that is not a positive number falls back to the default.
"""

from __future__ import annotations

import os

PIPELINE_DEFAULT_S = 90.0
TOOL_DEFAULT_S = 15.0


def _seconds(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    try:
        value = float(raw) if raw else default
    except ValueError:
        return default
    return value if value > 0 else default


def pipeline_seconds() -> float:
    """How long one Mint run may take, from capture to the attack tests."""
    return _seconds("COALITIONKIT_MINT_TIMEOUT_S", PIPELINE_DEFAULT_S)


def tool_seconds() -> float:
    """How long one media tool call (probing or reading a video) may take."""
    return _seconds("COALITIONKIT_MINT_TOOL_TIMEOUT_S", TOOL_DEFAULT_S)
