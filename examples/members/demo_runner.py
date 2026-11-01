# SPDX-License-Identifier: Apache-2.0
"""Paced demo choreography. Only the room can supply owner consent."""

from __future__ import annotations

import asyncio
import importlib
import os
from fractions import Fraction
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_contracts import new_ulid
from coalitionkit_contracts.payloads import Cost, QueryPayload
from coalitionkit_gardener import Offer, Problem, Task, build_propose, generate_plans
from coalitionkit_gardener.tension import tension_from_plans
from coalitionkit_mcp.gateway import build_envelope
from coalitionkit_runtime import Acknowledgement
from coalitionkit_server.app import Server
from coalitionkit_vault.psi import Context, Requester, Responder
from coalitionkit_vault.store import Capacity, Facts, Vault

Document = dict[str, Any]
PUBLIC: Document = {"audience": "coalition"}
FAR = "2099-12-31T00:00:00Z"


def example_module(name: str) -> Any:
    return importlib.import_module(name)


def ignore_usage(use: object) -> None:
    """The gateway meter records usage, including failed turns."""


class Demo:
    def __init__(self, server: Server, coalition: str, pace: float = 2) -> None:
        if pace < 0:
            raise ValueError("pace must be nonnegative")
        self.server, self.coalition, self.pace = server, coalition, pace
        self.host = server.hosts[coalition]
        self.members = list(self.host.state.members)
        self.tasks: list[str] = []
        self.phase = "charter"
        self.steps = 0
        self.requests: set[str] = set()
        self.changed = False
        self.blocked: Document | None = None
        self.overlap: list[str] | int | None = None

    async def emit(self, kind: str, body: Document, scope: Document = PUBLIC) -> Document:
        await asyncio.sleep(self.pace)
        reply = self.host.host_emit(kind, body, scope)
        if not isinstance(reply, Acknowledgement):
            raise ValueError(f"demo host {kind} refused: {reply}")
        assert reply.accepted is not None
        return reply.accepted

    async def send(
        self, member: str, kind: str, body: Document, scope: Document = PUBLIC
    ) -> Document:
        if kind not in {"offer", "answer", "match", "observe", "commit", "ripple"}:
            raise ValueError("demo member tool not allowed")
        await asyncio.sleep(self.pace)
        person = self.server.registry.hosted_for(self.coalition, member)
        envelope = build_envelope(person, self.coalition, f"coalition.{kind}", body, scope=scope)
        reply = await self.server.accept(envelope, person.card_url)
        if "error" in reply:
            raise ValueError(f"demo member {kind} refused: {reply}")
        return reply

    async def step(self) -> bool:
        """Advance until the next human boundary; return false while waiting."""
        self.steps += 1
        state = self.host.state
        if self.phase == "charter":
            if not all(state.accepted_charter(m) for m in self.members):
                return False
            await self.seed()
            self.phase = "plan"
            return True
        if self.phase == "plan":
            if not all(state.tasks[t]["status"] == "decided" for t in self.tasks):
                return False
            if any(state.tasks[t]["assignee"] not in self.members for t in self.tasks):
                raise ValueError("the runtime needs a decided plan with assignments to continue")
            for task in self.tasks:
                member = str(state.tasks[task]["assignee"])
                shared = example_module("members.kit.brain")
                instruction = shared.work_instruction(member, [{"task_id": task, "label": "task"}])
                for _ in range(4):  # re-ask a model that ended its turn without the request
                    await self.drive(member, instruction, MemberTools(self, member, []))
                    if task in self.requests:
                        break
                else:
                    raise ValueError(f"demo member did not request commitment for {task}")
            self.phase = "approval"
            return True
        if self.phase == "approval":
            approved = next(
                (t for t in self.tasks if state.tasks[t]["status"] == "committed"), None
            )
            if approved is None:
                return False
            member = str(state.tasks[approved]["assignee"])
            await self.send(
                member, "ripple", {"change": "my availability changed", "invalidates": [approved]}
            )
            self.changed = True
            await self.propose([approved])
            self.phase = "finished"
            return True
        return False

    async def run(self) -> None:
        while self.phase != "finished":
            await self.step()
            await asyncio.sleep(max(self.pace, 0.1))

    async def seed(self) -> None:
        for index, _ in enumerate(self.members):
            event = await self.emit(
                "need",
                {
                    "description": f"task t{index + 1}",
                    "requirements": [],
                    "window": {"start": "2026-01-01T00:00:00Z", "end": FAR},
                },
            )
            self.tasks.append(str(event["payload"]["need_id"]))
        for index, member in enumerate(self.members):
            terms: list[Document] = []
            for offset, minutes, money in ((0, 120, 0), (1, 60, 90)):
                task = self.tasks[(index + offset) % len(self.tasks)]
                terms.append({"need_id": task, "minutes": minutes, "money": money, "effort": "low"})
            await self.offers(member, terms)
        for member, task in zip(self.members, self.tasks, strict=True):
            vault = Vault(member)
            vault.put(task, Facts(capacities=(Capacity(2, "hours"),)))
            scope: Document = {"audience": "participants", "participants": [member]}
            query = QueryPayload(
                query_id=new_ulid(),
                kind="feasible",
                subject=task,
                task_id=task,
                deadline_ms=max(10000, int(self.pace * 2000)),
            )
            await self.emit("query", query.model_dump(mode="json"), scope)
            await self.send(member, "answer", vault.answer(query).to_wire(), scope)
        if len(self.members) >= 2:
            await self.match()
        await self.propose(self.tasks)
        await self.block_request()

    async def block_request(self) -> None:
        """An existing policy escalates this request; the host refuses it closed."""
        content = example_module("members.demo_policy").BLOCKED_STATEMENT
        person = self.server.registry.hosted_for(self.coalition, self.members[0])
        await asyncio.sleep(self.pace)
        envelope = build_envelope(
            person,
            self.coalition,
            "coalition.observe",
            {"source": "chat", "content": content},
            scope={"audience": "host"},
        )
        reply = await self.server.accept(envelope, person.card_url)
        if reply.get("error", {}).get("code") != "steward_blocked":
            raise ValueError(f"demo expected a Steward refusal: {reply}")
        self.blocked = reply
        await self.send(
            self.members[0],
            "observe",
            {
                "source": "chat",
                "content": "Steward blocked a request: " + reply["error"]["detail"]["policy_id"],
            },
            {"audience": "self"},
        )

    async def offers(self, member: str, terms: list[Document]) -> None:
        tools = MemberTools(self, member, terms)
        shared = example_module("members.kit.brain")
        remaining = terms
        for _ in range(4):
            if not remaining:
                return
            instruction = shared.offers_instruction(member, remaining)
            await self.drive(member, instruction, tools)
            remaining = [t for t in terms if str(t["need_id"]) not in tools.offered]
        if remaining:
            missed = sorted({str(t["need_id"]) for t in remaining})
            raise ValueError(f"demo member did not finish its offers; missing needs: {missed}")

    async def drive(self, member: str, instruction: str, tools: MemberTools) -> None:
        if os.environ.get("COALITIONKIT_META_API_KEY"):
            module = example_module("members.hosted_member.brain")
            from coalitionkit_models import ModelGateway
            from coalitionkit_models.settings import Settings

            gateway = ModelGateway(Settings(), meter=self.server.gateway.meter)
            try:
                brain = module.HostedBrain(gateway, self.coalition, member)
                await brain.run(instruction, tools, ignore_usage)
            finally:
                await gateway.aclose()
        else:
            shared = example_module("members.kit.brain")
            runner = example_module("members.hosted_member.brain")
            seen: list[Any] = []
            while calls := shared.scripted_next(instruction, seen):
                for name, args in calls:
                    result = await runner._run_tool(tools, name, args)
                    seen.append((name, args, result))

    async def match(self) -> None:
        first, second = self.members[:2]
        a, b = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
        context = Context(self.coalition, new_ulid(), first, second, "overlap", self.tasks[0])
        requester = Requester(context, ["slot-1", "slot-2"], a, b.public_key())
        responder = Responder(context, ["slot-2", "slot-3"], b, a.public_key())
        scope: Document = {"audience": "participants", "participants": [first, second]}
        setup = responder.setup()
        await self.send(second, "match", setup.to_wire(), scope)
        request = requester.request(setup)
        await self.send(first, "match", request.to_wire(), scope)
        response = responder.respond(request)
        await self.send(second, "match", response.to_wire(), scope)
        self.overlap = requester.finish(response)

    async def propose(self, tasks: list[str]) -> None:
        state = self.host.state
        offers = tuple(
            Offer(o["owner"], o["target"]["id"], Cost.model_validate(o["cost"]))
            for o in state.offers.values()
            if o["counted"] and o["target"]["id"] in tasks
        )
        problem = Problem(
            tuple(Task(t) for t in tasks),
            offers,
            dict.fromkeys(self.members, 1),
            max_ratio=Fraction(2),
        )
        table = problem.bid_table()
        plans = generate_plans(
            problem,
            third=lambda assignments: float(
                sum(table[t, m].cost.minutes for t, m in assignments.items())
            ),
        )
        if not plans.plans:
            raise ValueError("demo has no feasible plan")
        scope = PUBLIC
        await self.emit(
            "propose",
            build_propose(plans, deadline=FAR, proposal_set_id=new_ulid()).model_dump(mode="json"),
            scope,
        )
        tension = tension_from_plans(plans, deciders=self.members, deadline=FAR)
        if tension:
            await self.emit("tension", tension.model_dump(mode="json"), scope)


