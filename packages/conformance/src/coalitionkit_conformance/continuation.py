# SPDX-License-Identifier: Apache-2.0
"""Decision continuation and replan checks over independent member connections."""

from coalitionkit_contracts import new_ulid
from coalitionkit_edges.a2a.client import MemberClient

from .probes import refused
from .scenarios import Scenario


async def continuation(s: Scenario) -> str:
    task = await s.task()
    plan = await s.plan(task)
    await s.p.client.send(s.p.decision(kind="plan", identifier=plan))
    await refused(
        s.p,
        s.p.event("commit", {"commitment_id": new_ulid(), "task_id": task, "status": "pending"}),
        "stage_mismatch",
    )
    other = s.people[1]
    await other.client.close()
    other.client = await MemberClient.connect(
        s.http, s.target, other.token, s.host.public_key, s.host.kid
    )
    await other.client.send(other.decision(kind="plan", identifier=plan))
    cid = new_ulid()
    await s.p.client.send(
        s.p.event("commit", {"commitment_id": cid, "task_id": task, "status": "pending"})
    )
    await s.p.client.send(s.p.decision(kind="commitment", identifier=cid))
    await s.p.client.send(s.p.event("ripple", {"change": "Update", "invalidates": [task]}))
    await refused(s.p, s.p.event("done", {"task_id": task, "evidence": []}), "stage_mismatch")
    plan = await s.plan(task)
    await s.decide("plan", plan)
    await refused(s.p, s.p.decision(kind="commitment", identifier=cid), "stale_subject")
    fresh = new_ulid()
    await s.p.client.send(
        s.p.event("commit", {"commitment_id": fresh, "task_id": task, "status": "pending"})
    )
    await refused(s.p, s.p.event("done", {"task_id": task, "evidence": []}), "stage_mismatch")
    await s.p.client.send(s.p.decision(kind="commitment", identifier=fresh))
    await s.p.client.send(s.p.event("done", {"task_id": task, "evidence": []}))
    return f"task={task}: disconnect preserved consent; replan superseded {cid}; fresh approval"
