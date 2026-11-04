# SPDX-License-Identifier: Apache-2.0
"""The demo acts through the host and waits at each owner consent boundary."""

import json
import os
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import SecretStr

from coalitionkit_cli.demo import enroll
from coalitionkit_cli.demo_agents import demo_gateway, demo_runner, example_module
from coalitionkit_contracts import HOST_ONLY_TYPES
from coalitionkit_models import (
    CostMeter,
    FakeModel,
    ModelGateway,
    ScriptedResponse,
    load_price_table,
)
from coalitionkit_models.settings import Settings as ModelSettings
from coalitionkit_runtime.lifecycle import State
from coalitionkit_server import Settings, create_server
from coalitionkit_server.app import Server
from coalitionkit_surfaces.agent import open_requests


async def approve(server: Server, coalition: str, tokens: dict[str, str], kind: str) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=server.surfaces[coalition]), base_url="http://test"
    ) as client:
        for member, token in tokens.items():
            requests = [r for r in open_requests(server.hosts[coalition], member) if r.kind == kind]
            assert requests
            response = await client.post(
                "/v1/agent/answers",
                headers={"Authorization": f"Bearer {token}"},
                json={"interrupt_id": requests[0].interrupt_id, "consent": True},
            )
            assert response.status_code == 200, response.text


async def exercise(tmp_path: Path, live: bool = False) -> dict[str, Any]:
    gateway = (
        ModelGateway(ModelSettings(), meter=CostMeter(load_price_table()))
        if live
        else demo_gateway()
    )
    app = create_server(
        Settings(
            store=SecretStr(f"sqlite:///{tmp_path / 'demo.db'}"),
            host_key_file=tmp_path / "host.key",
        ),
        model_gateway=gateway,
    )
    server: Server = app.state.server
    started = time.perf_counter()
    try:
        coalition, tokens = await enroll(server, 3)
        demo = demo_runner(server, coalition, 0)
        assert not await demo.step()
        for forbidden in ("need", "query", "propose", "tension", "decide"):
            with pytest.raises(ValueError, match="not allowed"):
                await demo.send("p1", forbidden, {})
        assert not server.hosts[coalition].state.offers
        await approve(server, coalition, tokens, "charter")
        assert await demo.step()
        host = server.hosts[coalition]
        assert demo.overlap == ["slot-2"]
        assert demo.blocked is not None
        assert demo.blocked["error"]["code"] == "steward_blocked"
        assert demo.blocked["error"]["detail"]["policy_id"] == "no-regulated-advice"
        assert not await demo.step()
        assert not any(s["kind"] == "commitment" for s in host.state.subjects.values())
        for member in tokens:
            assert host.view(member)["events"]
            assert any(o["owner"] == member for o in host.state.offers.values())
        await approve(server, coalition, tokens, "plan")
        assert await demo.step()
        assert not await demo.step()
        assert all(host.state.tasks[t]["status"] == "decided" for t in demo.tasks)
        # One explicit human answer; the demo never has a signer or calls the answer endpoint.
        task = demo.tasks[0]
        member = str(host.state.tasks[task]["assignee"])
        await approve(server, coalition, {member: tokens[member]}, "commitment")
        before = {t: dict(v) for t, v in host.state.tasks.items()}
        head = len(server.store.read(coalition))
        assert await demo.step()
        after = host.state
        assert demo.changed
        for other in set(demo.tasks) - {task}:
            assert after.tasks[other] == before[other]
        new = server.store.read(coalition)[head:]
        ripple = next(e for e in new if e["type"] == "coalition.ripple")
        assert ripple["payload"]["invalidates"] == [task]
        assert {
            a["task_id"]
            for e in new
            if e["type"] == "coalition.propose"
            for p in e["payload"]["plans"]
            for a in p["assignments"]
        } == {task}
        events = server.store.read(coalition)
        folded = State(coalition)
        for event in events:
            folded.apply(event)
            if event["event_id"] == ripple["event_id"]:
                assert folded.tasks[task]["status"] == "negotiating"
                for other in set(demo.tasks) - {task}:
                    assert folded.tasks[other]["status"] == before[other]["status"]
                break
        matches = [e for e in events if e["type"] == "coalition.match"]
        assert [e["payload"]["round"] for e in matches] == ["setup", "request", "response"]
        assert len({e["on_behalf_of"] for e in matches}) == 2
        assert "slot-2" not in json.dumps(matches)
        tension = next(e for e in events if e["type"] == "coalition.tension")
        assert 2 <= len(tension["payload"]["options"]) <= 3
        kinds = [e["type"].removeprefix("coalition.") for e in events]
        cursor = 0
        for kind in [
            "join",
            "decide",
            "need",
            "offer",
            "query",
            "answer",
            "match",
            "propose",
            "tension",
            "observe",
            "decide",
            "commit",
            "decide",
            "ripple",
            "propose",
        ]:
            cursor = kinds.index(kind, cursor) + 1
        for event in events:
            if event["on_behalf_of"] in tokens:
                assert event["type"] not in HOST_ONLY_TYPES
            if event["type"] == "coalition.decide":
                assert event["payload"]["consent_sig"]
        assert gateway.meter is not None
        records = [r for r in gateway.meter.records if r.coalition_id == coalition]
        return {
            "steps": demo.steps,
            "model_calls": len(records),
            "latency_s": time.perf_counter() - started,
            "events": len(events),
            "prompt_tokens": sum(r.prompt_tokens for r in records),
            "completion_tokens": sum(r.completion_tokens for r in records),
            "cost_micro_usd": sum(r.cost_micro_usd for r in records),
        }
    finally:
        server.close()
        if live:
            assert gateway.meter is not None
            records = gateway.meter.records
            print(
                {
                    "model_calls": len(records),
                    "latency_s": time.perf_counter() - started,
                    "prompt_tokens": sum(r.prompt_tokens for r in records),
                    "completion_tokens": sum(r.completion_tokens for r in records),
                    "cost_micro_usd": sum(r.cost_micro_usd for r in records),
                }
            )


