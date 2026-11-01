# SPDX-License-Identifier: Apache-2.0
"""Plan sets: up to three plans where none beats another on every objective."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from fractions import Fraction

from coalitionkit_contracts.payloads import Assignment, Plan, ProposePayload

from ._ids import derive_ulid
from .model import Assignments, Bid, Problem, max_share_ratio, total_cost
from .strategies import AuctionStrategy, Unresolved, select_strategy

#: Scores a full assignment; lower is better.
type ThirdObjective = Callable[[Assignments], float]
type Objectives = tuple[Fraction, Fraction, Fraction]

DEFAULT_LAMBDAS = tuple(Fraction(n) for n in (0, 1, 2, 4, 8, 16, 64, 256, 1024))
MAX_CLIMB_PASSES = 50


@dataclass(frozen=True)
class PlanConfig:
    lambdas: tuple[Fraction, ...] = DEFAULT_LAMBDAS
    max_plans: int = 3
    third_name: str = "third"
    allocation: str | None = None
    fairness: Mapping[str, float] = field(default_factory=dict[str, float])


@dataclass(frozen=True, slots=True)
class PlanCandidate:
    assignments: Mapping[str, str]
    objectives: Objectives
    plan_id: str


@dataclass(frozen=True, slots=True)
class PlanSet:
    plans: tuple[PlanCandidate, ...]
    unresolved: tuple[Unresolved, ...] = ()
    objective_names: tuple[str, str, str] = field(
        default=("total_cost", "max_share_ratio", "third")
    )


def dominates(a: Objectives, b: Objectives) -> bool:
    """``a`` is no worse everywhere and strictly better somewhere (all objectives minimise)."""
    return all(x <= y for x, y in zip(a, b, strict=True)) and a != b


def _no_third(_: Assignments) -> float:
    return 0.0


def generate_plans(
    problem: Problem,
    third: ThirdObjective | None = None,
    config: PlanConfig | None = None,
) -> PlanSet:
    """Up to ``config.max_plans`` complete, cap-respecting, mutually non-dominated plans."""
    cfg = config or PlanConfig()
    score3 = third or _no_third
    names = ("total_cost", "max_share_ratio", cfg.third_name)
    if cfg.allocation is not None:
        strategy, problem = select_strategy(problem, cfg.allocation, cfg.fairness)
        outcome = strategy.run(problem, problem.task_ids, {})
        if outcome.unresolved:
            return PlanSet((), outcome.unresolved, names)
        key = tuple(sorted(outcome.chosen.items()))
        candidate = PlanCandidate(
            dict(key),
            _objectives(problem, problem.bid_table(), outcome.chosen, score3),
            derive_ulid("plan", *(f"{t}={a}" for t, a in key)),
        )
        return PlanSet((candidate,), (), names)
    table = problem.bid_table()
    task_ids = problem.task_ids
    found: dict[tuple[tuple[str, str], ...], Objectives] = {}
    failed: tuple[Unresolved, ...] = ()
    for lam in cfg.lambdas:
        outcome = AuctionStrategy(lam).run(problem, task_ids, {})
        if outcome.unresolved:
            failed = failed or outcome.unresolved
            continue
        _remember(found, problem, table, outcome.chosen, score3)
    for start in list(found):
        for axis in range(3):
            better = _climb(problem, table, dict(start), axis, score3)
            _remember(found, problem, table, better, score3)
    if not found:
        return PlanSet((), failed, names)
    front = _front(found)
    chosen = _select(front, cfg.max_plans)
    plans = tuple(
        PlanCandidate(dict(key), obj, derive_ulid("plan", *(f"{t}={a}" for t, a in key)))
        for key, obj in chosen
    )
    return PlanSet(plans, (), names)


def _objectives(
    problem: Problem,
    table: Mapping[tuple[str, str], Bid],
    assign: Assignments,
    score3: ThirdObjective,
) -> Objectives:
    return (
        Fraction(total_cost(problem, assign, table)),
        max_share_ratio(problem, assign, table),
        Fraction(score3(assign)),
    )


def _remember(
    found: dict[tuple[tuple[str, str], ...], Objectives],
    problem: Problem,
    table: Mapping[tuple[str, str], Bid],
    assign: Assignments,
    score3: ThirdObjective,
) -> None:
    key = tuple(sorted(assign.items()))
    if key not in found:
        found[key] = _objectives(problem, table, assign, score3)


def _within_cap(problem: Problem, ratio: Fraction) -> bool:
    return problem.max_ratio is None or ratio <= problem.max_ratio


def _climb(
    problem: Problem,
    table: Mapping[tuple[str, str], Bid],
    start: dict[str, str],
    axis: int,
    score3: ThirdObjective,
) -> dict[str, str]:
    """Single-task reassignments that lower objective ``axis`` (the others break ties)."""

    def key(obj: Objectives) -> tuple[Fraction, ...]:
        return (obj[axis], *obj[:axis], *obj[axis + 1 :])

    current = dict(start)
    best = _objectives(problem, table, current, score3)
    for _ in range(MAX_CLIMB_PASSES):
        improved = False
        for tid in sorted(current):
            for (t, who), _bid in sorted(table.items()):
                if t != tid or who == current[tid]:
                    continue
                trial = {**current, tid: who}
                obj = _objectives(problem, table, trial, score3)
                if _within_cap(problem, obj[1]) and key(obj) < key(best):
                    current, best, improved = trial, obj, True
        if not improved:
            break
    return current


def _front(
    found: Mapping[tuple[tuple[str, str], ...], Objectives],
) -> list[tuple[tuple[tuple[str, str], ...], Objectives]]:
    items = sorted(found.items(), key=lambda kv: (kv[1], kv[0]))
    return [
        (k, o) for k, o in items if not any(dominates(other, o) for _, other in items if other != o)
    ]


def _select(
    front: list[tuple[tuple[tuple[str, str], ...], Objectives]], limit: int
) -> list[tuple[tuple[tuple[str, str], ...], Objectives]]:
    """The best plan on each objective first, then the rest in order, up to ``limit``."""
    picked: list[tuple[tuple[tuple[str, str], ...], Objectives]] = []
    for axis in range(3):
        best = min(front, key=lambda kv, a=axis: (kv[1][a], kv[1], kv[0]))
        if best not in picked:
            picked.append(best)
    for item in front:
        if item not in picked:
            picked.append(item)
    return sorted(picked[:limit], key=lambda kv: (kv[1], kv[0]))


def decision_deadline(at: datetime, window: timedelta) -> str:
    """An absolute RFC 3339 UTC deadline ``window`` after ``at``."""
    moment = (at if at.tzinfo else at.replace(tzinfo=UTC)).astimezone(UTC) + window
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_propose(
    plan_set: PlanSet,
    *,
    deadline: str,
    proposal_set_id: str,
    revision: int = 1,
) -> ProposePayload:
    """The ``coalition.propose`` payload for a non-empty plan set."""
    plans = [
        Plan(
            plan_id=p.plan_id,
            revision=revision,
            assignments=[
                Assignment(task_id=t, assignee=a) for t, a in sorted(p.assignments.items())
            ],
            objective_scores={
                name: float(value)
                for name, value in zip(plan_set.objective_names, p.objectives, strict=True)
            },
        )
        for p in plan_set.plans
    ]
    return ProposePayload(proposal_set_id=proposal_set_id, plans=plans, decision_deadline=deadline)
