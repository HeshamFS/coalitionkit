# SPDX-License-Identifier: Apache-2.0
"""Convert receipt-only success to the metadata expected by MCP write tools."""

from coalitionkit_edges.a2a.host_port import HostPort as EdgePort

from .adapter import Document


class MCPPort:
    def __init__(self, host: EdgePort) -> None:
        self.host = host

    async def accept(self, envelope_json: Document, authenticated_sender: str) -> Document:
        reply = await self.host.accept(envelope_json, authenticated_sender)
        note = getattr(self.host, "offered_over_mcp", None)
        # An offer or a line said over MCP means this seat's own agent speaks for it.
        acts = envelope_json.get("type") in {"coalition.offer", "coalition.say"}
        if note and acts and "error" not in reply:
            note(str(envelope_json["coalition_id"]), str(envelope_json["on_behalf_of"]))
        if reply.get("accepted") is None and "receipt" in reply:
            # This internal tool result is not a protocol delivery. Only receipt metadata
            # and the caller's own event id are exposed; the host-only payload stays private.
            return {
                **reply,
                "accepted": {
                    "event_id": envelope_json["event_id"],
                    "seq": reply["receipt"]["payload"]["seq"],
                },
            }
        return reply
