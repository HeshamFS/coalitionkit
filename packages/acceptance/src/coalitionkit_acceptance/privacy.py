# SPDX-License-Identifier: Apache-2.0
"""Acceptance test 2, privacy: many runs, 20 canaries each, adversarial members, zero found."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from contextlib import AsyncExitStack
from dataclasses import dataclass, field

import httpx

from coalitionkit_surfaces import create_app

from .adversaries import Attacker, scripted_program
from .canaries import Registry
from .metrics import Recorder
from .privacy_collect import HONEST, Observer, agent_prompts, steward_pass
from .privacy_mcp import HostBackedPorts, McpRun
from .privacy_world import NAMES, PrivacyWorld
from .scanner import Leak, ScanResult, merge, scan

Driver = Callable[[Attacker], Awaitable[None]]


@dataclass
class PrivacyResult:
    seed: int
    registry: Registry
    result: ScanResult
    events: int
    refusals: dict[str, str]
    psi_refusals: list[str]
    psi_overlap_ok: bool
    verdicts: int
    prompts: int
    attack_log: dict[str, list[str]] = field(default_factory=lambda: dict[str, list[str]]())

    @property
    def leaks(self) -> list[Leak]:
        return self.result.leaks


async def run_privacy(
    seed: int,
    *,
    steward_mode: str = HONEST,
    drivers: Mapping[str, Driver] | None = None,
    after_attacks: Callable[[PrivacyWorld], Awaitable[None]] | None = None,
) -> PrivacyResult:
    """One run. ``drivers`` maps a member to its attack program (scripted by default)."""
    world = PrivacyWorld(seed)
    observer = Observer(world)

    def on_phase(label: str) -> None:
        if label == "enrolled":
            observer.open_feeds()
        else:
            observer.step_feeds(label)

    world.build(on_phase)
    ports = HostBackedPorts(
        world.host, world.people, lambda s, v, label, value: world.record(s, v, label, value)
    )
    mcp = McpRun(ports, observer.tokens)
    attack_log: dict[str, list[str]] = {}
    transport = httpx.ASGITransport(app=create_app(observer.hub))
    with mcp.serve():
        async with AsyncExitStack() as stack:
            http = await stack.enter_async_context(
                httpx.AsyncClient(transport=transport, base_url="http://hub")
            )
            attackers: list[Attacker] = []
            for name in NAMES:
                session = await stack.enter_async_context(mcp.session(name))
                attackers.append(Attacker(world, observer, session, http, name))
            for attacker in attackers:
                driver = (drivers or {}).get(attacker.name, scripted_program)
                await driver(attacker)
                attack_log[attacker.name] = attacker.log
    observer.step_feeds("after attacks")
    if after_attacks is not None:
        await after_attacks(world)
    observer.collect()
    prompts = await agent_prompts(world)
    verdicts = await steward_pass(world, steward_mode)
    events = len(world.arena.events())
    overlap_ok = sorted(world.psi.overlap) == sorted(
        set(world.psi_sets["p3"]) & set(world.psi_sets["p4"])
    )
    outcome = PrivacyResult(
        seed,
        world.registry,
        scan(world.ledger, world.registry),
        events,
        world.refusals,
        world.psi.refusals,
        overlap_ok,
        verdicts,
        prompts,
        attack_log,
    )
    world.arena.close()
    return outcome


def record(recorder: Recorder, outcome: PrivacyResult) -> None:
    """Add one run's counts to the recorder: canaries, events, per-surface scans and leaks."""
    recorder.count("runs")
    recorder.count("canaries", len(outcome.registry.canaries))
    recorder.count("events", outcome.events)
    recorder.count("canaries_found_outside_vault", len(outcome.leaks))
    for key, count in outcome.result.scanned.items():
        recorder.count(f"scanned.{key}", count)
    for key, count in outcome.result.sightings.items():
        recorder.count(f"sightings_allowed.{key}", count)
    for key, count in outcome.result.model_prompts.items():
        recorder.count(f"sent_to_model.{key}", count)
    for key, count in outcome.result.leaked.items():
        recorder.count(f"leaks.{key}", count)


def totals(outcomes: list[PrivacyResult]) -> dict[str, dict[str, int]]:
    scanned: dict[str, int] = {}
    sightings: dict[str, int] = {}
    leaked: dict[str, int] = {}
    for item in outcomes:
        merge(scanned, item.result.scanned)
        merge(sightings, item.result.sightings)
        merge(leaked, item.result.leaked)
    sent: dict[str, int] = {}
    for item in outcomes:
        merge(sent, item.result.model_prompts)
    return {
        "scanned": scanned,
        "sightings_allowed": sightings,
        "leaks": leaked,
        "sent_to_models": sent,
    }
