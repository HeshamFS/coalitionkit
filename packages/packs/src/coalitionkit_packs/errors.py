# SPDX-License-Identifier: Apache-2.0
"""The loader's report: every rule a pack broke, by rule id and place."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Problem:
    rule: str
    where: str
    message: str

    def __str__(self) -> str:
        return f"[{self.rule}] {self.where}: {self.message}"


class PackError(Exception):
    """A pack failed validation or verification and does not load."""

    def __init__(self, problems: list[Problem]) -> None:
        super().__init__("; ".join(str(p) for p in problems))
        self.problems = problems

    def rules(self) -> set[str]:
        return {p.rule for p in self.problems}


class Report:
    """Collects problems so one run names every broken rule."""

    def __init__(self) -> None:
        self.problems: list[Problem] = []

    def add(self, rule: str, where: str, message: str) -> None:
        self.problems.append(Problem(rule, where, message))

    def raise_if_any(self) -> None:
        if self.problems:
            raise PackError(list(self.problems))
