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
        waiting = asyncio.ensure_future(anext(stream))
        await asyncio.to_thread(world.need)
        assert "STATE_DELTA" in await asyncio.wait_for(waiting, timeout=1)
    finally:
        await stream.aclose()
