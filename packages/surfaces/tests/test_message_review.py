# SPDX-License-Identifier: Apache-2.0
"""Regression tests for the message door."""

from __future__ import annotations

from typing import Any

import pytest
from message_support import MsgWorld, make_rig

from coalitionkit_surfaces.catalog import Catalog
from coalitionkit_surfaces.message import (
    WITHHELD,
    ConfirmGate,
    Doors,
    HostTreeSource,
    InMemoryChannel,
    MessageDoor,
    Reply,
    render_tree,
    split_blocks,
)

Node = dict[str, Any]


def texts(components: list[Node], doors: Doors) -> str:
    return "\n".join(s.text for s in render_tree(components, None, doors).sections)


# 1. A withheld component withholds its whole subtree, whatever else it carries.


def test_a_vault_summary_on_an_off_door_component_does_not_print(doors: Doors) -> None:
    tree: list[Node] = [
        {"id": "root", "component": "Column", "children": ["m"]},
        {
            "id": "m",
            "component": "Meter",
            "label": "x",
            "summary": "secret",
            "provenance": "vault",
        },
    ]
    shown = texts(tree, doors)
    assert "secret" not in shown
    assert WITHHELD in shown


def test_a_vault_root_prints_nothing_from_its_children(doors: Doors) -> None:
    tree: list[Node] = [
        {"id": "root", "component": "Column", "provenance": "vault", "children": ["a", "pick"]},
        {"id": "a", "component": "Text", "text": "ordinary child"},
        {
            "id": "pick",
            "component": "ChoicePicker",
            "options": [{"id": "o", "label": "ordinary option"}],
        },
    ]
    rendered = render_tree(tree, None, doors)
    assert "ordinary" not in "\n".join(s.text for s in rendered.sections)
    assert rendered.options == []


def test_a_vault_subtree_hides_its_options_and_descendants(doors: Doors) -> None:
    tree: list[Node] = [
        {"id": "root", "component": "Column", "children": ["box", "ok"]},
        {"id": "box", "component": "Column", "provenance": "vault", "children": ["inner"]},
        {"id": "inner", "component": "Text", "text": "inner secret"},
        {"id": "ok", "component": "Text", "text": "fine"},
    ]
    shown = texts(tree, doors)
    assert "inner secret" not in shown
    assert "fine" in shown


# 2. A tension offers its real options, and the ticket binds the option and the revision.


def test_a_tension_offers_its_options_and_the_ticket_names_one(
    message_world: MsgWorld, catalog: Catalog, doors: Doors
) -> None:
    tension = message_world.tension(message_world.need("Task"))
    rig = make_rig(message_world, catalog, doors)
    rig.door.sync("p1")
    shown = "\n".join(rig.channel.texts_to("p1"))
    assert "1. First (opens the confirm step)" in shown
    assert "2. Second (opens the confirm step)" in shown
    rig.channel.push("p1", "2")
    [outcome] = rig.door.poll()
    assert outcome.ticket is not None
    assert outcome.ticket.choice == "b"
    assert outcome.ticket.subject == {"kind": "tension_option", "id": tension, "revision": 1}


def test_a_new_tension_revision_offers_the_new_subject(
    message_world: MsgWorld, catalog: Catalog, doors: Doors
) -> None:
    task = message_world.need("Task")
    tension = message_world.tension(task)
    rig = make_rig(message_world, catalog, doors, min_interval=0.0)
    rig.door.sync("p1")
    message_world.tension(task, tension)
    rig.door.sync("p1")
    rig.channel.push("p1", "1")
    [outcome] = rig.door.poll()
    assert outcome.ticket is not None
    assert outcome.ticket.subject["revision"] == 2
    assert outcome.ticket.choice == "a"


# 3. State moves only after a successful send; the rest of a failed message is kept.


class Flaky:
    """Fails the sends whose (1-based) attempt number is in ``fail_on``."""

    def __init__(self, fail_on: set[int]) -> None:
        self.inner = InMemoryChannel()
        self.fail_on, self.attempts = fail_on, 0

    def send(self, viewer: str, text: str) -> None:
        self.attempts += 1
        if self.attempts in self.fail_on:
            raise OSError("channel down")
        self.inner.send(viewer, text)

    def receive(self) -> list[Reply]:
        return self.inner.receive()


