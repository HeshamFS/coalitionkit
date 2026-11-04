# SPDX-License-Identifier: Apache-2.0
"""MCP and surface adapters, based only on the runtime's scoped projection."""

from typing import Any

from mcp.server.auth.middleware.auth_context import get_access_token

from coalitionkit_mcp.elicit import sign_decision
from coalitionkit_mcp.gateway import build_envelope
from coalitionkit_runtime import CoalitionHost
from coalitionkit_runtime.host import utc_now

from .adapter import Document
from .registry import Registry


class ViewerAuth:
    def __init__(self, registry: Registry, host: CoalitionHost) -> None:
        self.registry, self.host = registry, host

    def viewer_for(self, token: str) -> str | None:
        row = self.registry.lookup(token)
        if row and row["coalition"] == self.host.coalition_id:
            participant: str = row["participant"]
            if participant in self.host.state.members:
                return participant
        return None


class OwnerSigner:
    def __init__(self, registry: Registry, coalition: str, participant: str) -> None:
        self.registry, self.coalition, self.participant = registry, coalition, participant

    def sign_decision(self, subject: Document, choice: str, consent: bool) -> Document:
        person = self.registry.hosted_for(self.coalition, self.participant)
        body = sign_decision(person, self.coalition, subject, choice, consent, utc_now())
        return build_envelope(
            person, self.coalition, "coalition.decide", body, scope={"audience": "coalition"}
        )


class ViewPort:
    def __init__(
        self, hosts: dict[str, CoalitionHost], registry: Registry, room: Any = None
    ) -> None:
        self.hosts, self.registry, self.room = hosts, registry, room

    def authorized(self, participant: str, coalition: str) -> bool:
        access = get_access_token()
        row = self.registry.lookup(access.token) if access else None
        return bool(row and row["coalition"] == coalition and row["participant"] == participant)

    async def is_member(self, participant: str, coalition_id: str) -> bool:
        host = self.hosts.get(coalition_id)
        return (
            self.authorized(participant, coalition_id)
            and host is not None
            and participant in host.state.members
        )

    def events(self, participant: str, coalition: str, kind: str) -> list[Document]:
        host = self.hosts.get(coalition)
        if (
            not self.authorized(participant, coalition)
            or host is None
            or participant not in host.state.members
        ):
            return []
        events: list[Document] = list(host.view(participant)["events"].values())
        return [event["payload"] for event in events if event["type"] == f"coalition.{kind}"]

    async def charter(self, participant: str, coalition_id: str) -> Document | None:
        events = self.events(participant, coalition_id, "charter")
        return events[-1] if events else None

    async def coalition(self, participant: str, coalition_id: str) -> Document | None:
        charter = await self.charter(participant, coalition_id)
        if not await self.is_member(participant, coalition_id):
            return None
        return {
            "coalition_id": coalition_id,
            "goal": (charter or {}).get("goal", ""),
            "roles": (charter or {}).get("roles", []),
            "status": "active",
        }

    async def coalitions(self, participant: str) -> list[Document]:
        result: list[Document] = []
        for coalition in self.hosts:
            item = await self.coalition(participant, coalition)
            if item:
                result.append(item)
        return result

    async def my_tasks(self, participant: str, coalition_id: str) -> list[Document]:
        return self.events(participant, coalition_id, "need")

    async def log(self, participant: str, coalition_id: str, since: int) -> list[Document]:
        if not await self.is_member(participant, coalition_id):
            return []
        return self.hosts[coalition_id].replay(participant, since)

    async def open_asks(self, participant: str, coalition_id: str) -> list[Document]:
        host = self.hosts.get(coalition_id)
        if host is None or not await self.is_member(participant, coalition_id):
            return []
        asks: list[Document] = []
        for ask in host.open_consents(participant):
            if ask["kind"] == "tension_option":
                options = host.state.subject("tension_option", ask["id"]).get("options", [])
                ask = {**ask, "options": options}
            asks.append(ask)
        return asks

    async def pending_questions(self, participant: str, coalition_id: str) -> list[Document]:
        answered = {item["query_id"] for item in self.events(participant, coalition_id, "answer")}
        return [
            item
            for item in self.events(participant, coalition_id, "query")
            if item.get("query_id") not in answered
        ]

    async def surface(self, participant: str, coalition_id: str, device: str) -> Document:
        if not await self.is_member(participant, coalition_id):
            return {}
        return self.hosts[coalition_id].view(participant)

    async def talk(self, participant: str, coalition_id: str) -> Document | None:
        """The room's talk, from this participant's own projection. No whisper is included."""
        host = self.hosts.get(coalition_id)
        if host is None or not await self.is_member(participant, coalition_id):
            return None
        if self.room is None or not self.room.drives(coalition_id):
            thread = [
                {
                    **e["payload"],
                    "id": e["event_id"],
                    "seq": e.get("seq"),
                    "from": e["on_behalf_of"],
                }
                for e in host.view(participant)["events"].values()
                if e["type"] == "coalition.say"
            ]
            return {"open": False, "round": 0, "rounds": 0, "thread": thread}
        from .room.talk_view import talk_of

        found = talk_of(
            self.room, coalition_id, participant, host.state, self.room.read(coalition_id)
        )
        return {k: v for k, v in found.items() if k != "mine"}

    async def subject_revision(
        self, participant: str, coalition_id: str, kind: str, subject_id: str
    ) -> int | None:
        if not await self.is_member(participant, coalition_id):
            return None
        # Consent metadata is already limited to the requesting decider by the host.
        for item in self.hosts[coalition_id].open_consents(participant):
            if item.get("kind") == kind and item.get("id", item.get("subject_id")) == subject_id:
                return int(item["revision"])
        return None
