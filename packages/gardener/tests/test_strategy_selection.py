# SPDX-License-Identifier: Apache-2.0
from fractions import Fraction

import pytest

from coalitionkit_contracts.payloads import Cost
from coalitionkit_gardener import Offer, PlanConfig, Problem, Task, generate_plans
from coalitionkit_gardener.strategies import select_strategy


def test_weight_changes_allocation_and_settings_reach_problem() -> None:
    problem = Problem(
        (Task("first"), Task("second")),
        tuple(
            Offer(who, task, Cost(minutes=60, money=money, effort="low"))
            for task in ("first", "second")
            for who, money in (("a", 0), ("b", 1))
        ),
        {"a": 1, "b": 1},
    )
    cheap, original = select_strategy(problem, "auction", {"weight": 0})
    fair, configured = select_strategy(
        problem, "auction", {"weight": 10, "max_ratio": 3, "minute_value": 2}
    )
    assert set(cheap.run(original, original.task_ids, {}).chosen.values()) == {"a"}
    assert set(fair.run(configured, configured.task_ids, {}).chosen.values()) == {"a", "b"}
    assert configured.max_ratio == Fraction(3)
    assert configured.minute_value == 2
    assert problem.max_ratio is None and problem.minute_value == 1
    for weight, expected in [(0, {"a"}), (10, {"a", "b"})]:
        plans = generate_plans(
            problem, config=PlanConfig(allocation="auction", fairness={"weight": weight})
        )
        assert len(plans.plans) == 1
        assert set(plans.plans[0].assignments.values()) == expected


@pytest.mark.parametrize("name", ["auction", "match", "vote"])
def test_named_strategy(name: str) -> None:
    strategy, _ = select_strategy(Problem((), (), {}), name)
    assert strategy.name == name


@pytest.mark.parametrize(
    "name,fairness", [("unknown", {}), ("match", {"weight": 1}), ("auction", {"unknown": 1})]
)
def test_unknown_strategy_or_key(name: str, fairness: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        select_strategy(Problem((), (), {}), name, fairness)
