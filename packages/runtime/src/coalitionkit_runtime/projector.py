# SPDX-License-Identifier: Apache-2.0
"""Viewer documents are folded exclusively from visible, redacted log deliveries."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any, cast

from coalitionkit_contracts import Scope, ScopeSource, resolve_narrowest

from .lifecycle import State
from .store import Document

Signer = Callable[[str, Document, Document], Document]


def derive_scope(state: State, sources: list[Document]) -> Document:
    return resolve_narrowest(
        [ScopeSource(Scope.model_validate(e["scope"]), e["on_behalf_of"]) for e in sources],
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
    if viewer not in {"host", "steward"} and not state.visible(event, viewer):
        return None
    if viewer in {"host", "steward"}:
        return deepcopy(event)
    paths = sorted(set(event["scope"].get("redact", [])) | set(extra_redact))
    own_plan = event["type"] == "coalition.propose"
    if not paths and not own_plan:
        return deepcopy(event)
    body = deepcopy(event["payload"])
    if own_plan:
        for plan in body["plans"]:
            plan["assignments"] = [a for a in plan["assignments"] if a["assignee"] == viewer]
    for path in paths:
        remove_path(body, path.split(".")[1:])
    projected = {
        "source": {k: event[k] for k in ("event_id", "seq", "type", "on_behalf_of")},
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
                "payload": body["payload"] if item["type"] == "coalition.projection" else body,
            }
    return {"coalition_id": state.coalition_id, "events": visible}


def patch(previous: Document, current: Document) -> list[Document]:
    """A root replacement is a valid atomic RFC 6902 patch, including removals."""
    return (
        [] if previous == current else [{"op": "replace", "path": "", "value": deepcopy(current)}]
    )
