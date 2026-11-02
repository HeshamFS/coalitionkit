# SPDX-License-Identifier: Apache-2.0
"""The screen after the first sentence is chosen for that sentence, from the closed catalog."""

from __future__ import annotations

import json
import os
import time
from typing import Any

import pytest

from coalitionkit_models import CostMeter, ModelGateway, load_price_table
from coalitionkit_models import Settings as ModelSettings
from coalitionkit_server.genesis_compose import (
    Card,
    CardChoice,
    Composition,
    arrange,
    compose_draft,
    composition_catalog,
)
from coalitionkit_server.genesis_draft import ModelDraft, draft_goal, read_goal
from coalitionkit_surfaces import validate_surface

PLACED = "Twelve of us meet at Hall 3. Finish everything tonight, fairly."
ORDERED = "Sort and pack these boxes across two teams by Friday."
WEEKLY = "Bring the supplies on Saturday and keep the turns fair across the group."


def components(goal: str) -> set[str]:
    return {card.component for card in read_goal(goal).composition.cards}


def test_each_sentence_gets_its_own_components() -> None:
    assert components(PLACED) == {"MapView", "SeatRing", "Deadline", "FairnessMeter"}
    assert components(ORDERED) == {"DependencyGraph", "SeatRing", "Deadline", "CalendarWeek"}
    assert components(WEEKLY) == {"CalendarWeek", "SeatRing", "FairnessMeter"}


@pytest.mark.parametrize("goal", [PLACED, ORDERED, WEEKLY, "Do the thing"])
def test_every_card_passes_the_catalog_and_quotes_the_goal(goal: str) -> None:
    catalog = composition_catalog()
    cards = read_goal(goal).composition.cards
    assert 1 <= len(cards) <= 6
    assert len({card.id for card in cards}) == len(cards)
    assert any(card.component == "SeatRing" for card in cards)
    for card in cards:
        assert card.word is None or card.word in goal
        assert not validate_surface(
            catalog,
            catalog.catalog_id,
            [{"id": "root", "component": card.component, **card.props}],
            known_events={"draft:roles"},
        )


def test_the_place_is_read_in_the_goals_words() -> None:
    assert read_goal(PLACED).draft.place == "Hall 3"
    assert read_goal("Meet at door B12 tonight").draft.place == "door B12"
    assert read_goal("Finish in 3 days").draft.place is None
    assert read_goal(WEEKLY).draft.place is None


def test_the_sheet_is_built_around_what_the_sentence_is_about() -> None:
    placed = read_goal(PLACED).composition.cards
    assert (placed[0].component, placed[0].size) == ("MapView", "hero")
    ordered = read_goal(ORDERED).composition.cards
    assert (ordered[0].component, ordered[0].size) == ("DependencyGraph", "wide")
    weekly = read_goal(WEEKLY).composition.cards
    assert (weekly[0].component, weekly[0].size) == ("CalendarWeek", "hero")


def test_rows_fill_twelve_columns() -> None:
    width = {"wide": 12, "half": 6, "third": 4}

    def rows(n: int, lead: str) -> int:
        cards = [Card(id=lead, component="X", title="", word=None, size="third", props={})]
        cards += [
            Card(id=f"c{i}", component="X", title="", word=None, size="third", props={})
            for i in range(n)
        ]
        arranged = arrange(cards)
        return sum(width[c.size] for c in arranged if c.size != "hero" and c is not arranged[0])

    assert rows(2, "map") % 4 == 0
    assert rows(3, "graph") == 12
    assert rows(5, "graph") % 12 == 0


def test_a_broken_model_choice_falls_back_to_the_readers_cards() -> None:
    result = read_goal(PLACED)
    result.model_cards = [CardChoice(kind="map", word="absent words")]
    composed = compose_draft(result)
    assert composed.source == "reader"
    assert "MapView" in {card.component for card in composed.cards}


def test_no_invented_facts_in_the_props() -> None:
    cards = {c.component: c.props for c in read_goal(WEEKLY).composition.cards}
    assert cards["CalendarWeek"]["events"] == []
    assert all(row["hours"]["value"] == 0 for row in cards["FairnessMeter"]["rows"])


def test_the_reply_model_is_a_closed_schema_and_the_host_reply_is_not_it() -> None:
    schema = ModelDraft.model_json_schema()
    assert schema["additionalProperties"] is False
    assert "composition" not in schema["properties"]
    assert schema["$defs"]["Reading"]["additionalProperties"] is False
    assert schema["$defs"]["CardChoice"]["additionalProperties"] is False
    assert schema["$defs"]["GraphChoice"]["additionalProperties"] is False
    assert Composition().cards == []


@pytest.mark.live
@pytest.mark.parametrize("goal", [PLACED, ORDERED, WEEKLY])
async def test_live_model_composes_within_the_catalog(goal: str) -> None:
    if os.environ.get("COALITIONKIT_LIVE") != "1" or not os.environ.get(
        "COALITIONKIT_META_API_KEY"
    ):
        pytest.skip("no key")
    meter = CostMeter(load_price_table())
    gateway = ModelGateway(ModelSettings(), meter=meter)
    started = time.perf_counter()
    try:
        result = await draft_goal(goal, gateway, 60)
    finally:
        await gateway.aclose()
    measured: dict[str, Any] = {
        "goal": goal,
        "seconds": round(time.perf_counter() - started, 2),
        "source": result.composition.source,
        "components": [card.component for card in result.composition.cards],
        "cost": str(meter.total("")),
    }
    print(json.dumps(measured))
    assert result.composition.cards
    assert any(card.component == "SeatRing" for card in result.composition.cards)
