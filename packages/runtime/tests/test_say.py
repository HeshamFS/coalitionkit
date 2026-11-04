# SPDX-License-Identifier: Apache-2.0
"""``coalition.say``: one line to the room or to one seat, checked like any member message."""

from __future__ import annotations

from coalitionkit_contracts import new_ulid

from .conftest import World, accepted, error

ROOM = {"audience": "coalition"}


def line(to: str = "room", **extra: str) -> dict[str, str]:
    return {
        "to": to,
        "text": "I could take the shopping if someone cooks.",
        "intent": "trade",
    } | extra


def test_say_to_the_room_and_to_a_seat_is_accepted_and_seen(world: World) -> None:
    first = accepted(world.alice.send("say", line(), ROOM))
    accepted(
        world.bob.send("say", line("alice", intent="agree", re=first.accepted["event_id"]), ROOM)
    )
    seen = [
        e for e in world.host.view("observer")["events"].values() if e["type"] == "coalition.say"
    ]
    assert [e["payload"]["to"] for e in seen] == ["room", "alice"]


def test_say_to_yourself_a_stranger_or_an_unseen_event_is_refused(world: World) -> None:
    error(world.alice.send("say", line("alice"), ROOM), "not_authorized")
    error(world.alice.send("say", line("nobody"), ROOM), "not_authorized")
    error(world.alice.send("say", line(re=new_ulid()), ROOM), "not_authorized")
    hidden = world.need({"audience": "participants", "participants": ["alice"]})
    event = hidden.accepted["event_id"]
    error(world.bob.send("say", line(re=event), ROOM), "not_authorized")


def test_say_too_long_is_a_schema_refusal(world: World) -> None:
    error(world.alice.send("say", line(text="x" * 281), ROOM), "schema_invalid")