def door_over(
    channel: Flaky, world: MsgWorld, catalog: Catalog, doors: Doors, limit: int = 1000
) -> MessageDoor:
    return MessageDoor(
        channel,
        HostTreeSource(world.host),
        catalog,
        doors,
        ConfirmGate(lambda _v, _s: False),
        limit=limit,
        min_interval=0.0,
    )


def test_a_failed_first_view_is_sent_on_the_next_sync(
    message_world: MsgWorld, catalog: Catalog, doors: Doors
) -> None:
    message_world.need("Need one")
    channel = Flaky({1})
    door = door_over(channel, message_world, catalog, doors)
    with pytest.raises(OSError, match="channel down"):
        door.sync("p3")
    assert channel.inner.sent == []
    assert door.sync("p3") == 1
    assert "Need one" in channel.inner.texts_to("p3")[0]
    assert door.sync("p3") == 0  # now it counts as sent


def test_a_failed_delta_is_not_lost(
    message_world: MsgWorld, catalog: Catalog, doors: Doors
) -> None:
    message_world.need("Need one")
    channel = Flaky({2})
    door = door_over(channel, message_world, catalog, doors)
    door.sync("p3")
    message_world.need("Need two")
    with pytest.raises(OSError, match="channel down"):
        door.sync("p3")
    message_world.need("Need three")  # the state moves on while the delivery is stuck
    assert door.sync("p3") == 2  # the stuck message, then the newer change
    assert channel.inner.texts_to("p3")[-2:] == ["New: Need two", "New: Need three"]
    assert door.flush() == 0
    assert door.sync("p3") == 0


def test_a_newer_change_waits_pending_when_the_rate_limit_holds_it(
    message_world: MsgWorld, catalog: Catalog, doors: Doors
) -> None:
    message_world.need("Need one")
    rig = make_rig(message_world, catalog, doors, min_interval=30.0)
    rig.door.sync("p3")
    rig.clock.advance(31)
    message_world.need("Need two")
    rig.door.sync("p3")
    message_world.need("Need three")
    assert rig.door.sync("p3") == 0  # inside the waiting time: held, not dropped
    rig.clock.advance(31)
    assert rig.door.flush() == 1
    assert rig.channel.texts_to("p3")[-1] == "New: Need three"


def test_a_partly_delivered_message_resumes_with_the_missing_parts_only(
    message_world: MsgWorld, catalog: Catalog, doors: Doors
) -> None:
    for index in range(10):
        message_world.need(f"Need number {index} " + "detail " * 6)
    whole = Flaky(set())
    door_over(whole, message_world, catalog, doors, limit=120).sync("p3")
    expected = whole.inner.texts_to("p3")
    assert len(expected) > 3
    channel = Flaky({3})
    door = door_over(channel, message_world, catalog, doors, limit=120)
    with pytest.raises(OSError, match="channel down"):
        door.sync("p3")
    assert len(channel.inner.texts_to("p3")) == 2
    door.sync("p3")
    assert channel.inner.texts_to("p3") == expected  # nothing repeated, nothing missing
    assert door.sync("p3") == 0


# 5. The page suffix is sized from the page count.


def test_four_digit_page_counts_stay_within_the_limit() -> None:
    parts = split_blocks(["x" * 30000], 40)
    assert len(parts) >= 1000
    assert max(len(p) for p in parts) <= 40
    assert parts[-1].endswith(f"({len(parts)}/{len(parts)})")
    assert sum(p.count("x") for p in parts) == 30000


@pytest.mark.parametrize("size", [90, 900, 9000, 90000])
def test_the_limit_holds_at_every_page_count_boundary(size: int) -> None:
    for limit in (40, 41, 55):
        parts = split_blocks(["y" * size], limit)
        assert max(len(p) for p in parts) <= limit
        assert sum(p.count("y") for p in parts) == size
