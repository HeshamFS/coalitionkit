# SPDX-License-Identifier: Apache-2.0
"""Decisions per decider: first answer wins, a subject is decided when every decider consented."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Literal

State = Literal["pending", "decided", "refused"]
ChoiceState = Literal["pending", "decided", "refused", "split"]


class NotADeciderError(ValueError):
    """The answering participant is not named for this subject (``not_a_decider``)."""


def record_answer[T](
    answers: Mapping[str, T], named: Collection[str], decider: str, consent: T
) -> tuple[dict[str, T], bool]:
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


def tally_choice(
    named: Collection[str], answers: Mapping[str, tuple[bool, str]]
) -> tuple[ChoiceState, str | None]:
    """Tally a subject whose consents each name a ``choice`` (a ``tension_option``).

    ``answers`` maps a decider to ``(consent, choice)``. Returns the state and the chosen option:
    ``refused`` on any refusal; ``split`` when two consents name different options (no option has
    every decider, so the tension is replanned); ``decided`` when every named decider consented to
    the same option; otherwise ``pending``.
    """
    if any(answers.get(name, (True, ""))[0] is False for name in named):
        return "refused", None
    chosen = {answers[name][1] for name in named if name in answers}
    if len(chosen) > 1:
        return "split", None
    if named and all(name in answers for name in named):
        return "decided", next(iter(chosen))
    return "pending", None
