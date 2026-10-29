# SPDX-License-Identifier: Apache-2.0
"""Model gateways for the server runs: a scripted one, and the live one on the contributor tier.

The Steward audits every proposal set with a model. Scripted runs answer ``allow`` with fixed
usage; live runs call Muse Spark 1.3 (contributor tier, synthetic data only). Both are metered.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from coalitionkit_models import CostMeter, ModelGateway, Settings, load_price_table
from coalitionkit_models.gateway import ChatMessage, RawCompletion, Usage
from coalitionkit_models.settings import ROLES, Role, Route

ALLOW = '{"action": "allow", "policy_id": null, "reason": "scripted", "redact": []}'


class AuditTransport:
    """Answers every call with an ``allow`` verdict; usage depends on the prompt size only."""

    def __init__(self) -> None:
        self.calls = 0

    async def create(
        self, route: Route, messages: Sequence[ChatMessage], opts: Mapping[str, Any]
    ) -> RawCompletion:
        self.calls += 1
        size = sum(len(m["content"]) for m in messages)
        return RawCompletion(ALLOW, Usage(200 + size // 4, 30, 0))


def scripted_gateway(meter: CostMeter) -> tuple[ModelGateway, AuditTransport]:
    limits: dict[Role, int] = dict.fromkeys(ROLES, 10_000_000)
    settings = Settings(_env_file=None, rate_limit_per_minute=limits)  # pyright: ignore[reportCallIssue]
    transport = AuditTransport()
    return ModelGateway(settings, transport=transport, meter=meter), transport


def new_meter() -> CostMeter:
    return CostMeter(load_price_table())


@dataclass(frozen=True)
class Kit:
    """The gateway of the server, the gateway of the agents, and the one meter both feed.

    The two gateways are separate objects when they reach a real model, because each owns HTTP
    clients that belong to the event loop that first used them (the server's Steward has its own).
    """

    gateway: ModelGateway
    agents: ModelGateway
    meter: CostMeter
    transports: tuple[Any, ...] = ()


def scripted_kit() -> Kit:
    meter = new_meter()
    gateway = scripted_gateway(meter)[0]
    return Kit(gateway, gateway, meter)
