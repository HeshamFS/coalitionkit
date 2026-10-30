# SPDX-License-Identifier: Apache-2.0
"""Operator-created fixtures, observed through member protocol deliveries."""

import asyncio
from datetime import UTC, datetime, timedelta

import httpx

from coalitionkit_contracts import new_ulid, verify_envelope, verify_receipt
from coalitionkit_edges.a2a.identity import CardKey

from .operator import Operator
from .probes import refused
from .report import Document
from .wire import Participant

PUBLIC: Document = {"audience": "coalition"}
FAR = "2099-01-01T00:00:00Z"


def need_body() -> Document:
    return {
        "description": "Shared task",
        "requirements": [],
        "window": {"start": datetime.now(UTC).isoformat(), "end": FAR},
    }


class Scenario:
    def __init__(
        self,
        people: list[Participant],
        operator: Operator,
        http: httpx.AsyncClient,
        host: CardKey,
        target: str,
    ) -> None:
        self.people, self.operator, self.http, self.host = people, operator, http, host
        self.p = people[0]
        self.target = target

    async def emit(
        self,
        kind: str,
        body: Document,
        scope: Document | None = PUBLIC,
        *,
        sources: list[str] | None = None,
    ) -> Document:
        result = await self.operator.emit(self.p.coalition, kind, body, scope, sources=sources)
        if result.get("type") == "coalition.error":
            raise AssertionError(
                f"host {kind}: {result['payload']['code']} ref={result['payload']['ref']}"
            )
        event = result["accepted"]
        if event is None:
            raise AssertionError(f"host {kind}: no setup acknowledgement")
        verify_envelope(event, self.host.public_key)
        verify_receipt(result["receipt"], self.host.public_key, accepted=event)
        return event

    async def task(self) -> str:
        event = await self.emit("need", need_body())
        return str(event["payload"]["need_id"])

    async def query(self, task: str) -> str:
        query = new_ulid()
        await self.emit(
            "query",
            {"query_id": query, "kind": "feasible", "subject": task, "task_id": task},
            {"audience": "participants", "participants": [self.p.participant]},
        )
        return query

    async def plan(self, task: str, deadline: str = FAR) -> str:
        companion = await self.task()
        event = await self.emit(
            "propose",
            {
                "proposal_set_id": new_ulid(),
                "decision_deadline": deadline,
                "plans": [
                    {
                        "assignments": [
                            {"task_id": task, "assignee": self.p.participant},
                            {"task_id": companion, "assignee": self.people[1].participant},
                        ],
                        "objective_scores": {},
                    }
                ],
            },
        )
        return str(event["payload"]["plans"][0]["plan_id"])

    async def decide(self, kind: str, identifier: str, *, consent: bool = True) -> None:
        await asyncio.gather(
            *(
                p.client.send(p.decision(kind=kind, identifier=identifier, consent=consent))
                for p in self.people
            )
        )

    async def committed(self, task: str) -> str:
        plan = await self.plan(task)
        await self.decide("plan", plan)
        cid = new_ulid()
        await self.p.client.send(
            self.p.event("commit", {"commitment_id": cid, "task_id": task, "status": "pending"})
        )
        await self.p.client.send(self.p.decision(kind="commitment", identifier=cid))
        return cid

    async def view(self) -> Document:
        return await self.p.view(self.http, self.operator.feed_url)


async def derivation(s: Scenario) -> str:
    from .vectors import scope_vectors

    vectors = await scope_vectors()
    source = s.p.event(
        "observe",
        {"source": "device", "content": "derived-private"},
        {"audience": "participants", "participants": [s.p.participant]},
    )
    await s.p.client.send(source)
    event = await s.emit("need", need_body(), None, sources=[source["event_id"]])
    if event["scope"] != {"audience": "participants", "participants": [s.p.participant]}:
        raise AssertionError(f"derived scope widened: {event['scope']}")
    other = await s.people[1].view(s.http, s.operator.feed_url)
    if event["event_id"] in other["events"]:
        raise AssertionError("derived output delivered outside its source scope")
    widened = await s.operator.emit(
        s.p.coalition, "need", need_body(), PUBLIC, sources=[source["event_id"]]
    )
    if widened.get("payload", {}).get("code") != "scope_violation":
        raise AssertionError("explicit derivation widening was not refused")
    verify_envelope(widened, s.host.public_key)
    return (
        f"{vectors}; live source={source['event_id']} derived={event['event_id']}; widening refused"
    )


