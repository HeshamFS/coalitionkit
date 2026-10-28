# SPDX-License-Identifier: Apache-2.0
"""Ripples: which tasks a change invalidates, and a re-plan that touches only those."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass

from coalitionkit_contracts.payloads import RipplePayload

from .model import Assignments, Problem
from .strategies import AuctionStrategy, Strategy, Unresolved

#: Task id to the tasks it depends on (its prerequisites).
type TaskGraph = Mapping[str, Collection[str]]


@dataclass(frozen=True)
class Change:
    """Tasks that changed directly, and participants who left or can no longer serve."""

    description: str
    tasks: frozenset[str] = frozenset()
    participants: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class ReplanResult:
    assignments: Mapping[str, str]
    replanned: frozenset[str]
    unresolved: tuple[Unresolved, ...]


def invalidated(change: Change, graph: TaskGraph, current: Assignments) -> frozenset[str]:
    """The directly changed tasks, the tasks held by a departed participant, and every task that
    depends on them, directly or through other tasks. Nothing else."""
    dependents: dict[str, set[str]] = {}
    for task, prerequisites in graph.items():
        for pre in prerequisites:
            dependents.setdefault(pre, set()).add(task)
    seeds = set(change.tasks)
    seeds.update(t for t, who in current.items() if who in change.participants)
    seen = set(seeds)
    queue = sorted(seeds)
    while queue:
        task = queue.pop()
        for nxt in sorted(dependents.get(task, ())):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return frozenset(seen)


def replan(
    problem: Problem,
    current: Assignments,
    invalid: frozenset[str],
    *,
    departed: frozenset[str] = frozenset(),
    strategy: Strategy | None = None,
) -> ReplanResult:
    """Re-plan only ``invalid`` tasks against the updated ``problem``. Every other assignment is
    returned unchanged and counts toward the fairness load."""
    live = problem.without(departed)
    known = set(live.task_ids)
    kept = {t: a for t, a in current.items() if t not in invalid and t in known}
    todo = sorted(t for t in invalid if t in known)
    outcome = (strategy or AuctionStrategy()).run(live, todo, kept)
    return ReplanResult({**kept, **outcome.chosen}, frozenset(todo), outcome.unresolved)


def ripple_payload(change: Change, invalid: frozenset[str]) -> RipplePayload:
    """The ``coalition.ripple`` payload; task IDs must be ULIDs."""
    return RipplePayload(change=change.description, invalidates=sorted(invalid))
