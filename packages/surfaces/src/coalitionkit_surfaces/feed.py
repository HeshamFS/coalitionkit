# SPDX-License-Identifier: Apache-2.0
"""The feed session: state and surfaces for one viewer. It never interrupts."""

from __future__ import annotations

from collections.abc import Callable, Collection
from copy import deepcopy
from typing import Any, Protocol, cast

from ag_ui.core import (
    ActivitySnapshotEvent,
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

from .a2ui import ACTIVITY_TYPE
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
    ) -> None:
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

    # -- the run -----------------------------------------------------------------------------

    def start(self) -> list[Frame]:
        """A new run with a fresh snapshot. Connecting, reconnecting and rotating all call this."""
        self._created = set()
        self.run_id = self.new_id()
        self._started = self.clock()
        self._previous = deepcopy(self.source.view(self.viewer))
        frames: list[Frame] = [
            RunStartedEvent(thread_id=self.thread_id, run_id=self.run_id),
            StateSnapshotEvent(snapshot=deepcopy(self._previous)),
        ]
        for surface_id, messages in self._surfaces.items():
            frames.append(self._activity(surface_id, messages))
        return self._sent(frames)

    def changed(self) -> list[Frame]:
        """Call after a bus wake. A delta only when this viewer's own projection changed."""
        if self._closed:
            return []
        current = deepcopy(self.source.view(self.viewer))
        ops = json_patch(self._previous, current)
        self._previous = current
        frames: list[Frame] = self._drain()
        if ops:
            frames.insert(0, StateDeltaEvent(delta=cast(Any, ops)))
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
        if not frames and now - self._last_sent >= self.keep_alive:
            frames.append(KeepAlive())
        return self._sent(frames)

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
        composed = compose_surface(self.catalog, surface_id, components, data_model, known_events)
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