async def test_demo_consent_and_ripple(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COALITIONKIT_META_API_KEY", raising=False)
    await exercise(tmp_path)


@pytest.mark.parametrize("finish", [True, False])
async def test_member_retries_only_missing_offers(finish: bool) -> None:
    module = example_module("members.demo_runner")
    brain_module = example_module("members.hosted_member.brain")
    host = SimpleNamespace(state=SimpleNamespace(members=["p1"]))
    demo = module.Demo(SimpleNamespace(hosts={"c": host}), "c", 0)
    demo.send = AsyncMock(return_value={})
    terms = [
        {"need_id": need, "minutes": 60, "money": 0, "effort": "low"}
        for need in ("need-a", "need-b")
    ]

    def offer(index: int) -> ScriptedResponse:
        return ScriptedResponse(
            json.dumps({"calls": [{"tool": "make_offer", "args": terms[index]}]})
        )

    done = ScriptedResponse('{"calls": []}')
    fake = FakeModel(
        [offer(0), done, offer(1), done] if finish else [offer(0), done, done, done, done]
    )
    gateway = ModelGateway(ModelSettings(), transport=fake)
    instructions: list[dict[str, Any]] = []

    async def drive(member: str, instruction: str, tools: Any) -> None:
        instructions.append(json.loads(instruction.split("FACTS: ")[1]))
        brain = brain_module.HostedBrain(gateway, "c", member)
        await brain.run(instruction, tools, module.ignore_usage)

    demo.drive = drive
    try:
        if finish:
            await demo.offers("p1", terms)
        else:
            with pytest.raises(ValueError, match="missing needs: \\['need-b'\\]"):
                await demo.offers("p1", terms)
        assert instructions[0]["tasks"] == terms
        assert len(instructions) == (2 if finish else 4)
        assert all(i["tasks"] == [terms[1]] for i in instructions[1:])
        assert demo.send.await_count == (2 if finish else 1)
        assert all(call.args[1] == "offer" for call in demo.send.await_args_list)
    finally:
        await gateway.aclose()


@pytest.mark.parametrize("asks", [2, 5])
async def test_member_re_asked_for_its_commitment_request(asks: int) -> None:
    module = example_module("members.demo_runner")
    tasks = {"t1": {"status": "decided", "assignee": "p1"}}
    host = SimpleNamespace(state=SimpleNamespace(members=["p1"], tasks=tasks))
    demo = module.Demo(SimpleNamespace(hosts={"c": host}), "c", 0)
    demo.tasks, demo.phase = ["t1"], "plan"
    turns: list[str] = []

    async def drive(member: str, instruction: str, tools: Any) -> None:
        turns.append(member)
        if len(turns) == asks:  # the model makes the request only on this turn
            demo.requests.add("t1")

    demo.drive = drive
    if asks <= 4:
        assert await demo.step()
        assert demo.phase == "approval"
    else:
        with pytest.raises(ValueError, match="did not request commitment for t1"):
            await demo.step()
    assert len(turns) == min(asks, 4)


@pytest.mark.live
@pytest.mark.skipif(
    not (
        os.environ.get("COALITIONKIT_META_API_KEY")
        and os.environ.get("COALITIONKIT_BASETEN_API_KEY")
    ),
    reason="needs the Meta key and the Steward's Baseten key",
)
async def test_demo_live(tmp_path: Path) -> None:
    await exercise(tmp_path, live=True)


async def test_demo_continues_when_optional_psi_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def unavailable(name: str) -> Any:
        raise ModuleNotFoundError(name=name)

    monkeypatch.setattr("coalitionkit_vault._group.import_module", unavailable)
    app = create_server(
        Settings(
            store=SecretStr(f"sqlite:///{tmp_path / 'demo.db'}"),
            host_key_file=tmp_path / "host.key",
        ),
        model_gateway=demo_gateway(),
    )
    server: Server = app.state.server
    try:
        coalition, tokens = await enroll(server, 3)
        demo = demo_runner(server, coalition, 0)
        await approve(server, coalition, tokens, "charter")
        assert await demo.step()
        assert demo.phase == "plan"
        assert demo.overlap is None
        assert "PSI not run" in capsys.readouterr().out
        assert not any(e["type"] == "coalition.match" for e in server.store.read(coalition))
    finally:
        server.close()
