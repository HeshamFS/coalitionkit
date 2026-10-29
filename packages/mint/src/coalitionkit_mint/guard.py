# SPDX-License-Identifier: Apache-2.0
"""Bound each call, then run the Steward's deterministic policy evaluator."""

import json
import re
from typing import Any

from coalitionkit_contracts import Scope
from coalitionkit_mint.refusal import Refusal
from coalitionkit_steward.conditions import StewardContext, Subject, evaluate_all
from coalitionkit_steward.policy import Policy, When

POLICIES = (
    Policy(
        id="mint-injection",
        applies_to=["coalition.observe"],
        when=When(
            any_text_matches=[
                r"ignore.*instructions",
                r"system\s*prompt",
                r"execute\s*code",
                r"https?://",
                r"<script",
            ]
        ),
        then="block",
        explain="Instruction-like input is not a tool argument.",
    ),
)


def guard(tool: str, args: dict[str, Any]) -> None:
    if len(json.dumps(args)) > 8192:
        raise Refusal("oversized input")
    subject = Subject(
        "message",
        "mint",
        "call",
        1,
        "coalition.observe",
        "member",
        Scope(audience="host"),
        {"tool": tool, "arguments": args},
    )
    if evaluate_all(POLICIES, subject, StewardContext()):
        raise Refusal("Steward blocked input")
    if "id" in args and (
        not isinstance(args["id"], str) or not re.fullmatch(r"[a-z0-9_]{1,48}", args["id"])
    ):
        raise Refusal("invalid identifier")
