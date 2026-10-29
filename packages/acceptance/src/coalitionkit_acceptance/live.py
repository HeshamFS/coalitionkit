# SPDX-License-Identifier: Apache-2.0
"""The live gateways for the server runs: Muse Spark 1.3 on the contributor tier.

Only synthetic scenario data goes to the model, so the contributor tier (which allows Meta to
train on prompts) is acceptable. The key is read from ``COALITIONKIT_META_API_KEY`` by the
settings module; it is never stored, printed or passed on.
"""

from __future__ import annotations

from coalitionkit_models import CostMeter, ModelGateway

from .gateways import Kit
from .privacy_live import (
    CONTRIBUTOR,
    CONTRIBUTOR_PRICES,
    LiveTransport,
    live_enabled,
    live_settings,
    live_skip_reason,
)

__all__ = ["CONTRIBUTOR", "close_kit", "live_enabled", "live_kit", "live_skip_reason"]


def live_kit() -> Kit:
    """Two live gateways (server and agents) feeding one meter priced for the contributor tier."""
    settings = live_settings().model_copy(update={"steward_model": CONTRIBUTOR})
    meter = CostMeter(CONTRIBUTOR_PRICES)
    server_side, agent_side = LiveTransport(settings), LiveTransport(settings)
    return Kit(
        ModelGateway(settings, transport=server_side, meter=meter),
        ModelGateway(settings, transport=agent_side, meter=meter),
        meter,
        (server_side, agent_side),
    )


async def close_kit(kit: Kit) -> None:
    await kit.agents.aclose()
