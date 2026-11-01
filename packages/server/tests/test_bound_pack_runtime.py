# SPDX-License-Identifier: Apache-2.0
"""Bound pack behavior through signed submissions and durable runtime events."""

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_contracts import new_ulid, public_key_to_jwk, sign_consent, sign_owner_proof
from coalitionkit_gardener import build_propose
from coalitionkit_mcp.gateway import build_envelope
from coalitionkit_mcp.ports import HostedParticipant
from coalitionkit_packs import Pack, inspect_pack
from coalitionkit_packs.manifest import Strategy
from coalitionkit_packs.sections import TaskTemplate
from coalitionkit_runtime import Acknowledgement, AuthenticatedSender, CoalitionHost, SQLiteStore
from coalitionkit_runtime.steward import FakeSteward, Verdict
from coalitionkit_server import Settings
from coalitionkit_server.adapter import Document, HostPort
from coalitionkit_server.app import Server
from coalitionkit_server.packs import bind_runtime, plan_for
from coalitionkit_surfaces import load_catalog

NOW = "2026-11-01T00:00:00Z"
END = "2099-01-01T00:00:00Z"
PUBLIC: Document = {"audience": "coalition"}


def accepted(result: Acknowledgement | Document) -> Document:
    assert isinstance(result, Acknowledgement), result
    assert result.accepted is not None
    return result.accepted


@pytest.fixture
def pack() -> Pack:
    root = Path(__file__).parents[2] / "packs/tests/fixtures/pack-alpha"
    catalog = load_catalog(Path("spec/catalog/coalitionkit-v0_9.json"))
    loaded = inspect_pack(root, core_catalog=catalog)
    return replace(
        loaded,
        task_templates=(
            TaskTemplate(
                id="first", title="First task", requirements=["ready"], ext={"item_kind": "item"}
            ),
        ),
        schemas={**loaded.schemas, "offer": loaded.schemas["need"]},
    )


def person(name: str, owner: Ed25519PrivateKey | None = None) -> HostedParticipant:
    return HostedParticipant(
        name,
        "https://" + name + ".example/card",
        Ed25519PrivateKey.generate(),
        name,
        owner or Ed25519PrivateKey.generate(),
        name + "-owner",
    )


def open_host(store: SQLiteStore, pack: Pack | None) -> CoalitionHost:
    host = CoalitionHost(
        store,
        new_ulid(),
        "https://host.example/card",
        Ed25519PrivateKey.generate(),
        "host",
        clock=lambda: NOW,
    )
    bind_runtime(host, {(pack.name, pack.manifest.version): pack} if pack else {})
    host.create()
    charter: Document = {
        "goal": "Finish together",
        "roles": [{"id": "coordinator"}],
        "rules": [],
        "deadline": END,
        "deciders": ["a", "b"],
    }
    if pack:
        charter["pack"] = {"name": pack.name, "version": pack.manifest.version}
    accepted(host.host_emit("charter", charter, PUBLIC))
    return host


def send(
    host: CoalitionHost, who: HostedParticipant, kind: str, body: Document
) -> Acknowledgement | Document:
    return host.accept(
        build_envelope(who, host.coalition_id, "coalition." + kind, body, scope=PUBLIC),
        AuthenticatedSender(who.card_url, who.participant),
    )


def join(host: CoalitionHost, who: HostedParticipant) -> None:
    auth = AuthenticatedSender(who.card_url, who.participant)
    host.pin_card(auth, who.agent_key.public_key(), who.agent_kid)
    host.invite(auth)
    jwk = public_key_to_jwk(who.owner_key.public_key(), who.owner_kid)
    accepted(
        send(
            host,
            who,
            "join",
            {
                "card_url": who.card_url,
                "owner_key": jwk,
                "owner_proof": sign_owner_proof(
                    host.coalition_id, who.participant, who.card_url, jwk, who.owner_key
                ),
                "roles_requested": ["coordinator"],
                "surfaces": [],
                "vault": "local",
            },
        )
    )


def decide(
    host: CoalitionHost,
    who: HostedParticipant,
    kind: str = "charter",
    identifier: str | None = None,
) -> Document:
    identifier = identifier or host.coalition_id
    body: Document = {
        "subject": {"kind": kind, "id": identifier, "revision": 1},
        "choice": identifier,
        "consent": True,
        "decided_at": NOW,
    }
    body["consent_sig"] = sign_consent(
        host.coalition_id, body, who.owner_key, who.owner_kid, participant=who.participant
    )
    return accepted(send(host, who, "decide", body))


