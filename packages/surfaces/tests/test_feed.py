# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from typing import Any

from ag_ui.core import (
    ActivitySnapshotEvent,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    StateDeltaEvent,
    StateSnapshotEvent,
    StepFinishedEvent,
    StepStartedEvent,
)
from surfaces_support import FIXTURE, World, dump, ops_of

from coalitionkit_surfaces import (
    FeedSession,
    KeepAlive,
    apply_patch,
    fallback_components,
    load_catalog,
)
from coalitionkit_surfaces.fakes import FakeClock


def session(world: World, viewer: str, clock: FakeClock) -> FeedSession:
    return FeedSession(world.host, viewer, clock=clock, catalog=load_catalog(FIXTURE))


class Scripted:
    """A view source whose projection the test sets directly."""

    coalition_id = "c1"

    def __init__(self, *views: dict[str, Any]) -> None:
        self.views = list(views)
        self.calls = 0

    def view(self, viewer: str) -> dict[str, Any]:
        self.calls += 1
        return self.views.pop(0) if len(self.views) > 1 else self.views[0]


# -- C-19: nothing outside the viewer's scope, from the first snapshot on -----------------------


def test_first_snapshot_and_delta_hide_redacted_paths(world: World, clock: FakeClock) -> None:
    redacted = {"audience": "coalition", "redact": ["payload.description"]}
    window = {"start": "2026-10-28T12:00:00Z", "end": "2026-10-29T12:00:00Z"}
    body: dict[str, Any] = {"description": "SECRETDESC", "requirements": [], "window": window}
    world.emit("need", body, redacted)
    feed = session(world, "alice", clock)
    first = feed.start()
    assert [type(f) for f in first] == [RunStartedEvent, StateSnapshotEvent]
    assert "SECRETDESC" not in dump(first)
    assert "window" in dump(first)
    world.emit("need", body, redacted)
    delta = feed.changed()
    assert [type(f) for f in delta] == [StateDeltaEvent]
    assert "SECRETDESC" not in dump(delta) and "description" not in dump(delta)


def test_invisible_change_makes_no_delta_and_visible_one_does(
    world: World, clock: FakeClock
) -> None:
    task = world.need()
    alice, bob = session(world, "alice", clock), session(world, "bob", clock)
    alice.start()
    bob.start()
    only_alice = {"audience": "participants", "participants": ["alice"]}
    query_id = "01JAAAAAAAAAAAAAAAAAAAAAAA"
    world.emit(
        "query",
        {"query_id": query_id, "kind": "feasible", "subject": task, "task_id": task},
        only_alice,
    )
    assert bob.changed() == []
    delta = alice.changed()
    assert [type(f) for f in delta] == [StateDeltaEvent] and query_id in dump(delta)
    assert query_id not in dump(session(world, "bob", clock).start())


def test_other_viewers_plan_assignments_never_reach_a_viewer(
    world: World, clock: FakeClock
) -> None:
    task = world.need()
    bob = session(world, "bob", clock)
    bob.start()
    world.propose(task, ["alice", "bob"])
    delta = dump(bob.changed())
    assert '"assignee":"bob"' in delta and '"assignee":"alice"' not in delta
    assert '"assignee":"alice"' not in dump(session(world, "bob", clock).start())
    assert '"assignee":"alice"' in dump(session(world, "alice", clock).start())


def test_unchanged_projection_sends_nothing() -> None:
    source = Scripted({"a": 1}, {"a": 1})
    feed = FeedSession(source, "v", clock=FakeClock())
    feed.start()
    assert feed.changed() == []


def test_deltas_use_the_viewers_own_projection_not_shared_state(
    world: World, clock: FakeClock
) -> None:
    feed = session(world, "carol", clock)
    feed.start()
    world.need(scope={"audience": "participants", "participants": ["alice", "bob"]})
    assert feed.changed() == []


def test_delta_applied_to_snapshot_gives_next_projection() -> None:
    first, second = {"events": {"a": {"n": 1}}}, {"events": {"a": {"n": 2}, "b": {"n": 3}}}
    source = Scripted(first, second)
    feed = FeedSession(source, "v", clock=FakeClock())
    start = feed.start()
    snapshot = next(f for f in start if isinstance(f, StateSnapshotEvent)).snapshot
    delta = next(f for f in feed.changed() if isinstance(f, StateDeltaEvent))
    ops = ops_of(delta)
    assert apply_patch(snapshot, ops) == second


