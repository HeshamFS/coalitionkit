# SPDX-License-Identifier: Apache-2.0
"""The hub ties a host to its viewers' sessions and drives the SSE streams."""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from collections.abc import AsyncGenerator, Awaitable, Callable, Mapping
from contextlib import suppress
from typing import Any, Protocol, cast

from coalitionkit_contracts import new_ulid, public_key_to_jwk
from coalitionkit_runtime import CoalitionHost, SubscriberDropped, Subscription

from .agent import AgentSession
from .catalog import Catalog
from .compose import compose_surface
from .feed import FeedSession
from .frames import Document, Frame, encode
from .ports import OwnerSigner, ViewerAuth


class Session(Protocol):
    def start(self) -> list[Frame]: ...
    def changed(self) -> list[Frame]: ...
    def tick(self) -> list[Frame]: ...
    def fail(self, message: str, code: str | None = None) -> list[Frame]: ...


def latest_seq(host: CoalitionHost) -> int:
    events = host.store.read(host.coalition_id)
    return events[-1]["seq"] if events else 0


class SurfaceHub:
    def __init__(
        self,
        host: CoalitionHost,
        auth: ViewerAuth,
        signer_for: Callable[[str], OwnerSigner],
        *,
        catalog: Catalog | None = None,
        clock: Callable[[], float] = time.monotonic,
        new_id: Callable[[], str] = new_ulid,
        sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
        poll_interval: float = 0.5,
        max_ticks: int | None = None,
        pack_state: Callable[[], Document | None] | None = None,
        pack_catalog: Callable[[], Catalog | None] | None = None,
        pack_views: Callable[[], Mapping[str, Mapping[str, tuple[str, ...]]]] | None = None,
    ) -> None:
        self.pack_state, self.pack_catalog, self.pack_views = pack_state, pack_catalog, pack_views
        self.host, self.auth, self.signer_for, self.catalog = host, auth, signer_for, catalog
        self.clock, self.new_id, self.sleep = clock, new_id, sleep
        self.poll_interval, self.max_ticks = poll_interval, max_ticks
        self.outboxes: dict[str, deque[str]] = {}
        self.active_agents: dict[str, int] = {}
        self.feeds: dict[str, list[FeedSession]] = {}
        self.refusals: dict[str, list[Document]] = {}

    def log(
        self,
        viewer: str,
        *,
        fresh: bool = True,
        retained_entries: list[Document] | None = None,
        advance: bool = False,
    ) -> Document:
        # A fresh replay also exposes edits to stored rows rather than masking them
        # behind the runtime's incremental projection cache.
        host = self.host
        reader = (
            CoalitionHost(
                host.store,
                host.coalition_id,
                host.card_url,
                host.private_key,
                host.kid,
                clock=host.clock,
            )
            if fresh
            else host
        )
        entries = reader.replay(viewer) if retained_entries is None else retained_entries
        if retained_entries is not None and advance:
            last = entries[-1] if entries else {}
            since = (
                last["payload"]["source"]["seq"]
                if last.get("type") == "coalition.projection"
                else last.get("seq", 0)
            )
            entries = [*entries, *reader.replay(viewer, since=since)]
        replay_length = len(entries) if retained_entries is None else None
        # Hidden events cannot announce themselves, even as hash-only stubs.
        # Retain intervening stubs when a later visible delivery closes the gap.
        while entries and "type" not in entries[-1]:
            entries.pop()
        with host.store.transaction(host.coalition_id) as tx:
            row = tx.execute(
                "SELECT created_at, seq FROM coalitions WHERE id = ?", (host.coalition_id,)
            ).fetchone()
            rows = tx.execute(
                "SELECT e.body, r.body FROM events e JOIN receipts r "
                "ON e.coalition_id = r.coalition_id AND e.event_id = r.event_id "
                "WHERE e.coalition_id = ? AND e.seq <= ? ORDER BY e.seq",
                (host.coalition_id, replay_length if replay_length is not None else row[1]),
            ).fetchall()
        return {
            "coalition_id": host.coalition_id,
            "host_card_url": host.card_url,
            "created_at": row[0] if row else None,
            "host_key": public_key_to_jwk(host.private_key.public_key(), host.kid),
            "entries": entries,
            "receipts": [
                json.loads(receipt)
                for event, receipt in rows
                if json.loads(event)["on_behalf_of"] == viewer
            ],
        }

    def refused(self, viewer: str, kind: str, error: Document) -> None:
        """Keep only safe refusal metadata, never the refused payload or error detail."""
        if error.get("code") != "steward_blocked":
            return
        item: Document = {"type": kind, "code": "steward_blocked", "at": self.host.clock()}
        policy = error.get("detail", {}).get("policy_id")
        if isinstance(policy, str):
            item["policy"] = policy
        self.refusals.setdefault(viewer, []).append(item)

    def view_as(self, viewer: str, target: str) -> list[Document]:
        """Compose only values present in both projections; never merge their scopes."""
        member = self.host.state.members.get(target)
        if member is None:
            raise KeyError(target)
        own = self.host.view(viewer)["events"]
        other = self.host.view(target)["events"]
        events = {
            key: intersect(own[key], other[key])
            for key in own.keys() & other.keys()
            if own[key]["type"] not in {"coalition.join", "coalition.charter"}
            and not (
                own[key]["type"] == "coalition.decide"
                and own[key]["payload"].get("subject", {}).get("kind") == "charter"
            )
        }
        summary = {"seat": target, "role": member["roles_requested"], "status": "joined"}
        data: Document = {"summary": summary}
        if events:
            # Display numbers carry their provenance, as required by the catalog.
            data["events"] = {key: bound(value, key) for key, value in events.items()}
        from .a2ui import CATALOG_ID
        from .catalog import ComponentSpec, PropSpec

        catalog = self.catalog or Catalog(
            CATALOG_ID, {"Card": ComponentSpec({"title": PropSpec("string", required=True)})}
        )
        return compose_surface(
            catalog,
            "view-as",
            [{"id": "root", "component": "Card", "title": target}],
            data,
            set(events),
        ).messages

    # -- what the rest of the system calls ---------------------------------------------------

    def say(self, viewer: str, text: str) -> None:
        """Deliver only to this viewer, independently on the feed and legacy agent channel."""
        sessions = self.feeds.get(viewer, [])
        if not sessions or self.active_agents.get(viewer, 0):
            self.outboxes.setdefault(viewer, deque()).append(text)
        for session in sessions:
            if session.agent is not None:
                session.agent.say(text)

    def step_started(self, viewer: str, name: str) -> None:
        for session in self.feeds.get(viewer, []):
            session.step_started(name)

    def step_finished(self, viewer: str, name: str) -> None:
        for session in self.feeds.get(viewer, []):
            session.step_finished(name)

    def feed_session(self, viewer: str, device: str = "wide") -> FeedSession:
        log: Document | None = None

        def extra_state(visible_changed: bool, reset: bool) -> Document:
            nonlocal log
            # Hidden bus wakes still refresh the viewer's own receipts, but must
            # neither advance nor re-sign the log's last visible prefix.
            retained = log["entries"] if log is not None and not reset else None
            log = self.log(viewer, fresh=reset, retained_entries=retained, advance=visible_changed)
            state: Document = {"log": log, "refusals": self.refusals.get(viewer, [])}
            pack = self.pack_state() if self.pack_state else None
            if pack is not None:
                state["pack"] = pack
            return state

        agent = AgentSession(
            self.host,
            viewer,
            self.signer_for(viewer),
            clock=self.clock,
            new_id=self.new_id,
        )
        return FeedSession(
            self.host,
            viewer,
            clock=self.clock,
            new_id=self.new_id,
            catalog=self.pack_catalog() if self.pack_catalog else self.catalog,
            views=self.pack_views() if self.pack_views else None,
            roles=self.host.state.members.get(viewer, {}).get("roles_requested", []),
            device=device,
            extra_state=extra_state,
            agent=agent,
        )

    def agent_session(self, viewer: str) -> AgentSession:
        return AgentSession(
            self.host,
            viewer,
            self.signer_for(viewer),
            clock=self.clock,
            new_id=self.new_id,
            outbox=self.outboxes.setdefault(viewer, deque()),
            on_refusal=self.refused,
        )

    # -- streams -----------------------------------------------------------------------------

    async def stream(self, session: Session, viewer: str | None = None) -> AsyncGenerator[str]:
        """SSE text for one connection. Subscribes before the first snapshot so nothing is lost."""
        bus = self.host.bus
        loop = asyncio.get_running_loop()
        wake = asyncio.Event()

        def notify() -> None:
            loop.call_soon_threadsafe(wake.set)

        sub: Subscription = bus.subscribe(
            self.host.coalition_id,
            await asyncio.to_thread(latest_seq, self.host),
            notify,
        )
        registered = isinstance(session, FeedSession) and viewer is not None
        if registered and viewer is not None and isinstance(session, FeedSession):
            self.feeds.setdefault(viewer, []).append(session)
            # Pending messages belong to the next connected channel. Active feed
            # tabs get independent queues; do not retain an unused legacy copy.
            if session.agent is not None and not self.active_agents.get(viewer, 0):
                pending = self.outboxes.setdefault(viewer, deque())
                while pending:
                    session.agent.say(pending.popleft())
        agent_viewer = session.viewer if isinstance(session, AgentSession) else None
        if agent_viewer is not None:
            self.active_agents[agent_viewer] = self.active_agents.get(agent_viewer, 0) + 1
        try:
            try:
                for frame in await asyncio.to_thread(session.start):
                    yield encode(frame)
                ticks = 0
                while self.max_ticks is None or ticks < self.max_ticks:
                    if self.sleep is asyncio.sleep:
                        with suppress(TimeoutError):
                            await asyncio.wait_for(wake.wait(), timeout=self.poll_interval)
                        wake.clear()
                    else:
                        await self.sleep(self.poll_interval)
                    ticks += 1
                    frames = await asyncio.to_thread(self._poll, session, sub)
                    for frame in frames:
                        yield encode(frame)
            except SubscriberDropped:
                for frame in session.fail("connection fell behind", "subscriber_dropped"):
                    yield encode(frame)
            except Exception:
                for frame in session.fail("the stream failed", "stream_error"):
                    yield encode(frame)
        finally:
            bus.unsubscribe(sub)
            if agent_viewer is not None:
                self.active_agents[agent_viewer] -= 1
            if registered and viewer is not None and isinstance(session, FeedSession):
                self.feeds[viewer].remove(session)

    def _poll(self, session: Session, sub: Subscription) -> list[Frame]:
        frames: list[Frame] = []
        if sub.wake.is_set():
            sub.read(self.host.store)  # advances the cursor and clears the wake
            frames += session.changed()
        elif isinstance(session, FeedSession) and session.refusals_changed(
            self.refusals.get(session.viewer, [])
        ):
            frames += session.changed()
        return frames + session.tick()


def intersect(left: Any, right: Any) -> Any:
    """Conservative structural intersection, including viewer-specific list items."""
    if isinstance(left, dict) and isinstance(right, dict):
        left, right = cast(Document, left), cast(Document, right)
        return {
            key: intersect(value, right[key])
            for key, value in left.items()
            if key in right
            and (
                value == right[key]
                or (isinstance(value, (dict, list)) and type(cast(Any, value)) is type(right[key]))
            )
        }
    if isinstance(left, list) and isinstance(right, list):
        return [value for value in cast(list[Any], left) if value in right]
    return cast(Any, left) if left == right else None


def bound(value: Any, event: str) -> Any:
    if isinstance(value, dict):
        return {key: bound(item, event) for key, item in cast(Document, value).items()}
    if isinstance(value, list):
        return [bound(item, event) for item in cast(list[Any], value)]
    if isinstance(value, (float, int)) and not isinstance(value, bool):
        return {"value": value, "event_ref": event}
    return value
