# SPDX-License-Identifier: Apache-2.0
"""Translate authenticated edge calls to runtime submissions."""

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

from a2a.types import AgentCard
from fastapi import HTTPException

from coalitionkit_contracts import is_ulid, new_ulid
from coalitionkit_edges.a2a.identity import CardRegistry
from coalitionkit_runtime import Acknowledgement, AuthenticatedSender, CoalitionHost
from coalitionkit_runtime.pool import StoreUnavailable

from . import hook

Document = dict[str, Any]
logger = logging.getLogger("coalitionkit.server")


class HostPort:
    def __init__(self, host: CoalitionHost) -> None:
        self.host = host
        self.cards = CardRegistry(host.coalition_id)
        self.on_refusal: Callable[[str, str, Document], None] | None = None
        hook.watch(host.bus)

    def invite(self, participant: str, card_url: str, card: AgentCard) -> None:
        pin = self.cards.admit(card_url, card)
        sender = AuthenticatedSender(card_url, participant)
        self.host.pin_card(sender, pin.public_key, pin.kid)
        self.host.invite(sender)

    async def accept(self, envelope_json: Document, authenticated_sender: str) -> Document:
        pin = self.host.cards.get(authenticated_sender)
        if pin is None:
            ref = envelope_json.get("event_id")
            return {
                "error": {
                    "code": "unknown_participant",
                    "detail": {},
                    "ref": ref if is_ulid(ref) else new_ulid(),
                }
            }
        sender = AuthenticatedSender(authenticated_sender, pin.participant)
        await hook.reached("received", envelope_json)
        try:
            reply = await asyncio.to_thread(self.host.accept, envelope_json, sender)
        except StoreUnavailable:
            raise HTTPException(
                503, "store unavailable; retry the same event", headers={"Retry-After": "1"}
            ) from None
        if isinstance(reply, Acknowledgement):
            await hook.reached("persisted", envelope_json, reply.receipt["payload"]["seq"])
        if isinstance(reply, Acknowledgement):
            payload = reply.receipt["payload"]
            logger.info(
                json.dumps(
                    {
                        "event_id": envelope_json["event_id"],
                        "seq": payload["seq"],
                        "code": "accepted",
                    }
                )
            )
            result: Document = {"accepted": reply.accepted, "receipt": reply.receipt}
            if envelope_json["type"] == "coalition.join":
                result["skills"] = self.host.skills(pin.participant)
            return result
        logger.info(
            json.dumps({"event_id": reply["payload"]["ref"], "code": reply["payload"]["code"]})
        )
        if self.on_refusal is not None:
            self.on_refusal(pin.participant, str(envelope_json.get("type", "")), reply["payload"])
        return {"error": reply["payload"]}
