# SPDX-License-Identifier: Apache-2.0
"""Private records keyed by public subject identifiers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from coalitionkit_contracts.payloads import AnswerPayload, Cost, QueryPayload, Window


@dataclass(frozen=True)
class Capacity:
    amount: int
    unit: str

    def __post_init__(self) -> None:
        if type(self.amount) is not int or not 0 <= self.amount <= 2**53 - 1:
            raise ValueError("invalid capacity")
        if not self.unit:
            raise ValueError("capacity needs a unit")


@dataclass(frozen=True)
class Interval:
    start: str
    end: str

    def __post_init__(self) -> None:
        Window(start=self.start, end=self.end)
        if self.bounds()[0] >= self.bounds()[1]:
            raise ValueError("interval must have positive duration")

    def bounds(self) -> tuple[datetime, datetime]:
        return datetime.fromisoformat(self.start.upper()), datetime.fromisoformat(self.end.upper())


@dataclass(frozen=True)
class Facts:
    """A subject's stock, slots and sets; any positive record makes it feasible.

    Availability means at least one free slot. Cost is an explicitly registered
    tariff and is returned only for a feasible subject. No clock-dependent policy
    is inferred from the query's response timeout.
    """

    slots: tuple[Interval, ...] = ()
    capacities: tuple[Capacity, ...] = ()
    sets: dict[str, frozenset[str]] = field(default_factory=lambda: dict[str, frozenset[str]]())
    cost: Cost | None = None


class Vault:
    def __init__(self, participant_id: str) -> None:
        if not participant_id:
            raise ValueError("participant required")
        self.participant_id = participant_id
        self._facts: dict[str, Facts] = {}
        self._notes: list[str] = []

    def put(self, subject: str, facts: Facts) -> None:
        self._facts[subject] = Facts(
            tuple(facts.slots), tuple(facts.capacities), dict(facts.sets), facts.cost
        )

    def add_private_note(self, note: str) -> None:
        self._notes.append(note)

    def answer(self, query: QueryPayload, *, elapsed_ms: int = 0) -> AnswerPayload:
        from .answer import answer

        return answer(self._facts.get(query.subject), query, elapsed_ms=elapsed_ms)
