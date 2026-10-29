# SPDX-License-Identifier: Apache-2.0
"""A scripted LangChain chat model: it makes the tool calls a well-behaved model would."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from members.kit.brain import Seen, scripted_next


def _history(messages: Sequence[BaseMessage]) -> tuple[str, list[Seen]]:
    instruction = ""
    calls: dict[str, tuple[str, dict[str, Any]]] = {}
    seen: list[Seen] = []
    for message in messages:
        if isinstance(message, HumanMessage) and not instruction:
            instruction = str(message.content)
        elif isinstance(message, AIMessage):
            for call in message.tool_calls:
                calls[call["id"] or ""] = (call["name"], dict(call["args"]))
        elif isinstance(message, ToolMessage):
            name, args = calls[message.tool_call_id]
            seen.append((name, args, str(message.content)))
    return instruction, seen


class ScriptedChat(BaseChatModel):
    calls_made: int = 0

    @property
    def _llm_type(self) -> str:
        return "scripted-chat"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> ScriptedChat:  # type: ignore[override]
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        instruction, seen = _history(messages)
        self.calls_made += 1
        nxt = scripted_next(instruction, seen)
        if nxt:
            name, args = nxt[0]
            reply = AIMessage(
                content="", tool_calls=[{"name": name, "args": args, "id": f"call-{len(seen)}"}]
            )
        else:
            reply = AIMessage(content="done")
        reply.usage_metadata = {"input_tokens": 120, "output_tokens": 24, "total_tokens": 144}
        return ChatResult(generations=[ChatGeneration(message=reply)])
