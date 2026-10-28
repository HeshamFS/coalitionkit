# SPDX-License-Identifier: Apache-2.0
"""Pluggable allocation strategies: an auction, PSI slot matching and plurality voting."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Protocol

from .model import Assignments, Bid, Problem, cost_scalar, share_ratio

DEFAULT_NODE_LIMIT = 50_000


@dataclass(frozen=True, slots=True)
class Unresolved:
    """A task a strategy could not settle. ``options`` lists the tied choices, if any."""

    task_id: str
    reason: str
    options: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Outcome:
    """What a strategy chose (task to assignee, slot or option) and what it could not."""

    chosen: Mapping[str, str]
    unresolved: tuple[Unresolved, ...] = ()


class Strategy(Protocol):
    """Settles ``task_ids`` while the ``fixed`` assignments stay as they are."""

    @property
    def name(self) -> str: ...

    def run(self, problem: Problem, task_ids: Sequence[str], fixed: Assignments) -> Outcome: ...


@dataclass(frozen=True)
class AuctionStrategy:
    """Contract-Net: each task goes to the bid with the lowest cost plus lambda times the
    bidder's share ratio after winning, within the ``Problem.max_ratio`` cap.

    The search is depth-first over bids in score order, so the first complete allocation is the
    greedy one and a dead end backtracks. Ties break by participant ID. After ``node_limit``
    nodes without a complete allocation it falls back to a greedy partial one.
    """

    lam: Fraction = Fraction(0)
    node_limit: int = DEFAULT_NODE_LIMIT
    label: str = field(default="auction", compare=False)

    @property
    def name(self) -> str:
        return self.label

    def run(self, problem: Problem, task_ids: Sequence[str], fixed: Assignments) -> Outcome:
        table = problem.bid_table()
        bids = _bids_by_task(table)
        base = _fixed_loads(fixed, table)
        order = sorted(set(task_ids), key=lambda t: (len(bids.get(t, ())), t))
        search = _Search(problem, self.lam, bids, base, self.node_limit)
        if search.solve(order):
            return Outcome(dict(search.chosen))
        return self._greedy_partial(problem, order, bids, base)

    def _greedy_partial(
        self,
        problem: Problem,
        order: list[str],
        bids: Mapping[str, list[Bid]],
        base: Mapping[str, int],
    ) -> Outcome:
        loads = dict(base)
        chosen: dict[str, str] = {}
        missing: list[Unresolved] = []
        for tid in sorted(order):
            ranked = _ranked(problem, self.lam, bids.get(tid, []), loads)
            if not ranked:
                reason = "no eligible bidder" if not bids.get(tid) else "fairness cap reached"
                missing.append(Unresolved(tid, reason))
                continue
            bid = ranked[0]
            chosen[tid] = bid.participant
            loads[bid.participant] = loads.get(bid.participant, 0) + bid.cost.minutes
        return Outcome(chosen, tuple(missing))


def _bids_by_task(table: Mapping[tuple[str, str], Bid]) -> dict[str, list[Bid]]:
    grouped: dict[str, list[Bid]] = {}
    for (task_id, _who), bid in sorted(table.items()):
        grouped.setdefault(task_id, []).append(bid)
    return grouped


def _fixed_loads(fixed: Assignments, table: Mapping[tuple[str, str], Bid]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for task_id, who in fixed.items():
        bid = table.get((task_id, who))
        if bid is not None:
            totals[who] = totals.get(who, 0) + bid.cost.minutes
    return totals


def _ranked(
    problem: Problem, lam: Fraction, bids: Sequence[Bid], loads: Mapping[str, int]
) -> list[Bid]:
    """Bids that respect the cap, best first; the participant ID breaks ties."""
    scored: list[tuple[Fraction, str, Bid]] = []
    for bid in bids:
        ratio = share_ratio(
            loads.get(bid.participant, 0) + bid.cost.minutes, problem.shares[bid.participant]
        )
        if problem.max_ratio is not None and ratio > problem.max_ratio:
            continue
        score = cost_scalar(bid.cost, problem.minute_value) + lam * ratio
        scored.append((score, bid.participant, bid))
    scored.sort(key=lambda item: (item[0], item[1]))
    return [bid for _, _, bid in scored]


class _Search:
    def __init__(
        self,
        problem: Problem,
        lam: Fraction,
        bids: Mapping[str, list[Bid]],
        base: Mapping[str, int],
        limit: int,
    ) -> None:
        self.problem = problem
        self.lam = lam
        self.bids = bids
        self.loads = dict(base)
        self.limit = limit
        self.nodes = 0
        self.chosen: dict[str, str] = {}

    def solve(self, order: Sequence[str], index: int = 0) -> bool:
        if index == len(order):
            return True
        self.nodes += 1
        if self.nodes > self.limit:
            return False
        tid = order[index]
        for bid in _ranked(self.problem, self.lam, self.bids.get(tid, []), self.loads):
            who = bid.participant
            self.chosen[tid] = who
            self.loads[who] = self.loads.get(who, 0) + bid.cost.minutes
            if self.solve(order, index + 1):
                return True
            self.loads[who] -= bid.cost.minutes
            del self.chosen[tid]
        return False


@dataclass(frozen=True)
class MatchStrategy:
    """Assigns each task the earliest slot every party shares, from a PSI overlap result."""

    @property
    def name(self) -> str:
        return "match"

    def run(self, problem: Problem, task_ids: Sequence[str], fixed: Assignments) -> Outcome:
        chosen: dict[str, str] = {}
        missing: list[Unresolved] = []
        for tid in sorted(set(task_ids)):
            overlap = problem.overlaps.get(tid)
            if overlap is None or not overlap.slots:
                missing.append(Unresolved(tid, "no shared slot"))
            else:
                chosen[tid] = min(overlap.slots)
        return Outcome(chosen, tuple(missing))


@dataclass(frozen=True)
class VoteStrategy:
    """Plurality over ``Problem.ballots``. A tie settles nothing and lists the tied options."""

    @property
    def name(self) -> str:
        return "vote"

    def run(self, problem: Problem, task_ids: Sequence[str], fixed: Assignments) -> Outcome:
        chosen: dict[str, str] = {}
        missing: list[Unresolved] = []
        for tid in sorted(set(task_ids)):
            counts: dict[str, int] = {}
            for option in problem.ballots.get(tid, {}).values():
                counts[option] = counts.get(option, 0) + 1
            if not counts:
                missing.append(Unresolved(tid, "no votes"))
                continue
            top = max(counts.values())
            leaders = tuple(sorted(o for o, n in counts.items() if n == top))
            if len(leaders) == 1:
                chosen[tid] = leaders[0]
            else:
                missing.append(Unresolved(tid, "tie", leaders))
        return Outcome(chosen, tuple(missing))
