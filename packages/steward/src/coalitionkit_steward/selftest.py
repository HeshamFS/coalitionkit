# SPDX-License-Identifier: Apache-2.0
"""A known-answer self-test: the Steward refuses to start unless its core policies classify a
bundled set of examples correctly. It catches a policy file that was edited, truncated or
replaced, before it can wave a message through."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from coalitionkit_contracts import Scope

from .conditions import StewardContext, Subject, evaluate_all
from .policy import PolicySet

_ID = "01M4XRC0Z8185GR38E1W8124GK"
_COALITION = "01M4XRC000000G40R40M30E209"
_TASK_1 = "01M4XRC2A00000000000000002"
_TASK_2 = "01M4XRC2A00000000000000003"
_TASK_3 = "01M4XRC2A00000000000000004"


class SelfTestError(RuntimeError):
    """A core policy gave the wrong answer on a known example."""


@dataclass(frozen=True)
class Example:
    name: str
    type: str
    payload: dict[str, Any]
    expected_action: str
    expected_policy: str  # "default" when nothing should match
    scope: Scope = field(default_factory=lambda: Scope(audience="coalition"))
    context: StewardContext = field(default_factory=StewardContext)


def _plan(*assignees: str) -> dict[str, Any]:
    tasks = (_TASK_1, _TASK_2, _TASK_3)
    return {
        "proposal_set_id": "set-1",
        "plans": [
            {
                "plan_id": _ID,
                "revision": 1,
                "assignments": [
                    {"task_id": tasks[i], "assignee": who} for i, who in enumerate(assignees)
                ],
                "objective_scores": {},
            }
        ],
        "decision_deadline": "2026-11-05T12:00:00Z",
    }


EXAMPLES: tuple[Example, ...] = (
    Example(
        "advice-positive",
        "coalition.observe",
        {"source": "chat", "content": "You should take 200 mg every four hours."},
        "escalate",
        "no-regulated-advice",
    ),
    Example(
        "advice-negative",
        "coalition.observe",
        {"source": "chat", "content": "The room is free on Wednesday."},
        "allow",
        "default",
    ),
    Example(
        "contact-details-positive",
        "coalition.observe",
        {"source": "chat", "content": "Call me on +49 170 1234567 after six."},
        "block",
        "no-contact-details-in-room",
    ),
    Example(
        "contact-details-negative",
        "coalition.observe",
        {"source": "chat", "content": "Meet on 2026-11-05 at 10:00, about 120 minutes, 90 for me."},
        "allow",
        "default",
    ),
    Example(
        "contact-positive",
        "coalition.offer",
        {"note": "hello"},
        "block",
        "no-contact-before-consent",
        Scope(audience="participants", participants=["p9"]),
        StewardContext(consented=frozenset({"p1"})),
    ),
    Example(
        "contact-negative",
        "coalition.offer",
        {"note": "hello"},
        "allow",
        "default",
        Scope(audience="participants", participants=["p1"]),
        StewardContext(consented=frozenset({"p1"})),
    ),
    Example(
        "private-positive",
        "coalition.observe",
        {"source": "chat", "content": "call me", "contact": {"phone": "+49 000 0000"}},
        "redact",
        "no-private-field-in-outbound",
    ),
    Example(
        "private-negative",
        "coalition.observe",
        {"source": "chat", "content": "call me", "contact": {"phone": "+49 000 0000"}},
        "allow",
        "default",
        Scope(audience="host"),
    ),
    Example(
        "fairness-positive",
        "coalition.propose",
        _plan("p1", "p1", "p2"),
        "escalate",
        "fairness-cap-exceeded",
    ),
    Example("fairness-negative", "coalition.propose", _plan("p1", "p2", "p3"), "allow", "default"),
)


def run_selftest(policies: PolicySet, examples: tuple[Example, ...] = EXAMPLES) -> None:
    """Raise SelfTestError unless every example gets its expected action and policy."""
    failures: list[str] = []
    for ex in examples:
        subject = Subject("message", _COALITION, _ID, 1, ex.type, "p1", ex.scope, ex.payload)
        matches = evaluate_all(policies, subject, ex.context)
        if matches:
            top = max(matches, key=lambda m: m.policy.severity)
            got = (top.policy.then, top.policy.id)
        else:
            got = ("allow", "default")
        if got != (ex.expected_action, ex.expected_policy):
            failures.append(
                f"{ex.name}: expected {ex.expected_action}/{ex.expected_policy}, got {got}"
            )
    if failures:
        raise SelfTestError("core policy self-test failed: " + "; ".join(failures))
