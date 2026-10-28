# SPDX-License-Identifier: Apache-2.0
"""Tensions: unmet hard constraints, vote ties and plan sets with large trade-offs."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

from coalitionkit_contracts.payloads import TensionOption, TensionPayload

from ._ids import derive_ulid
from .plans import PlanSet
from .strategies import Unresolved

RELAX_OPTION = "relax-cap"
DEFER_OPTION = "defer"


@dataclass(frozen=True)
class TradeoffPolicy:
    """A plan set holds a tension when an objective's (max - min) / max reaches ``min_gap``."""

    min_gap: Fraction = Fraction(1, 2)


def tensions_from_unresolved(
    unresolved: Sequence[Unresolved],
    *,
    deciders: Sequence[str],
    deadline: str,
    revision: int = 1,
) -> list[TensionPayload]:
    """One tension per tied vote, plus one for all tasks no plan can cover."""
    out: list[TensionPayload] = []
    blocked = sorted(u.task_id for u in unresolved if not u.options)
    if blocked:
        reasons = sorted({u.reason for u in unresolved if not u.options})
        out.append(
            _make(
                blocked,
                [
                    TensionOption(
                        option_id=RELAX_OPTION,
                        summary="Relax the binding constraint (for example raise the fairness cap)",
                    ),
                    TensionOption(option_id=DEFER_OPTION, summary="Defer these tasks"),
                ],
                [f"No plan satisfies every hard constraint: {', '.join(reasons)}"],
                deciders,
                deadline,
                revision,
            )
        )
    for tied in sorted((u for u in unresolved if u.options), key=lambda u: u.task_id):
        options = [TensionOption(option_id=o, summary=f"Choose {o}") for o in tied.options]
        out.append(
            _make(
                [tied.task_id],
                options,
                [f"Vote {tied.reason}: {', '.join(tied.options)}"],
                deciders,
                deadline,
                revision,
            )
        )
    return out


def tension_from_plans(
    plan_set: PlanSet,
    *,
    deciders: Sequence[str],
    deadline: str,
    policy: TradeoffPolicy | None = None,
    revision: int = 1,
) -> TensionPayload | None:
    """A tension when the Pareto plans differ a lot on some objective, else None."""
    gap = (policy or TradeoffPolicy()).min_gap
    plans = plan_set.plans
    if len(plans) < 2:
        return None
    tradeoffs: list[str] = []
    for axis, name in enumerate(plan_set.objective_names):
        values = [p.objectives[axis] for p in plans]
        high, low = max(values), min(values)
        if high > 0 and (high - low) / high >= gap:
            tradeoffs.append(f"{name} ranges from {float(low):.4g} to {float(high):.4g}")
    tasks = sorted(
        t for t in plans[0].assignments if len({p.assignments.get(t) for p in plans}) > 1
    )
    if not tradeoffs or not tasks:
        return None
    options = [
        TensionOption(
            option_id=p.plan_id,
            summary="Plan "
            + ", ".join(
                f"{n} {float(v):.4g}"
                for n, v in zip(plan_set.objective_names, p.objectives, strict=True)
            ),
        )
        for p in plans
    ]
    return _make(tasks, options, tradeoffs, deciders, deadline, revision)


def tension_for_plan_set(
    plan_set: PlanSet,
    *,
    deciders: Sequence[str],
    deadline: str,
    policy: TradeoffPolicy | None = None,
    revision: int = 1,
) -> list[TensionPayload]:
    """Tensions for an empty plan set (hard constraints) or for a set with big trade-offs."""
    if not plan_set.plans:
        return tensions_from_unresolved(
            plan_set.unresolved, deciders=deciders, deadline=deadline, revision=revision
        )
    one = tension_from_plans(
        plan_set, deciders=deciders, deadline=deadline, policy=policy, revision=revision
    )
    return [one] if one else []


def _make(
    task_ids: Sequence[str],
    options: list[TensionOption],
    tradeoffs: list[str],
    deciders: Sequence[str],
    deadline: str,
    revision: int,
) -> TensionPayload:
    ident = derive_ulid("tension", str(revision), *task_ids, *(o.option_id for o in options))
    return TensionPayload(
        tension_id=ident,
        revision=revision,
        task_ids=list(task_ids),
        options=options,
        tradeoffs=tradeoffs,
        deciders=list(deciders),
        decision_deadline=deadline,
    )
