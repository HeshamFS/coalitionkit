# SPDX-License-Identifier: Apache-2.0
"""The live gateways for the server runs: Muse Spark 1.3 on the contributor tier.

Only synthetic scenario data goes to the model, so the contributor tier (which allows Meta to
train on prompts) is acceptable. The key is read from ``COALITIONKIT_META_API_KEY`` by the
settings module; it is never stored, printed or passed on.
"""

from __future__ import annotations

import os

from pydantic import SecretStr

from coalitionkit_models import CostMeter, ModelGateway

from .gateways import Kit
from .ledger import KEY_VAR, dedicated_key_set
from .privacy_live import CONTRIBUTOR, CONTRIBUTOR_PRICES, LiveTransport, live_settings
from .privacy_live import KEY_VAR as API_KEY_VAR

__all__ = ["CONTRIBUTOR", "close_kit", "live_enabled", "live_kit", "live_skip_reason"]


def live_enabled() -> bool:
    """COALITIONKIT_LIVE=1 and a key: the dedicated acceptance key, else the API key."""
    on = os.environ.get("COALITIONKIT_LIVE", "") == "1"
    return on and (dedicated_key_set() or bool(os.environ.get(API_KEY_VAR, "").strip()))


def live_skip_reason() -> str:
    if os.environ.get("COALITIONKIT_LIVE", "") != "1":
        return "live test not enabled (set COALITIONKIT_LIVE=1)"
    return "no key"


def live_kit() -> Kit:
    """Two live gateways (server and agents) feeding one meter priced for the contributor tier."""
    settings = live_settings().model_copy(update={"steward_model": CONTRIBUTOR})
    if dedicated_key_set():  # runs made with this key are the ones the export is filtered to
        key = SecretStr(os.environ[KEY_VAR].strip())
        settings = settings.model_copy(update={"meta_api_key": key})
    if dedicated_key_set():  # runs made with this key are the ones the export is filtered to
        key = SecretStr(os.environ[KEY_VAR].strip())
        settings = settings.model_copy(update={"meta_api_key": key})
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
