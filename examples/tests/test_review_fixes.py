# SPDX-License-Identifier: Apache-2.0
"""Regression tests for the five review findings; each fails without its fix."""

from __future__ import annotations

import json
import re
from typing import Any

import interop.coalition as coalition_module
import interop.run as run_module
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from interop.coalition import InteropCoalition
from interop.rig import KEY_VARIABLE, BuiltBrain, Mode, vault_for
from interop.run import run_once
from interop.scorecard import build_scorecard
from members.adk_member import AdkBrain, ScriptedAdkLlm
from members.kit.brain import BrainResult, ModelUse, UseSink, offers_instruction
from members.kit.core import DeliveryRefused, Invitation, MemberCore, _Tools
from members.kit.identity import MemberIdentity
from members.kit.policy import AutoOwner, Terms
from members.kit.redact import scrub

from coalitionkit_contracts import new_ulid, sign_envelope
from coalitionkit_edges.a2a import HostSigner

COALITION = new_ulid()
HOST_URL = "http://127.0.0.1:9/.well-known/agent-card.json"
FAKE_KEY = "sk-FAKEKEY1234567890abcdefghijkl"
NEED = new_ulid()


class Rig:
    def __init__(self, brain: Any = None, name: str = "p1") -> None:
        self.host_key = Ed25519PrivateKey.generate()
        self.signer = HostSigner(HOST_URL, self.host_key, "host-key-1")
        invitation = Invitation(COALITION, HOST_URL, self.host_key.public_key(), "host-key-1", "t")
        vault = vault_for(name)
        self.core = MemberCore(
            MemberIdentity(name, "http://127.0.0.1:9"),
            invitation,
            brain,
            vault,
            AutoOwner(terms=vault.terms),
        )
        self.sent: list[tuple[str, dict[str, Any]]] = []

        async def send(kind: str, body: dict[str, Any], scope: dict[str, Any]) -> str:
            self.sent.append((kind, body))
            return "accepted"

        self.core.send = send  # type: ignore[method-assign]

    def need_payload(self) -> dict[str, Any]:
        window = {"start": "2026-01-01T00:00:00Z", "end": "2026-01-02T00:00:00Z"}
        return {"need_id": NEED, "description": "t1: neutral task t1", "requirements": [],
                "window": window}  # fmt: skip


def forged(rig: Rig, kind: str, payload: dict[str, Any], sender: str, coalition: str = COALITION):
    envelope: dict[str, Any] = {
        "ext_version": "0.1",
        "coalition_id": coalition,
        "event_id": new_ulid(),
        "type": kind,
        "sender": sender,
        "on_behalf_of": "p2",
        "scope": {"audience": "self"},
        "payload": payload,
    }
    envelope["sig"] = sign_envelope(envelope, Ed25519PrivateKey.generate(), "evil-key")
    return envelope


# ---- 1. delivery authentication --------------------------------------------------------------


async def test_host_only_types_from_another_sender_are_refused() -> None:
    rig = Rig()
    receipt = {"coalition_id": COALITION, "seq": 1, "head_hash": "a" * 64}
    for kind, payload in (
        ("coalition.need", rig.need_payload()),
        ("coalition.receipt", receipt),
    ):
        with pytest.raises(DeliveryRefused) as refused:
            await rig.core.handle(forged(rig, kind, payload, "http://evil.example/card"))
        assert refused.value.code == "not_authorized"
    assert rig.core.needs == {}


async def test_host_events_need_the_host_signature_and_the_invited_coalition() -> None:
    rig = Rig()
    good = rig.signer.envelope(COALITION, "coalition.need", rig.need_payload())
    assert await rig.core.handle(good) == "need noted"
    wrong = rig.signer.envelope(new_ulid(), "coalition.need", rig.need_payload())
    with pytest.raises(DeliveryRefused) as refused:
        await rig.core.handle(wrong)
    assert refused.value.code == "wrong_coalition"
    bad_key = forged(rig, "coalition.need", rig.need_payload(), HOST_URL)
    bad_key["on_behalf_of"] = "host"
    bad_key["sig"] = sign_envelope(bad_key, Ed25519PrivateKey.generate(), "host-key-1")
    with pytest.raises(DeliveryRefused) as refused:
        await rig.core.handle(bad_key)
    assert refused.value.code == "bad_signature"


