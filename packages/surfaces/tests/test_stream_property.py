# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from typing import Any

from ag_ui.core import StateDeltaEvent, StateSnapshotEvent
from hypothesis import given, settings
from hypothesis import strategies as st
from surfaces_support import World, ops_of

from coalitionkit_surfaces import FeedSession, SurfaceHub, apply_patch, json_patch
from coalitionkit_surfaces.fakes import FakeClock

scalars = st.none() | st.booleans() | st.integers(-5, 5) | st.text(max_size=4)
values = st.recursive(
    scalars,
    lambda inner: (
        st.lists(inner, max_size=3) | st.dictionaries(st.text(max_size=3), inner, max_size=3)
    ),
    max_leaves=12,
)
documents = st.dictionaries(st.text(max_size=3), values, max_size=4)


class Sequence:
    coalition_id = "c"

    def __init__(self, docs: list[dict[str, Any]]) -> None:
        self.docs = docs

    def view(self, viewer: str) -> dict[str, Any]:
        return self.docs.pop(0)


@given(st.lists(documents, min_size=2, max_size=6))
@settings(max_examples=150, deadline=None)
def test_deltas_applied_to_the_snapshot_reproduce_every_next_projection(
    docs: list[dict[str, Any]],
) -> None:
    feed = FeedSession(Sequence([dict(d) for d in docs]), "v", clock=FakeClock())
    frames = feed.start()
    state = next(f for f in frames if isinstance(f, StateSnapshotEvent)).snapshot
    assert state == docs[0]
    for expected in docs[1:]:
        for frame in feed.changed():
            assert isinstance(frame, StateDeltaEvent)
            ops = ops_of(frame)
            state = apply_patch(state, ops)
        assert state == expected


@given(documents, documents)
def test_json_patch_is_empty_only_for_equal_documents(a: dict[str, Any], b: dict[str, Any]) -> None:
    ops = json_patch(a, b)
    assert (ops == []) == (a == b)
    assert apply_patch(a, ops) == b


def test_real_host_projection_round_trips_through_deltas(world: World, hub: SurfaceHub) -> None:
    feed = FeedSession(world.host, "bob", clock=FakeClock())
    state = next(f for f in feed.start() if isinstance(f, StateSnapshotEvent)).snapshot
    task = world.need()
    world.propose(task, ["alice", "bob"])
    world.need(scope={"audience": "participants", "participants": ["alice"]})
    for frame in feed.changed():
        assert isinstance(frame, StateDeltaEvent)
        state = apply_patch(state, ops_of(frame))
    assert state == world.host.view("bob")


async def test_stream_driver_sends_snapshot_then_delta_on_bus_wake(
    world: World, hub: SurfaceHub
) -> None:
    hub.max_ticks = 2
    ticks = 0

    async def sleep(_: float) -> None:
        nonlocal ticks
        ticks += 1
        if ticks == 1:
            world.need()

    hub.sleep = sleep
    chunks = [c async for c in hub.stream(hub.feed_session("alice"), "alice")]
    kinds = [c.split('"type":"')[1].split('"')[0] for c in chunks if c.startswith("data:")]
    assert kinds == ["RUN_STARTED", "STATE_SNAPSHOT", "STATE_DELTA"]
