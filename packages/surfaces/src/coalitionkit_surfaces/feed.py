# SPDX-License-Identifier: Apache-2.0
"""The feed session: state and surfaces for one viewer. It never interrupts.

The hub supplies ``log`` and sender-only ``refusals`` as AG-UI state keys:
the initial snapshot includes them, and subsequent wakes send JSON Patch deltas.
Log entries use the same host replay delivery path as the MCP log resource.
Viewer-scoped agent runs travel inside ``coalitionkit.agent`` CUSTOM events so
their interrupts never finish or reset the enclosing feed run.
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping
from copy import deepcopy
from typing import Any, Protocol, cast

from ag_ui.core import (
    ActivitySnapshotEvent,
    CustomEvent,
    RunErrorEvent,
    RunFinishedEvent,
    RunFinishedSuccessOutcome,
    RunStartedEvent,
    StateDeltaEvent,
    StateSnapshotEvent,
    StepFinishedEvent,
    StepStartedEvent,
)

from coalitionkit_contracts import new_ulid
from coalitionkit_runtime import CoalitionHost
from coalitionkit_runtime.projector import ViewerProjection

from .a2ui import ACTIVITY_TYPE
from .agent import AgentSession
from .catalog import Catalog
from .compose import compose_surface
from .frames import Document, Frame, KeepAlive, json_patch

KEEP_ALIVE_SECONDS = 15.0
ROTATE_SECONDS = 600.0


class ViewSource(Protocol):
    """What the feed needs from the host: one viewer's own projection."""

    coalition_id: str

    def view(self, viewer: str) -> Document: ...