async def stages(s: Scenario) -> str:
    a, b = await s.task(), await s.task()
    await refused(s.p, s.p.event("done", {"task_id": a, "evidence": []}), "stage_mismatch")
    qa = await s.query(a)
    await s.p.client.send(
        s.p.event(
            "answer",
            {"query_id": qa, "result": "yes"},
            {"audience": "participants", "participants": [s.p.participant]},
        )
    )
    qb = await s.query(b)
    await s.committed(b)
    plan = await s.plan(a)
    await s.decide("plan", plan)
    cid = new_ulid()
    await s.p.client.send(
        s.p.event("commit", {"commitment_id": cid, "task_id": a, "status": "pending"})
    )
    await s.p.client.send(
        s.p.event(
            "commit", {"commitment_id": cid, "task_id": a, "status": "withdrawn", "revision": 1}
        )
    )
    await refused(s.p, s.p.decision(kind="commitment", identifier=cid), "stage_mismatch")
    qa = await s.query(a)
    await s.p.client.send(
        s.p.event(
            "answer",
            {"query_id": qa, "result": "yes"},
            {"audience": "participants", "participants": [s.p.participant]},
        )
    )
    await s.p.client.send(
        s.p.event(
            "match",
            {
                "match_id": new_ulid(),
                "task_id": a,
                "peer": s.people[1].participant,
                "round": "setup",
                "blob": "",
                "reveal": "overlap",
            },
        )
    )
    await s.p.client.send(s.p.event("offer", offer(a)))
    await refused(s.p, s.p.event("done", {"task_id": a, "evidence": []}), "stage_mismatch")
    await s.p.client.send(s.p.event("done", {"task_id": b, "evidence": []}))
    await refused(s.p, s.p.event("answer", {"query_id": qb, "result": "yes"}), "stage_mismatch")
    return f"tasks {a}, {b}: independent stages, withdrawal closes consent; exchanges accepted"


def offer(task: str) -> Document:
    return {
        "offer_id": new_ulid(),
        "target": {"kind": "task", "id": task},
        "capacity": 1,
        "cost": {"minutes": 0, "money": 0, "effort": "low"},
        "valid_until": FAR,
    }


async def decisions(s: Scenario) -> str:
    from .feed_probes import consent_rejections

    evidence = await consent_rejections(s.p)
    task = await s.task()
    plan = await s.plan(task)
    await refused(s.p, s.p.decision(2, kind="plan", identifier=plan), "stale_subject")
    await s.p.client.send(s.p.decision(kind="plan", identifier=plan))
    await refused(s.p, s.p.decision(kind="plan", identifier=plan), "not_authorized")
    await s.people[1].client.send(s.people[1].decision(kind="plan", identifier=plan))
    cid = new_ulid()
    await s.p.client.send(
        s.p.event("commit", {"commitment_id": cid, "task_id": task, "status": "pending"})
    )
    await s.p.client.send(s.p.decision(kind="commitment", identifier=cid, consent=False))
    await refused(s.p, s.p.event("done", {"task_id": task, "evidence": []}), "stage_mismatch")
    tension = await s.emit(
        "tension",
        {
            "task_ids": [task],
            "options": [
                {"option_id": "o1", "summary": "First"},
                {"option_id": "o2", "summary": "Second"},
            ],
            "tradeoffs": [],
            "deciders": [p.participant for p in s.people],
            "decision_deadline": FAR,
        },
    )
    tid = tension["payload"]["tension_id"]
    await asyncio.gather(
        *(
            p.client.send(p.decision(kind="tension_option", identifier=tid, choice=f"o{i + 1}"))
            for i, p in enumerate(s.people)
        )
    )
    await refused(
        s.p,
        s.p.event("commit", {"commitment_id": new_ulid(), "task_id": task, "status": "pending"}),
        "stage_mismatch",
    )
    deadline = (datetime.now(UTC) + timedelta(seconds=1)).isoformat()
    plan = await s.plan(task, deadline)
    await asyncio.sleep(
        max(0, (datetime.fromisoformat(deadline) - datetime.now(UTC)).total_seconds()) + 0.05
    )
    await refused(s.p, s.p.decision(kind="plan", identifier=plan), "deadline_exceeded")
    await s.query(task)
    from .continuation import continuation

    continued = await continuation(s)
    return f"{evidence}; refusal, split tension, real deadline; {continued}"


