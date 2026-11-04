# SPDX-License-Identifier: Apache-2.0
"""What a person reads in a result: whole lines and no internals."""

from coalitionkit_server.genesis_draft import read_goal
from coalitionkit_server.room.makers import short_line
from coalitionkit_server.room.results import shows_internals
from coalitionkit_server.room.say import OPENS_TO_ROOM


def test_a_line_drops_its_tail_about_being_a_proposal() -> None:
    assert (
        short_line("Baguette sandwiches with cheese - this is a proposal for the group", 100)
        == "Baguette sandwiches with cheese"
    )
    assert (
        short_line("Member 2 confirms the place, this whole schedule is a proposal to adjust", 140)
        == "Member 2 confirms the place"
    )
    assert short_line("Water and juice", 100) == "Water and juice"


def test_internal_fields_and_empty_values_are_refused() -> None:
    def tree(*fields: dict[str, str]) -> list[dict[str, object]]:
        return [{"id": "root", "component": "Card", "title": "Place", "fields": list(fields)}]

    assert shows_internals(tree({"label": "why", "value": "It has shade"}), "N1") is None
    assert shows_internals(tree({"label": "id", "value": "22TQ"}), "N1")
    assert shows_internals(tree({"label": "kind", "value": "place"}), "N1")
    assert shows_internals(tree({"label": "chosen", "value": "null"}), "N1")
    assert shows_internals(tree({"label": "why", "value": "None"}), "N1")
    assert shows_internals(tree({"label": "note", "value": "see 22TQVW"}), "22TQVW")


def test_counted_people_become_seats() -> None:
    for goal in ("Two friends plan a picnic", "three colleagues share lunch", "4 neighbours meet"):
        wanted = {"Two": 2, "three": 3, "4": 4}[goal.split()[0]]
        assert [(r.id, r.count) for r in read_goal(goal).draft.roles] == [("member", wanted)]


def test_a_sentence_that_opens_to_the_room_is_for_the_room() -> None:
    for text in ("Everyone, call me", "@room hello", "tell the group I am late", "room: hi"):
        assert OPENS_TO_ROOM.match(text)
    for text in ("all good here", "room for one more?", "I told everyone"):
        assert not OPENS_TO_ROOM.match(text)
