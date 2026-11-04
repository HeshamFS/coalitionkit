# SPDX-License-Identifier: Apache-2.0
"""A member run by CoalitionKit's own ModelGateway.

The gateway returns text only (no tool-call objects), so this brain speaks a small JSON
protocol: the model answers with {"calls": [{"tool": ..., "args": {...}}]} one call at a time,
the brain runs the call and shows the result, until the model answers with no calls.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from coalitionkit_models import ChatMessage, ModelGateway, Route
from coalitionkit_models.gateway import RawCompletion

from .brain import (
    MAX_TOKENS,
    REASONING_EFFORT,
    SYSTEM_PROMPT,
    BrainResult,
    ModelUse,
    Seen,
    Toolbox,
    UseSink,
    scripted_next,
)

MAX_ROUNDS = 8
TOOL_NAMES = ("make_offer", "commit_to_task", "report_done")
FORMAT_PROMPT = (
    "You have no tool-calling API. Answer with one JSON object only: "
    '{"calls": [{"tool": "<name>", "args": {...}}]} with at most one call per answer, using the '
    "tools make_offer(need_id, minutes, money, effort), commit_to_task(task_id) and "
    "report_done(task_id, evidence_ref). Keep answering with the next call until every task in "
    'FACTS has been handled; only then answer {"calls": []}.'
)
RESPONSE_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "member_calls",
        "strict": False,
        "schema": {
            "type": "object",
            "properties": {
                "calls": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool": {"type": "string", "enum": list(TOOL_NAMES)},
                            "args": {"type": "object"},
                        },
                        "required": ["tool", "args"],
                    },
                }
            },
            "required": ["calls"],
        },
    },
}
NEXT_HINT = (
    "Now give the next call for a step in FACTS that has no successful result yet, "
    'or {"calls": []} if every step in FACTS is done.'
)
_RESULT = re.compile(r"^RESULT (\w+) (\{.*?\}): (.*)$", re.M)


class HostedBrain:
    framework = "coalitionkit-gateway"

    def __init__(self, gateway: ModelGateway, coalition_id: str, participant: str) -> None:
        self._gateway = gateway
        self._coalition_id = coalition_id
        self._participant = participant
        self.model = gateway.settings.route("hosted_agent").model

    async def run(self, instruction: str, tools: Toolbox, on_use: UseSink) -> BrainResult:
        messages: list[ChatMessage] = [
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n{FORMAT_PROMPT}"},
            {"role": "user", "content": instruction},
        ]
        text = ""
        for _ in range(MAX_ROUNDS):
            done = await self._gateway.complete(
                "hosted_agent",
                messages,
                coalition_id=self._coalition_id,
                participant=self._participant,
                max_tokens=MAX_TOKENS,
                reasoning_effort=REASONING_EFFORT,
                response_format=RESPONSE_FORMAT,
            )
            usage = done.usage
            on_use(ModelUse(usage.prompt_tokens, usage.completion_tokens, usage.cached_tokens))
            text = done.text
            calls = _parse(done.text)
            if not calls:
                break
            results: list[str] = []
            for name, args in calls:
                result = await _run_tool(tools, name, args)
                results.append(f"RESULT {name} {json.dumps(args, sort_keys=True)}: {result}")
            messages.append({"role": "assistant", "content": done.text})
            results.append(NEXT_HINT)
            messages.append({"role": "user", "content": "\n".join(results)})
        return BrainResult(text)


def _parse(text: str) -> list[tuple[str, dict[str, Any]]]:
    try:
        data: Any = json.loads(text)
        return [(c["tool"], dict(c["args"])) for c in data["calls"]]
    except ValueError, KeyError, TypeError:
        return []


async def _run_tool(tools: Toolbox, name: str, args: dict[str, Any]) -> str:
    if name not in TOOL_NAMES:
        return f"refused: unknown tool {name}"
    try:
        return await getattr(tools, name)(**args)
    except TypeError as exc:
        return f"refused: bad arguments ({exc})"


class PolicyTransport:
    """A scripted gateway transport: answers the way a well-behaved model would, no network."""

    def __init__(self) -> None:
        self.calls = 0

    async def create(
        self, route: Route, messages: Sequence[ChatMessage], opts: Mapping[str, Any]
    ) -> RawCompletion:
        from coalitionkit_models import Usage

        self.calls += 1
        instruction = next(
            m["content"] for m in messages if m["role"] == "user" and isinstance(m["content"], str)
        )
        seen: list[Seen] = []
        for message in messages:
            if message["role"] != "user" or not isinstance(message["content"], str):
                continue
            for found in _RESULT.finditer(message["content"]):
                seen.append((found.group(1), json.loads(found.group(2)), found.group(3)))
        nxt = scripted_next(instruction, seen)
        payload = {"calls": [{"tool": name, "args": args} for name, args in nxt[:1]]}
        return RawCompletion(json.dumps(payload), Usage(150, 30))
