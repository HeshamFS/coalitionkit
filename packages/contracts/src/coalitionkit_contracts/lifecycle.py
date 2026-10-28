# SPDX-License-Identifier: Apache-2.0
"""Task status, commitment states and decision deadlines (spec: Lifecycle rules and ordering).

Pure tables and functions the host applies; nothing here stores state.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from datetime import datetime
from typing import Literal

TaskStatus = Literal["open", "negotiating", "proposed", "decided", "committed", "done", "withdrawn"]
#: What a message is, for the task-status check: its type plus the part that changes the answer.
Action = Literal[
    "offer",
    "answer",
    "match",
    "ripple",
    "decide.plan",
    "decide.tension_option",
    "decide.task",
    "decide.commitment",
    "commit.pending",
    "commit.withdrawn",
    "done",
]
CommitmentState = Literal["pending", "approved", "withdrawn", "superseded"]

#: Accepted-about-the-task table from the spec. ``commit.withdrawn`` is accepted in ``decided``
#: (a pending commitment) as well as in ``committed`` (an approved one).
ACCEPTS: Mapping[TaskStatus, frozenset[Action]] = {
    "open": frozenset({"offer", "ripple"}),
    "negotiating": frozenset({"answer", "match", "offer", "ripple"}),
    "proposed": frozenset({"decide.plan", "decide.tension_option", "decide.task", "ripple"}),
    "decided": frozenset(
        {"commit.pending", "commit.withdrawn", "decide.commitment", "decide.task", "ripple"}
    ),
    "committed": frozenset({"done", "commit.withdrawn", "ripple"}),
    "done": frozenset(),
    "withdrawn": frozenset(),
}

#: A commitment in one of these states is the task's *active* commitment.
ACTIVE_COMMITMENT_STATES: frozenset[CommitmentState] = frozenset({"pending", "approved"})


def accepts(status: TaskStatus, action: Action) -> bool:
    """True when a message of this kind about a task in ``status`` passes the status check."""
    return action in ACCEPTS[status]


def after_planning_start(status: TaskStatus) -> TaskStatus:
    """Status after the host's first query, proposal or tension names the task."""
    return "negotiating" if status == "open" else status


def after_replan(status: TaskStatus) -> TaskStatus:
    """Status after a refusal, a withdrawn commitment, a ripple or a decision expiry."""
    return "negotiating" if status in ("proposed", "decided", "committed") else status


def may_create_commitment(states: Collection[CommitmentState]) -> bool:
    """One active commitment per task: creation needs none of the task's commitments active."""
    return not any(state in ACTIVE_COMMITMENT_STATES for state in states)


def supersede_active(states: Mapping[str, CommitmentState]) -> dict[str, CommitmentState]:
    """The commitments of a task after a replan: every active one becomes ``superseded``."""
    return {
        cid: ("superseded" if state in ACTIVE_COMMITMENT_STATES else state)
        for cid, state in states.items()
    }


class DecisionExpiredError(ValueError):
    """The decision arrived after its subject's ``decision_deadline`` (``deadline_exceeded``)."""


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.upper())


def decision_expired(decision_deadline: str, at: str) -> bool:
    """True when ``at`` (the host's acceptance time, or its clock) is after the deadline."""
    return _parse(at) > _parse(decision_deadline)


def check_decision_window(decision_deadline: str, accepted_at: str) -> None:
    """Raise DecisionExpiredError when a decision is accepted after the deadline."""
    if decision_expired(decision_deadline, accepted_at):
        raise DecisionExpiredError(decision_deadline)
