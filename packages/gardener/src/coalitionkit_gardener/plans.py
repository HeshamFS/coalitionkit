# SPDX-License-Identifier: Apache-2.0
"""Plan sets: up to three plans where none beats another on every objective."""

from __future__ import annotations

import itertools
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
    #: The most any one assignee may hold of a plan's tasks (counted in tasks). A plan over it
    #: never enters the front, so the plans compared are all inside the cap. If no complete
    #: allocation fits (too few people), the cap is dropped rather than leaving no plan.
    max_task_share: Fraction | None = None
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


ENUMERATION_LIMIT = 20_000  # most complete allocations tried one by one; larger rooms search


def _fair(assign: Mapping[str, str], cap: Fraction | None) -> bool:
    """No one holds more than ``cap`` of the tasks (a lone task or lone person always passes)."""
    if cap is None or len(assign) < 2:
        return True
    counts: dict[str, int] = {}
    for who in assign.values():
        counts[who] = counts.get(who, 0) + 1
    return Fraction(max(counts.values()), len(assign)) <= cap


def _enumerate(
    problem: Problem,
    table: Mapping[tuple[str, str], Bid],
    task_ids: tuple[str, ...],
    score3: ThirdObjective,
    cfg: PlanConfig,
) -> dict[tuple[tuple[str, str], ...], Objectives] | None:
    """Every complete allocation inside the share cap, scored exactly, for a small room.

    Deterministic (tasks and bidders in sorted order). Returns None when the room is too big to
    enumerate, when there is no cap, or when some task has no bidder, so the search runs as before.
    """
    if cfg.max_task_share is None:
        return None
    bidders = [sorted(w for (t, w) in table if t == task) for task in task_ids]
    size = 1
    for options in bidders:
        size *= len(options)
    if not task_ids or size == 0 or size > ENUMERATION_LIMIT:
        return None
    every: dict[tuple[tuple[str, str], ...], Objectives] = {}
    fair: dict[tuple[tuple[str, str], ...], Objectives] = {}
    for combo in itertools.product(*bidders):
        assign = dict(zip(task_ids, combo, strict=True))
        obj = _objectives(problem, table, assign, score3)
        if not _within_cap(problem, obj[1]):
            continue
        key = tuple(sorted(assign.items()))
        every[key] = obj
        if _fair(assign, cfg.max_task_share):
            fair[key] = obj
    return fair or every or None


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
    exact = _enumerate(problem, table, task_ids, score3, cfg)
    if exact is not None:
        found = exact
    for lam in cfg.lambdas if exact is None else ():
        outcome = AuctionStrategy(lam).run(problem, task_ids, {})
        if outcome.unresolved:
            failed = failed or outcome.unresolved
            continue
        if _fair(outcome.chosen, cfg.max_task_share):
            _remember(found, problem, table, outcome.chosen, score3)
    for start in list(found) if exact is None else []:
        for axis in range(3):
            better = _climb(problem, table, dict(start), axis, score3, cfg.max_task_share)
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
    cap: Fraction | None = None,
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
                if _within_cap(problem, obj[1]) and _fair(trial, cap) and key(obj) < key(best):
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
