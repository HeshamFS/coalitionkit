# SPDX-License-Identifier: Apache-2.0
"""Offline demo audit responses; the real deterministic Steward still checks every event."""

from collections.abc import Mapping, Sequence
from typing import Any

from coalitionkit_models import CostMeter, ModelGateway, Settings, load_price_table
from coalitionkit_models.gateway import ChatMessage, RawCompletion, Usage
from coalitionkit_models.settings import Route


class DemoAudit:
    async def create(
        self, route: Route, messages: Sequence[ChatMessage], opts: Mapping[str, Any]
    ) -> RawCompletion:
        return RawCompletion(
            '{"action":"allow","policy_id":null,"reason":"scripted demo","redact":[]}',
            Usage(0, 0),
        )


def demo_gateway(*, live: bool = False) -> ModelGateway:
    return ModelGateway(
        Settings(), transport=None if live else DemoAudit(), meter=CostMeter(load_price_table())
    )
