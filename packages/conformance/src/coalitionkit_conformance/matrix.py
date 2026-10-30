# SPDX-License-Identifier: Apache-2.0
"""Additional target-authorization rows, including exchange role binding."""

from coalitionkit_contracts import new_ulid, sign_envelope

from .probes import refused
from .report import Document
from .scenarios import FAR, PUBLIC, Scenario, need_body, offer


async def matrix(s: Scenario) -> None:
    p, other = s.people[:2]
    hidden = await s.emit(
        "need", need_body(), {"audience": "participants", "participants": [p.participant]}
    )
    hidden_id = hidden["payload"]["need_id"]
    await refused(other, other.event("offer", offer(hidden_id)), "not_authorized")
    await refused(
        other,
        other.event("ripple", {"change": "Update", "invalidates": [hidden_id]}),
        "not_authorized",
    )
    impersonated = p.event("leave", {})
    impersonated["on_behalf_of"] = other.participant
    impersonated["sig"] = sign_envelope(impersonated, p.key, "agent")
    await refused(p, impersonated, "sender_mismatch")
    task, alternate = await s.task(), await s.task()
    query = await s.query(task)
    await s.query(alternate)
    scope = {"audience": "participants", "participants": [p.participant]}
    answer = {"query_id": query, "result": "yes"}
    await p.client.send(p.event("answer", answer, scope))
    await refused(p, p.event("answer", answer, scope), "not_authorized")
    exchange = {
        "match_id": new_ulid(),
        "task_id": task,
        "peer": other.participant,
        "round": "setup",
        "blob": "",
        "reveal": "overlap",
    }
    await p.client.send(p.event("match", exchange))
    await refused(p, p.event("match", {**exchange, "round": "request"}), "not_authorized")
    request = {**exchange, "peer": p.participant, "round": "request"}
    await refused(other, other.event("match", {**request, "task_id": alternate}), "not_authorized")
    await other.client.send(other.event("match", request))
    await refused(other, other.event("match", {**request, "round": "response"}), "not_authorized")
    await p.client.send(p.event("match", {**exchange, "round": "response"}))
    await refused(p, p.event("match", {**exchange, "round": "response"}), "not_authorized")
    open_task = await s.task()
    await refused(
        p,
        p.event("match", {**exchange, "match_id": new_ulid(), "task_id": open_task}),
        "stage_mismatch",
    )
    await host_only(s, task)


async def host_only(s: Scenario, task: str) -> None:
    view = await s.view()
    bodies: dict[str, Document] = {}
    for event in view["events"].values():
        bodies[event["type"].removeprefix("coalition.")] = event["payload"]
    bodies["dissolve"] = {"reason": "cancelled", "skills_written": []}
    bodies["error"] = {"code": "not_authorized", "detail": {}, "ref": new_ulid()}
    ack = await s.p.client.send(
        s.p.event(
            "observe",
            {"source": "device", "content": "private"},
            {**PUBLIC, "redact": ["payload.content"]},
        )
    )
    if ack.accepted is None:
        raise AssertionError("missing redacted delivery")
    bodies["projection"] = ack.accepted["payload"]
    bodies["receipt"] = ack.receipt["payload"]
    # These valid schemas need no accepted proposal or tension setup.
    bodies["propose"] = {
        "proposal_set_id": new_ulid(),
        "decision_deadline": FAR,
        "plans": [
            {"plan_id": new_ulid(), "revision": 1, "assignments": [], "objective_scores": {}}
        ],
    }
    bodies["tension"] = {
        "tension_id": new_ulid(),
        "revision": 1,
        "task_ids": [task],
        "options": [
            {"option_id": "o1", "summary": "First"},
            {"option_id": "o2", "summary": "Second"},
        ],
        "tradeoffs": [],
        "deciders": [s.p.participant],
        "decision_deadline": FAR,
    }
    for kind in (
        "charter",
        "need",
        "query",
        "propose",
        "tension",
        "dissolve",
        "projection",
        "receipt",
        "error",
    ):
        await refused(s.p, s.p.event(kind, bodies[kind]), "not_authorized")