async def test_a_tampered_projection_is_refused() -> None:
    rig = Rig()
    source = {
        "event_id": new_ulid(),
        "seq": 3,
        "type": "coalition.need",
        "on_behalf_of": "host",
        "prev_hash": "b" * 64,
        "hash": "c" * 64,
    }
    projection = rig.signer.envelope(
        COALITION, "coalition.projection", {"source": source, "payload": rig.need_payload()}
    )
    projection["payload"]["payload"]["description"] = "t9: tampered"
    with pytest.raises(DeliveryRefused) as refused:
        await rig.core.handle(projection)
    assert refused.value.code == "bad_signature"


async def test_bearer_tokens_are_random_per_member() -> None:
    coalition = InteropCoalition(Mode(live=False))
    await coalition.run(120)
    tokens = coalition._tokens_out  # pyright: ignore[reportPrivateUsage]
    assert len(set(tokens.values())) == len(tokens) == 3
    for name, token in tokens.items():
        # Random, not derived: long, URL-safe, and never one of the old predictable forms.
        assert len(token) >= 32 and re.fullmatch(r"[A-Za-z0-9_-]+", token)
        assert token not in {f"from-host-{name}", f"to-host-{name}", name}


# ---- 2. the owner's policy bounds what the model may sign ------------------------------------


async def test_the_model_cannot_offer_terms_the_owner_did_not_set() -> None:
    rig = Rig()
    rig.core.needs[NEED] = "t1"
    rig.core.queried[NEED] = "yes"
    tools = _Tools(rig.core)
    cheat = await tools.make_offer(NEED, 1, 0, "low")
    assert cheat.startswith("refused") and rig.sent == []
    assert "minutes 30" in cheat
    assert (await tools.make_offer(NEED, 30, 5, "low")).startswith("accepted")
    assert [kind for kind, _ in rig.sent] == ["offer"]
    assert len(rig.core.policy_refusals) == 1


async def test_the_model_cannot_offer_a_task_the_vault_refused_or_act_on_foreign_tasks() -> None:
    rig = Rig()
    rig.core.needs[NEED] = "t2"  # p1's vault says no to t2
    rig.core.queried[NEED] = "no"
    tools = _Tools(rig.core)
    assert (await tools.make_offer(NEED, 45, 8, "medium")).startswith("refused")
    assert (await tools.commit_to_task(new_ulid())).startswith("refused")
    assert (await tools.report_done(new_ulid(), "result-x")).startswith("refused")
    assert rig.sent == []


# ---- 3. usage of failed turns is kept --------------------------------------------------------


class _FailsOnSecondCall(ScriptedAdkLlm):
    calls: int = 0

    async def generate_content_async(self, llm_request: Any, stream: bool = False):  # type: ignore[override]
        self.calls += 1
        if self.calls > 1:
            raise RuntimeError(f"401 invalid key {FAKE_KEY}")
        async for response in super().generate_content_async(llm_request, stream):
            yield response


async def test_a_failing_turn_still_counts_the_calls_it_made() -> None:
    rig = Rig(AdkBrain(_FailsOnSecondCall()))
    rig.core.needs.update({new_ulid(): "t1", new_ulid(): "t3"})
    rig.core.queried.update({k: "yes" for k in rig.core.needs})
    tasks = [
        {"need_id": k, "label": v, "minutes": 1, "money": 1, "effort": "low"}
        for k, v in rig.core.needs.items()
    ]
    await rig.core._turn("offers", offers_instruction("p1", tasks))  # pyright: ignore[reportPrivateUsage]
    assert len(rig.core.log.uses) == 1  # the first call returned before the second failed
    assert len(rig.core.log.turn_errors) == 1
    # 4. and the error text, which echoed a key, is not kept
    assert "RuntimeError" in rig.core.log.turn_errors[0]
    assert FAKE_KEY not in rig.core.log.turn_errors[0]


