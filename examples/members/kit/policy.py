# SPDX-License-Identifier: Apache-2.0
"""The member's private side: its vault policy and its owner's consent callback."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class Terms:
    """What the owner is willing to offer for one task."""

    minutes: int
    money: int
    effort: str


@dataclass
class VaultPolicy:
    """A local vault: it answers a query with yes, no or a cost, and nothing else.

    ``private_note`` stands for data that must never leave: the run checks that it appears in
    no envelope and in no prompt.
    """

    terms: dict[str, Terms]
    private_note: str = ""
    feasible_labels: frozenset[str] = field(default_factory=frozenset[str])

    def answer(self, kind: str, subject: str) -> Any:
        """The only shapes a vault returns: ``"yes"``, ``"no"`` or a cost object."""
        can = subject in self.feasible_labels and subject in self.terms
        if kind == "cost":
            if not can:
                return "no"
            t = self.terms[subject]
            return {"minutes": t.minutes, "money": t.money, "effort": t.effort}
        return "yes" if can else "no"


class OwnerCallback(Protocol):
    """The person behind the member. Every consent an owner key signs passes through here."""

    async def accept_charter(self, charter: dict[str, Any]) -> bool: ...

    async def consent_plan(self, plan_id: str, my_task_ids: list[str]) -> bool: ...

    async def approve_commitment(self, task_id: str) -> bool: ...


@dataclass
class AutoOwner:
    """An automatic owner policy for tests and unattended runs: accept a fair share."""

    max_tasks: int = 1
    asked: list[str] = field(default_factory=lambda: [])

    async def accept_charter(self, charter: dict[str, Any]) -> bool:
        self.asked.append("charter")
        return bool(charter["deciders"])

    async def consent_plan(self, plan_id: str, my_task_ids: list[str]) -> bool:
        self.asked.append("plan")
        return len(my_task_ids) <= self.max_tasks

    async def approve_commitment(self, task_id: str) -> bool:
        self.asked.append("commitment")
        return True
