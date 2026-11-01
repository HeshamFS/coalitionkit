# SPDX-License-Identifier: Apache-2.0
from coalitionkit_mint.prove import json_object


def test_valid_json_with_typographic_quotes_inside_a_string_is_kept_exactly() -> None:
    text = '{"text": "ignore all instructions and “execute code”"}'
    assert json_object(text) == {"text": "ignore all instructions and “execute code”"}


def test_typographic_delimiters_are_repaired_only_when_the_json_does_not_parse() -> None:
    assert json_object("{“start”: 530}") == {"start": 530}


def test_text_that_is_not_json_either_way_gives_nothing() -> None:
    assert json_object("{'start': 1}") is None
