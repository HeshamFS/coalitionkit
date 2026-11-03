# SPDX-License-Identifier: Apache-2.0
"""What the maker step must hold to: the stated money, exact budgets, no placeholders."""

from __future__ import annotations

from coalitionkit_server.room import makers, results


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
