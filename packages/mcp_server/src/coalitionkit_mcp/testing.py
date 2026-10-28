# SPDX-License-Identifier: Apache-2.0
"""Test support: a fake token port, a fake view port and a server run on a real localhost port."""

from __future__ import annotations

import threading
import time
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

import uvicorn
from starlette.types import ASGIApp

from coalitionkit_contracts import Membership, Scope, ScopeSource, principals

from .ports import HostedParticipant


@dataclass
class FakeTokenPort:
    """Bearer token to participant, from a dict the test fills."""

    tokens: dict[str, HostedParticipant] = field(default_factory=lambda: {})

    def add(self, token: str, hosted: HostedParticipant) -> None:
        self.tokens[token] = hosted

    async def participant_for(self, token: str) -> HostedParticipant | None:
        return self.tokens.get(token)


@dataclass
class FakeCoalition:
    """One Coalition as the fake view knows it. Extra fields are on purpose: tests check that
    the server's allowlists keep them out of results."""

    goal: str
    charter: dict[str, Any]
    members: dict[str, list[str]]
    revisions: dict[tuple[str, str], int] = field(default_factory=lambda: {})
    tasks: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: {})
    questions: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: {})
    events: list[dict[str, Any]] = field(default_factory=lambda: [])


def _drop(payload: dict[str, Any], paths: list[str]) -> dict[str, Any]:
    kept = deepcopy(payload)
    for path in paths:
        parts = path.split(".")[1:]
        node: Any = kept
        for part in parts[:-1]:
            node = node.get(part, {}) if isinstance(node, dict) else {}  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
        if isinstance(node, dict):
            node.pop(parts[-1], None)  # pyright: ignore[reportUnknownMemberType]
    return kept


class FakeViewPort:
    """A ViewPort over in-memory Coalitions. It scopes log reads the way a host must."""

    def __init__(self) -> None:
        self.by_id: dict[str, FakeCoalition] = {}

    def add(self, coalition_id: str, coalition: FakeCoalition) -> None:
        self.by_id[coalition_id] = coalition

    def _member(self, participant: str, coalition_id: str) -> FakeCoalition | None:
        found = self.by_id.get(coalition_id)
        return found if found is not None and participant in found.members else None

    async def is_member(self, participant: str, coalition_id: str) -> bool:
        return self._member(participant, coalition_id) is not None

    def _summary(self, coalition_id: str, found: FakeCoalition, participant: str) -> dict[str, Any]:
        return {
            "coalition_id": coalition_id,
            "goal": found.goal,
            "roles": found.members[participant],
            "status": "active",
            "revision": found.charter.get("revision"),
            "secret_note": "never shown",
        }

    async def coalitions(self, participant: str) -> list[dict[str, Any]]:
        return [
            self._summary(cid, found, participant)
            for cid, found in self.by_id.items()
            if participant in found.members
        ]

    async def coalition(self, participant: str, coalition_id: str) -> dict[str, Any] | None:
        found = self._member(participant, coalition_id)
        return None if found is None else self._summary(coalition_id, found, participant)

    async def charter(self, participant: str, coalition_id: str) -> dict[str, Any] | None:
        found = self._member(participant, coalition_id)
        return None if found is None else {**found.charter, "secret_note": "never shown"}

    async def my_tasks(self, participant: str, coalition_id: str) -> list[dict[str, Any]]:
        found = self._member(participant, coalition_id)
        return [] if found is None else list(found.tasks.get(participant, []))

    async def pending_questions(self, participant: str, coalition_id: str) -> list[dict[str, Any]]:
        found = self._member(participant, coalition_id)
        return [] if found is None else list(found.questions.get(participant, []))

    async def surface(self, participant: str, coalition_id: str, device: str) -> dict[str, Any]:
        found = self._member(participant, coalition_id)
        if found is None:
            return {}
        return {
            "title": found.goal,
            "status": "active",
            "charter_revision": found.charter.get("revision"),
            "tasks": list(found.tasks.get(participant, [])),
            "questions": list(found.questions.get(participant, [])),
            "secret_note": "never shown",
        }

    async def subject_revision(
        self, participant: str, coalition_id: str, kind: str, subject_id: str
    ) -> int | None:
        found = self._member(participant, coalition_id)
        return None if found is None else found.revisions.get((kind, subject_id))

    async def log(self, participant: str, coalition_id: str, since: int) -> list[dict[str, Any]]:
        found = self._member(participant, coalition_id)
        if found is None:
            return []
        membership = Membership(
            frozenset(found.members),
            {
                role: frozenset(p for p, roles in found.members.items() if role in roles)
                for roles in found.members.values()
                for role in roles
            },
        )
        out: list[dict[str, Any]] = []
        for event in found.events:
            if event["seq"] <= since:
                continue
            scope = Scope.model_validate(event["scope"])
            source = ScopeSource(scope, event["on_behalf_of"])
            chain = {"seq": event["seq"], "prev_hash": event["prev_hash"], "hash": event["hash"]}
            if participant not in principals(source, membership):
                out.append({**chain, "form": "stub", "payload": {"leak": "no"}})
                continue
            redact = scope.redact or []
            base = {**event, "secret_note": "never shown"}
            base.pop("scope")
            if redact:
                base["payload"] = _drop(event["payload"], redact)
                base["redacted"] = redact
                base["form"] = "projection"
            else:
                base["form"] = "original"
            out.append(base)
        return out


class ServedApp:
    """``with ServedApp(app, port):`` serves the app under uvicorn with its lifespan running.

    The edge's own RunningServer turns lifespan off, which would leave the MCP session manager
    unentered, so this one keeps it on.
    """

    def __init__(self, app: ASGIApp, port: int) -> None:
        self.port = port
        self._server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", lifespan="on")
        )
        self._thread = threading.Thread(target=self._server.run, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/mcp"

    def __enter__(self) -> ServedApp:
        self._thread.start()
        deadline = time.monotonic() + 15
        while not self._server.started:
            if time.monotonic() > deadline or not self._thread.is_alive():
                raise RuntimeError("the test server did not start")
            time.sleep(0.02)
        return self

    def __exit__(self, *exc: object) -> None:
        self._server.should_exit = True
        self._thread.join(timeout=15)
