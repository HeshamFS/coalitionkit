# SPDX-License-Identifier: Apache-2.0
"""Task status table, replanning, commitment states, decision deadlines and choice consensus."""

from __future__ import annotations

from typing import get_args

import pytest

from coalitionkit_contracts import (
    ACCEPTS,
    DecisionExpiredError,
    accepts,
    after_planning_start,
    after_replan,
    check_decision_window,
    decision_expired,
    delivery_form,
    may_create_commitment,
    record_answer,
    supersede_active,
    tally_choice,
)
from coalitionkit_contracts.lifecycle import Action, CommitmentState, TaskStatus

STATUSES: tuple[TaskStatus, ...] = get_args(TaskStatus)
NAMED = ["p1", "p2"]


def test_every_status_has_a_row() -> None:
    assert set(ACCEPTS) == set(STATUSES)
    assert all(a in get_args(Action) for row in ACCEPTS.values() for a in row)


def test_c10_two_task_scenario() -> None:
    # Task A went back to negotiating, task B is committed.
    for action in ("answer", "match", "offer"):
        assert accepts("negotiating", action)
    assert not accepts("negotiating", "done")
    assert accepts("committed", "done")
    assert not accepts("committed", "answer")
    assert not accepts("committed", "match")
    assert not accepts("committed", "offer")


def test_a_pending_commitment_can_be_withdrawn_in_decided() -> None:
    assert accepts("decided", "commit.withdrawn")
    assert accepts("decided", "commit.pending")
    assert accepts("committed", "commit.withdrawn")
    assert not accepts("proposed", "commit.withdrawn")
    assert not accepts("negotiating", "commit.withdrawn")


def test_terminal_statuses_accept_nothing() -> None:
    assert ACCEPTS["done"] == ACCEPTS["withdrawn"] == frozenset()


def test_planning_starts_an_open_task_only() -> None:
    assert after_planning_start("open") == "negotiating"
    for status in STATUSES:
        if status != "open":
            assert after_planning_start(status) == status


def test_replan_sends_decided_work_back_to_negotiating() -> None:
    for status in STATUSES:
        expected = "negotiating" if status in ("proposed", "decided", "committed") else status
        assert after_replan(status) == expected


def test_replan_supersedes_the_active_commitment_and_frees_the_task() -> None:
    states: dict[str, CommitmentState] = {"c1": "approved", "c0": "withdrawn"}
    assert not may_create_commitment(states.values())
    after = supersede_active(states)
    assert after == {"c1": "superseded", "c0": "withdrawn"}
    assert may_create_commitment(after.values())
    assert supersede_active({"c2": "pending"}) == {"c2": "superseded"}


def test_decision_deadline_is_absolute_and_strict() -> None:
    deadline = "2026-11-01T18:00:00Z"
    assert not decision_expired(deadline, "2026-11-01T18:00:00Z")
    assert not decision_expired(deadline, "2026-11-01T19:00:00+02:00")
    assert decision_expired(deadline, "2026-11-01T18:00:00.001Z")
    check_decision_window(deadline, "2026-11-01T17:59:59Z")
    with pytest.raises(DecisionExpiredError):
        check_decision_window(deadline, "2026-11-01T20:00:00+01:00")


def test_same_option_from_every_decider_decides_it() -> None:
    assert tally_choice(NAMED, {"p1": (True, "a"), "p2": (True, "a")}) == ("decided", "a")
    assert tally_choice(NAMED, {"p1": (True, "a")}) == ("pending", None)
    assert tally_choice(NAMED, {}) == ("pending", None)


def test_different_options_split_and_decide_nothing() -> None:
    assert tally_choice(NAMED, {"p1": (True, "a"), "p2": (True, "b")}) == ("split", None)
    three = ["p1", "p2", "p3"]
    assert tally_choice(three, {"p1": (True, "a"), "p2": (True, "b")}) == ("split", None)


def test_any_refusal_refuses_whatever_the_others_chose() -> None:
    assert tally_choice(NAMED, {"p1": (True, "a"), "p2": (False, "a")}) == ("refused", None)
    assert tally_choice(NAMED, {"p1": (False, "b")}) == ("refused", None)


def test_choice_answers_are_recorded_first_wins() -> None:
    answers, recorded = record_answer({}, NAMED, "p1", (True, "a"))
    assert recorded
    again, recorded = record_answer(answers, NAMED, "p1", (True, "b"))
    assert not recorded
    assert again == {"p1": (True, "a")}


def test_delivery_form_for_acknowledgements_and_deliveries() -> None:
    assert delivery_form(in_scope=True, redacted=False, viewer_specific=False) == "original"
    assert delivery_form(in_scope=True, redacted=True, viewer_specific=False) == "projection"
    assert delivery_form(in_scope=True, redacted=False, viewer_specific=True) == "projection"
    assert delivery_form(in_scope=False, redacted=False, viewer_specific=False) == "receipt_only"
    assert delivery_form(in_scope=False, redacted=True, viewer_specific=True) == "receipt_only"
