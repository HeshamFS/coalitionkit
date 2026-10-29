# SPDX-License-Identifier: Apache-2.0
"""A reply can only open the trusted confirm step; it is never an owner-signed decision."""

from __future__ import annotations

import itertools

import pytest
from message_support import MsgWorld, Rig, make_rig

from coalitionkit_surfaces.catalog import Catalog
from coalitionkit_surfaces.message import STALE, ConfirmVoid, Doors


def decide_events(world: MsgWorld) -> list[str]:
    return [
        e["event_id"]
        for e in world.host.store.read(world.host.coalition_id)
        if e["type"] == "coalition.decide" and e["payload"]["subject"]["kind"] != "charter"
    ]


def with_plan(world: MsgWorld, catalog: Catalog, doors: Doors) -> Rig:
    world.propose(world.need("Task for p1"), ["p1"])
    rig = make_rig(world, catalog, doors)
    rig.door.sync("p1")
    return rig


def test_a_reply_opens_the_confirm_step_and_signs_nothing(
    message_world: MsgWorld, catalog: Catalog, doors: Doors
) -> None:
    rig = with_plan(message_world, catalog, doors)
    log_before = len(message_world.host.store.read(message_world.host.coalition_id))
    rig.channel.push("p1", "1")
    [outcome] = rig.door.poll()
    assert outcome.kind == "confirm"
    assert outcome.answer is None
    ticket = outcome.ticket
    assert ticket is not None
    assert ticket.subject["kind"] == "plan"
    assert ticket.viewer == "p1"
    reply = rig.channel.texts_to("p1")[-1]
    assert ticket.code in reply
    assert "not your decision" in reply
    log_after = message_world.host.store.read(message_world.host.coalition_id)
    assert len(log_after) == log_before
    assert decide_events(message_world) == []
    assert message_world.host.open_consents("p1")  # still waiting for the owner-signed decision


def test_the_confirm_step_works_once_and_for_that_person_only(
    message_world: MsgWorld, catalog: Catalog, doors: Doors
) -> None:
    rig = with_plan(message_world, catalog, doors)
    rig.channel.push("p1", "1")
    ticket = rig.door.poll()[0].ticket
    assert ticket is not None
    with pytest.raises(ConfirmVoid) as wrong:
        rig.gate.redeem(ticket.code, "p2")
    assert wrong.value.code == ConfirmVoid.WRONG_VIEWER
    assert rig.gate.redeem(ticket.code, "p1") == ticket
    with pytest.raises(ConfirmVoid) as again:
        rig.gate.redeem(ticket.code, "p1")
    assert again.value.code == ConfirmVoid.USED
    with pytest.raises(ConfirmVoid) as unknown:
        rig.gate.redeem("nope", "p1")
    assert unknown.value.code == ConfirmVoid.UNKNOWN


def test_the_confirm_step_expires(message_world: MsgWorld, catalog: Catalog, doors: Doors) -> None:
    rig = with_plan(message_world, catalog, doors)
    rig.channel.push("p1", "1")
    ticket = rig.door.poll()[0].ticket
    assert ticket is not None
    rig.clock.advance(rig.gate.ttl + 1)
    with pytest.raises(ConfirmVoid) as expired:
        rig.gate.redeem(ticket.code, "p1")
    assert expired.value.code == ConfirmVoid.EXPIRED


def test_a_stale_revision_voids_the_confirm_step(
    message_world: MsgWorld, catalog: Catalog, doors: Doors
) -> None:
    task = message_world.need("Task for p1")
    tension = message_world.tension(task)
    rig = make_rig(message_world, catalog, doors)
    rig.door.sync("p1")
    rig.channel.push("p1", "1")
    ticket = rig.door.poll()[0].ticket
    assert ticket is not None
    assert ticket.subject["revision"] == 1
    message_world.tension(task, tension)  # the same tension, now at revision 2
    assert message_world.host.state.subject("tension_option", tension)["revision"] == 2
    with pytest.raises(ConfirmVoid) as stale:
        rig.gate.redeem(ticket.code, "p1")
    assert stale.value.code == ConfirmVoid.STALE


def test_a_reply_to_an_outdated_option_gets_no_ticket(
    message_world: MsgWorld, catalog: Catalog, doors: Doors
) -> None:
    task = message_world.need("Task for p1")
    tension = message_world.tension(task)
    rig = make_rig(message_world, catalog, doors)
    rig.door.sync("p1")
    message_world.tension(task, tension)  # revision 2 before the person replies
    rig.channel.push("p1", "1")
    [outcome] = rig.door.poll()
    assert outcome.kind == "stale"
    assert outcome.ticket is None
    assert rig.channel.texts_to("p1")[-1] == STALE


def test_codes_are_fresh_each_time(message_world: MsgWorld, catalog: Catalog, doors: Doors) -> None:
    message_world.propose(message_world.need("Task for p1"), ["p1"])
    counter = itertools.count(1)
    rig = make_rig(message_world, catalog, doors, make_code=lambda: f"code{next(counter)}")
    rig.door.sync("p1")
    for _ in range(2):
        rig.channel.push("p1", "1")
    codes = [o.ticket.code for o in rig.door.poll() if o.ticket]
    assert codes == ["code1", "code2"]
