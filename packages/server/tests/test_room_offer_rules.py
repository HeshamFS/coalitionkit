# SPDX-License-Identifier: Apache-2.0
"""What an offer means: one estimate per need, capped per offer, and no bare need."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from coalitionkit_server.adapter import Document
from coalitionkit_server.room.offer_rules import (
    MAX_MINUTES,
    MIN_MINUTES,
    Limits,
    OfferItem,
    OffersReply,
    checked,
    cover_items,
    limits,
    rule_offers,
    span,
)

KINDS = ["place", "schedule", "budget", "list", "draft"]


def needs_of(kinds: list[str]) -> list[Document]:
    return [
        {"id": f"n{i}", "title": f"Job {chr(97 + i)} {k}", "kind": k, "detail": ""}
        for i, k in enumerate(kinds)
    ]


limit_strategy = st.builds(
    Limits,
    cap=st.one_of(st.none(), st.just(0), st.integers(min_value=60, max_value=60 * 40)),
    money=st.integers(min_value=0, max_value=500),
    picked=st.lists(
        st.sampled_from(["Job a place", "Job b budget", "nothing like it"]), max_size=2
    ).map(tuple),
    answered=st.booleans(),
)
item_strategy = st.builds(
    OfferItem,
    need_id=st.sampled_from(["n0", "n1", "n2", "n3", "wrong", ""]),
    minutes=st.integers(min_value=-(10**9), max_value=10**12),
    money=st.integers(min_value=-(10**6), max_value=10**9),
    effort=st.sampled_from(["low", "medium", "high"]),
)
reply_strategy = st.one_of(
    st.none(),
    st.builds(OffersReply, offers=st.lists(item_strategy, max_size=8), note=st.text(max_size=20)),
)


@settings(max_examples=300, deadline=None)
@given(
    kinds=st.lists(st.sampled_from(KINDS), min_size=1, max_size=6),
    people=st.lists(st.tuples(limit_strategy, reply_strategy), min_size=1, max_size=4),
)
def test_no_need_is_left_bare_unless_everyone_said_zero_hours(
    kinds: list[str], people: list[tuple[Limits, OffersReply | None]]
) -> None:
    needs = needs_of(kinds)
    hosted = {f"p{i}": lim for i, (lim, _) in enumerate(people)}
    made: dict[str, list[OfferItem]] = {}
    for i, (lim, reply) in enumerate(people):
        items = checked(reply, needs, lim)
        made[f"p{i}"] = items if items is not None else rule_offers(needs, lim)
    offered = {item.need_id for items in made.values() for item in items}
    bare = [n for n in needs if n["id"] not in offered]
    for who, items in cover_items(needs, bare, hosted).items():
        made[who] = [*made[who], *items]
    final = {item.need_id for items in made.values() for item in items}
    if any(not lim.silent for lim in hosted.values()):
        assert final == {n["id"] for n in needs}, "a need was left without an offer"
    for who, items in made.items():
        lim = hosted[who]
        assert not (lim.silent and items), "0 hours means no offer, whatever the model said"
        top = MAX_MINUTES if lim.cap is None else lim.cap
        for item in items:
            assert MIN_MINUTES <= item.minutes <= max(top, MIN_MINUTES)
            assert 0 <= item.money <= max(lim.money, 0)
        ids = [item.need_id for item in items]
        assert len(ids) == len(set(ids)) or lim.cap is None, ids


def test_estimates_differ_by_need_and_by_what_was_chosen() -> None:
    needs = needs_of(["place", "budget", "draft"])
    told: list[Document] = [
        {"kind": "choice", "answer": "Job a place", "unit": "", "ask": ""},
        {"kind": "amount", "answer": 3, "unit": "hours", "ask": ""},
    ]
    offers = {o.need_id: o for o in rule_offers(needs, limits(told))}
    assert [(o.minutes, o.effort) for o in offers.values()] == [
        (45, "low"),
        (67, "high"),
        (135, "high"),
    ]
    plain = rule_offers(needs, limits([]))
    assert [(o.minutes, o.effort) for o in plain] == [
        (60, "medium"),
        (45, "medium"),
        (90, "medium"),
    ]
    assert (
        rule_offers(needs, limits([{"kind": "amount", "answer": 0, "unit": "hours", "ask": ""}]))
        == []
    )


def test_hours_are_not_summed_and_spans_read_plainly() -> None:
    told: list[Document] = [
        {"kind": "amount", "answer": 2, "unit": "hours", "ask": ""},
        {"kind": "amount", "answer": 3, "unit": "hrs", "ask": ""},
    ]
    assert limits(told).cap == 180
    assert [span(m) for m in (45, 90, 120, 180, 60 * 24)] == [
        "45 minutes",
        "1.5 hours",
        "2 hours",
        "3 hours",
        "24 hours",
    ]
