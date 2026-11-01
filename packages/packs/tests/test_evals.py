# SPDX-License-Identifier: Apache-2.0
"""Pack evals exercise signed host traffic, including failure and no-key reporting."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest
from packs_support import copy_pack, core_catalog, rewrite

from coalitionkit_acceptance.pack_evals import ScenarioRun, run_scenario
from coalitionkit_cli.main import main as kit_main
from coalitionkit_models import ChatMessage, OpenAITransport, Route
from coalitionkit_models.gateway import RawCompletion, Usage
from coalitionkit_packs import PackError
from coalitionkit_packs.cli import main
from coalitionkit_packs.loader import inspect_pack
from coalitionkit_runtime import CoalitionHost


@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("observer_first", [False, True])
async def test_participant_role(tmp_path: Path, explicit: bool, observer_first: bool) -> None:
    folder = copy_pack("pack-beta", tmp_path)
    member = "  member: { may: [offer, decide, decide_own, commit] }"
    observer = "  observer: { may: [decide_own] }"
    rewrite(
        folder / "pack.yaml",
        member,
        "\n".join([observer, member] if observer_first else [member, observer]),
    )
    if explicit:
        rewrite(folder / "evals/solo.yaml", "id: p1", "id: p1\n    role: member")
    pack = inspect_pack(folder, core_catalog=core_catalog())
    result = await run_scenario(pack, pack.evals[0])
    assert result["status"] == "pass", result


@pytest.mark.parametrize("role", [None, "unknown"])
def test_eval_role_refusal_is_explained(tmp_path: Path, role: str | None) -> None:
    folder = copy_pack("pack-beta", tmp_path)
    if role:
        rewrite(folder / "evals/solo.yaml", "id: p1", f"id: p1\n    role: {role}")
    else:
        rewrite(folder / "pack.yaml", "[offer, decide, decide_own, commit]", "[decide_own]")
    with pytest.raises(PackError, match="not declared" if role else "both offer and decide"):
        inspect_pack(folder, core_catalog=core_catalog())


@pytest.mark.parametrize("name", ["pack-alpha", "pack-beta"])
async def test_pass(tmp_path: Path, name: str) -> None:
    pack = inspect_pack(copy_pack(name, tmp_path), core_catalog=core_catalog())
    result = await run_scenario(pack, pack.evals[0])
    assert result["status"] == "pass", result
    assert result["messages"] > 1


async def test_wrong_decision(tmp_path: Path) -> None:
    folder = copy_pack("pack-alpha", tmp_path)
    rewrite(
        folder / "evals/two-parties.yaml",
        'decision: { slot: "slot-b" }',
        'decision: { slot: "slot-a" }',
    )
    pack = inspect_pack(folder, core_catalog=core_catalog())
    result = await run_scenario(pack, pack.evals[0])
    assert result["status"] == "fail"
    assert any("!= expected" in reason for reason in result["reasons"])
    assert result["decision"] == {"slot": "slot-b"}


async def test_projection_canary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pack = inspect_pack(copy_pack("pack-alpha", tmp_path), core_catalog=core_catalog())
    original = CoalitionHost.view

    def leaking(self: CoalitionHost, viewer: str) -> dict[str, object]:
        return {**original(self, viewer), "injected": "C-ALPHA-1"}

    monkeypatch.setattr(CoalitionHost, "view", leaking)
    result = await run_scenario(pack, pack.evals[0])
    assert result["status"] == "fail"
    assert result["canaries_leaked"] == 1


async def test_message_limit(tmp_path: Path) -> None:
    folder = copy_pack("pack-alpha", tmp_path)
    rewrite(folder / "evals/two-parties.yaml", "max_messages: 40", "max_messages: 3")
    pack = inspect_pack(folder, core_catalog=core_catalog())
    result = await run_scenario(pack, pack.evals[0])
    assert result["status"] == "fail"
    assert any("max_messages" in reason for reason in result["reasons"])
    assert result["messages"] <= 3


def test_bound_host(tmp_path: Path) -> None:
    pack = inspect_pack(copy_pack("pack-alpha", tmp_path), core_catalog=core_catalog())
    run = ScenarioRun(pack, pack.evals[0])
    try:
        assert run.arena.host.state.charter["pack"] == {
            "name": pack.name,
            "version": pack.manifest.version,
        }
    finally:
        run.arena.close()


def test_no_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("COALITIONKIT_META_API_KEY", raising=False)
    folder = copy_pack("pack-beta", tmp_path)
    assert main(["eval", str(folder), "--live"]) == 0
    assert "not run (no key)" in capsys.readouterr().out
    assert main(["eval", str(folder), "--live", "--require-live", "--json"]) == 1
    row = json.loads(capsys.readouterr().out)["scenarios"][0]
    assert row["status"] == "not run"


def test_top_level(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = copy_pack("pack-beta", tmp_path)
    assert kit_main(["pack", "eval", str(folder), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["scenarios"][0]["status"] == "pass"


async def test_live_gateway(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise live routing and metering without making a billable call in CI."""
    monkeypatch.setenv("COALITIONKIT_META_API_KEY", "synthetic-test-key")
    calls: list[str] = []

    async def create(
        self: OpenAITransport,
        route: Route,
        messages: Sequence[ChatMessage],
        opts: Mapping[str, Any],
    ) -> RawCompletion:
        calls.append(route.role)
        assert "C-ALPHA" not in json.dumps(messages)
        return RawCompletion("slot-b", Usage(100, 20, 0))

    monkeypatch.setattr(OpenAITransport, "create", create)
    pack = inspect_pack(copy_pack("pack-alpha", tmp_path), core_catalog=core_catalog())
    result = await run_scenario(pack, pack.evals[0], live=True)
    assert result["status"] == "pass", result
    assert calls == ["hosted_agent", "hosted_agent"]
    assert result["usage"]["model_calls"] == 2
    assert result["usage"]["prompt_tokens"] == 200
    assert result["usage"]["completion_tokens"] == 40
    assert result["usage"]["cost_micro_usd"] > 0
    assert result["usage"]["latency_seconds"] >= 0


@pytest.mark.parametrize("channel", ["log", "steward", "agent"])
async def test_other_canary_channels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, channel: str
) -> None:
    pack = inspect_pack(copy_pack("pack-alpha", tmp_path), core_catalog=core_catalog())
    original = ScenarioRun.collect

    def collect(self: ScenarioRun) -> list[object]:
        if channel == "steward":
            self.steward.inputs.append({"injected": "C-ALPHA-2"})
        elif channel == "agent":
            self.channels.append("C-ALPHA-2")
        surfaces = original(self)
        if channel == "log":
            surfaces[0] = [{"original": "C-ALPHA-2"}]
        return surfaces

    monkeypatch.setattr(ScenarioRun, "collect", collect)
    result = await run_scenario(pack, pack.evals[0])
    assert result["status"] == "fail"
    assert result["canaries_leaked"] == 1


def test_eval_refuses_undeclared_role(tmp_path: Path) -> None:
    from coalitionkit_acceptance.arena import Participant, refusal_code

    pack = inspect_pack(copy_pack("pack-alpha", tmp_path), core_catalog=core_catalog())
    run = ScenarioRun(pack, pack.evals[0])
    try:
        person = Participant(run.arena.host, run.scenario.participants[0].id)
        run.arena.attach(person)
        body = person.join_body()
        assert refusal_code(person.send("join", body)) == "not_authorized"
    finally:
        run.arena.close()
