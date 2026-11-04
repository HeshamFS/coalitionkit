# SPDX-License-Identifier: Apache-2.0
"""Whole-journey pack acceptance against the bound in-process server."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI
from pydantic import SecretStr

from coalitionkit_contracts import (
    Envelope,
    new_ulid,
    public_key_to_jwk,
    sign_consent,
    verify_consent,
)
from coalitionkit_contracts.owner import jwk_to_public_key
from coalitionkit_contracts.payloads import QueryPayload
from coalitionkit_contracts.resources import spec_path
from coalitionkit_gardener import build_propose
from coalitionkit_models import ChatMessage, CostMeter, FakeModel, ModelGateway
from coalitionkit_models.settings import Settings as ModelSettings
from coalitionkit_packs import Pack, inspect_pack, sign_pack
from coalitionkit_packs.errors import Report
from coalitionkit_packs.files import take_snapshot
from coalitionkit_packs.sections import AcceptanceScenario
from coalitionkit_runtime.host import utc_now
from coalitionkit_server import Settings
from coalitionkit_server.app import Server
from coalitionkit_server.genesis import enroll_member, mount_genesis
from coalitionkit_server.packs import plan_for
from coalitionkit_steward import StewardContext, Subject
from coalitionkit_steward.conditions import evaluate_all, walk
from coalitionkit_surfaces import load_catalog
from coalitionkit_surfaces.agent import open_requests
from coalitionkit_vault.store import Capacity, Facts, Vault

from .harness import FAR, Member, emit
from .pack_evals import BoundPolicy, MessageLimit, RecordingSteward
from .privacy_live import CONTRIBUTOR_PRICES, LiveTransport, live_settings

Document = dict[str, Any]


def load_scenario(pack: Pack) -> AcceptanceScenario:
    path = pack.manifest.acceptance
    if path is None:
        raise ValueError("pack does not declare acceptance")
    report = Report()
    data = take_snapshot(pack.root).yaml(path, "acceptance", report)
    report.raise_if_any()
    scenario = AcceptanceScenario.model_validate(data)
    if any(p.role not in pack.manifest.roles for p in [*scenario.members, *scenario.businesses]):
        raise ValueError("acceptance role is not a pack role")
    return scenario


class Journey:
    def __init__(self, pack: Pack, scenario: AcceptanceScenario, directory: Path) -> None:
        self.directory = directory
        copied = directory / "pack"
        for relative, data in take_snapshot(pack.root).files.items():
            target = copied / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        author = Ed25519PrivateKey.generate()
        sign_pack(copied, author, "acceptance-author")
        catalog = spec_path("catalog", "coalitionkit-v0_9.json")
        pack = inspect_pack(copied, core_catalog=load_catalog(catalog))
        self.pack, self.scenario = pack, scenario
        self.server = Server(
            Settings(
                store=SecretStr("sqlite:///:memory:"),
                host_key_file=directory / "host.key",
                genesis="local",
                public_base_url="http://127.0.0.1:8000",
                packs=[],
                pack_trusted_keys={},
                catalog_file=catalog,
            ),
            model_gateway=ModelGateway(ModelSettings(), transport=FakeModel([])),
        )
        self.server.packs[(pack.name, pack.manifest.version)] = pack
        self.server.settings.pack_trusted_keys["acceptance-author"] = public_key_to_jwk(
            author.public_key(), "acceptance-author"
        )
        self.steward = RecordingSteward()
        self.server.steward = self.steward  # pyright: ignore[reportAttributeAccessIssue]
        self.app = FastAPI()
        mount_genesis(self.app, self.server)
        self.cid = ""
        self.owner_token = ""
        self.members: dict[str, Member] = {}
        self.vaults: dict[str, Vault] = {}
        self.businesses: list[Member] = []
        self.channels: list[Any] = []
        self.steps: list[Document] = []
        self.stage = "genesis"
        self.needs: list[str] = []
        self.refused = 0

    @property
    def host(self):
        return self.server.hosts[self.cid]

    def check(self, name: str, condition: bool, reason: str) -> None:
        self.steps.append(
            {"step": name, "status": "pass" if condition else "fail", "reason": reason}
        )

    def collect(self) -> list[Any]:
        surfaces: list[Any] = [self.channels, self.steward.inputs]
        if self.cid:
            surfaces.append(self.server.store.read(self.cid))
            hub = self.server.surfaces[self.cid].state.hub
            for name in self.host.state.members:
                surfaces.extend(
                    (self.host.view(name), self.host.replay(name), hub.agent_session(name).start())
                )
        return surfaces

    def record_views(self) -> None:
        hub = self.server.surfaces[self.cid].state.hub
        for name in self.host.state.members:
            self.channels.extend(
                (self.host.view(name), self.host.replay(name), hub.agent_session(name).start())
            )

    async def send(
        self,
        name: str,
        kind: str,
        body: Document,
        *,
        allow_refusal: bool = False,
        scope: Document | None = None,
    ) -> Document:
        if (
            len(self.server.store.read(self.cid)) + self.refused
            >= self.scenario.expect.max_messages
        ):
            raise MessageLimit("submission budget exhausted")
        envelope = self.members[name].envelope(kind, body, scope)
        self.channels.append(deepcopy(envelope))
        reply = await self.server.accept(envelope, self.members[name].person.card_url)
        self.channels.append(deepcopy(reply))
        self.refused += int("error" in reply)
        self.record_views()
        if not allow_refusal and "error" in reply:
            raise AssertionError(f"{kind} refused: {reply['error']['code']}")
        return reply

    def consent(self, kind: str, identifier: str, names: list[str] | None = None) -> None:
        hub = self.server.surfaces[self.cid].state.hub
        for name in names or list(self.members):
            for request in open_requests(self.host, name):
                if request.kind == kind and request.subject_id == identifier:
                    session = hub.agent_session(name)
                    self.channels.extend(session.start())
                    self.channels.append(session.answer(request.interrupt_id, True))
                    self.record_views()

    async def genesis(self, http: httpx.AsyncClient) -> None:
        scenario = self.scenario
        response = await http.post(
            "/v1/genesis/draft",
            json={
                "goal": scenario.goal,
                "utc_offset_minutes": scenario.utc_offset_minutes,
                "pack": {"name": self.pack.name, "version": self.pack.manifest.version},
            },
        )
        response.raise_for_status()
        draft = response.json()["draft"]
        roles = list(dict.fromkeys(m.role for m in scenario.members))
        draft["roles"] = [
            {"id": r, "label": r, "count": sum(m.role == r for m in scenario.members)}
            for r in roles
        ]
        response = await http.post(
            "/v1/genesis/start",
            json={"draft": draft},
            headers={"Authorization": "Start " + self.server.registry.issue_start()},
        )
        response.raise_for_status()
        started = response.json()
        self.cid, self.owner_token = started["coalition_id"], started["owner"]["token"]
        # This journey plays the Gardener itself (needs, plans, the ripple's re-plan), so the
        # host's own Genesis driver must not race it.
        await self.server.gardener.release(self.cid)
        self.host.policy = self.policy
        for index, entry in enumerate(scenario.members, 1):
            name = f"p{index}"
            if index == 1:
                token = self.owner_token
            else:
                invitation = self.server.registry.issue_invitation(self.cid, "member")
                redeemed = self.server.registry.redeem(
                    invitation["link"].split("#", 1)[1], self.server.ports, None, None
                )
                await enroll_member(self.server, redeemed, entry.role)
                token = redeemed["token"]
                assert redeemed["participant"] == name
            person = self.server.registry.hosted_for(self.cid, name)
            self.members[name] = Member(name, token, person, self.cid)
            vault = Vault(name)
            vault.add_private_note(json.dumps(entry.vault))
            for slot in entry.vault.get("free", []):
                vault.put(str(slot), Facts(capacities=(Capacity(1, "slot"),)))
            self.vaults[name] = vault
        self.consent("charter", self.cid)
        self.needs = list(self.host.state.tasks)
        if not self.needs:
            for description in draft["needs"]:
                event = emit(
                    self.host,
                    "need",
                    {
                        "description": description,
                        "requirements": [],
                        "window": {"start": utc_now(), "end": draft["deadline"] or FAR},
                    },
                )
                self.needs.append(event["payload"]["need_id"])
        self.check(
            "genesis",
            self.host.state.charter.get("pack") == draft["pack"] and bool(self.needs),
            "pack bound, members joined and charter approved; needs drafted",
        )

    def policy(self, event: Document) -> BoundPolicy | None:
        matches = evaluate_all(
            self.pack.policies,
            Subject.from_envelope(Envelope.model_validate(event)),
            StewardContext(members=frozenset(self.members)),
        )
        if not matches:
            return None
        match = max(matches, key=lambda m: m.policy.severity)
        action = match.policy.then
        assert action != "quarantine"
        return BoundPolicy(action, match.policy.id, match.redact)

    async def offers(self, gateway: ModelGateway | None) -> None:
        for entry in self.scenario.offers:
            body = deepcopy(entry.offer)
            body.update(offer_id=new_ulid(), target={"kind": "need", "id": self.needs[entry.need]})
            if gateway:
                prompt: list[ChatMessage] = [
                    {
                        "role": "system",
                        "content": "You are the hosted member agent. "
                        "Return this offer as JSON unchanged.",
                    },
                    {"role": "user", "content": json.dumps(body)},
                ]
                self.channels.append(prompt)
                result = await gateway.complete(
                    "hosted_agent", prompt, coalition_id=self.cid, participant=entry.member
                )
                self.channels.append(result.text)
                body = json.loads(result.text)
            await self.send(entry.member, "offer", body)
        self.check(
            "offers",
            bool(self.host.state.offers),
            "member offers accepted through core and pack validation",
        )

    def plan(self) -> Document:
        plans = plan_for(self.host, self.server.packs)
        assert plans.plans, "Gardener produced no complete plan"
        candidate = plans.plans[0]
        emit(
            self.host,
            "propose",
            build_propose(plans, deadline=FAR, proposal_set_id=new_ulid()).to_wire(),
        )
        self.consent("plan", candidate.plan_id)
        self.check(
            "plan",
            self.host.state.subject("plan", candidate.plan_id)["status"] == "decided",
            "Gardener plan approved by owners",
        )
        return dict(zip(plans.objective_names, map(float, candidate.objectives), strict=True))

    async def commitments(self) -> None:
        refused = True
        for task in self.needs:
            name = self.host.state.tasks[task]["assignee"]
            identifier = new_ulid()
            await self.send(
                name, "commit", {"commitment_id": identifier, "task_id": task, "status": "pending"}
            )
            member = self.members[name]
            forged = member.decision_envelope("commitment", identifier, 1)["payload"]
            forged["consent_sig"] = sign_consent(
                self.cid, forged, member.person.agent_key, member.person.agent_kid, participant=name
            )
            reply = await self.send(name, "decide", forged, allow_refusal=True)
            refused = refused and reply.get("error", {}).get("code") == "bad_signature"
            self.check(
                "commitment_waits",
                self.host.state.subject("commitment", identifier)["status"] == "pending",
                "agent signature cannot approve commitment",
            )
            self.consent("commitment", identifier, [name])
        self.check(
            "agent_only_yes_refused",
            refused,
            "agent-only yes refused by owner consent verification",
        )
        decisions = [
            e
            for e in self.server.store.read(self.cid)
            if e["type"] == "coalition.decide" and e["payload"]["subject"]["kind"] == "commitment"
        ]
        for event in decisions:
            owner = event["on_behalf_of"]
            verify_consent(
                self.cid,
                event["payload"],
                jwk_to_public_key(self.host.state.members[owner]["owner_key"]),
                participant=owner,
            )
        self.check(
            "commitments_signed_by_owner",
            bool(decisions)
            and all(self.host.state.tasks[t]["status"] == "committed" for t in self.needs),
            "commitments carry verified owner signatures",
        )

    async def distinguish(self) -> None:
        case = self.scenario.expect.distinguishing
        if case.absent_answered:
            entry = case.absent_answered
            slots = self.scenario.members[int(entry.member[1:]) - 1].vault.get("free", [])
            assert slots, "absent member has no feasible slot in vault"
            query = QueryPayload(query_id=new_ulid(), kind="feasible", subject=str(slots[0]))
            emit(
                self.host,
                "query",
                query.to_wire(),
                {"audience": "participants", "participants": [entry.member]},
            )
            answer = self.vaults[entry.member].answer(query)
            await self.send(
                entry.member,
                "answer",
                answer.to_wire(),
                scope={"audience": "participants", "participants": [entry.member]},
            )
            self.check(
                "absent_answered",
                answer.result == entry.answer,
                "hosted vault agent answered while owner was absent",
            )
        elif case.business_holds:
            from .pack_actors import business_hold

            await business_hold(self)
        else:
            from .pack_actors import minted_reading

            await minted_reading(self)

    async def ripple(self) -> None:
        change = self.scenario.expect.change
        before = deepcopy(self.host.state.tasks)
        await self.send(
            change.by,
            "ripple",
            {"change": "task changed", "invalidates": [self.needs[i] for i in change.invalidates]},
        )
        affected = {
            i for i, task in enumerate(self.needs) if self.host.state.tasks[task] != before[task]
        }
        self.check(
            "change.affected",
            affected == set(change.affected),
            "ripple affected exactly the expected needs",
        )
        self.plan()
        self.check(
            "change.untouched",
            all(
                self.host.state.tasks[self.needs[i]] == before[self.needs[i]]
                for i in change.untouched
            ),
            "untouched task state and assignment preserved after replanning",
        )

    async def probe(self) -> None:
        probe = self.scenario.expect.policy_probe
        before = len(self.server.store.read(self.cid))
        reply = await self.send(
            probe.by, probe.type.removeprefix("coalition."), probe.payload, allow_refusal=True
        )
        reference = reply["error"]["ref"] if "error" in reply else reply["accepted"]["event_id"]
        with self.server.store.transaction(self.cid) as tx:
            rows = tx.execute(
                "SELECT policy_id, action FROM pack_policy_outcomes "
                "WHERE coalition = ? AND event_id = ? ORDER BY rowid",
                (self.cid, reference),
            ).fetchall()
        actual = rows[-1] if rows else None
        self.check(
            "policy_probe",
            actual == (probe.policy_id, probe.outcome),
            "observed policy id and action match expectation",
        )
        if probe.outcome in {"block", "escalate"}:
            self.check(
                "policy_probe.held",
                "error" in reply and len(self.server.store.read(self.cid)) == before,
                "blocked or held probe did not enter the log",
            )

    async def script(self, gateway: ModelGateway | None) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app, client=("127.0.0.1", 1234)),
            base_url="http://127.0.0.1:8000",
            headers={"Origin": "http://127.0.0.1:8000"},
        ) as http:
            await self.genesis(http)
            from .pack_actors import join_businesses

            await join_businesses(self)
            self.stage = "distinguishing"
            if not self.scenario.expect.distinguishing.minted_reading:
                await self.distinguish()
            self.stage = "offers"
            await self.offers(gateway)
            self.stage = "plan"
            scores = self.plan()
            if self.scenario.expect.distinguishing.minted_reading:
                self.stage = "minted_reading"
                await self.distinguish()
                self.plan()
            exp = self.scenario.expect
            if exp.allocation is not None:
                actual = {
                    i: self.host.state.tasks[self.needs[i]].get("assignee") for i in exp.allocation
                }
                self.check(
                    "allocation",
                    actual == exp.allocation,
                    "actual Gardener allocation compared with expected allocation",
                )
            if exp.fairness:
                self.check(
                    "fairness",
                    scores["max_share_ratio"] <= exp.fairness.max_share_ratio,
                    "plan objective max_share_ratio within bound",
                )
            self.stage = "commitments"
            await self.commitments()
            self.stage = "change"
            await self.ripple()
            self.stage = "policy_probe"
            await self.probe()
            self.stage = "dissolve"
            response = await http.post(
                "/v1/coalition/dissolve",
                json={"reason": exp.dissolve.reason},
                headers={"Authorization": "Bearer " + self.owner_token},
            )
            response.raise_for_status()
            event = next(
                e for e in self.server.store.read(self.cid) if e["type"] == "coalition.dissolve"
            )
            self.check(
                "dissolve",
                self.host.state.stage == "Dissolve"
                and len(event["payload"]["skills_written"]) >= exp.dissolve.lessons,
                "Dissolve wrote the required lessons",
            )


async def run_acceptance(
    pack: Pack, scenario: AcceptanceScenario | None = None, *, live: bool = False
) -> Document:
    scenario = scenario or load_scenario(pack)
    if live and not os.environ.get("COALITIONKIT_META_API_KEY", "").strip():
        return {"status": "not run", "reason": "no key", "steps": []}
    transport = LiveTransport(live_settings()) if live else None
    meter = CostMeter(CONTRIBUTOR_PRICES)
    gateway = ModelGateway(live_settings(), transport=transport, meter=meter) if live else None
    with tempfile.TemporaryDirectory() as temporary:
        run = Journey(pack, scenario, Path(temporary))
        try:
            try:
                await run.script(gateway)
            except Exception as exc:
                run.check(run.stage, False, f"execution failed ({type(exc).__name__})")
            surfaces = run.collect()
            if transport:
                surfaces.append(transport.calls)
            text = json.dumps(surfaces, default=str, ensure_ascii=False)
            text += "\n" + "\n".join(str(leaf) for _, leaf in walk(surfaces))
            leaked = sum(m.vault["canary"] in text for m in scenario.members)
            run.check(
                "canaries_leaked", leaked == 0, f"{leaked} canaries found across recorded channels"
            )
            messages = (len(run.server.store.read(run.cid)) + run.refused) if run.cid else 0
            run.check(
                "max_messages",
                messages <= scenario.expect.max_messages,
                f"{messages} accepted events and refused submissions",
            )
            result: Document = {
                "status": "fail" if any(s["status"] == "fail" for s in run.steps) else "pass",
                "steps": run.steps,
                "messages": messages,
                "canaries_leaked": leaked,
            }
            if transport:
                result["usage"] = {
                    "model_calls": len(transport.calls),
                    "prompt_tokens": sum(r.prompt_tokens for r in meter.records),
                    "completion_tokens": sum(r.completion_tokens for r in meter.records),
                    "latency_seconds": sum(transport.latencies),
                    "cost_micro_usd": sum(r.cost_micro_usd for r in meter.records),
                }
            return result
        finally:
            run.server.close()
            await run.server.gateway.aclose()
            if gateway:
                await gateway.aclose()


def command(directory: Path, *, live: bool, as_json: bool) -> int:
    catalog = spec_path("catalog", "coalitionkit-v0_9.json")
    pack = inspect_pack(directory, core_catalog=load_catalog(catalog))
    result = asyncio.run(run_acceptance(pack, live=live))
    if not as_json:
        for step in result["steps"]:
            print(f"{step['step']}: {step['status']} ({step['reason']})")
        if result["status"] == "not run":
            print("not run (no key)")
    print(json.dumps({"pack": pack.name, "live": live, **result}))
    return int(result["status"] == "fail")
