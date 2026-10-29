# SPDX-License-Identifier: Apache-2.0
"""A neutral tree for a viewer, built only from the viewer's own projection on the host."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from coalitionkit_runtime import CoalitionHost

from ..a2ui import ROOT_ID, bound_number

Document = dict[str, Any]


def _need_card(event_id: str, event: Document) -> Document:
    body = event["payload"]
    window = body.get("window", {})
    return {
        "id": f"n-{event_id}",
        "component": "TaskCard",
        "title": str(body.get("description", "")),
        "task_id": str(body.get("need_id", event_id)),
        "status": "open",
        "window": window if isinstance(window, dict) else {},
    }


def _plan_cards(event_id: str, event: Document) -> list[Document]:
    cards: list[Document] = []
    for plan in event["payload"].get("plans", []):
        mine = [f"{a['task_id']} -> {a['assignee']}" for a in plan.get("assignments", [])]
        key = f"p-{plan['plan_id']}"
        pairs: list[Document] = [{"label": "Assigned", "value": line} for line in mine]
        pairs.append({"label": "Revision", "value": bound_number(plan["revision"], event_id)})
        cards += [
            {"id": key, "component": "Column", "children": [f"{key}-h", f"{key}-v"]},
            {"id": f"{key}-h", "component": "Heading", "text": "Plan"},
            {"id": f"{key}-v", "component": "KeyValue", "pairs": pairs},
        ]
    return cards


def _tension_card(events: Document, row: Document) -> Document | None:
    """A tension shown with the options of the viewer's own projected copy, at exactly the
    revision the consent request names. ``None`` when that copy is not in the viewer's view."""
    if row["kind"] != "tension_option":
        return None
    for event in events.values():
        body = event["payload"]
        if (
            event["type"] == "coalition.tension"
            and body.get("tension_id") == row["id"]
            and body.get("revision") == row["revision"]
        ):
            options = [
                {"id": str(o["option_id"]), "label": str(o.get("summary") or o["option_id"])}
                for o in body.get("options", [])
            ]
            return {
                "id": f"c-{row['kind']}-{row['id']}",
                "component": "TensionCard",
                "options": options,
                "deciders": [str(d) for d in body.get("deciders", [])],
                "decision_deadline": body["decision_deadline"],
                "subject": {"kind": row["kind"], "id": row["id"], "revision": row["revision"]},
            }
    return None


def host_is_open(host: CoalitionHost) -> Callable[[str, Document], bool]:
    """For ``ConfirmGate``: the subject, at exactly that revision, still waits for this person."""

    def is_open(viewer: str, subject: Document) -> bool:
        return any(row == subject for row in host.open_consents(viewer))

    return is_open


class HostTreeSource:
    """``TreeSource`` over a host: needs, plans and open consent requests as this person sees
    them. Nothing outside ``host.view(viewer)`` and ``host.open_consents(viewer)`` is read."""

    def __init__(self, host: CoalitionHost) -> None:
        self.host = host

    def tree(self, viewer: str) -> tuple[list[Document], Any]:
        events: Document = self.host.view(viewer)["events"]
        cards: list[Document] = []
        for event_id, event in sorted(events.items(), key=lambda item: item[1]["seq"]):
            if event["type"] == "coalition.need":
                cards.append(_need_card(event_id, event))
            elif event["type"] == "coalition.propose":
                cards += _plan_cards(event_id, event)
        deadline = str(self.host.state.charter.get("deadline", ""))
        for row in self.host.open_consents(viewer):
            subject = self.host.state.subject(row["kind"], row["id"])
            tension = _tension_card(events, row)
            if tension is not None:
                cards.append(tension)
                continue
            cards.append(
                {
                    "id": f"c-{row['kind']}-{row['id']}",
                    "component": "ConsentCard",
                    "summary": f"Your decision is needed on a {row['kind'].replace('_', ' ')}",
                    "consequence": "Saying yes binds you to it.",
                    "decision_deadline": subject.get("decision_deadline") or deadline,
                    "subject": {"kind": row["kind"], "id": row["id"], "revision": row["revision"]},
                }
            )
        linked = {c for card in cards for c in card.get("children", [])}
        root: Document = {
            "id": ROOT_ID,
            "component": "Column",
            "children": [c["id"] for c in cards if c["id"] not in linked],
        }
        return [root, *cards], {}