def need(host: CoalitionHost, **extra: object) -> Acknowledgement | Document:
    return host.host_emit(
        "need",
        {
            "description": "Another task",
            "requirements": [],
            "window": {"start": NOW, "end": END},
            **extra,
        },
        PUBLIC,
    )


def test_ext_and_transactional_template_seeding(pack: Pack) -> None:
    with_store = SQLiteStore()
    host = open_host(with_store, pack)
    a, b = person("a"), person("b")
    join(host, a)
    join(host, b)
    decide(host, a)
    assert not host.state.tasks
    event = decide(host, b)
    seeded = list(host.state.tasks.values())
    assert len(seeded) == 1
    assert seeded[0]["source"]["seq"] == event["seq"] + 1
    assert seeded[0]["description"] == "First task"
    assert seeded[0]["ext"] == {"item_kind": "item"}
    assert seeded[0]["requirements"] == ["ready"]
    assert seeded[0]["window"] == {"start": NOW, "end": END}
    accepted(host.accept(event, AuthenticatedSender(b.card_url, "b")))
    assert len(host.state.tasks) == 1
    accepted(need(host, ext={"item_kind": "valid"}))
    refused = need(host, ext={"item_kind": 1})
    assert isinstance(refused, dict) and refused["payload"]["code"] == "schema_invalid"
    for ext, valid in [({"item_kind": "valid"}, True), ({"item_kind": 1}, False)]:
        result = send(
            host,
            a,
            "offer",
            {
                "offer_id": new_ulid(),
                "target": {"kind": "need", "id": seeded[0]["need_id"]},
                "capacity": 1,
                "cost": {"minutes": 60, "money": 0, "effort": "low"},
                "valid_until": END,
                "ext": ext,
            },
        )
        assert isinstance(result, Acknowledgement) == valid
        if isinstance(result, dict):
            assert result["payload"]["code"] == "schema_invalid"
    plain = open_host(with_store, None)
    join(plain, person("a"))
    refused = need(plain, ext={})
    assert isinstance(refused, dict) and refused["payload"]["code"] == "schema_invalid"
    accepted(need(plain))
    with_store.close()


@pytest.mark.parametrize("weight,expected", [(0, {"a"}), (10, {"a", "b"})])
def test_runtime_planner_uses_bound_strategy(
    pack: Pack, weight: int, expected: set[str], tmp_path: Path
) -> None:
    pack = replace(
        pack,
        manifest=pack.manifest.model_copy(
            update={"strategy": Strategy(allocation="auction", fairness={"weight": weight})}
        ),
    )
    store = SQLiteStore()
    host = open_host(store, pack)
    a, b = person("a"), person("b")
    for who in (a, b):
        join(host, who)
        decide(host, who)
    accepted(need(host))
    for task_id in host.state.tasks:
        for who, money in ((a, 0), (b, 1)):
            accepted(
                send(
                    host,
                    who,
                    "offer",
                    {
                        "offer_id": new_ulid(),
                        "target": {"kind": "need", "id": task_id},
                        "capacity": 1,
                        "cost": {"minutes": 60, "money": money, "effort": "low"},
                        "valid_until": END,
                    },
                )
            )
    plans = plan_for(host, {(pack.name, pack.manifest.version): pack})
    assert set(plans.plans[0].assignments.values()) == expected
    server = Server(
        Settings.model_validate(
            {"store": "sqlite:///:memory:", "host_key_file": tmp_path / "host.key"}
        )
    )
    try:
        server.packs = {(pack.name, pack.manifest.version): pack}
        server.hosts[host.coalition_id] = host
        proposal = accepted(server.plan(host.coalition_id, END))
        assert {a["assignee"] for a in proposal["payload"]["plans"][0]["assignments"]} == expected
    finally:
        server.close()
        store.close()


