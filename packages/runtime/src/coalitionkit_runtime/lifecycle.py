# SPDX-License-Identifier: Apache-2.0
"""Deterministic lifecycle fold, shared by live reads and crash recovery."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from coalitionkit_contracts import (
    Membership,
    Scope,
    ScopeSource,
    after_planning_start,
    after_replan,
    decision_expired,
    next_revision,
    principals,
    record_answer,
    supersede_active,
    tally,
    tally_choice,
)

from .store import Document


@dataclass
class State:
    coalition_id: str
    stage: str = "Germinate"
    former: dict[str, Document] = field(default_factory=lambda: dict[str, Document]())
    charter: Document = field(default_factory=lambda: dict[str, Any]())
    members: dict[str, Document] = field(default_factory=lambda: dict[str, Document]())
    tasks: dict[str, Document] = field(default_factory=lambda: dict[str, Document]())
    subjects: dict[str, Document] = field(default_factory=lambda: dict[str, Document]())
    queries: dict[str, Document] = field(default_factory=lambda: dict[str, Document]())
    matches: dict[str, Document] = field(default_factory=lambda: dict[str, Document]())
    offers: dict[str, Document] = field(default_factory=lambda: dict[str, Document]())
    events: dict[str, Document] = field(default_factory=lambda: dict[str, Document]())

    def membership(self) -> Membership:
        roles: dict[str, frozenset[str]] = {}
        for owner, member in self.members.items():
            for role in member["roles_requested"]:
                roles[role] = roles.get(role, frozenset()) | {owner}
        return Membership(frozenset(self.members), roles)

    def visible(self, event: Document, viewer: str) -> bool:
        return viewer in principals(
            ScopeSource(Scope.model_validate(event["scope"]), event["on_behalf_of"]),
            self.membership(),
        )

    def subject(self, kind: str, identifier: str) -> Document:
        return self.subjects.get(f"{kind}:{identifier}", {})

    def accepted_charter(self, owner: str) -> bool:
        return self.members.get(owner, {}).get("accepted_revision") == self.charter.get(
            "revision", 0
        )

    def task_ids(self, event: Document) -> list[str]:
        body, kind = event["payload"], event["type"].split(".")[-1]
        if kind == "need":
            return [body["need_id"]]
        if kind in {"commit", "done", "match"}:
            return [body["task_id"]]
        if kind == "offer":
            return [body["target"]["id"]]
        if kind == "query":
            return [body["task_id"]] if "task_id" in body else []
        if kind == "answer":
            query = self.queries.get(body["query_id"], {})
            return [query["task_id"]] if "task_id" in query else []
        if kind == "propose":
            return sorted({a["task_id"] for p in body["plans"] for a in p["assignments"]})
        if kind == "ripple":
            return body["invalidates"]
        if kind == "decide":
            subject = body["subject"]
            return self.subject(subject["kind"], subject["id"]).get("tasks", [])
        if kind == "tension":
            return body["task_ids"]
        return []

    def set_status(self, ids: list[str], status: str) -> None:
        for identifier in ids:
            task = self.tasks[identifier]
            if task["status"] != status:
                task["status"] = status
                task["revision"] = next_revision(task["revision"])
                subject = self.subject("task", identifier)
                subject.update(
                    revision=task["revision"],
                    answers={},
                    status="pending" if status in {"proposed", "decided"} else "superseded",
                )
        active = [t for t in self.tasks.values() if t["status"] not in {"done", "withdrawn"}]
        if active and all(t["status"] == "negotiating" for t in active):
            self.stage = "Negotiate"

    def put_subject(
        self,
        kind: str,
        identifier: str,
        revision: int,
        tasks: list[str],
        deciders: list[str],
        **extra: object,
    ) -> None:
        self.subjects[f"{kind}:{identifier}"] = {
            "kind": kind,
            "id": identifier,
            "revision": revision,
            "tasks": tasks,
            "deciders": deciders,
            "answers": {},
            **extra,
        }

    def apply(self, event: Document) -> None:
        event = deepcopy(event)
        body, owner = event["payload"], event["on_behalf_of"]
        kind = event["type"].split(".")[-1]
        ids = self.task_ids(event)
        self.expire(event["ts"])
        if kind in {"query", "propose", "tension"}:
            for identifier in ids:
                self.set_status(
                    [identifier], after_planning_start(self.tasks[identifier]["status"])
                )
        if kind == "charter":
            self.charter = body
            for offer in self.offers.values():
                offer["counted"] = False
            self.put_subject("charter", self.coalition_id, body["revision"], [], list(self.members))
            for subject in self.subjects.values():
                if subject["kind"] == "commitment" and subject.get("status") != "withdrawn":
                    subject["suspended"] = True
        elif kind == "join":
            self.members[owner] = {**body, "sender": event["sender"], "accepted_revision": 0}
            charter = self.subject("charter", self.coalition_id)
            if charter:
                charter["deciders"] = list(self.members)
            required = {r["id"] for r in self.charter.get("roles", []) if r.get("required")}
            if self.charter and required <= self.membership().role_holders.keys():
                self.stage = "Gather"
        elif kind == "leave":
            self.former[owner] = self.members.pop(owner)
            self.offers = {k: v for k, v in self.offers.items() if v["owner"] != owner}
        elif kind == "need":
            identifier = body["need_id"]
            old = self.tasks.get(identifier)
            revision = next_revision(old["revision"]) if old else 1
            self.tasks[identifier] = {
                **body,
                "status": "open",
                "revision": revision,
                "source": event,
                "assignee": None,
            }
            self.put_subject("task", identifier, revision, [identifier], [])
        elif kind == "query":
            self.queries[body["query_id"]] = {**body, "event": event, "answered": False}
        elif kind == "answer":
            self.queries[body["query_id"]]["answered"] = True
        elif kind == "match":
            if body["round"] == "setup":
                self.matches[body["match_id"]] = {
                    "requester": body["peer"],
                    "responder": owner,
                    "tasks": ids,
                    "round": "setup",
                    "reveal": body["reveal"],
                }
            else:
                self.matches[body["match_id"]]["round"] = body["round"]
        elif kind == "offer":
            self.offers[body["offer_id"]] = {
                **body,
                "owner": owner,
                "counted": self.accepted_charter(owner),
            }
        elif kind in {"propose", "tension"}:
            self._proposal(event, ids)
        elif kind == "decide":
            self._decision(body, owner)
        elif kind == "commit":
            identifier = body["commitment_id"]
            if body["status"] == "pending":
                self.put_subject(
                    "commitment",
                    identifier,
                    1,
                    ids,
                    [owner],
                    status="pending",
                    owner=owner,
                    sender=event["sender"],
                    suspended=not self.accepted_charter(owner),
                )
            else:
                subject = self.subject("commitment", identifier)
                subject.update(status="withdrawn", revision=next_revision(subject["revision"]))
                self.replan(ids)
        elif kind == "ripple":
            self.replan(ids)
        elif kind == "done":
            self.set_status(ids, "done")
        elif kind == "dissolve":
            self.set_status(
                [k for k, t in self.tasks.items() if t["status"] != "done"], "withdrawn"
            )
            self.stage = "Dissolve"
        self.events[event["event_id"]] = event

    def _proposal(self, event: Document, ids: list[str]) -> None:
        body = event["payload"]
        if event["type"] == "coalition.propose":
            for plan in body["plans"]:
                self.put_subject(
                    "plan",
                    plan["plan_id"],
                    plan["revision"],
                    [a["task_id"] for a in plan["assignments"]],
                    self.charter["deciders"],
                    assignments=plan["assignments"],
                    proposal_set_id=body["proposal_set_id"],
                    decision_deadline=body["decision_deadline"],
                    status="pending",
                )
        else:
            self.put_subject(
                "tension_option",
                body["tension_id"],
                body["revision"],
                ids,
                body["deciders"],
                options=body["options"],
                decision_deadline=body["decision_deadline"],
                status="pending",
            )
        self.set_status(ids, "proposed")
        self.stage = "Decide"

    def _decision(self, body: Document, owner: str) -> None:
        reference = body["subject"]
        kind = reference["kind"]
        subject = self.subject(kind, reference["id"])
        subject["answers"], _ = record_answer(
            subject["answers"], subject["deciders"], owner, body["consent"]
        )
        if kind == "charter":
            if body["consent"]:
                self.members[owner]["accepted_revision"] = reference["revision"]
                for offer in self.offers.values():
                    if offer["owner"] == owner:
                        offer["counted"] = True
                for item in self.subjects.values():
                    if item["kind"] == "commitment" and item.get("owner") == owner:
                        item["suspended"] = False
                        if item.get("status") == "approved":
                            self.set_status(item["tasks"], "committed")
            return
        outcome = tally(subject["deciders"], subject["answers"])
        winner: str | None = None
        if kind == "tension_option":
            choices = subject.setdefault("choices", {})
            choices[owner] = (body["consent"], body["choice"])
            outcome, winner = tally_choice(subject["deciders"], choices)
        if outcome in {"refused", "split"}:
            if kind != "commitment":
                subject["status"] = "refused"
            self.replan(subject["tasks"])
        elif outcome == "decided":
            subject["status"] = "decided"
            # A tension whose options are plans decides the chosen plan (spec, rule 5).
            assignments = subject.get("assignments", [])
            chosen_plan = self.subject("plan", winner) if winner else {}
            if chosen_plan and chosen_plan.get("status") not in {"superseded", "refused"}:
                chosen_plan["status"] = "decided"
                assignments = chosen_plan.get("assignments", [])
                self._supersede_others(chosen_plan)
            if kind == "plan":
                self._supersede_others(subject)
            if kind == "commitment":
                subject["status"] = "approved"
                if not subject["suspended"]:
                    self.set_status(subject["tasks"], "committed")
                    self.stage = "Live"
            else:
                self.set_status(subject["tasks"], "decided")
                for assignment in assignments:
                    task = self.tasks[assignment["task_id"]]
                    task["assignee"] = assignment["assignee"]
                    self.subject("task", assignment["task_id"])["deciders"] = [task["assignee"]]
                self.stage = "Act"

    def _supersede_others(self, plan: Document) -> None:
        for other in self.subjects.values():
            if (
                other is not plan
                and other["kind"] == "plan"
                and other.get("proposal_set_id") == plan.get("proposal_set_id")
            ):
                other["status"] = "superseded"

    def replan(self, ids: list[str]) -> None:
        for identifier in ids:
            self.set_status([identifier], after_replan(self.tasks[identifier]["status"]))
        affected = {
            key: subject["status"]
            for key, subject in self.subjects.items()
            if subject["kind"] == "commitment" and set(subject["tasks"]) & set(ids)
        }
        for key, status in supersede_active(affected).items():
            self.subjects[key]["status"] = status
        for subject in self.subjects.values():
            if (
                subject["kind"] in {"plan", "tension_option"}
                and subject.get("status") == "pending"
                and set(subject["tasks"]) & set(ids)
            ):
                subject["status"] = "superseded"

    def expire(self, at: str) -> None:
        for subject in self.subjects.values():
            if (
                subject.get("status") == "pending"
                and "decision_deadline" in subject
                and decision_expired(subject["decision_deadline"], at)
            ):
                subject["status"] = "expired"
                self.replan(subject["tasks"])


def rebuild(coalition_id: str, events: list[Document], at: str | None = None) -> State:
    state = State(coalition_id)
    for event in events:
        state.apply(event)
    if at is not None:
        state.expire(at)
    return state
