# SPDX-License-Identifier: Apache-2.0
"""The demo acts through the host and waits at each owner consent boundary."""

import json
import os
import time
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from coalitionkit_cli.demo import enroll
from coalitionkit_cli.demo_agents import demo_gateway, demo_runner
from coalitionkit_contracts import HOST_ONLY_TYPES
from coalitionkit_models import CostMeter, ModelGateway, load_price_table
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
            "latency_s": time.perf_counter() - started,
            "events": len(events),
            "prompt_tokens": sum(r.prompt_tokens for r in records),
            "completion_tokens": sum(r.completion_tokens for r in records),
            "cost_micro_usd": sum(r.cost_micro_usd for r in records),
        }
    finally:
        server.close()


async def test_demo_consent_and_ripple(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COALITIONKIT_META_API_KEY", raising=False)
    await exercise(tmp_path)


@pytest.mark.live
@pytest.mark.skipif(not os.environ.get("COALITIONKIT_META_API_KEY"), reason="no key")
async def test_demo_live(tmp_path: Path) -> None:
    print(await exercise(tmp_path, live=True))