@pytest.mark.parametrize("template", [True, False])
def test_lessons_are_redacted_durable_and_owner_scoped(pack: Pack, template: bool) -> None:
    text = (
        "# Retrospective\n{{goal}}|{{members}}|{{tasks}}|{{allocation}}|"
        "{{decisions}}|{{changes}}|{{policy_outcomes}}|{{duration}}"
    )
    pack = replace(pack, lessons={"lesson.md": text} if template else {})
    store = SQLiteStore()
    host = open_host(store, pack)
    a, b = person("a"), person("b")
    for who in (a, b):
        join(host, who)
        decide(host, who)
    host.steward = FakeSteward(Verdict("redact", "hide-description", ("payload.description",)))
    accepted(need(host, description="REDACTED_CANARY", ext={"item_kind": "VAULT_CANARY"}))
    host.steward = FakeSteward(Verdict("block", "blocked-item"))
    blocked = need(host, description="BLOCKED_CANARY")
    assert isinstance(blocked, dict) and blocked["payload"]["code"] == "steward_blocked"
    host.steward = FakeSteward()
    result = accepted(host.host_emit("dissolve", {"reason": "completed", "skills_written": []}))
    identifiers = result["payload"]["skills_written"]
    assert len(identifiers) == 1
    later = open_host(store, pack)
    join(later, person("a", a.owner_key))
    joining = next(e for e in later.state.events.values() if e["type"] == "coalition.join")
    reply = asyncio.run(HostPort(later).accept(joining, joining["sender"]))
    skills = reply["skills"]
    lesson = next(s for s in skills if s["name"] in identifiers)
    assert "First task" in lesson["text"] and "Finish together" in lesson["text"]
    assert "hide-description: redact" in lesson["text"]
    assert "blocked-item: block" in lesson["text"]
    assert "BLOCKED_CANARY" not in lesson["text"]
    assert "{{" not in lesson["text"]
    assert "VAULT_CANARY" not in lesson["text"] and "REDACTED_CANARY" not in lesson["text"]
    join(later, person("b"))
    assert not any(s["name"] in identifiers for s in later.skills("b"))
    assert not later.skills("outsider")
    restored = CoalitionHost(
        store, later.coalition_id, later.card_url, later.private_key, later.kid
    )
    bind_runtime(restored, {(pack.name, pack.manifest.version): pack})
    assert restored.skills("a") == skills
    store.close()


def test_no_pack_writes_generic_lesson() -> None:
    store = SQLiteStore()
    host = open_host(store, None)
    a = person("a")
    join(host, a)
    result = accepted(host.host_emit("dissolve", {"reason": "completed", "skills_written": []}))
    identifiers = result["payload"]["skills_written"]
    assert len(identifiers) == 1
    skill = next(s for s in host.skills("a") if s["name"] in identifiers)
    assert "goal: Finish together" in skill["text"]
    assert "tasks: 0" in skill["text"]
    again = accepted(host.host_emit("dissolve", {"reason": "completed", "skills_written": []}))
    assert again["payload"]["skills_written"] == identifiers
    store.close()


def test_failed_seed_rolls_back_decision_and_cache(pack: Pack) -> None:
    broken = replace(
        pack, task_templates=(pack.task_templates[0].model_copy(update={"ext": {"item_kind": 7}}),)
    )
    store = SQLiteStore()
    host = open_host(store, broken)
    a, b = person("a"), person("b")
    join(host, a)
    join(host, b)
    decide(host, a)
    with pytest.raises(AssertionError):
        decide(host, b)
    assert not host.state.accepted_charter("b")
    assert not host.state.tasks
    bind_runtime(host, {(pack.name, pack.manifest.version): pack})
    decide(host, b)
    assert len(host.state.tasks) == 1
    store.close()


def test_redacted_decisions_do_not_leak_through_lesson_allocation(pack: Pack) -> None:
    store = SQLiteStore()
    host = open_host(store, pack)
    a, b = person("a"), person("b")
    for who in (a, b):
        join(host, who)
        decide(host, who)
    task_id = next(iter(host.state.tasks))
    accepted(
        send(
            host,
            a,
            "offer",
            {
                "offer_id": new_ulid(),
                "target": {"kind": "need", "id": task_id},
                "capacity": 1,
                "cost": {"minutes": 1, "money": 0, "effort": "low"},
                "valid_until": END,
            },
        )
    )
    plans = plan_for(host, {(pack.name, pack.manifest.version): pack})
    payload = build_propose(plans, deadline=END, proposal_set_id=new_ulid()).to_wire()
    accepted(host.host_emit("propose", payload, PUBLIC))
    host.steward = FakeSteward(Verdict("redact", "hide-decision", ("payload.consent",)))
    for who in (a, b):
        decide(host, who, "plan", plans.plans[0].plan_id)
    assert host.state.tasks[task_id]["assignee"] == "a"
    host.steward = FakeSteward()
    result = accepted(host.host_emit("dissolve", {"reason": "completed", "skills_written": []}))
    lesson = next(s for s in host.skills("a") if s["name"] in result["payload"]["skills_written"])
    assert "allocation: \n" in lesson["text"]
    assert "→" not in lesson["text"]
    store.close()
