# SPDX-License-Identifier: Apache-2.0
"""A pack's allocation strategy keeps to the room's task-share cap."""

from fractions import Fraction

from coalitionkit_contracts.payloads import Cost
from coalitionkit_gardener import Offer, PlanConfig, Problem, Task, generate_plans


def lopsided() -> Problem:
    """Seat a is cheapest on every task; b and c can each take any task for a little more."""
    tasks = tuple(Task(t) for t in ("t1", "t2", "t3", "t4"))
    offers = tuple(
        Offer(who, task.task_id, Cost(minutes=minutes, money=0, effort="low"))
        for task in tasks
        for who, minutes in (("a", 10), ("b", 30), ("c", 30))
    )
    return Problem(tasks, offers, {"a": 1, "b": 1, "c": 1})


def counts(assignments: dict[str, str]) -> int:
    return max(list(assignments.values()).count(w) for w in set(assignments.values()))


def test_the_strategy_plan_stands_when_it_keeps_to_the_cap() -> None:
    plans = generate_plans(
        lopsided(), config=PlanConfig(allocation="auction", fairness={"weight": 0})
    )
    assert len(plans.plans) == 1
    assert set(plans.plans[0].assignments.values()) == {"a"}


def test_a_strategy_plan_over_the_cap_gives_way_to_plans_inside_it() -> None:
    cap = Fraction(1, 2)
    plans = generate_plans(
        lopsided(),
        config=PlanConfig(allocation="auction", fairness={"weight": 0}, max_task_share=cap),
    )
    assert plans.plans
    for plan in plans.plans:
        assert Fraction(counts(dict(plan.assignments)), 4) <= cap
