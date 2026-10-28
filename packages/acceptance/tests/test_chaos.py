# SPDX-License-Identifier: Apache-2.0
"""Acceptance test 7: chaos, with the pass conditions that do not depend on timing."""

from __future__ import annotations

from pathlib import Path

import pytest

from coalitionkit_acceptance import chaos
from coalitionkit_acceptance.config import database_url
from coalitionkit_acceptance.metrics import SESSION, Recorder


def clean(recorder: Recorder) -> None:
    SESSION.add(recorder)
    assert recorder.counter("lost_events") == 0
    assert recorder.counter("duplicate_events") == 0
    assert recorder.counter("max_decisions_per_revision") == 1


def check_kill(recorder: Recorder) -> None:
    clean(recorder)
    assert recorder.counter("replies_lost") == 1
    assert recorder.counter("commits_lost") == 1
    assert recorder.counter("replayed_receipts_match_log") == 1
    assert recorder.counter("prefix_intact") == 1
    assert recorder.counter("not_committed_before_retry") == 0
    assert recorder.counter("events_added_by_retries") == 2
    assert recorder.counter("plan_decided") == 1
    assert len(recorder.series("recovery_s")) == 2


def test_kill_the_host_mid_negotiation_and_restart_from_the_store(tmp_path: Path) -> None:
    check_kill(chaos.kill_and_restart(tmp_path))


@pytest.mark.skipif(database_url() is None, reason="needs COALITIONKIT_TEST_DATABASE_URL")
def test_kill_and_restart_on_postgres(tmp_path: Path) -> None:
    check_kill(chaos.kill_and_restart(tmp_path, database_url()))


def test_dropped_database_connection_loses_and_repeats_nothing() -> None:
    recorder = chaos.drop_connection()
    clean(recorder)
    assert recorder.counter("faults_fired") >= 12
    assert recorder.counter("retries") >= 12
    assert recorder.counter("viewer_lost_events") == 0


def test_two_deciders_answering_at_once_decide_once_per_revision() -> None:
    rounds = 20
    recorder = chaos.concurrent_deciders(rounds)
    clean(recorder)
    assert recorder.counter("accepted_alice") == rounds
    assert recorder.counter("accepted_bob") == rounds
    outcomes = recorder.counter("outcome_decided") + recorder.counter("outcome_refused")
    assert outcomes == rounds
    assert recorder.counter("outcome_decided") > 0
    assert recorder.counter("outcome_refused") > 0


def test_a_viewer_disconnecting_with_a_consent_open_misses_nothing() -> None:
    recorder = chaos.viewer_disconnects_with_consent_open()
    clean(recorder)
    assert recorder.counter("consent_still_open") == 1
    assert recorder.counter("plan_still_pending") == 1
    assert recorder.counter("events_caught_up") == 6
    assert recorder.counter("plan_decided") == 1
    assert recorder.counter("viewer_lost_events") == 0