# -- keep-alive, rotation, reconnect --------------------------------------------------------------


def test_keep_alive_every_fifteen_seconds(clock: FakeClock) -> None:
    feed = FeedSession(Scripted({"a": 1}), "v", clock=clock)
    feed.start()
    clock.advance(14.9)
    assert feed.tick() == []
    clock.advance(0.1)
    assert feed.tick() == [KeepAlive()]
    assert feed.tick() == []
    clock.advance(15)
    assert feed.tick() == [KeepAlive()]


def test_data_resets_the_keep_alive_timer(clock: FakeClock) -> None:
    source = Scripted({"a": 1}, {"a": 2})
    feed = FeedSession(source, "v", clock=clock)
    feed.start()
    clock.advance(10)
    assert feed.changed()
    clock.advance(10)
    assert feed.tick() == []


def test_run_rotates_every_ten_minutes_with_a_fresh_snapshot(clock: FakeClock) -> None:
    ids = iter(f"run{i}" for i in range(10))
    feed = FeedSession(Scripted({"a": 1}), "v", clock=clock, new_id=lambda: next(ids))
    feed.start()
    clock.advance(599)
    assert all(isinstance(f, KeepAlive) for f in feed.tick())
    clock.advance(1)
    frames = feed.tick()
    assert [type(f) for f in frames] == [RunFinishedEvent, RunStartedEvent, StateSnapshotEvent]
    assert isinstance(frames[1], RunStartedEvent) and frames[1].run_id == "run1"
    clock.advance(600)
    assert isinstance(feed.tick()[1], RunStartedEvent)


def test_reconnect_is_a_new_run_with_a_fresh_snapshot(world: World, clock: FakeClock) -> None:
    world.need()
    old = session(world, "alice", clock)
    old.start()
    world.need()
    new = session(world, "alice", clock)
    frames = new.start()
    snapshot = next(f for f in frames if isinstance(f, StateSnapshotEvent)).snapshot
    assert len(snapshot["events"]) == len(world.host.view("alice")["events"])
    assert new.run_id != old.run_id


def test_fail_ends_the_run_with_run_error(clock: FakeClock) -> None:
    feed = FeedSession(Scripted({"a": 1}), "v", clock=clock)
    feed.start()
    frames = feed.fail("boom", "x")
    assert isinstance(frames[0], RunErrorEvent)
    clock.advance(100)
    assert feed.tick() == [] and feed.changed() == []


# -- planning steps and surfaces ------------------------------------------------------------------


def test_planning_steps_go_out_on_the_feed(clock: FakeClock) -> None:
    feed = FeedSession(Scripted({"a": 1}), "v", clock=clock)
    feed.start()
    feed.step_started("match")
    feed.step_finished("match")
    assert [type(f) for f in feed.tick()] == [StepStartedEvent, StepFinishedEvent]


def test_surface_is_an_activity_snapshot_and_survives_rotation(
    world: World, clock: FakeClock
) -> None:
    feed = session(world, "alice", clock)
    feed.start()
    components = [{"id": "root", "component": "Card", "title": "Hello"}]
    assert feed.publish_surface("main", components, {"fields": []})
    (event,) = feed.tick()
    assert isinstance(event, ActivitySnapshotEvent)
    kinds = [next(iter(set(m) - {"version"})) for m in event.content["messages"]]
    assert kinds == ["createSurface", "updateComponents", "updateDataModel"]
    assert feed.publish_surface("main", components, {"fields": []})
    (again,) = feed.tick()
    assert isinstance(again, ActivitySnapshotEvent)
    assert "createSurface" not in dump([again])
    clock.advance(600)
    rotated = feed.tick()
    replay = [f for f in rotated if isinstance(f, ActivitySnapshotEvent)]
    assert len(replay) == 1 and "createSurface" in dump(replay)


def test_invalid_surface_is_replaced_by_the_fallback(world: World, clock: FakeClock) -> None:
    feed = session(world, "alice", clock)
    feed.start()
    assert not feed.publish_surface("main", [{"id": "root", "component": "Script"}])
    (event,) = feed.tick()
    assert isinstance(event, ActivitySnapshotEvent)
    sent = event.content["messages"][1]["updateComponents"]["components"]
    assert sent == fallback_components()