class _CountsThenFails:
    framework, model = "fake", "fake"

    async def run(self, instruction: str, tools: Any, on_use: UseSink) -> BrainResult:
        on_use(ModelUse(10, 5))
        on_use(ModelUse(20, 6))
        raise RuntimeError("boom")


async def test_usage_recorded_before_a_failure_is_not_lost() -> None:
    rig = Rig(_CountsThenFails())
    await rig.core._turn("offers", "x")  # pyright: ignore[reportPrivateUsage]
    assert [u.prompt_tokens for u in rig.core.log.uses] == [10, 20]
    assert rig.core.log.turns[-1].model_calls == 2


# ---- 4. no secrets in scorecards -------------------------------------------------------------


class _Exploding:
    framework, model = "fake", "fake"

    async def run(self, instruction: str, tools: Any, on_use: UseSink) -> BrainResult:
        raise RuntimeError(f"401 from provider, Authorization: Bearer {FAKE_KEY}, key={FAKE_KEY}")


async def test_a_key_planted_in_an_exception_never_reaches_the_scorecard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(KEY_VARIABLE, FAKE_KEY)
    real = coalition_module.build_brain

    def build(spec: Any, mode: Any, coalition_id: str) -> BuiltBrain:
        return BuiltBrain(_Exploding()) if spec.name == "p1" else real(spec, mode, coalition_id)

    monkeypatch.setattr(coalition_module, "build_brain", build)
    card = await run_once(Mode(live=False), time_limit_s=120)
    text = json.dumps(card)
    assert FAKE_KEY not in text and "FAKEKEY" not in text
    errors = card["members"]["p1"]["turn_errors"]
    assert errors and all("RuntimeError" in e for e in errors)
    assert card["passed"] is False  # p1 never offered, so the goal is not reached


def test_scrub_removes_planted_secrets_and_key_shapes() -> None:
    text = f"Bearer abc.def key={FAKE_KEY} also {'x' * 40} and exact-secret-value"
    cleaned = scrub(text, ["exact-secret-value"])
    for leaked in ("abc.def", FAKE_KEY, "x" * 40, "exact-secret-value"):
        assert leaked not in cleaned
    assert scrub(f"event {COALITION}") == f"event {COALITION}"  # identifiers survive


# ---- 5. passed means clean --------------------------------------------------------------------


async def test_passed_requires_no_leaks_and_no_delivery_failures() -> None:
    coalition = InteropCoalition(Mode(live=False))
    outcome = await coalition.run(120)
    assert build_scorecard(outcome, "scripted")["passed"] is True
    outcome.delivery_failures.append("p1: a delivery was refused")
    assert build_scorecard(outcome, "scripted")["passed"] is False
    outcome.delivery_failures.clear()
    member = outcome.members["p1"]
    member.core.log.prompts.append("leak " + member.core.vault.private_note)
    card = build_scorecard(outcome, "scripted")
    assert card["canary_leaks"] == 1 and card["passed"] is False


@pytest.mark.parametrize(("passed", "code"), [(True, 0), (False, 1)])
def test_main_exits_non_zero_when_a_run_did_not_pass(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], passed: bool, code: int
) -> None:
    async def fake_run(mode: Mode, number: int = 1, limit: float = 1.0) -> dict[str, Any]:
        return {"passed": passed}

    monkeypatch.setattr(run_module, "run_once", fake_run)
    assert run_module.main(["--scripted"]) == code
    capsys.readouterr()


def test_terms_dataclass_is_what_the_owner_enforces() -> None:
    assert vault_for("p1").terms["t1"] == Terms(30, 5, "low")
