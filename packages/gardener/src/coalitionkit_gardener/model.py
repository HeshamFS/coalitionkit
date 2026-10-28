# SPDX-License-Identifier: Apache-2.0
"""Typed planning inputs and the cost and fairness arithmetic every strategy shares."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from fractions import Fraction
from typing import Literal

from coalitionkit_contracts.payloads import Cost, Window

#: A vault reply: yes, no, or a cost. ``coalition.answer`` carries the same union.
type VaultAnswer = Literal["yes", "no"] | Cost
#: Task id to the assignee (or slot, or option) chosen for it.
type Assignments = Mapping[str, str]

MINUTES_PER_HOUR = 60


@dataclass(frozen=True, slots=True)
class Task:
    task_id: str
    requirements: tuple[str, ...] = ()
    window: Window | None = None


@dataclass(frozen=True, slots=True)
class Offer:
    """One participant's offer for one task: minutes, money in minor units, effort."""

    participant: str
    task_id: str
    cost: Cost


@dataclass(frozen=True, slots=True)
class Overlap:
    """The slots two or more participants share, as PSI revealed them."""

    task_id: str
    slots: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Bid:
    participant: str
    task_id: str
    cost: Cost


@dataclass(frozen=True)
class Problem:
    """Everything the strategies read.

    ``shares`` are positive integer weights; a participant without one cannot be assigned.
    ``answers`` maps (participant, task_id) to a vault reply: ``"no"`` removes the bid, a
    ``Cost`` replaces the offered cost, ``"yes"`` or no reply leaves the offer as it is.
    ``max_ratio`` caps hours per share unit for any participant (None means no cap).
    """

    tasks: tuple[Task, ...]
    offers: tuple[Offer, ...]
    shares: Mapping[str, int]
    answers: Mapping[tuple[str, str], VaultAnswer] = field(
        default_factory=dict[tuple[str, str], VaultAnswer]
    )
    overlaps: Mapping[str, Overlap] = field(default_factory=dict[str, Overlap])
    ballots: Mapping[str, Mapping[str, str]] = field(default_factory=dict[str, Mapping[str, str]])
    minute_value: int = 1
    max_ratio: Fraction | None = None

    @property
    def task_ids(self) -> tuple[str, ...]:
        return tuple(sorted(t.task_id for t in self.tasks))

    def without(self, participants: frozenset[str]) -> Problem:
        """The same problem with these participants' offers removed."""
        kept = tuple(o for o in self.offers if o.participant not in participants)
        return replace(self, offers=kept)

    def bid_table(self) -> dict[tuple[str, str], Bid]:
        """Eligible bids keyed by (task_id, participant); the cheapest offer wins a duplicate."""
        table: dict[tuple[str, str], Bid] = {}
        for offer in self.offers:
            if self.shares.get(offer.participant, 0) <= 0:
                continue
            answer = self.answers.get((offer.participant, offer.task_id))
            if answer == "no":
                continue
            cost = answer if isinstance(answer, Cost) else offer.cost
            key = (offer.task_id, offer.participant)
            bid = Bid(offer.participant, offer.task_id, cost)
            old = table.get(key)
            if old is None or cost_scalar(cost, self.minute_value) < cost_scalar(
                old.cost, self.minute_value
            ):
                table[key] = bid
        return table


def cost_scalar(cost: Cost, minute_value: int) -> int:
    """One number for a cost: money plus minutes valued at ``minute_value`` minor units."""
    return cost.money + cost.minutes * minute_value


def share_ratio(minutes: int, share: int) -> Fraction:
    """Assigned hours per share unit."""
    return Fraction(minutes, MINUTES_PER_HOUR * share)


def loads(
    problem: Problem, assignments: Assignments, table: Mapping[tuple[str, str], Bid]
) -> dict[str, int]:
    """Assigned minutes per participant. Entries without a bid are ignored."""
    totals: dict[str, int] = {}
    for task_id, who in assignments.items():
        bid = table.get((task_id, who))
        if bid is not None:
            totals[who] = totals.get(who, 0) + bid.cost.minutes
    return totals


def total_cost(
    problem: Problem, assignments: Assignments, table: Mapping[tuple[str, str], Bid]
) -> int:
    return sum(
        cost_scalar(bid.cost, problem.minute_value)
        for task_id, who in assignments.items()
        if (bid := table.get((task_id, who))) is not None
    )


def max_share_ratio(
    problem: Problem, assignments: Assignments, table: Mapping[tuple[str, str], Bid]
) -> Fraction:
    worst = Fraction(0)
    for who, minutes in loads(problem, assignments, table).items():
        worst = max(worst, share_ratio(minutes, problem.shares[who]))
    return worst
