# SPDX-License-Identifier: Apache-2.0
"""Acceptance test 2: privacy canaries. Pass mark: no canary found outside its vault."""

from __future__ import annotations

import pytest

from coalitionkit_acceptance.canaries import Canary, Registry
from coalitionkit_acceptance.config import full_run
from coalitionkit_acceptance.metrics import SESSION, Recorder
from coalitionkit_acceptance.privacy import PrivacyResult, record, run_privacy, totals
from coalitionkit_acceptance.privacy_world import PrivacyWorld
from coalitionkit_acceptance.scanner import SURFACES, Ledger, scan

RUNS = 100 if full_run() else 10


def describe(outcomes: list[PrivacyResult]) -> str:
    return "\n".join(f"seed {o.seed}: {leak.describe()}" for o in outcomes for leak in o.leaks[:5])


async def test_no_canary_is_found_outside_its_vault() -> None:
    recorder = Recorder("privacy" if not full_run() else "privacy_full")
    outcomes: list[PrivacyResult] = []
    for seed in range(RUNS):
        outcome = await run_privacy(seed)
        record(recorder, outcome)
        outcomes.append(outcome)
        assert len(outcome.registry.canaries) == 20
    recorder.value("totals", totals(outcomes))
    recorder.value("canary_placements", outcomes[0].registry.counts())
    SESSION.add(recorder)
    assert recorder.counter("canaries") == 20 * RUNS
    assert recorder.counter("canaries_found_outside_vault") == 0, describe(outcomes)
    # The scanners really looked: every surface was read, and the allowed sightings are real.
    scanned = totals(outcomes)["scanned"]
    assert set(scanned) >= set(SURFACES) - {"adversary_guess"}
    assert all(scanned[s] > 0 for s in scanned)
    assert totals(outcomes)["sightings_allowed"]["log"] > 0


async def test_the_adversaries_actually_ran() -> None:
    outcome = await run_privacy(3)
    for name, steps in outcome.attack_log.items():
        kinds = {line.split(":")[0] for line in steps}
        assert {
            "view",
            "mcp_tool",
            "mcp_resource",
            "probe",
            "widen_scope",
            "replay_old",
        } <= kinds, name
    assert outcome.psi_overlap_ok
    replays = [
        line for steps in outcome.attack_log.values() for line in steps if "replay_old" in line
    ]
    assert replays and all("duplicate_mismatch" in line and "detail={}" in line for line in replays)


def test_the_registry_spans_every_placement_and_shape() -> None:
    world = PrivacyWorld(5)
    world.build()
    registry = world.registry
    assert len(registry.canaries) == 20
    assert registry.counts() == {
        "vault_fact": 5, "vault_note": 3, "redact": 3, "private_scope": 3,
        "assignment": 2, "psi_input": 4,
    }  # fmt: skip
    assert {c.shape for c in registry.canaries} == {"number", "word", "slot", "document"}
    world.arena.close()


def test_derived_outputs_take_the_narrowest_scope_and_are_never_widened() -> None:
    world = PrivacyWorld(11)
    world.build()
    tensions = [e for e in world.arena.events() if e["type"] == "coalition.tension"]
    scopes = {e["scope"]["audience"] for e in tensions}
    assert scopes == {"host", "participants"}
    host_only = next(e for e in tensions if e["scope"]["audience"] == "host")
    assert "redact" not in host_only["scope"]
    assert set(world.refusals.values()) == {"scope_violation"}
    world.arena.close()


async def test_scanners_detect_a_leak_when_redaction_is_broken(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Negative control: with the host's redaction switched off the run must report leaks."""
    monkeypatch.setattr("coalitionkit_runtime.projector.remove_path", drop)
    outcome = await run_privacy(2)
    surfaces = set(outcome.result.leaked)
    assert {"delivery", "view", "ack"} <= surfaces
    assert {leak.placement for leak in outcome.leaks} == {"redact"}


def test_a_canary_is_found_in_every_encoding() -> None:
    canary = Canary("c1", "slot", "vault_fact", "p1", "2077-03-04T05:06:00Z", "2077-03-04T05:06")
    registry = Registry([canary])
    ledger = Ledger()
    for index, form in enumerate(canary.variants()):
        ledger.record("http", "p2", f"form {index}", f"xx {form} yy")
    result = scan(ledger, registry)
    assert len(result.leaks) == len(canary.variants())
    ledger = Ledger()
    ledger.record("prompt", "p2", "own agent", canary.needle, agent_owner="p1")
    assert scan(ledger, registry).leaks == []
    ledger.record("prompt", "p2", "another agent", canary.needle, agent_owner="p2")
    assert len(scan(ledger, registry).leaks) == 1


def drop(*_args: object) -> None:
    return None
