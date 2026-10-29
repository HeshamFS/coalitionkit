# SPDX-License-Identifier: Apache-2.0
"""What every framework brain shares: the tools it may call, its usage record and the prompts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

MAX_TOKENS = 2000
REASONING_EFFORT = "minimal"

SYSTEM_PROMPT = (
    "You are the software agent of one member of a multi-party Coalition. Act only through the "
    "tools you are given. Use exactly the numbers and identifiers in the FACTS block; never "
    "invent them. Call one tool at a time, read each result, and when every step is done reply "
    "with the single word: done. If a tool result starts with 'refused', do not retry the same "
    "call; stop and reply with what happened."
)


@dataclass(frozen=True)
class ModelUse:
    """Tokens of one model call, as the provider reported them."""

    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int = 0
    reasoning_tokens: int = 0


@dataclass
class BrainResult:
    text: str
    uses: list[ModelUse] = field(default_factory=lambda: [])


class Toolbox(Protocol):
    """The three things a model may do for its member. Each returns text the model reads."""

    async def make_offer(self, need_id: str, minutes: int, money: int, effort: str) -> str: ...

    async def commit_to_task(self, task_id: str) -> str: ...

    async def report_done(self, task_id: str, evidence_ref: str) -> str: ...


class Brain(Protocol):
    framework: str
    model: str

    async def run(self, instruction: str, tools: Toolbox) -> BrainResult: ...


def offers_instruction(member: str, tasks: list[dict[str, Any]]) -> str:
    facts = {"turn": "offers", "member": member, "tasks": tasks}
    return (
        f"You speak for member {member}. The Coalition has published tasks. Your owner's price "
        "sheet below lists the tasks you can do and the terms you offer. For each task in FACTS, "
        "call make_offer with need_id, minutes, money and effort exactly as listed.\n"
        f"FACTS: {json.dumps(facts, sort_keys=True)}"
    )


def work_instruction(member: str, tasks: list[dict[str, Any]]) -> str:
    facts = {"turn": "work", "member": member, "tasks": tasks}
    return (
        f"You speak for member {member}. The plan was decided and these tasks are assigned to "
        "you. For each task in FACTS: first call commit_to_task with its task_id and wait for "
        "the result. Only when the result starts with 'approved', do the neutral work and call "
        "report_done with the same task_id and evidence_ref 'result-' followed by the label.\n"
        f"FACTS: {json.dumps(facts, sort_keys=True)}"
    )


type Call = tuple[str, dict[str, Any]]
type Seen = tuple[str, dict[str, Any], str]


def scripted_next(instruction: str, seen: list[Seen]) -> list[Call]:
    """The next tool calls a well-behaved model makes; [] means it is finished.

    A pure function of the instruction's FACTS block and the tool results so far, so a scripted
    model in every framework behaves the same.
    """
    facts: dict[str, Any] = json.loads(instruction.rsplit("\nFACTS: ", 1)[1].splitlines()[0])
    if facts["turn"] == "offers":
        offered = {args["need_id"] for name, args, _ in seen if name == "make_offer"}
        for task in facts["tasks"]:
            if task["need_id"] not in offered:
                keys = ("minutes", "money", "effort")
                return [("make_offer", {"need_id": task["need_id"]} | {k: task[k] for k in keys})]
        return []
    for task in facts["tasks"]:
        committed = [
            r for n, a, r in seen if n == "commit_to_task" and a["task_id"] == task["task_id"]
        ]
        reported = [a for n, a, _ in seen if n == "report_done" and a["task_id"] == task["task_id"]]
        if not committed:
            return [("commit_to_task", {"task_id": task["task_id"]})]
        if not committed[0].startswith("approved"):
            return []
        if not reported:
            evidence = f"result-{task['label']}"
            return [("report_done", {"task_id": task["task_id"], "evidence_ref": evidence})]
    return []
