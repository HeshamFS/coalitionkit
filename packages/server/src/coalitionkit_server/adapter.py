# SPDX-License-Identifier: Apache-2.0
"""Translate authenticated edge calls to runtime submissions."""

import asyncio
import json
import logging
from typing import Any

from a2a.types import AgentCard

from coalitionkit_contracts import is_ulid, new_ulid
from coalitionkit_edges.a2a.identity import CardRegistry
from coalitionkit_runtime import Acknowledgement, AuthenticatedSender, CoalitionHost

Document = dict[str, Any]
logger = logging.getLogger("coalitionkit.server")


class HostPort:
    def __init__(self, host: CoalitionHost) -> None:
        self.host = host
        self.cards = CardRegistry(host.coalition_id)

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
        reply = await asyncio.to_thread(self.host.accept, envelope_json, sender)
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
            return {"accepted": reply.accepted, "receipt": reply.receipt}
        logger.info(
            json.dumps({"event_id": reply["payload"]["ref"], "code": reply["payload"]["code"]})
        )
        return {"error": reply["payload"]}
