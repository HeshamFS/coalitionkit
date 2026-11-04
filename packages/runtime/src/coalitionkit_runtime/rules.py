# SPDX-License-Identifier: Apache-2.0
"""Ordered stage, target authorization, and disclosure checks."""

from __future__ import annotations

from datetime import datetime
from typing import cast

from coalitionkit_contracts import (
    HOST_ONLY_TYPES,
    Scope,
    ScopeSource,
    accepts,
    may_create_commitment,
    principals,
    resolve_narrowest,
)
from coalitionkit_contracts.lifecycle import Action

from .lifecycle import State
from .store import Document


class Refusal(Exception):
    def __init__(self, code: str, detail: Document | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail or {}


def require(condition: bool, code: str = "not_authorized") -> None:
    if not condition:
        raise Refusal(code)


def stage_check(state: State, event: Document, host: bool) -> None:
    kind, body = event["type"].split(".")[-1], event["payload"]
    charter_decision = kind == "decide" and body["subject"]["kind"] == "charter"
    if kind == "leave" or (host and kind == "dissolve"):
        return
    require(state.stage != "Dissolve", "stage_mismatch")
    if kind == "join":
        require(state.stage in {"Germinate", "Gather"}, "stage_mismatch")
        return
    if charter_decision or kind == "charter":
        return
    if not host and event["type"] in HOST_ONLY_TYPES | {"coalition.error"}:
        return
    require(state.stage != "Germinate", "stage_mismatch")
    if kind in {"observe", "need", "say"}:
        return
    ids = state.task_ids(event)
    # Unknown targets are authorization failures, not invented task states.
    for identifier in ids:
        task = state.tasks.get(identifier)
        if task is None:
            continue
        if host and kind in {"query", "propose", "tension"}:
            allowed = {"open", "negotiating"} | ({"proposed"} if kind == "tension" else set[str]())
            require(task["status"] in allowed, "stage_mismatch")
            continue
        if kind == "decide":
            subject = state.subject(body["subject"]["kind"], body["subject"]["id"])
            if subject.get("status") in {"expired", "superseded"}:
                continue  # The transactional deadline/revision checks own this refusal.
            action = "decide." + body["subject"]["kind"]
        elif kind == "commit":
            action = "commit." + body["status"]
        else:
            action = kind
        require(accepts(task["status"], cast(Action, action)), "stage_mismatch")


def authorize(state: State, event: Document, host: bool, now: str) -> None:
    kind, body, owner = event["type"].split(".")[-1], event["payload"], event["on_behalf_of"]
    ids = state.task_ids(event)
    if host:
        require(kind in {"charter", "need", "query", "propose", "tension", "dissolve", "tool"})
        if kind == "charter" and state.charter:
            require(body.get("pack") == state.charter.get("pack"), "not_authorized")
        if kind in {"query", "propose", "tension"}:
            require((bool(ids) or kind == "query") and all(i in state.tasks for i in ids))
        if kind == "query":
            require(body["query_id"] not in state.queries)
            recipients = principals(
                ScopeSource(Scope.model_validate(event["scope"]), "host"), state.membership()
            )
            require(len(recipients) == 1)
        return
    require(event["type"] not in HOST_ONLY_TYPES | {"coalition.error"})
    if kind == "join":
        require(
            owner not in state.members
            and owner not in state.former
            and body["card_url"] == event["sender"]
        )
        declared = {r["id"] for r in state.charter.get("roles", [])}
        require(set(body["roles_requested"]) <= declared)
    elif kind in {"offer", "ripple"}:
        require(
            all(i in state.tasks and state.visible(state.tasks[i]["source"], owner) for i in ids)
        )
        if kind == "offer":
            old = state.offers.get(body["offer_id"])
            require(old is None or old["owner"] == owner)
    elif kind == "say":
        # A line is for the room or for one other seated member, and answers only what its
        # speaker could see.
        require(state.accepted_charter(owner))
        require(body["to"] == "room" or (body["to"] in state.members and body["to"] != owner))
        if "re" in body:
            cited = state.events.get(body["re"])
            require(cited is not None and state.visible(cited, owner))
    elif kind == "answer":
        query = state.queries.get(body["query_id"])
        require(query is not None)
        assert query is not None
        require(not query["answered"] and state.visible(query["event"], owner))
        elapsed = datetime.fromisoformat(now) - datetime.fromisoformat(query["event"]["ts"])
        require(
            elapsed.total_seconds() * 1000 <= query.get("deadline_ms", 10000), "deadline_exceeded"
        )
    elif kind == "match":
        _match(state, event)
    elif kind == "decide":
        reference = body["subject"]
        subject = state.subject(reference["kind"], reference["id"])
        require(owner in subject.get("deciders", []), "not_a_decider")
        if reference["kind"] == "tension_option":
            require(body["choice"] in {o["option_id"] for o in subject["options"]})
        else:
            require(body["choice"] == reference["id"])
        # Stale answers must reach the atomic revision check, even if an older answer exists.
        if reference["revision"] == subject["revision"] and subject.get("status") not in {
            "superseded",
            "expired",
        }:
            require(owner not in subject["answers"])
    elif kind in {"commit", "done"}:
        task = state.tasks.get(body["task_id"], {})
        require(task.get("assignee") == owner)
        if kind == "done":
            require(state.accepted_charter(owner))
            require(
                any(
                    s["kind"] == "commitment"
                    and s["tasks"] == ids
                    and s.get("status") == "approved"
                    and not s.get("suspended")
                    for s in state.subjects.values()
                )
            )
        elif body["status"] == "pending":
            require("revision" not in body)
            require(not state.subject("commitment", body["commitment_id"]))
            require(
                may_create_commitment(
                    [
                        s["status"]
                        for s in state.subjects.values()
                        if s["kind"] == "commitment" and s["tasks"] == ids
                    ]
                )
            )
        else:
            subject = state.subject("commitment", body["commitment_id"])
            require(subject.get("sender") == event["sender"] and subject.get("tasks") == ids)
            require(body.get("revision") == subject.get("revision"), "stale_subject")
            require(subject.get("status") in {"pending", "approved"}, "stale_subject")


def _match(state: State, event: Document) -> None:
    body, owner = event["payload"], event["on_behalf_of"]
    exchange = state.matches.get(body["match_id"])
    if body["round"] == "setup":
        require(exchange is None and body["peer"] in state.members and body["peer"] != owner)
        ids = state.task_ids(event)
        require(bool(ids) and all(i in state.tasks for i in ids))
        require(all(state.visible(state.tasks[i]["source"], owner) for i in ids))
        if body["reveal"] == "count":
            require(body["peer"] in state.charter.get("count_trusted", []))
        return
    require(exchange is not None)
    assert exchange is not None
    requester, responder = exchange["requester"], exchange["responder"]
    if body["round"] == "request":
        require(owner == requester and body["peer"] == responder and exchange["round"] == "setup")
    else:
        require(owner == responder and body["peer"] == requester and exchange["round"] == "request")
    require(body["reveal"] == exchange["reveal"] and [body["task_id"]] == exchange["tasks"])


def scope_check(state: State, event: Document, sources: list[Document]) -> None:
    scope = Scope.model_validate(event["scope"])
    addressable = set(state.members)
    if event["type"] == "coalition.join":
        addressable.add(event["on_behalf_of"])
    require(set(scope.participants or []) <= addressable, "scope_violation")
    require(set(scope.roles or []) <= state.membership().role_holders.keys(), "scope_violation")
    if not sources:
        return
    narrow = resolve_narrowest(
        [ScopeSource(Scope.model_validate(e["scope"]), e["on_behalf_of"]) for e in sources],
        state.membership(),
    )
    requested = principals(ScopeSource(scope, event["on_behalf_of"]), state.membership())
    permitted = principals(ScopeSource(narrow, "host"), state.membership())
    require(
        requested <= permitted and set(narrow.redact or []) <= set(scope.redact or []),
        "scope_violation",
    )
