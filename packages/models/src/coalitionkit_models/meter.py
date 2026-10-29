# SPDX-License-Identifier: Apache-2.0
"""The cost meter: integer micro-USD per Coalition and per participant, with a budget.

It warns once at 80 percent of a Coalition's budget and refuses new model calls at 100 percent
(``BudgetExhaustedError``, protocol error ``budget_exhausted``). Calls already in flight finish.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from .errors import BudgetExhaustedError
from .prices import PriceTable

SYSTEM_PARTICIPANT = "_system"
WARN_PERCENT = 80

EventKind = Literal["budget_warning", "budget_exhausted"]


@dataclass(frozen=True)
class BudgetEvent:
    kind: EventKind
    coalition_id: str
    spent: int
    limit: int


@dataclass(frozen=True)
class CostRecord:
    coalition_id: str
    participant: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int
    cost_micro_usd: int
    reasoning_tokens: int = 0
    images: int = 0
    audio_ms: int = 0


class CostMeter:
    def __init__(
        self, prices: PriceTable, on_event: Callable[[BudgetEvent], None] | None = None
    ) -> None:
        self.prices = prices
        self._on_event = on_event
        self._lock = threading.Lock()
        self._limits: dict[str, int] = {}
        self._by_coalition: dict[str, int] = defaultdict(int)
        self._by_participant: dict[tuple[str, str], int] = defaultdict(int)
        self._fired: set[tuple[str, EventKind]] = set()
        self.events: list[BudgetEvent] = []
        self.records: list[CostRecord] = []

    def set_budget(self, coalition_id: str, limit_micro_usd: int) -> None:
        if limit_micro_usd < 0:
            raise ValueError("a budget cannot be negative")
        with self._lock:
            self._limits[coalition_id] = limit_micro_usd

    def total(self, coalition_id: str) -> int:
        return self._by_coalition[coalition_id]

    def participant_total(self, coalition_id: str, participant: str) -> int:
        return self._by_participant[(coalition_id, participant)]

    def participant_totals(self, coalition_id: str) -> dict[str, int]:
        return {p: c for (cid, p), c in self._by_participant.items() if cid == coalition_id}

    def is_exhausted(self, coalition_id: str) -> bool:
        limit = self._limits.get(coalition_id)
        return limit is not None and self._by_coalition[coalition_id] >= limit

    def check(self, coalition_id: str) -> None:
        """Raise BudgetExhaustedError when the Coalition may not start another model call."""
        if self.is_exhausted(coalition_id):
            raise BudgetExhaustedError(
                coalition_id, self._by_coalition[coalition_id], self._limits[coalition_id]
            )

    def record(
        self,
        coalition_id: str,
        participant: str,
        model: str,
        *,
        prompt_tokens: int,
        completion_tokens: int,
        cached_tokens: int = 0,
        reasoning_tokens: int = 0,
    ) -> CostRecord:
        """Price one response from its usage fields and add it to the totals.

        ``reasoning_tokens`` are already inside ``completion_tokens`` (they bill at the output
        rate); they are kept on the record so reasoning cost can be reported.
        """
        cost = self.prices.cost_micro_usd(
            model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cached_tokens=cached_tokens,
        )
        entry = CostRecord(
            coalition_id,
            participant,
            model,
            prompt_tokens,
            completion_tokens,
            cached_tokens,
            cost,
            reasoning_tokens=reasoning_tokens,
        )
        return self._add(entry)

    def record_media(
        self,
        coalition_id: str,
        participant: str,
        model: str,
        *,
        images: int = 0,
        audio_ms: int = 0,
    ) -> CostRecord:
        """Price one media call (images generated or segmented, audio transcribed)."""
        cost = self.prices.media_cost_micro_usd(model, images=images, audio_ms=audio_ms)
        entry = CostRecord(
            coalition_id, participant, model, 0, 0, 0, cost, images=images, audio_ms=audio_ms
        )
        return self._add(entry)

    def reasoning_tokens(self, coalition_id: str) -> int:
        return sum(r.reasoning_tokens for r in self.records if r.coalition_id == coalition_id)

    def _add(self, entry: CostRecord) -> CostRecord:
        coalition_id, participant, cost = (
            entry.coalition_id,
            entry.participant,
            entry.cost_micro_usd,
        )
        with self._lock:
            self._by_coalition[coalition_id] += cost
            self._by_participant[(coalition_id, participant)] += cost
            self.records.append(entry)
            fired = self._threshold_events(coalition_id)
        if self._on_event is not None:
            for event in fired:
                self._on_event(event)
        return entry

    def _threshold_events(self, coalition_id: str) -> list[BudgetEvent]:
        limit = self._limits.get(coalition_id)
        if limit is None:
            return []
        spent = self._by_coalition[coalition_id]
        due: list[EventKind] = []
        if spent * 100 >= limit * WARN_PERCENT:
            due.append("budget_warning")
        if spent >= limit:
            due.append("budget_exhausted")
        out: list[BudgetEvent] = []
        for kind in due:
            if (coalition_id, kind) not in self._fired:
                self._fired.add((coalition_id, kind))
                event = BudgetEvent(kind, coalition_id, spent, limit)
                self.events.append(event)
                out.append(event)
        return out