class MemberTools:
    """Model arguments cannot widen the demo's offers or approve a commitment."""

    def __init__(self, demo: Demo, member: str, terms: list[Document]) -> None:
        self.demo, self.member, self.terms = demo, member, terms
        self.offered: set[str] = set()

    async def make_offer(self, need_id: str, minutes: int, money: int, effort: str) -> str:
        term = {"need_id": need_id, "minutes": minutes, "money": money, "effort": effort}
        if term not in self.terms or need_id in self.offered:
            return "refused: outside private limits or already offered"
        await self.demo.send(
            self.member,
            "offer",
            {
                "offer_id": new_ulid(),
                "target": {"kind": "need", "id": need_id},
                "capacity": 1,
                "cost": {"minutes": minutes, "money": money, "effort": effort},
                "valid_until": FAR,
            },
        )
        self.offered.add(need_id)
        return "offered"

    async def commit_to_task(self, task_id: str) -> str:
        state = self.demo.host.state
        task = state.tasks.get(task_id, {})
        if (
            self.demo.phase != "plan"
            or task_id not in self.demo.tasks
            or task.get("assignee") != self.member
            or task.get("status") != "decided"
            or task_id in self.demo.requests
        ):
            return "refused: wait for a human plan decision in the room"
        await self.demo.send(
            self.member,
            "commit",
            {
                "commitment_id": new_ulid(),
                "task_id": task_id,
                "status": "pending",
            },
        )
        self.demo.requests.add(task_id)
        return "pending: waiting for owner approval in the room"

    async def report_done(self, task_id: str, evidence_ref: str) -> str:
        return "refused: this demo does not perform work"
