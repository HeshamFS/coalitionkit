# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from fractions import Fraction

from coalitionkit_gardener import (
    AuctionStrategy,
    Change,
    MatchStrategy,
    Offer,
    Overlap,
    Problem,
    Task,
    TradeoffPolicy,
    VoteStrategy,
    build_propose,
    generate_plans,
    invalidated,
    replan,
    ripple_payload,
    tension_for_plan_set,
    tensions_from_unresolved,
)
from coalitionkit_gardener._ids import derive_ulid
from coalitionkit_gardener.model import loads
from coalitionkit_gardener.plans import PlanSet

from coalitionkit_contracts.payloads import Cost, ProposePayload

DEADLINE = "2030-01-01T00:00:00Z"


def tid(n: int) -> str:
    return derive_ulid("task", str(n))


def offer(who: str, task: str, minutes: int, money: int = 0) -> Offer:
    return Offer(who, task, Cost(minutes=minutes, money=money, effort="low"))


def test_auction_is_deterministic_and_breaks_ties_by_participant() -> None:
    tasks = tuple(Task(tid(i)) for i in range(4))
    offers = tuple(offer(p, t.task_id, 60, 5) for t in tasks for p in ("zed", "amy", "kit"))
    problem = Problem(tasks, offers, {"zed": 1, "amy": 1, "kit": 1})
    first = AuctionStrategy().run(problem, problem.task_ids, {})
    flipped = Problem(tasks, offers[::-1], problem.shares)
    again = AuctionStrategy().run(flipped, list(reversed(problem.task_ids)), {})
    assert dict(first.chosen) == dict(again.chosen)
    assert set(first.chosen.values()) == {"amy"}


def test_fairness_cap_limits_load() -> None:
    tasks = tuple(Task(tid(i)) for i in range(4))
    offers = tuple(offer("cheap", t.task_id, 60, 1) for t in tasks) + tuple(
        offer("dear", t.task_id, 60, 50) for t in tasks
    )
    uncapped = Problem(tasks, offers, {"cheap": 1, "dear": 1})
    assert set(AuctionStrategy().run(uncapped, uncapped.task_ids, {}).chosen.values()) == {"cheap"}
    capped = Problem(tasks, offers, {"cheap": 1, "dear": 1}, max_ratio=Fraction(2))
    out = AuctionStrategy().run(capped, capped.task_ids, {})
    table = capped.bid_table()
    assert not out.unresolved
    assert max(loads(capped, out.chosen, table).values()) <= 120


def test_infeasible_cap_leaves_tasks_unresolved_and_raises_tension() -> None:
    tasks = tuple(Task(tid(i)) for i in range(3))
    offers = tuple(offer("solo", t.task_id, 60) for t in tasks)
    problem = Problem(tasks, offers, {"solo": 1}, max_ratio=Fraction(1))
    plan_set = generate_plans(problem)
    assert plan_set.plans == ()
    assert plan_set.unresolved
    (tension,) = tension_for_plan_set(plan_set, deciders=["d1"], deadline=DEADLINE)
    assert set(tension.task_ids) == {u.task_id for u in plan_set.unresolved}
    assert len(tension.options) >= 2


def test_vault_no_removes_a_bid_and_cost_replaces_it() -> None:
    t = tid(1)
    problem = Problem(
        (Task(t),),
        (offer("a", t, 10, 1), offer("b", t, 10, 5)),
        {"a": 1, "b": 1},
        answers={("a", t): "no", ("b", t): Cost(minutes=5, money=2, effort="low")},
    )
    assert dict(AuctionStrategy().run(problem, [t], {}).chosen) == {t: "b"}
    assert problem.bid_table()[(t, "b")].cost.money == 2


def test_match_picks_the_shared_slot() -> None:
    a, b = tid(1), tid(2)
    problem = Problem(
        (Task(a), Task(b)),
        (),
        {},
        overlaps={a: Overlap(a, ("2030-01-02T10:00", "2030-01-01T14:00")), b: Overlap(b, ())},
    )
    out = MatchStrategy().run(problem, [a, b], {})
    assert dict(out.chosen) == {a: "2030-01-01T14:00"}
    assert [u.task_id for u in out.unresolved] == [b]


def test_vote_plurality_and_tie_makes_a_tension() -> None:
    win, tie = tid(1), tid(2)
    problem = Problem(
        (Task(win), Task(tie)),
        (),
        {},
        ballots={win: {"p1": "x", "p2": "x", "p3": "y"}, tie: {"p1": "x", "p2": "y"}},
    )
    out = VoteStrategy().run(problem, [win, tie], {})
    assert dict(out.chosen) == {win: "x"}
    assert out.unresolved[0].options == ("x", "y")
    (tension,) = tensions_from_unresolved(out.unresolved, deciders=["p1", "p2"], deadline=DEADLINE)
    assert tension.task_ids == [tie]
    assert [o.option_id for o in tension.options] == ["x", "y"]


