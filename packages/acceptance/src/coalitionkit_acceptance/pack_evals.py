# SPDX-License-Identifier: Apache-2.0
"""Pack scenarios on the existing Arena, with private hosted vaults and signed decisions.

The pre-registry binding seam is a charter reference plus the host's policy callback.
The scripted member protocol publishes availability, proposes options, then signs consent.
Expected decisions are never inputs to that protocol. A live member chooses from the same
public candidates through the hosted_agent gateway; raw vault notes never enter prompts.
"""

from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from coalitionkit_contracts import Envelope
from coalitionkit_contracts.payloads import QueryPayload
from coalitionkit_models import ChatMessage, CostMeter, ModelGateway
from coalitionkit_packs.loader import Pack, inspect_pack
from coalitionkit_packs.sections import EvalOutcome, EvalScenario
from coalitionkit_runtime import Acknowledgement, SQLiteStore
from coalitionkit_runtime.steward import ReviewContext, Verdict
from coalitionkit_steward import StewardContext, Subject
from coalitionkit_steward.conditions import evaluate_all, walk
from coalitionkit_surfaces import load_catalog
from coalitionkit_vault.store import Capacity, Facts, Vault

from .arena import DEADLINE, PUBLIC, Arena, Document, Reply, accepted
from .privacy_live import CONTRIBUTOR_PRICES, LiveTransport, live_settings


class MessageLimit(Exception):
    """The next scripted submission would exceed the scenario budget."""


class RecordingSteward:
    def __init__(self) -> None:
        self.inputs: list[Document] = []

    def review(self, envelope: Document, *, context: ReviewContext) -> Verdict:
        self.inputs.append(deepcopy(envelope))
        return Verdict()


@dataclass(frozen=True)
class BoundPolicy:
    action: Literal["allow", "redact", "block", "escalate"]
    policy_id: str
    paths: tuple[str, ...]


class ScenarioRun:
    """A bounded script; all externally visible channels are retained for canary checks."""

    def __init__(self, pack: Pack, scenario: EvalScenario) -> None:
        self.pack, self.scenario = pack, scenario
        self.limit = scenario.expect.max_messages or 100
        self.channels: list[object] = []
        self.messages = 1  # charter
        names = [p.id for p in scenario.participants]
        self.arena = Arena.open(
            SQLiteStore(),
            names,
            charter={
                "goal": scenario.charter,
                "roles": [{"id": "member"}],
                "rules": [],
                "deadline": DEADLINE,
                "deciders": names,
                "pack": {"name": pack.name, "version": pack.manifest.version},
            },
        )
        self.steward = RecordingSteward()
        self.arena.host.steward = self.steward
        self.arena.host.policy = self.policy
        self.arena.on_exchange = self.record_exchange
        self.vaults: dict[str, Vault] = {}
        self.decision: Document | None = None

    def record_exchange(self, envelope: Document, reply: Reply) -> None:
        self.channels.append(deepcopy(envelope))
        if isinstance(reply, Acknowledgement):
            self.channels.extend((deepcopy(reply.accepted), deepcopy(reply.receipt)))
        else:
            self.channels.append(deepcopy(reply))

    def policy(self, event: Document) -> BoundPolicy | None:
        matches = evaluate_all(
            self.pack.policies,
            Subject.from_envelope(Envelope.model_validate(event)),
            StewardContext(members=frozenset(self.arena.members)),
        )
        if not matches:
            return None
        match = max(matches, key=lambda m: m.policy.severity)
        action = match.policy.then
        if action == "quarantine":
            raise ValueError("pack policies cannot quarantine")
        return BoundPolicy(action, match.policy.id, match.redact)

    def reserve(self, count: int = 1) -> None:
        if self.messages + count > self.limit:
            raise MessageLimit(f"max_messages {self.limit} exhausted before decision")
        self.messages += count

    def collect(self) -> list[object]:
        surfaces: list[object] = [self.arena.events(), self.steward.inputs, self.channels]
        for name in self.arena.members:
            surfaces.extend((self.arena.host.view(name), self.arena.host.replay(name)))
        return surfaces

    async def script(self, gateway: ModelGateway | None) -> None:
        for entry in self.scenario.participants:
            self.reserve(2)
            self.arena.enroll(entry.id, vault="hosted")
            vault = Vault(entry.id)
            vault.add_private_note(json.dumps(entry.vault))
            slots: list[str] = entry.vault.get("free", [])
            for slot in slots:
                vault.put(slot, Facts(capacities=(Capacity(1, "slot"),)))
            self.vaults[entry.id] = vault
            available: list[str] = []
            for index, slot in enumerate(slots):
                query = QueryPayload(query_id=f"q-{index}", kind="feasible", subject=slot)
                answer = vault.answer(query)
                self.channels.extend((query.to_wire(), answer.to_wire()))
                if answer.result == "yes":
                    available.append(slot)
            # Only this explicit public availability statement leaves the vault boundary.
            self.reserve()
            envelope = self.arena.members[entry.id].observe_envelope(
                json.dumps({"free": available})
            )
            accepted(self.arena.members[entry.id].submit(envelope))

        offered: list[set[str]] = []
        for event in self.arena.events():
            if event["type"] == "coalition.observe":
                body = json.loads(event["payload"]["content"])
                offered.append(set(body["free"]))
        common = sorted(set[str].intersection(*offered)) if offered else []
        has_slots = any("free" in p.vault for p in self.scenario.participants)
        if not common and has_slots:
            raise ValueError("no shared slot; no decision reached")
        candidates = common if has_slots else ["proceed"]
        outcomes = {
            f"option-{i}": {"slot": slot} if has_slots else {} for i, slot in enumerate(candidates)
        }
        self.reserve()
        task = self.arena.need()
        self.reserve()
        proposal = accepted(
            self.arena.host.host_emit(
                "tension",
                {
                    "task_ids": [task],
                    "options": [
                        {"option_id": option, "summary": json.dumps(outcome)}
                        for option, outcome in outcomes.items()
                    ]
                    + [{"option_id": "defer", "summary": "Defer the decision"}],
                    "tradeoffs": [],
                    "deciders": list(self.arena.members),
                    "decision_deadline": DEADLINE,
                },
                PUBLIC,
            )
        )
        subject_id = proposal.accepted["payload"]["tension_id"]
        for name, person in self.arena.members.items():
            self.reserve()
            choice = candidates[0]
            if gateway is not None:
                prompt: list[ChatMessage] = [
                    {
                        "role": "system",
                        "content": "Choose the first available shared slot. "
                        "Return only its exact name. You are the hosted member agent.",
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "view": self.arena.host.view(name),
                                "candidates": candidates,
                            }
                        ),
                    },
                ]
                self.channels.append(prompt)
                result = await gateway.complete(
                    "hosted_agent",
                    prompt,
                    coalition_id=self.arena.host.coalition_id,
                    participant=name,
                )
                choice = result.text.strip()
                self.channels.append(result.text)
                if choice not in candidates:
                    raise ValueError("member returned an unavailable slot")
            option = f"option-{candidates.index(choice)}"
            envelope = person.decision_envelope("tension_option", subject_id, choice=option)
            accepted(person.submit(envelope))
        if self.arena.host.state.subject("tension_option", subject_id).get("status") != "decided":
            raise ValueError("members disagreed; no decision reached")
        recorded = [
            e
            for e in self.arena.events()
            if e["type"] == "coalition.decide" and e["payload"]["subject"]["id"] == subject_id
        ]
        self.decision = outcomes[recorded[-1]["payload"]["choice"]]


