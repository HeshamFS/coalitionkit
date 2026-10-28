# SPDX-License-Identifier: Apache-2.0
"""Subject revisions and decisions per decider."""

from __future__ import annotations

import pytest

from coalitionkit_contracts import (
    NotADeciderError,
    StaleSubjectError,
    check_revision,
    is_current,
    is_superseded,
    next_revision,
    record_answer,
    tally,
)
from coalitionkit_contracts.revisions import first_revision

NAMED = ["p1", "p2"]


def test_revisions_start_at_one_and_step_by_one() -> None:
    assert first_revision() == 1
    assert next_revision(1) == 2
    assert next_revision(41) == 42
    with pytest.raises(ValueError, match="start at 1"):
        next_revision(0)


def test_current_revision_passes_older_and_newer_fail() -> None:
    check_revision(3, 3)
    assert is_current(3, 3)
    for decided in (2, 4):
        assert not is_current(decided, 3)
        with pytest.raises(StaleSubjectError) as info:
            check_revision(decided, 3)
        assert (info.value.decided, info.value.current) == (decided, 3)


def test_a_change_supersedes_older_consent_requests_only() -> None:
    assert is_superseded(1, 2)
    assert not is_superseded(2, 2)
    assert not is_superseded(3, 2)


def test_first_answer_wins_per_decider() -> None:
    answers, recorded = record_answer({}, NAMED, "p1", True)
    assert recorded
    again, recorded = record_answer(answers, NAMED, "p1", False)
    assert not recorded
    assert again == {"p1": True}


def test_concurrent_answers_from_different_deciders_both_count() -> None:
    first, _ = record_answer({}, NAMED, "p1", True)
    second, recorded = record_answer(first, NAMED, "p2", True)
    assert recorded
    assert second == {"p1": True, "p2": True}
    assert tally(NAMED, second) == "decided"


def test_subject_is_decided_only_when_every_decider_consented() -> None:
    assert tally(NAMED, {}) == "pending"
    assert tally(NAMED, {"p1": True}) == "pending"
    assert tally(NAMED, {"p1": True, "p2": True}) == "decided"


def test_any_refusal_refuses_the_subject() -> None:
    assert tally(NAMED, {"p1": False}) == "refused"
    assert tally(NAMED, {"p1": True, "p2": False}) == "refused"


def test_an_unnamed_decider_is_refused() -> None:
    with pytest.raises(NotADeciderError):
        record_answer({}, NAMED, "p9", True)


def test_nobody_named_is_never_decided() -> None:
    assert tally([], {}) == "pending"