def two_way_problem() -> Problem:
    tasks = tuple(Task(tid(i)) for i in range(4))
    offers = tuple(offer("cheap", t.task_id, 60, 1) for t in tasks) + tuple(
        offer("dear", t.task_id, 60, 40) for t in tasks
    )
    return Problem(tasks, offers, {"cheap": 1, "dear": 1})


def test_every_plan_is_non_dominated_and_payload_validates() -> None:
    problem = two_way_problem()
    plan_set = generate_plans(problem)
    assert 1 <= len(plan_set.plans) <= 3
    objs = [p.objectives for p in plan_set.plans]
    for i, a in enumerate(objs):
        for j, b in enumerate(objs):
            assert i == j or not (all(x <= y for x, y in zip(a, b, strict=True)) and a != b)
    assert len(plan_set.plans) >= 2  # cost and fairness truly trade off here
    payload = build_propose(plan_set, deadline=DEADLINE, proposal_set_id="set-1")
    assert isinstance(payload, ProposePayload)
    assert payload.decision_deadline == DEADLINE
    assert set(payload.plans[0].objective_scores) == {"total_cost", "max_share_ratio", "third"}
    tension = tension_for_plan_set(
        plan_set, deciders=["d1"], deadline=DEADLINE, policy=TradeoffPolicy(Fraction(1, 4))
    )
    assert len(tension) == 1 and len(tension[0].options) == len(plan_set.plans)


def test_third_objective_shapes_the_set() -> None:
    problem = two_way_problem()
    first = problem.task_ids[0]
    plan_set = generate_plans(problem, third=lambda a: 1.0 if a[first] == "cheap" else 0.0)
    assert any(p.assignments[first] == "dear" for p in plan_set.plans)
    assert isinstance(plan_set, PlanSet)


def test_ripple_invalidates_only_dependents_and_replan_keeps_the_rest() -> None:
    ids = [tid(i) for i in range(6)]
    graph = {ids[1]: [ids[0]], ids[2]: [ids[1]], ids[4]: [ids[3]], ids[5]: []}
    tasks = tuple(Task(t) for t in ids)
    offers = tuple(offer(p, t, 30, c) for t in ids for p, c in (("a", 1), ("b", 2)))
    problem = Problem(tasks, offers, {"a": 1, "b": 1})
    current = dict(AuctionStrategy().run(problem, problem.task_ids, {}).chosen)
    change = Change("task 0 moved", tasks=frozenset({ids[0]}))
    bad = invalidated(change, graph, current)
    assert bad == {ids[0], ids[1], ids[2]}
    result = replan(problem, current, bad, departed=frozenset({"a"}))
    assert result.replanned == bad
    for t in ids:
        if t not in bad:
            assert result.assignments[t] == current[t]
    assert all(result.assignments[t] == "b" for t in bad)
    assert ripple_payload(change, bad).invalidates == sorted(bad)


def test_departed_participant_invalidates_their_tasks() -> None:
    ids = [tid(i) for i in range(3)]
    current = {ids[0]: "a", ids[1]: "b", ids[2]: "a"}
    bad = invalidated(Change("a left", participants=frozenset({"a"})), {ids[1]: [ids[0]]}, current)
    assert bad == set(ids)


def test_twenty_task_example_with_a_change_in_the_middle() -> None:
    """Acceptance test 4: a mid-plan change re-plans only what it touches."""
    ids = [tid(i) for i in range(20)]
    graph = {ids[i]: [ids[i - 1]] for i in range(11, 20)}  # a chain from the middle on
    graph.update({ids[i]: [ids[i - 1]] for i in range(1, 5)})
    people = {"ana": 2, "ben": 1, "cho": 1}
    prices = {"ana": 3, "ben": 4, "cho": 5}
    tasks = tuple(Task(t) for t in ids)
    offers = tuple(
        offer(p, t, 30 + 10 * (i % 3), prices[p] + i % 4) for i, t in enumerate(ids) for p in people
    )
    problem = Problem(tasks, offers, people, max_ratio=Fraction(7))
    plan_set = generate_plans(problem)
    assert plan_set.plans
    base = dict(plan_set.plans[0].assignments)
    assert set(base) == set(ids)
    change = Change("task 10 changed", tasks=frozenset({ids[10]}))
    bad = invalidated(change, graph, base)
    assert bad == set(ids[10:])
    updated = Problem(
        tasks,
        tuple(o for o in offers if not (o.task_id == ids[10] and o.participant == base[ids[10]])),
        people,
        max_ratio=Fraction(7),
    )
    result = replan(updated, base, bad)
    assert not result.unresolved
    assert {t: result.assignments[t] for t in ids[:10]} == {t: base[t] for t in ids[:10]}
    assert result.assignments[ids[10]] != base[ids[10]]
    assert set(result.assignments) == set(ids)