async def run_scenario(pack: Pack, scenario: EvalScenario, *, live: bool = False) -> Document:
    run = ScenarioRun(pack, scenario)
    transport = LiveTransport(live_settings()) if live else None
    meter = CostMeter(CONTRIBUTOR_PRICES)
    gateway = ModelGateway(live_settings(), transport=transport, meter=meter) if live else None
    problems: list[str] = []
    try:
        try:
            await run.script(gateway)
        except Exception as exc:
            # Do not print provider errors or host refusals containing private payloads.
            problems.append(
                str(exc)
                if isinstance(exc, MessageLimit)
                else f"scenario execution failed ({type(exc).__name__})"
            )
        surfaces = run.collect()
        if transport is not None:
            surfaces.append(transport.calls)
        text = json.dumps(surfaces, default=str, ensure_ascii=False)
        text += "\n" + "\n".join(str(leaf) for _, leaf in walk(surfaces))
        leaked = frozenset(c for c in scenario.canaries() if c in text)
        outcome = EvalOutcome(run.decision, run.messages, leaked)
        problems.extend(scenario.check(outcome))
        row: Document = {
            "scenario": scenario.scenario,
            "status": "fail" if problems else "pass",
            "reasons": problems,
            "decision": run.decision,
            "messages": run.messages,
            "canaries_leaked": len(leaked),
        }
        if transport is not None:
            row["usage"] = {
                "model_calls": len(transport.calls),
                "prompt_tokens": sum(r.prompt_tokens for r in meter.records),
                "completion_tokens": sum(r.completion_tokens for r in meter.records),
                "cached_tokens": sum(r.cached_tokens for r in meter.records),
                "latency_seconds": sum(transport.latencies),
                "cost_micro_usd": sum(r.cost_micro_usd for r in meter.records),
            }
        return row
    finally:
        run.arena.close()
        if gateway is not None:
            await gateway.aclose()


def command(directory: Path, *, live: bool, require_live: bool, as_json: bool) -> int:
    """Optional CLI entry point, loaded lazily by the pack command."""
    catalog_path = Path(__file__).resolve().parents[4] / "spec/catalog/coalitionkit-v0_9.json"
    pack = inspect_pack(directory, core_catalog=load_catalog(catalog_path))
    key = live_settings().meta_api_key if live else None
    no_key = live and (key is None or not key.get_secret_value().strip())
    if no_key:
        rows: list[Document] = [
            {"scenario": s.scenario, "status": "not run", "reasons": ["no key"]} for s in pack.evals
        ]
    else:
        rows = [asyncio.run(run_scenario(pack, s, live=live)) for s in pack.evals]
    if as_json:
        print(json.dumps({"pack": pack.name, "live": live, "scenarios": rows}))
    else:
        for row in rows:
            reason = "; ".join(row["reasons"])
            print(f"{row['scenario']}: {row['status']}" + (f" ({reason})" if reason else ""))
    return int(any(r["status"] == "fail" for r in rows) or (no_key and require_live))
