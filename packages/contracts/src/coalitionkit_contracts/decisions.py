# SPDX-License-Identifier: Apache-2.0
"""Decisions per decider: first answer wins, a subject is decided when every decider consented."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Literal

State = Literal["pending", "decided", "refused"]


class NotADeciderError(ValueError):
    """The answering participant is not named for this subject (``not_a_decider``)."""


def record_answer(
    answers: Mapping[str, bool], named: Collection[str], decider: str, consent: bool
) -> tuple[dict[str, bool], bool]:
    """Record one decider's answer for one (subject, revision).

    Returns the new answers and whether this answer was recorded. A second answer from the same
    decider is not recorded (the first one wins) and ``recorded`` is False.
    """
    if decider not in named:
        raise NotADeciderError(decider)
    if decider in answers:
        return dict(answers), False
    return {**answers, decider: consent}, True


def tally(named: Collection[str], answers: Mapping[str, bool]) -> State:
    """``refused`` on any refusal, ``decided`` when every named decider consented, else pending."""
    if any(answers.get(name) is False for name in named):
        return "refused"
    if named and all(answers.get(name) is True for name in named):
        return "decided"
    return "pending"
