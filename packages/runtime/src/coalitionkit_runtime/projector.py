# SPDX-License-Identifier: Apache-2.0
"""Viewer documents are folded exclusively from visible, redacted log deliveries."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, cast

from coalitionkit_contracts import (
    Membership,
    Scope,
    ScopeSource,
    delivery_form,
    prev_hash,
    resolve_narrowest,
)

from .lifecycle import State
from .store import Document

Signer = Callable[[str, Document, Document], Document]


@dataclass
class ViewerProjection:
    """A connection's fold; membership changes invalidate prior visibility decisions."""

    viewer: str
    sequence: int = 0
    membership: Membership | None = None
    document: Document = field(default_factory=lambda: dict[str, Any]())

    def update(
        self, state: State, sign: Signer, redactions: dict[str, tuple[str, ...]]
    ) -> list[Document]:
        membership = state.membership()
        head = next(reversed(state.events.values()))["seq"] if state.events else 0
        reset = membership != self.membership or head < self.sequence
        pending: list[Document] = []
        for event in reversed(state.events.values()):
            if not reset and event["seq"] <= self.sequence:
                break
            pending.append(event)
        additions = projection(state, list(reversed(pending)), self.viewer, sign, redactions)
        if reset:
            self.document = additions
            ops = [{"op": "replace", "path": "", "value": deepcopy(additions)}]
        else:
            ops = [
                {"op": "add", "path": f"/events/{key}", "value": deepcopy(value)}
                for key, value in additions["events"].items()
            ]
            self.document["events"].update(additions["events"])
        self.sequence, self.membership = head, membership
        return ops


def derive_scope(state: State, sources: list[Document]) -> Document:
    return resolve_narrowest(
        [
            ScopeSource(
                Scope.model_validate(e["scope"]),
                e["on_behalf_of"],
                projected=e.get("projected", False),
            )
            for e in sources
        ],
        state.membership(),
    ).to_wire()


def remove_path(value: Any, parts: list[str]) -> None:
    if not parts:
        return
    if isinstance(value, list):
        items = cast(list[Any], value)
        for item in items:
            remove_path(item, parts)
    elif isinstance(value, dict):
        mapping = cast(Document, value)
        if len(parts) == 1:
            mapping.pop(parts[0], None)
        elif parts[0] in mapping:
            remove_path(mapping[parts[0]], parts[1:])


def delivery(
    state: State, event: Document, viewer: str, sign: Signer, extra_redact: tuple[str, ...] = ()
) -> Document | None:
    privileged = viewer in {"host", "steward"}
    paths = [] if privileged else sorted(set(event["scope"].get("redact", [])) | set(extra_redact))
    own_plan = not privileged and event["type"] == "coalition.propose"
    own_commit = (
        not privileged and event["type"] == "coalition.commit" and viewer == event["on_behalf_of"]
    )
    form = delivery_form(
        in_scope=privileged or state.visible(event, viewer),
        redacted=bool(paths),
        viewer_specific=own_plan or own_commit,
    )
    if form == "receipt_only":
        return None
    if form == "original":
        return deepcopy(event)
    body = deepcopy(event["payload"])
    if own_commit:
        body["revision"] = 1 if body["status"] == "pending" else body["revision"] + 1
    if own_plan:
        for plan in body["plans"]:
            plan["assignments"] = [a for a in plan["assignments"] if a["assignee"] == viewer]
    for path in paths:
        remove_path(body, path.split(".")[1:])
    projected = {
        "source": {
            **{k: event[k] for k in ("event_id", "seq", "type", "on_behalf_of", "prev_hash")},
            "hash": prev_hash(event),
        },
        "payload": body,
    }
    if paths:
        projected["redacted"] = paths
    return sign("projection", projected, {"audience": "participants", "participants": [viewer]})


def projection(
    state: State,
    events: list[Document],
    viewer: str,
    sign: Signer,
    redactions: dict[str, tuple[str, ...]] | None = None,
) -> Document:
    # Do not serialize shared State then attempt to remove secrets from it.
    visible: Document = {}
    for event in events:
        item = delivery(state, event, viewer, sign, (redactions or {}).get(event["event_id"], ()))
        if item is not None:
            body = item["payload"]
            visible[event["event_id"]] = {
                "type": event["type"],
                "seq": event["seq"],
                "on_behalf_of": event["on_behalf_of"],
                "payload": body["payload"] if item["type"] == "coalition.projection" else body,
            }
    return {"coalition_id": state.coalition_id, "viewer": viewer, "events": visible}


def patch(previous: Document, current: Document) -> list[Document]:
    """A root replacement is a valid atomic RFC 6902 patch, including removals."""
    return (
        [] if previous == current else [{"op": "replace", "path": "", "value": deepcopy(current)}]
    )
