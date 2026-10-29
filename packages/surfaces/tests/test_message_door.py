# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from typing import Any

import pytest
from message_support import NAMES, MsgWorld, make_rig

from coalitionkit_surfaces.catalog import Catalog
from coalitionkit_surfaces.message import (
    HELP,
    INVALID_VIEW,
    NOTHING_OPEN,
    ConfirmGate,
    Doors,
    InMemoryChannel,
    MessageDoor,
    Rendered,
    Section,
    TypedAnswer,
)

Doc = dict[str, Any]


def scoped(names: list[str]) -> Doc:
    return {"audience": "participants", "participants": names}


def test_each_role_gets_only_its_own_scope(
    message_world: MsgWorld, catalog: Catalog, doors: Doors
) -> None:
    message_world.need("Need for everyone")
    message_world.need("Need for p1 only", scoped(["p1"]))
    message_world.need("Need for p2 and p3", scoped(["p2", "p3"]))
    message_world.need("Need for the host only", {"audience": "host"})
    rig = make_rig(message_world, catalog, doors)
    for name in NAMES:
        rig.door.sync(name)
    seen = {name: "\n".join(rig.channel.texts_to(name)) for name in NAMES}
    expected = {
        "p1": {"Need for everyone", "Need for p1 only"},
        "p2": {"Need for everyone", "Need for p2 and p3"},
        "p3": {"Need for everyone", "Need for p2 and p3"},
        "p4": {"Need for everyone"},
    }
    every = {"Need for everyone", "Need for p1 only", "Need for p2 and p3", "Need for the host"}
    for name in NAMES:
        for marker in every:
            assert (marker in seen[name]) == (marker in expected[name]), (name, marker)


def test_a_plan_shows_each_person_only_their_own_assignment(
    message_world: MsgWorld, catalog: Catalog, doors: Doors
) -> None:
    message_world.propose(message_world.need("Shared"), ["p3", "p4"])
    rig = make_rig(message_world, catalog, doors)
    for name in NAMES:
        rig.door.sync(name)
    assert "-> p3" in "\n".join(rig.channel.texts_to("p3"))
    assert "-> p4" not in "\n".join(rig.channel.texts_to("p3"))
    assert "-> p3" not in "\n".join(rig.channel.texts_to("p4"))


def test_only_what_changed_is_sent_to_the_viewer_it_changed_for(
    message_world: MsgWorld, catalog: Catalog, doors: Doors
) -> None:
    message_world.need("First need")
    rig = make_rig(message_world, catalog, doors)
    for name in NAMES:
        rig.door.sync(name)
    sent = len(rig.channel.sent)
    rig.clock.advance(60)
    message_world.need("Second need", scoped(["p2"]))
    counts = {name: rig.door.sync(name) for name in NAMES}
    assert counts == {"p1": 0, "p2": 1, "p3": 0, "p4": 0}
    assert len(rig.channel.sent) == sent + 1
    delta = rig.channel.texts_to("p2")[-1]
    assert delta == "New: Second need"
    assert "First need" not in delta


def test_a_changed_item_is_one_short_line(
    message_world: MsgWorld, catalog: Catalog, doors: Doors
) -> None:
    task = message_world.need("Task one")
    plan = message_world.propose(task, ["p3"])
    rig = make_rig(message_world, catalog, doors)
    rig.door.sync("p3")
    rig.clock.advance(60)
    message_world.propose(message_world.need("Task two"), ["p3"])  # a new plan card for p3
    rig.door.sync("p3")
    delta = rig.channel.texts_to("p3")[-1]
    assert delta == "New: Task two\nNew: Plan"
    assert plan not in delta
    assert len(delta) < 80


def test_deltas_are_rate_limited_per_viewer_and_lose_nothing(
    message_world: MsgWorld, catalog: Catalog, doors: Doors
) -> None:
    message_world.need("Need 0")
    rig = make_rig(message_world, catalog, doors, min_interval=30.0)
    rig.door.sync("p1")
    for index in (1, 2, 3):
        rig.clock.advance(5)
        message_world.need(f"Need {index}")
        assert rig.door.sync("p1") == 0  # held: inside the waiting time
    assert rig.door.flush() == 0
    sent_p1 = len(rig.channel.texts_to("p1"))
    rig.clock.advance(30)
    assert rig.door.flush() >= 1
    held = rig.channel.texts_to("p1")[sent_p1:]
    assert len(held) == 1
    assert all(f"New: Need {i}" in held[0] for i in (1, 2, 3))
    assert rig.door.flush() == 0  # nothing left to send


