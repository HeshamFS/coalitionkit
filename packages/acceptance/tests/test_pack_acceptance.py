# SPDX-License-Identifier: Apache-2.0
"""Acceptance assertions are tested against real host journeys and deliberate mismatches."""

import json
from pathlib import Path
from typing import Any

import pytest

from coalitionkit_acceptance.pack_acceptance import Journey, load_scenario, run_acceptance
from coalitionkit_packs import inspect_pack
from coalitionkit_packs.sections import AcceptanceScenario

FIXTURE = Path(__file__).parents[2] / "packs/tests/fixtures/pack-delta"


def scenario() -> tuple[Any, dict[str, Any]]:
    pack = inspect_pack(FIXTURE)
    return pack, load_scenario(pack).model_dump()


@pytest.mark.parametrize("case", ["absent", "business", "mint"])
async def test_whole_journey(case: str) -> None:
    pack, data = scenario()
    if case == "business":
        data["expect"]["distinguishing"] = {"business_holds": {"business": 0, "need": 0}}
    elif case == "mint":
        data["expect"]["distinguishing"] = {
            "minted_reading": {"template": "template.json", "value": 2, "changes_needs": [0]}
        }
    result = await run_acceptance(pack, AcceptanceScenario.model_validate(data))
    assert result["status"] == "pass", json.dumps(result, indent=2)
    assert any(
        s["step"] == "agent_only_yes_refused" and s["status"] == "pass" for s in result["steps"]
    )


@pytest.mark.parametrize(
    "bad,step",
    [
        ("allocation", "allocation"),
        ("probe", "policy_probe"),
        ("untouched", "change.untouched"),
        ("canary", "canaries_leaked"),
    ],
)
async def test_named_failure(bad: str, step: str, monkeypatch: pytest.MonkeyPatch) -> None:
    pack, data = scenario()
    if bad == "allocation":
        data["expect"]["allocation"][0] = "p1"
    elif bad == "probe":
        data["expect"]["policy_probe"]["outcome"] = "allow"
    elif bad == "untouched":
        original = Journey.plan

        def moved(self: Journey) -> dict[str, Any]:
            result = original(self)
            if self.stage == "change":
                # Persist a real extra ripple on the supposedly untouched task.
                from coalitionkit_runtime import Acknowledgement, AuthenticatedSender

                member = self.members["p3"]
                reply = self.host.accept(
                    member.envelope(
                        "ripple", {"change": "task changed", "invalidates": [self.needs[1]]}
                    ),
                    AuthenticatedSender(member.person.card_url, member.name),
                )
                assert isinstance(reply, Acknowledgement)
            return result

        monkeypatch.setattr(Journey, "plan", moved)
    else:
        original_collect = Journey.collect

        def leaked(self: Journey) -> list[Any]:
            return [
                *original_collect(self),
                {"connector": self.scenario.members[0].vault["canary"]},
            ]

        monkeypatch.setattr(Journey, "collect", leaked)
    result = await run_acceptance(pack, AcceptanceScenario.model_validate(data))
    assert result["status"] == "fail", result
    assert any(s["step"] == step and s["status"] == "fail" for s in result["steps"]), result


async def test_live_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COALITIONKIT_META_API_KEY", raising=False)
    pack, _ = scenario()
    assert (await run_acceptance(pack, live=True))["status"] == "not run"
