# SPDX-License-Identifier: Apache-2.0
"""Acceptance test 7 over the real server; the database cases run on postgres:18 in Docker."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from coalitionkit_acceptance import chaos_server as chaos
from coalitionkit_acceptance.ledger import record_run
from coalitionkit_acceptance.live import close_kit, live_enabled, live_kit, live_skip_reason
from coalitionkit_acceptance.metrics import SESSION, Recorder
from coalitionkit_acceptance.postgres import PostgresContainer, docker_missing_reason

RECOVERY_LIMIT_S = 60.0
NO_DOCKER = docker_missing_reason()


def clean(recorder: Recorder) -> None:
    SESSION.add(recorder)
    assert recorder.counter("lost_events") == 0
    assert recorder.counter("duplicate_events") == 0
    assert recorder.counter("max_decisions_per_revision") == 1


def check_recovery(recorder: Recorder) -> None:
    clean(recorder)
    assert recorder.counter("plan_decided") == 1
    (recovery,) = recorder.series("recovery_s")
    assert 0 < recovery < RECOVERY_LIMIT_S


def check_boundary(recorder: Recorder, *, stored: bool) -> None:
    """The kill landed at the defined boundary, and the client never got a reply."""
    check_recovery(recorder)
    assert recorder.counter("boundary_reached") == 1
    assert recorder.counter("in_flight_acknowledged") == 0
    assert recorder.counter("in_flight_lost_reply") == 1
    assert recorder.counter("persisted_before_retry") == int(stored)
    assert recorder.counter("viewer_missing_events") == 0


async def test_kill_after_the_decision_is_stored_and_before_the_reply(tmp_path: Path) -> None:
    """Persistence-before-reply: the event is in the store though the client heard nothing."""
    url = f"sqlite:///{tmp_path / 'host.db'}"
    recorder = await chaos.kill_server(tmp_path, url, "sqlite", boundary="persisted")
    check_boundary(recorder, stored=True)


async def test_kill_before_the_decision_is_stored(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'host.db'}"
    recorder = await chaos.kill_server(tmp_path, url, "sqlite", boundary="received")
    check_boundary(recorder, stored=False)


async def test_two_deciders_answering_at_once_decide_once_per_revision(tmp_path: Path) -> None:
    recorder = await chaos.concurrent_deciders(tmp_path)
    clean(recorder)
    rounds = 12
    assert recorder.counter("accepted_p1") == rounds
    assert recorder.counter("accepted_p2") == rounds
    assert recorder.counter("outcome_decided") + recorder.counter("outcome_refused") == rounds
    assert recorder.counter("outcome_decided") > 0
    assert recorder.counter("outcome_refused") > 0


async def test_a_viewer_disconnecting_with_a_consent_open_misses_nothing(tmp_path: Path) -> None:
    recorder = await chaos.viewer_disconnect(tmp_path)
    clean(recorder)
    assert recorder.counter("consent_still_open") == 1
    assert recorder.counter("plan_still_pending") == 1
    assert recorder.counter("events_caught_up") == 6
    assert recorder.counter("viewer_lost_events") == 0
    assert recorder.counter("plan_decided") == 1


@pytest.fixture(scope="module")
def postgres() -> Iterator[PostgresContainer]:
    if NO_DOCKER is not None:
        pytest.skip(NO_DOCKER)
    with PostgresContainer() as container:
        yield container


async def test_kill_the_server_and_restart_on_postgres(
    tmp_path: Path, postgres: PostgresContainer
) -> None:
    url = postgres.new_database()
    recorder = await chaos.kill_server(tmp_path, url, "postgres", boundary="persisted")
    check_boundary(recorder, stored=True)


async def test_kill_the_database_and_start_it_again(
    tmp_path: Path, postgres: PostgresContainer
) -> None:
    recorder = await chaos.database_fault(tmp_path, postgres, "kill")
    check_recovery(recorder)
    assert recorder.counter("refused_while_down") == 1
    assert len(recorder.series("database_restart_s")) == 1


async def test_drop_the_database_connection(tmp_path: Path, postgres: PostgresContainer) -> None:
    recorder = await chaos.database_fault(tmp_path, postgres, "drop")
    check_recovery(recorder)
    assert recorder.counter("connections_dropped") >= 1


@pytest.mark.live
async def test_kill_the_server_with_the_live_model_auditing_the_plan(tmp_path: Path) -> None:
    if not live_enabled():
        pytest.skip(live_skip_reason())
    kit = live_kit()
    try:
        recorder = await chaos.kill_server(
            tmp_path, f"sqlite:///{tmp_path / 'host.db'}", "sqlite_live", kit
        )
    finally:
        await close_kit(kit)
    recorder.value("live_cost_micro_usd", sum(r.cost_micro_usd for r in kit.meter.records))
    recorder.value("live_calls", len(kit.meter.records))
    record_run("chaos_live", kit.meter)
    check_recovery(recorder)
    assert len(kit.meter.records) >= 1  # the Steward audited the plan with the real model


async def test_a_lost_acknowledged_event_is_counted(tmp_path: Path) -> None:
    rig = chaos.Rig(tmp_path, f"sqlite:///{tmp_path / 'host.db'}")
    try:
        await rig.seed()
        rig.acknowledged.add("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        recorder = Recorder("audit_probe")
        rig.audit(recorder)
        assert recorder.counter("lost_events") == 1
    finally:
        rig.close()
