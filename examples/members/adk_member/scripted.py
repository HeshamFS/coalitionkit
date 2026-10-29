# SPDX-License-Identifier: Apache-2.0
"""A scripted ADK model: it makes the tool calls a well-behaved model would, with no network.

It is a real ``BaseLlm``, so ADK's agent loop, tool dispatch and session handling all run.
"""

from collections.abc import AsyncGenerator
from typing import Any

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from members.kit.brain import Seen, scripted_next


def _history(request: LlmRequest) -> tuple[str, list[Seen]]:
    instruction = ""
    calls: list[tuple[str, dict[str, Any]]] = []
    seen: list[Seen] = []
    for content in request.contents or []:
        for part in content.parts or []:
            if part.text and content.role == "user" and not instruction:
                instruction = part.text
            if part.function_call and part.function_call.name:
                calls.append((part.function_call.name, dict(part.function_call.args or {})))
            if part.function_response:
                response = part.function_response.response or {}
                name, args = calls[len(seen)]
                seen.append((name, args, str(response.get("result", response))))
    return instruction, seen


class ScriptedAdkLlm(BaseLlm):
    model: str = "scripted-adk"

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse]:
        instruction, seen = _history(llm_request)
        usage = types.GenerateContentResponseUsageMetadata(
            prompt_token_count=120, candidates_token_count=24, total_token_count=144
        )
        nxt = scripted_next(instruction, seen)
        if not nxt:
            part = types.Part(text="done")
        else:
            name, args = nxt[0]
            part = types.Part(function_call=types.FunctionCall(name=name, args=args))
        yield LlmResponse(content=types.Content(role="model", parts=[part]), usage_metadata=usage)
