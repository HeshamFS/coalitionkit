# SPDX-License-Identifier: Apache-2.0
"""Collectors: read every outbound surface of a run into the ledger.

Surfaces covered here: the log, per-viewer deliveries and views, AG-UI feed snapshots and deltas,
agent sessions, A2UI trees, model prompts (the hosted agents and the Steward) and Steward verdicts.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_contracts import Envelope, Scope, ScopeSource, principals
from coalitionkit_models import ChatMessage, ModelGateway, Role, Route, Settings
from coalitionkit_models.gateway import RawCompletion, Usage
from coalitionkit_steward import Artifact, Steward
from coalitionkit_surfaces import (
    CATALOG_ID,
    FeedSession,
    SurfaceHub,
    compose_surface,
)
from coalitionkit_surfaces.catalog import Catalog, ComponentSpec, PropSpec
from coalitionkit_surfaces.fakes import FakeClock, FakeOwnerSigner, FakeViewerAuth
from coalitionkit_surfaces.frames import Frame, KeepAlive

from .canaries import STEWARD
from .privacy_world import NAMES, PrivacyWorld

Document = dict[str, Any]
Reply = Callable[[Sequence[ChatMessage]], str]

HONEST = "honest"
ECHO = "echo"


def frames_text(frames: Sequence[Frame]) -> str:
    return "".join(f.model_dump_json() for f in frames if not isinstance(f, KeepAlive))


def catalog() -> Catalog:
    """The small closed catalog the acceptance surfaces are composed from."""
    return Catalog(
        CATALOG_ID,
        {
            "Card": ComponentSpec(
                {
                    "title": PropSpec("string", required=True),
                    "fields": PropSpec("array"),
                    "status": PropSpec("string"),
                    "provenance": PropSpec("string"),
                    "child": PropSpec("child"),
                }
            ),
            "List": ComponentSpec(
                {
                    "items": PropSpec("array"),
                    "columns": PropSpec("array"),
                    "sort": PropSpec("object"),
                    "children": PropSpec("children"),
                }
            ),
        },
    )


async def _no_sleep(_: float) -> None:
    return None


class Observer:
    """Feeds, agent sessions and the hub for one world; every read lands in the ledger."""

    def __init__(self, world: PrivacyWorld) -> None:
        self.world = world
        self.tokens = {n: f"tok-{world.rng.getrandbits(96):024x}" for n in NAMES}
        self.catalog = catalog()
        people = world.people
        self.hub = SurfaceHub(
            world.host,
            FakeViewerAuth({token: name for name, token in self.tokens.items()}),
            lambda viewer: self.signer(viewer),
            catalog=self.catalog,
            clock=FakeClock(),
            sleep=_no_sleep,
            max_ticks=1,
        )
        self.people = people
        self.feeds: dict[str, FeedSession] = {}

    def signer(self, viewer: str) -> FakeOwnerSigner:
        person = self.world.people[viewer]
        return FakeOwnerSigner(
            self.world.host.coalition_id,
            viewer,
            person.auth.card_url,
            person.agent,
            viewer,
            person.owner,
            viewer + "-owner",
        )

    # -- feeds -------------------------------------------------------------------------------

    def open_feeds(self) -> None:
        for name in NAMES:
            feed = FeedSession(self.world.host, name, clock=lambda: 0.0, catalog=self.catalog)
            self.feeds[name] = feed
            self.world.record("feed_snapshot", name, "feed open", frames_text(feed.start()))

    def step_feeds(self, label: str) -> int:
        """Deltas since the last step, for every connected viewer; returns the frame count."""
        count = 0
        for name, feed in self.feeds.items():
            frames = feed.changed()
            count += len(frames)
            self.world.record("feed_delta", name, label, frames_text(frames))
        return count

    # -- one pass over everything ------------------------------------------------------------

    def collect(self) -> None:
        world = self.world
        for event in world.arena.events():
            world.record("log", "host", f"seq {event['seq']} {event['type']}", event)
        for name in NAMES:
            world.record("view", name, "view", world.host.view(name))
            for item in world.host.replay(name):
                world.record("delivery", name, "replay", item)
            fresh = FeedSession(world.host, name, clock=lambda: 0.0, catalog=self.catalog)
            world.record("feed_snapshot", name, "fresh", frames_text(fresh.start()))
            agent = self.hub.agent_session(name)
            world.record("agent_session", name, "start", frames_text(agent.start()))
            self.record_a2ui(name)

    def record_a2ui(self, name: str) -> None:
        view = self.world.host.view(name)
        events = view["events"]
        ids = [f"e{index}" for index in range(len(events))]
        components: list[Document] = [{"id": "root", "component": "List", "children": ids}]
        rows: list[str] = []
        for ident, (event_id, item) in zip(ids, events.items(), strict=True):
            components.append({"id": ident, "component": "Card", "title": item["type"]})
            rows.append(json.dumps({"event": event_id, "payload": item["payload"]}, default=str))
        composed = compose_surface(
            self.catalog, f"s-{name}", components, {"rows": rows}, list(events)
        )
        self.world.record("a2ui", name, "surface", composed.messages)


# -- model prompts and the Steward ------------------------------------------------------------


class RecordingTransport:
    """A scripted transport that remembers every prompt it was sent."""

    def __init__(self, reply: Reply) -> None:
        self.reply = reply
        self.calls: list[tuple[Role, list[ChatMessage]]] = []

    async def create(
        self, route: Route, messages: Sequence[ChatMessage], opts: Mapping[str, Any]
    ) -> RawCompletion:
        self.calls.append((route.role, list(messages)))
        return RawCompletion(self.reply(messages), Usage(10, 10, 0))


def settings() -> Settings:
    rates: dict[Role, int] = {"gardener": 10**9, "composer": 10**9, "hosted_agent": 10**9,
                              "steward": 10**9, "vault": 10**9}  # fmt: skip
    return Settings(_env_file=None, rate_limit_per_minute=rates)  # pyright: ignore[reportCallIssue]


def allow_text(_: Sequence[ChatMessage]) -> str:
    return json.dumps(
        {"action": "allow", "policy_id": None, "reason": "nothing to flag", "redact": []}
    )


def echo_text(messages: Sequence[ChatMessage]) -> str:
    """The worst-case model: it repeats the message it was asked to judge as its reason."""
    reason = messages[-1]["content"][:480]
    return json.dumps(
        {"action": "escalate", "policy_id": reason[:60], "reason": reason, "redact": []}
    )


async def agent_prompts(world: PrivacyWorld) -> int:
    """Each member's hosted agent is shown that member's own view and nothing else."""
    transport = RecordingTransport(lambda _: "noted")
    gateway = ModelGateway(settings(), transport=transport)
    for name in NAMES:
        view = json.dumps(world.host.view(name), default=str)
        await gateway.complete(
            "hosted_agent",
            [
                {"role": "system", "content": f"You are the agent of {name}. Summarise the view."},
                {"role": "user", "content": view},
            ],
            participant=name,
        )
    for (_, messages), name in zip(transport.calls, NAMES, strict=True):
        world.record("prompt", name, "hosted agent", messages, owner=name)
    return len(transport.calls)


def audience(world: PrivacyWorld, event: Document) -> list[str]:
    """Who may see a verdict about ``event``: whoever may see the event; the host if nobody."""
    seen = principals(
        ScopeSource(Scope.model_validate(event["scope"]), event["on_behalf_of"]),
        world.host.state.membership(),
    )
    return sorted(seen) or ["host"]


async def steward_pass(world: PrivacyWorld, mode: str = HONEST) -> int:
    """Run the Steward over every logged event and every derived output."""
    transport = RecordingTransport(echo_text if mode == ECHO else allow_text)
    gateway = ModelGateway(settings(), transport=transport)
    steward = Steward(gateway, signing_key=Ed25519PrivateKey.generate(), kid="steward")
    verdicts = 0
    for event in world.arena.events():
        if event["type"] in {"coalition.join", "coalition.decide"}:
            continue
        envelope = Envelope.model_validate(event)
        signed = await steward.review(envelope, flagged=True)
        verdicts += 1
        body = signed.body
        for viewer in audience(world, event):
            world.record(
                "steward_verdict",
                viewer,
                f"verdict on seq {event['seq']}",
                [body.policy_id, body.explain, body.redact],
            )
        if event["type"] == "coalition.tension":
            artifact = Artifact(
                coalition_id=event["coalition_id"],
                event_id=event["event_id"],
                revision=1,
                on_behalf_of=event["on_behalf_of"],
                source_type=event["type"],
                scope=Scope.model_validate(event["scope"]),
                content=event["payload"],
            )
            made = await steward.review_artifact(artifact)
            for viewer in audience(world, event):
                world.record(
                    "steward_verdict",
                    viewer,
                    f"artifact verdict {event['event_id']}",
                    [made.body.policy_id, made.body.explain],
                )
    for _, messages in transport.calls:
        world.record("prompt", STEWARD, "steward audit", messages, owner=STEWARD)
    return verdicts
