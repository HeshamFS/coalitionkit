# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from fractions import Fraction
from itertools import product

from coalitionkit_gardener import Offer, Problem, Task, generate_plans
from coalitionkit_gardener._ids import derive_ulid
from coalitionkit_gardener.model import max_share_ratio
from hypothesis import given, settings
from hypothesis import strategies as st

from coalitionkit_contracts.payloads import Cost

PEOPLE = ("p0", "p1", "p2")


@st.composite
def problems(draw: st.DrawFn) -> Problem:
    n_tasks = draw(st.integers(1, 5))
    ids = [derive_ulid("t", str(i)) for i in range(n_tasks)]
    shares = {p: draw(st.integers(1, 4)) for p in PEOPLE}
    offers: list[Offer] = []
    for t in ids:
        for p in PEOPLE:
            if draw(st.booleans()):
                cost = Cost(
                    minutes=draw(st.integers(1, 180)), money=draw(st.integers(0, 500)), effort="low"
                )
                offers.append(Offer(p, t, cost))
    cap = draw(st.one_of(st.none(), st.fractions(Fraction(1, 2), 6, max_denominator=4)))
    return Problem(tuple(Task(t) for t in ids), tuple(offers), shares, max_ratio=cap)


def feasible(problem: Problem) -> bool:
    table = problem.bid_table()
    options = [[p for p in PEOPLE if (t, p) in table] for t in problem.task_ids]
    if any(not o for o in options):
        return False
    for combo in product(*options):
        assign = dict(zip(problem.task_ids, combo, strict=True))
        if (
            problem.max_ratio is None
            or max_share_ratio(problem, assign, table) <= problem.max_ratio
        ):
            return True
    return False


@settings(max_examples=150, deadline=None)
@given(problems(), st.integers(0, 3))
def test_plans_are_non_dominated_and_respect_the_cap(problem: Problem, bias: int) -> None:
    ids = problem.task_ids
    plan_set = generate_plans(problem, third=lambda a: float(sum(a[t] == "p0" for t in ids) * bias))
    if feasible(problem):
        assert 1 <= len(plan_set.plans) <= 3
    else:
        assert plan_set.plans == ()
    table = problem.bid_table()
    for plan in plan_set.plans:
        assert set(plan.assignments) == set(ids)
        if problem.max_ratio is not None:
            assert max_share_ratio(problem, plan.assignments, table) <= problem.max_ratio
    objs = [p.objectives for p in plan_set.plans]
    for a in objs:
        for b in objs:
            assert not (all(x <= y for x, y in zip(a, b, strict=True)) and a != b)
