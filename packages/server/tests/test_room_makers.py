# SPDX-License-Identifier: Apache-2.0
"""What the maker step must hold to: the stated money, exact budgets, no placeholders."""

from __future__ import annotations

from coalitionkit_server.room import fixed, makers, results


def test_the_amount_in_the_goal_is_found() -> None:
    goal = "share a 300 euro budget and write the invitation"
    assert makers.stated_amount(goal) == {"amount": 300, "unit": "EUR"}
    assert makers.stated_amount("a budget of €1,200 for us") == {"amount": 1200, "unit": "EUR"}
    assert makers.stated_amount("find a place and write the invitation") is None


def test_budget_lines_must_add_up_to_the_stated_amount() -> None:
    def out(*amounts: int) -> makers.BudgetOut:
        lines = [
            makers.Line(label=f"L{i}", amount=a, who_pays="all") for i, a in enumerate(amounts)
        ]
        return makers.BudgetOut(lines=lines, how_shared="equally")

    good = makers.clean_budget(out(100, 120, 80), 300)
    assert isinstance(good, dict) and sum(x["amount"] for x in good["lines"]) == 300
    slip = makers.clean_budget(out(100, 120, 77), 300)
    assert isinstance(slip, dict) and sum(x["amount"] for x in slip["lines"]) == 300
    assert isinstance(makers.clean_budget(out(100, 50), 300), str)
    assert isinstance(makers.clean_budget(out(300), 300), str)


def test_a_draft_with_a_placeholder_is_refused() -> None:
    facts = {"amount": None}
    body = "Hello [name], we would love you to come to our event. " * 3
    bad = makers.clean("draft", makers.DraftOut(subject="Hi", body=body), facts, set())
    assert isinstance(bad, str)
    ok = makers.clean("draft", makers.DraftOut(subject="Hi", body="Hello all. " * 12), facts, set())
    assert isinstance(ok, dict)


def test_a_money_budget_keeps_the_signed_minutes_apart() -> None:
    facts = {
        "amount": {"amount": 300, "unit": "EUR"},
        "plan": [{"who": "Ana", "title": "Book", "minutes": 30, "offer_event": "e1"}],
    }
    made = {"lines": [{"label": "Hall", "amount": 300, "who": "all"}], "how_shared": "equally"}
    data = results.budget_data(facts, made)
    assert data["currency"] == "EUR" and data["total"] == 300
    assert data["time_total"] == 30 and data["time"][0]["ref"] == "e1"


def test_every_card_of_a_fixed_tree_is_reachable_from_root() -> None:
    reading = {"label": "Mira: Find a place", "amount": 50, "provenance": "signed", "ref": "e1"}
    idea = {"why": "Room", "check": "Is it free", "provenance": "estimate"}
    cases = {
        "place": {"options": [{"name": f"Place {n}", **idea} for n in range(3)], "chosen": None},
        "schedule": {
            "items": [
                {"title": f"Step {n}", "start": "a", "end": "b", "where": "c"} for n in range(3)
            ],
            "steps": ["Meet", "Talk"],
        },
        "budget": {
            "currency": "EUR",
            "amount": 300,
            "rows": [
                {"label": "Hall", "amount": 200, "who": "all", "provenance": "estimate"},
                {"label": "Food", "amount": 100, "who": "all", "provenance": "estimate"},
            ],
            "how_shared": "equally",
            "suggested": [],
            "time": [reading],
            "time_total": 50,
            "total": 300,
        },
        "list": {"items": [{"label": "Chairs", "who": "anyone", "provenance": "estimate"}] * 2},
        "draft": {"subject": "Hello", "body": "Come to our fair. " * 6},
    }
    for kind, data in cases.items():
        tree = fixed.fixed_tree(kind, "Title", "Detail", data)
        shown = {n["id"] for n in results.reachable(tree)}
        assert {n["id"] for n in tree} == shown, kind
        cards = [n for n in tree if n["component"] == "Card"]
        wanted = {"place": 3, "schedule": 2, "budget": 2, "list": 1, "draft": 1}[kind]
        assert len(cards) == wanted, (kind, len(cards))
        rich = {"schedule": "Timeline", "budget": "CostSplit", "list": "Checklist"}.get(kind)
        assert rich is None or any(n["component"] == rich for n in tree), kind


def test_a_draft_may_not_present_free_slots_as_the_event_time() -> None:
    facts = {
        "amount": None,
        "goal": "A fair next Saturday",
        "common": [{"id": "s2", "label": "Thu 05 Nov, 14:00 UTC"}],
    }
    base = "Hello neighbours, we run a small fair next Saturday and we would love you to come. "
    for bad in (
        "Join us on Thu 05 Nov, 14:00 UTC.",
        "Come at 14:00.",
        "Meet Thu 05 Nov for a preview.",
    ):
        out = makers.clean("draft", makers.DraftOut(subject="Fair", body=base + bad), facts, set())
        assert isinstance(out, str) and "free" in out, bad
    fine = makers.clean(
        "draft", makers.DraftOut(subject="Fair", body=base + "Reply please."), facts, set()
    )
    assert isinstance(fine, dict)
    rules = results.draft_by_rules({**facts, "people": ["Mira"], "need": {"title": "Invitation"}})
    assert "Thu 05 Nov" not in rules["body"] and "still to be confirmed" in rules["body"]


def test_place_ideas_lose_the_hedge_in_front() -> None:
    assert (
        makers.plain("As a proposal, it could give room for tables.", 200)
        == "It could give room for tables."
    )
    assert (
        makers.plain("As a suggestion: Check the opening hours.", 200) == "Check the opening hours."
    )


def test_hedges_and_invented_clock_times_are_caught() -> None:
    said = makers.unhedged("We run a fair. As a proposal, we suggest a start. This is a proposal.")
    assert said == "We run a fair. We suggest a start."
    lines = makers.unhedged("Hello.\n\nAs a proposal, we meet late.")
    assert lines == "Hello.\n\nWe meet late."
    facts: dict[str, object] = {"amount": None, "goal": "A fair", "common": []}
    body = "Hello neighbours, we run a small fair next Saturday and we would love you to come. "
    out = makers.clean(
        "draft", makers.DraftOut(subject="Fair", body=body + "Start at 11am."), facts, set()
    )
    assert isinstance(out, str)
    idea = makers.Idea(
        kind_of_place="Hall", why_it_fits="Space", check_first="Ask before 18:00 UTC"
    )
    placed = makers.clean("place", makers.PlaceOut(ideas=[idea, idea]), facts, set())
    assert isinstance(placed, str)


def test_sentences_that_only_talk_about_being_a_proposal_are_dropped() -> None:
    assert makers.unhedged("It fits the fair. This set is a proposal.") == "It fits the fair."
    nl = chr(10)
    body = (
        "We run a fair." + nl + nl + "Please treat this invitation as a proposal while we finish."
    )
    assert makers.unhedged(body) == "We run a fair."


def test_dropped_sentences_leave_no_empty_paragraphs() -> None:
    nl = chr(10)
    body = "Hi." + nl + nl + "It is a proposal." + nl + nl + "Bye."
    assert makers.unhedged(body) == "Hi." + nl + nl + "Bye."