class FeedSession:
    """Frames for one connected viewer. Pure state machine: the caller supplies time and wakes."""

    def __init__(
        self,
        source: ViewSource,
        viewer: str,
        *,
        clock: Callable[[], float],
        new_id: Callable[[], str] = new_ulid,
        catalog: Catalog | None = None,
        keep_alive: float = KEEP_ALIVE_SECONDS,
        rotate_after: float = ROTATE_SECONDS,
        extra_state: Callable[[bool, bool], Document] | None = None,
        agent: AgentSession | None = None,
        views: Mapping[str, Mapping[str, tuple[str, ...]]] | None = None,
        roles: Collection[str] = (),
        device: str = "wide",
    ) -> None:
        self.views, self.roles, self.device = views, roles, device
        self.source, self.viewer, self.clock, self.new_id = source, viewer, clock, new_id
        self.catalog, self.keep_alive, self.rotate_after = catalog, keep_alive, rotate_after
        self.thread_id = f"{source.coalition_id}:{viewer}:feed"
        self.run_id = ""
        self._previous: Document = {}
        self._started = 0.0
        self._last_sent = 0.0
        self._pending: list[Frame] = []
        self._surfaces: dict[str, list[Document]] = {}
        self._created: set[str] = set()
        self._closed = False
        self._projection = ViewerProjection(viewer)
        self.agent = agent
        self.extra_state = extra_state
        self._extra: Document = {}

    # -- the run -----------------------------------------------------------------------------

    def start(self) -> list[Frame]:
        """A new run with a fresh snapshot. Connecting, reconnecting and rotating all call this."""
        self._created = set()
        self.run_id = self.new_id()
        self._started = self.clock()
        if isinstance(self.source, CoalitionHost):
            self.source.update_view(self._projection)
            self._previous = self._projection.document
        else:
            self._previous = deepcopy(self.source.view(self.viewer))
        frames: list[Frame] = [
            RunStartedEvent(thread_id=self.thread_id, run_id=self.run_id),
            StateSnapshotEvent(snapshot=deepcopy(self._previous)),
        ]
        if self.extra_state is not None:
            self._extra = self.extra_state(True, True)
            frames[1] = StateSnapshotEvent(snapshot=deepcopy({**self._previous, **self._extra}))
        for surface_id, messages in self._surfaces.items():
            frames.append(self._activity(surface_id, messages))
        if self.agent is not None:
            frames += self._agent_frames(self.agent.start())
        return self._sent(frames)

    def changed(self) -> list[Frame]:
        """Call after a bus wake. A delta only when this viewer's own projection changed."""
        if self._closed:
            return []
        if isinstance(self.source, CoalitionHost):
            ops = self.source.update_view(self._projection)
            self._previous = self._projection.document
        else:
            current = deepcopy(self.source.view(self.viewer))
            ops = json_patch(self._previous, current)
            self._previous = current
        frames: list[Frame] = self._drain()
        if self.extra_state is not None:
            reset = any(op["path"] == "" for op in ops)
            # The provider retains immutable delivered entries. Only outgoing
            # frames need detached copies; ordinary wakes reuse the prefix.
            current_extra = self.extra_state(bool(ops), reset)
            # Replay may freshly sign an unchanged projection. Keep its previous
            # valid envelope so a new log entry does not churn the entire history.
            old_log, new_log = self._extra.get("log", {}), current_extra.get("log", {})
            if reset and old_log.get("host_key") == new_log.get("host_key"):
                for index, (old, new) in enumerate(
                    zip(old_log.get("entries", []), new_log.get("entries", []), strict=False)
                ):
                    if (
                        old.get("type") == new.get("type") == "coalition.projection"
                        and old.get("payload") == new.get("payload")
                        and old.get("scope") == new.get("scope")
                    ):
                        new_log["entries"][index] = deepcopy(old)
            # Membership changes can replace the whole projection document.
            for op in ops:
                if op["path"] == "":
                    op["value"] = {**op["value"], **self._extra}
            old_entries, new_entries = old_log.get("entries", []), new_log.get("entries", [])
            if "log" in current_extra and new_entries[: len(old_entries)] == old_entries:
                # The common case is an append-only prefix. Avoid asking the
                # general list differ to compare the whole verified history.
                unchanged_entries: Document = {
                    **current_extra,
                    "log": {**new_log, "entries": []},
                }
                previous_extra: Document = {**self._extra, "log": {**old_log, "entries": []}}
                ops += json_patch(previous_extra, unchanged_entries)
                ops += [
                    {"op": "add", "path": "/log/entries/-", "value": entry}
                    for entry in new_entries[len(old_entries) :]
                ]
            else:
                ops += json_patch(self._extra, current_extra)
            self._extra = current_extra
        if self.agent is not None:
            frames += self._agent_frames(self.agent.changed())
        if ops:
            frames.insert(0, StateDeltaEvent(delta=cast(Any, deepcopy(ops))))
        return self._sent(frames)

    def tick(self) -> list[Frame]:
        """Call on a timer: queued events, run rotation, or a keep-alive comment."""
        if self._closed:
            return []
        now = self.clock()
        if now - self._started >= self.rotate_after:
            done = RunFinishedEvent(
                thread_id=self.thread_id,
                run_id=self.run_id,
                outcome=RunFinishedSuccessOutcome(),
            )
            return [done, *self.start()]
        frames: list[Frame] = self._drain()
        if self.agent is not None:
            frames += self._agent_frames(self.agent.tick())
        if not frames and now - self._last_sent >= self.keep_alive:
            frames.append(KeepAlive())
        return self._sent(frames)

    @staticmethod
    def _agent_frames(frames: list[Frame]) -> list[Frame]:
        # Nested run boundaries must not finish or reset the feed run.
        return [
            CustomEvent(name="coalitionkit.agent", value=frame.model_dump(by_alias=True))
            for frame in frames
            if not isinstance(frame, KeepAlive)
        ]

    def refusals_changed(self, refusals: list[Document]) -> bool:
        return self._extra.get("refusals", []) != refusals

    def fail(self, message: str, code: str | None = None) -> list[Frame]:
        """End the run with RUN_ERROR. The renderer keeps its last good surface and reconnects."""
        self._closed = True
        return [RunErrorEvent(message=message, code=code)]

    # -- planning steps, surfaces ------------------------------------------------------------

    def step_started(self, name: str) -> None:
        self._pending.append(StepStartedEvent(step_name=name))

    def step_finished(self, name: str) -> None:
        self._pending.append(StepFinishedEvent(step_name=name))

    def publish_surface(
        self,
        surface_id: str,
        components: list[Document],
        data_model: Any = None,
        known_events: Collection[str] | None = None,
    ) -> bool:
        """Queue a composed surface. Returns False when it failed validation and the fallback
        layout was queued instead. Callers pass content already limited to this viewer."""
        if self.catalog is None:
            raise ValueError("no catalog configured")
        composed = compose_surface(
            self.catalog,
            surface_id,
            components,
            data_model,
            known_events,
            views=self.views,
            roles=self.roles,
            device=self.device,
        )
        self._surfaces[surface_id] = composed.messages
        self._pending.append(self._activity(surface_id, composed.messages))
        return not composed.fallback

    def _activity(self, surface_id: str, messages: list[Document]) -> Frame:
        first = surface_id not in self._created
        self._created.add(surface_id)
        sent = messages if first else [m for m in messages if "createSurface" not in m]
        return ActivitySnapshotEvent(
            message_id=f"a2ui:{surface_id}",
            activity_type=ACTIVITY_TYPE,
            content={"messages": deepcopy(sent)},
            replace=True,
        )

    def _drain(self) -> list[Frame]:
        frames, self._pending = self._pending, []
        return frames

    def _sent(self, frames: list[Frame]) -> list[Frame]:
        if frames:
            self._last_sent = self.clock()
        return frames
