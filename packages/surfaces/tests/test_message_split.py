# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from coalitionkit_surfaces.message import Option, parse_reply, split_blocks

OPTIONS = [Option(n, f"Option {n}", "answer", "c1", f"o{n}") for n in (1, 2, 3)]


def test_a_short_text_is_one_message() -> None:
    assert split_blocks(["one", "two"], 1000) == ["one\n\ntwo"]


def test_blocks_stay_whole_and_parts_are_numbered() -> None:
    blocks = [f"Block {i} " + "w" * 30 for i in range(6)]
    parts = split_blocks(blocks, 100)
    assert len(parts) > 1
    assert all(len(p) <= 100 for p in parts)
    for index, part in enumerate(parts, start=1):
        assert part.endswith(f"({index}/{len(parts)})")
    joined = "\n\n".join(parts)
    assert all(block in joined for block in blocks)  # no block cut in the middle


def test_a_long_block_splits_on_lines_then_words_then_characters() -> None:
    lines = "\n".join(f"line {i} " + "x" * 20 for i in range(12))
    parts = split_blocks([lines], 120)
    assert all(len(p) <= 120 for p in parts)
    assert all(line in "\n".join(parts) for line in lines.split("\n"))
    words = split_blocks([" ".join(["word"] * 100)], 60)
    assert all(len(p) <= 60 for p in words)
    assert sum(p.count("word") for p in words) == 100
    hard = split_blocks(["y" * 500], 100)
    assert all(len(p) <= 100 for p in hard)
    assert sum(p.count("y") for p in hard) == 500


def test_a_limit_that_is_too_small_is_refused() -> None:
    with pytest.raises(ValueError, match="at least"):
        split_blocks(["x"], 10)


@given(st.lists(st.text(max_size=400), max_size=8), st.integers(min_value=40, max_value=300))
def test_no_part_is_over_the_limit_and_no_character_is_lost(blocks: list[str], limit: int) -> None:
    parts = split_blocks(blocks, limit)
    assert all(len(p) <= limit for p in parts)
    kept = "".join(parts)
    for block in blocks:
        for char in set(block) - set(" \n"):
            assert char in kept


@pytest.mark.parametrize("reply", ["2", " 2 ", "2.", "2)", "#2", "Option 2", "option2", "٢"])
def test_a_reply_that_names_one_option_parses(reply: str) -> None:
    option = parse_reply(reply, OPTIONS)
    assert option is not None
    assert option.number == 2


@pytest.mark.parametrize(
    "reply", ["", "yes", "0", "4", "1 2", "1,2", "two", "-1", "1 please", "2" * 50, "1\n2"]
)
def test_any_other_reply_is_rejected(reply: str) -> None:
    assert parse_reply(reply, OPTIONS) is None