def test_a_reply_is_one_option_or_a_fixed_help_line(
    message_world: MsgWorld, catalog: Catalog, doors: Doors
) -> None:
    message_world.need("Open need")
    rig = make_rig(message_world, catalog, doors)
    rig.door.sync("p3")  # p3 has nothing to answer
    for text in ("1", "hello", ""):
        outcome = rig.door.handle_reply("p3", text)
        assert outcome.kind == "rejected"
        assert rig.channel.texts_to("p3")[-1] == NOTHING_OPEN
    message_world.propose(message_world.need("Task"), ["p1"])
    rig.clock.advance(60)
    rig.door.sync("p1")
    for text in ("hello", "9", "1 2", "yes please"):
        assert rig.door.handle_reply("p1", text).kind == "rejected"
        assert rig.channel.texts_to("p1")[-1] == HELP


class OneChoice:
    """A source with a ChoicePicker, to check that answers are typed and carry no consent."""

    def tree(self, viewer: str) -> tuple[list[Doc], Any]:
        picker: Doc = {
            "id": "pick",
            "component": "ChoicePicker",
            "options": [
                {"id": "morning", "label": "Morning"},
                {"id": "evening", "label": "Evening"},
            ],
        }
        return [{"id": "root", "component": "Column", "children": ["pick"]}, picker], {}


def test_a_choice_reply_becomes_a_typed_answer(catalog: Catalog, doors: Doors) -> None:
    channel = InMemoryChannel()
    gate = ConfirmGate(lambda _v, _s: False)
    door = MessageDoor(channel, OneChoice(), catalog, doors, gate)
    door.sync("p1")
    assert "2. Evening" in channel.texts_to("p1")[0]
    channel.push("p1", "2")
    [outcome] = door.poll()
    assert outcome.kind == "answer"
    assert outcome.answer == TypedAnswer("p1", "pick", "evening", "Evening")
    assert outcome.ticket is None


def test_a_view_that_fails_validation_is_replaced_by_a_fixed_line(
    catalog: Catalog, doors: Doors
) -> None:
    class Broken:
        def tree(self, viewer: str) -> tuple[list[Doc], Any]:
            return [{"id": "root", "component": "Nope"}], {}

    channel = InMemoryChannel()
    MessageDoor(channel, Broken(), catalog, doors, ConfirmGate(lambda _v, _s: False)).sync("p1")
    assert channel.texts_to("p1") == [INVALID_VIEW]


def test_long_views_split_within_the_limit_and_options_stay_numbered(
    message_world: MsgWorld, catalog: Catalog, doors: Doors
) -> None:
    for index in range(12):
        message_world.need(f"Need number {index} " + "detail " * 8)
    message_world.propose(message_world.need("Task"), ["p1"])
    rig = make_rig(message_world, catalog, doors, limit=200)
    rig.door.sync("p1")
    texts = rig.channel.texts_to("p1")
    assert len(texts) > 1
    assert all(len(t) <= 200 for t in texts)
    assert texts[-1].endswith(f"({len(texts)}/{len(texts)})")
    assert "1. Open the confirm step" in "\n".join(texts)


def test_the_limit_defaults_to_one_thousand(
    message_world: MsgWorld, catalog: Catalog, doors: Doors
) -> None:
    for index in range(40):
        message_world.need(f"Need number {index} " + "detail " * 8)
    rig = make_rig(message_world, catalog, doors)
    rig.door.sync("p1")
    texts = rig.channel.texts_to("p1")
    assert len(texts) > 1
    assert max(len(t) for t in texts) <= 1000


def test_a_limit_that_is_too_small_is_refused_at_once(catalog: Catalog, doors: Doors) -> None:
    with pytest.raises(ValueError, match="at least"):
        MessageDoor(
            InMemoryChannel(),
            OneChoice(),
            catalog,
            doors,
            ConfirmGate(lambda _v, _s: False),
            limit=5,
        )


def test_the_rendered_type_compares_by_value() -> None:
    assert Rendered([Section("a", "x")]) == Rendered([Section("a", "x")])
