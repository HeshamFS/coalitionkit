# SPDX-License-Identifier: Apache-2.0
import asyncio

import pytest
from surfaces_support import World

from coalitionkit_surfaces import SurfaceHub


@pytest.mark.asyncio
async def test_bus_wakes_feed_without_waiting_for_timer(hub: SurfaceHub, world: World) -> None:
    hub.sleep = asyncio.sleep
    hub.poll_interval = 60
    stream = hub.stream(hub.feed_session("alice"), "alice")
    try:
        assert "RUN_STARTED" in await anext(stream)
        assert "STATE_SNAPSHOT" in await anext(stream)
        # The initial agent run is carried inside CUSTOM events.
        while "RUN_FINISHED" not in await anext(stream):
            pass
        waiting = asyncio.ensure_future(anext(stream))
        await asyncio.to_thread(world.need)
        assert "STATE_DELTA" in await asyncio.wait_for(waiting, timeout=1)
    finally:
        await stream.aclose()


@pytest.mark.asyncio
async def test_agent_lines_fan_out_to_each_live_tab_without_crossing_viewers(
    hub: SurfaceHub,
) -> None:
    streams = [hub.stream(hub.feed_session(name), name) for name in ("alice", "alice", "bob")]
    streams.append(hub.stream(hub.agent_session("alice"), "alice"))
    try:
        for stream in streams:
            while "RUN_FINISHED" not in await anext(stream):
                pass
        hub.say("alice", "only Alice's tabs")
        hub.say("bob", "only Bob's tab")
        for index, stream in enumerate(streams):
            frames = "".join([frame async for frame in stream])
            expected = "only Alice's tabs" if index != 2 else "only Bob's tab"
            other = "only Bob's tab" if index != 2 else "only Alice's tabs"
            assert expected in frames
            assert other not in frames
    finally:
        for stream in streams:
            await stream.aclose()
    assert not any(hub.feeds.values())
    assert not any(hub.active_agents.values())
    assert not any(hub.outboxes.values())
