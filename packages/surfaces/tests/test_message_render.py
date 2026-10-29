# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from typing import Any

from coalitionkit_surfaces import bound_number, validate_components
from coalitionkit_surfaces.catalog import Catalog
from coalitionkit_surfaces.message import (
    NOT_SHOWN,
    WITHHELD,
    Doors,
    render_tree,
)

Node = dict[str, Any]
DEADLINE = "2026-10-29T12:00:00Z"
SUBJECT = {"kind": "plan", "id": "plan1", "revision": 2}


def column(*nodes: Node) -> list[Node]:
    root: Node = {"id": "root", "component": "Column", "children": [n["id"] for n in nodes]}
    return [root, *nodes]


def text_of(components: list[Node], doors: Doors, data: Any = None) -> str:
    return "\n".join(s.text for s in render_tree(components, data, doors).sections)


def test_only_components_on_the_message_door_render(doors: Doors, catalog: Catalog) -> None:
    tree = column(
        {"id": "t", "component": "Text", "text": "Hello p1"},
        {"id": "m", "component": "Meter", "label": "Gauge label", "value": bound_number(3, "e1")},
    )
    assert validate_components(catalog, tree) == []
    shown = text_of(tree, doors)
    assert "Hello p1" in shown
    assert "Gauge label" not in shown
    assert NOT_SHOWN in shown


def test_a_hidden_component_falls_back_to_its_declared_summary(doors: Doors) -> None:
    tree = column({"id": "c", "component": "Meter", "label": "x", "summary": "Level is fine"})
    shown = text_of(tree, doors)
    assert "Level is fine" in shown
    assert NOT_SHOWN not in shown


def test_numbers_carry_their_source_event(doors: Doors, catalog: Catalog) -> None:
    tree = column(
        {
            "id": "card",
            "component": "KeyValue",
            "pairs": [{"label": "Count", "value": bound_number(7, "event-1")}],
        }
    )
    assert validate_components(catalog, tree) == []
    assert "Count: 7 [src event-1]" in text_of(tree, doors)


def test_nothing_from_a_vault_appears(doors: Doors) -> None:
    tree = column(
        {
            "id": "card",
            "component": "KeyValue",
            "pairs": [
                {"label": "Open", "value": "visible"},
                {"label": "Secret", "value": "hidden-value", "provenance": "vault"},
            ],
        },
        {"id": "t", "component": "Text", "text": "also-hidden", "provenance": "vault"},
    )
    shown = text_of(tree, doors)
    assert "visible" in shown
    assert "hidden-value" not in shown
    assert "also-hidden" not in shown
    assert WITHHELD in shown


def test_bindings_resolve_against_the_data_model(doors: Doors) -> None:
    tree = column({"id": "t", "component": "Text", "text": {"path": "/note"}})
    assert "From data" in text_of(tree, doors, {"note": "From data"})


def test_values_are_text_only(doors: Doors) -> None:
    tree = column({"id": "t", "component": "Text", "text": "a\x1b[31mred\x07\nnext"})
    shown = text_of(tree, doors)
    assert "\x1b" not in shown
    assert "\x07" not in shown
    assert "next" in shown


def test_options_are_numbered_across_the_whole_view(doors: Doors, catalog: Catalog) -> None:
    tree = column(
        {
            "id": "pick",
            "component": "ChoicePicker",
            "options": [{"id": "y", "label": "Yes"}, {"id": "n", "label": "No"}],
        },
        {
            "id": "ask",
            "component": "ConsentCard",
            "summary": "A plan",
            "consequence": "It binds you.",
            "decision_deadline": DEADLINE,
            "subject": SUBJECT,
        },
    )
    assert validate_components(catalog, tree) == []
    rendered = render_tree(tree, None, doors)
    assert [(o.number, o.kind, o.option_id) for o in rendered.options] == [
        (1, "answer", "y"),
        (2, "answer", "n"),
        (3, "confirm", "plan1"),
    ]
    assert rendered.options[2].subject == SUBJECT
    block = rendered.options_block()
    assert "1. Yes" in block
    assert "2. No" in block
    assert "3. Open the confirm step" in block
    assert not any("1." in s.text for s in rendered.sections)  # section text has no numbers


def test_a_tension_option_can_only_open_the_confirm_step(doors: Doors) -> None:
    subject = {"kind": "tension_option", "id": "ten1", "revision": 1}
    tree = column(
        {
            "id": "tc",
            "component": "TensionCard",
            "options": [{"id": "a", "label": "First"}, {"id": "b", "label": "Second"}],
            "deciders": ["p1"],
            "decision_deadline": DEADLINE,
            "subject": subject,
        }
    )
    options = render_tree(tree, None, doors).options
    assert [(o.kind, o.option_id) for o in options] == [("confirm", "a"), ("confirm", "b")]