async def authorization_rows(s: Scenario) -> str:
    from .matrix import matrix
    from .probes import authorization

    await matrix(s)
    await authorization(s.p)
    task = await s.task()
    query = await s.query(task)
    other = s.people[1]
    await refused(
        other, other.event("answer", {"query_id": query, "result": "yes"}), "not_authorized"
    )
    item = offer(task)
    await s.p.client.send(s.p.event("offer", item))
    await refused(other, other.event("offer", item), "not_authorized")
    plan = await s.plan(task)
    await s.decide("plan", plan)
    cid = new_ulid()
    await s.p.client.send(
        s.p.event("commit", {"commitment_id": cid, "task_id": task, "status": "pending"})
    )
    await refused(
        other,
        other.event("commit", {"commitment_id": new_ulid(), "task_id": task, "status": "pending"}),
        "not_authorized",
    )
    await refused(
        other,
        other.event(
            "commit", {"commitment_id": cid, "task_id": task, "status": "withdrawn", "revision": 1}
        ),
        "not_authorized",
    )
    await refused(other, other.decision(kind="task", identifier=task), "not_a_decider")
    await refused(other, other.decision(kind="commitment", identifier=cid), "not_a_decider")
    await refused(
        s.p,
        s.p.event("commit", {"commitment_id": cid, "task_id": task, "status": "pending"}),
        "not_authorized",
    )
    await s.p.client.send(s.p.decision(kind="commitment", identifier=cid))
    await refused(other, other.event("done", {"task_id": task, "evidence": []}), "not_authorized")
    return f"task={task}; wrong recipient, owner, assignee, decider and reused commitment refused"


async def charter_revision(s: Scenario) -> str:
    task = await s.task()
    await s.query(task)
    await s.committed(task)
    await s.emit(
        "charter",
        {
            "goal": "Coordinate shared tasks",
            "roles": [{"id": "member"}],
            "rules": [],
            "deadline": FAR,
            "deciders": [p.participant for p in s.people],
        },
    )
    await refused(s.p, s.p.event("done", {"task_id": task, "evidence": []}), "not_authorized")
    for p in s.people:
        await p.client.send(p.decision(2))
    await s.p.client.send(s.p.event("done", {"task_id": task, "evidence": []}))
    return f"task={task}; revision 2 suspends commitment until renewed charter consent"


async def steward_gate(s: Scenario) -> str:
    task = await s.task()
    companion = await s.task()
    proposal = new_ulid()
    result = await s.operator.emit(
        s.p.coalition,
        "propose",
        {
            "proposal_set_id": proposal,
            "decision_deadline": FAR,
            "plans": [
                {
                    "assignments": [
                        {"task_id": task, "assignee": s.p.participant},
                        {"task_id": companion, "assignee": s.p.participant},
                    ],
                    "objective_scores": {},
                }
            ],
        },
        PUBLIC,
    )
    verify_envelope(result, s.host.public_key)
    payload = result.get("payload", {})
    if payload.get("code") != "steward_blocked":
        raise AssertionError("unbalanced proposal was not blocked by Steward")
    if payload.get("detail", {}).get("policy_id") != "fairness-cap-exceeded":
        raise AssertionError(f"expected fairness policy, got {payload.get('detail')}")
    for p in s.people:
        view = await p.view(s.http, s.operator.feed_url)
        if proposal in str(view):
            raise AssertionError("blocked proposal delivered to a member")
    return f"proposal={proposal}: steward_blocked (fairness-cap-exceeded); absent from both feeds"
