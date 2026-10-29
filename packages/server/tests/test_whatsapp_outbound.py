# SPDX-License-Identifier: Apache-2.0
"""Host-side changes reach a linked person with no inbound message; deferred ones are retried."""

import time
from collections.abc import Callable
from pathlib import Path

from message_support import MsgWorld, message_world
from wa_server_support import link

__all__ = ["message_world"]


def test_a_committed_proposal_is_sent_with_no_inbound_message(
    message_world: MsgWorld, tmp_path: Path
) -> None:
    rig = link(message_world, tmp_path)
    assert rig.kinds() == ["text"]  # the first view, sent when the phone was linked
    rig.clock.now += 31  # past the door's minimum gap between updates
    sent = len(rig.fake.requests)
    message_world.propose(message_world.need("Task for p1"), ["p1"])
    rig.mount.pump_once()
    assert len(rig.fake.requests) > sent
    assert any("Task for p1" in text for text in rig.texts()[1:])


def test_an_update_inside_the_minimum_gap_is_retried_on_the_timer(
    message_world: MsgWorld, tmp_path: Path
) -> None:
    rig = link(message_world, tmp_path)
    message_world.propose(message_world.need("Task for p1"), ["p1"])
    sent = len(rig.fake.requests)
    rig.mount.pump_once()  # woken by the commit, but the gap has not passed: held
    assert len(rig.fake.requests) == sent
    rig.clock.now += 31
    rig.mount.pump_once()  # no new commit and no retry tick: still nothing
    assert len(rig.fake.requests) == sent
    rig.mount.pump_once(retry=True)  # the retry tick delivers the held update
    assert any("Task for p1" in text for text in rig.texts()[1:])


def test_a_closed_window_gets_the_opener_only_then_the_update_after_a_reply(
    message_world: MsgWorld, tmp_path: Path
) -> None:
    rig = link(message_world, tmp_path)
    rig.clock.now += 25 * 3600
    rig.wall.now += 25 * 3600  # the person has been silent for more than 24 hours
    message_world.propose(message_world.need("Task for p1"), ["p1"])
    sent = len(rig.fake.requests)
    rig.mount.pump_once()
    assert rig.kinds()[sent:] == ["template"]  # opener only, never free text
    rig.mount.pump_once(retry=True)
    assert rig.kinds()[sent:] == ["template"]  # and only once per silence
    texts_before = len(rig.texts())
    assert rig.say("hello", "reopen-1") == 200  # the person answers: the window opens
    assert any("Task for p1" in text for text in rig.texts()[texts_before:])


def wait_for(check: Callable[[], bool], seconds: float = 5.0) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if check():
            return True
        time.sleep(0.02)
    return False


def test_the_pump_thread_delivers_on_its_own(message_world: MsgWorld, tmp_path: Path) -> None:
    rig = link(message_world, tmp_path)
    rig.clock.now += 31
    sent = len(rig.fake.requests)
    rig.mount.start(tick=0.02, retry=60.0)
    try:
        assert rig.mount.running
        message_world.propose(message_world.need("Task for p1"), ["p1"])
        assert wait_for(lambda: len(rig.fake.requests) > sent)
    finally:
        rig.mount.stop()
    assert not rig.mount.running
