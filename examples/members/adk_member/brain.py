# SPDX-License-Identifier: Apache-2.0
"""A member brain on Google ADK: an ``LlmAgent`` with three function tools.

ADK builds its tool schemas from the function signatures and docstrings, and it needs real
annotation objects, so this module does not use ``from __future__ import annotations``.
The model is any ADK ``BaseLlm``: ``OpenAILlm`` pointed at the Meta API in a live run, a
scripted model in CI.
"""

import itertools

from google.adk.agents import LlmAgent
from google.adk.agents.run_config import RunConfig
from google.adk.apps import App
from google.adk.models.base_llm import BaseLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from members.kit.brain import SYSTEM_PROMPT, BrainResult, ModelUse, Toolbox, UseSink

APP_NAME = "coalition-member"
MAX_LLM_CALLS = 14


def meta_model(api_key: str, base_url: str, model: str, max_tokens: int):
    """``OpenAILlm`` on an OpenAI-compatible endpoint (the Meta API), no LiteLLM involved."""
    from google.adk.integrations.openai import OpenAILlm

    return OpenAILlm(model=model, api_key=api_key, base_url=base_url, max_tokens=max_tokens)


class AdkBrain:
    framework = "google-adk"

    def __init__(self, model: BaseLlm, effort: str | None = None) -> None:
        self.llm = model
        self.model = model.model
        self._effort = effort
        self._counter = itertools.count(1)
        self._sessions = InMemorySessionService()

    def _config(self) -> types.GenerateContentConfig | None:
        if self._effort is None:
            return None
        from google.adk.integrations.openai import OpenAIGenerateContentConfig

        return OpenAIGenerateContentConfig(effort=self._effort)  # type: ignore[arg-type]

    async def run(self, instruction: str, tools: Toolbox, on_use: UseSink) -> BrainResult:
        async def make_offer(need_id: str, minutes: int, money: int, effort: str) -> str:
            """Offer to do one published task. effort is one of low, medium, high."""
            return await tools.make_offer(need_id, minutes, money, effort)

        async def commit_to_task(task_id: str) -> str:
            """Commit to an assigned task; returns 'approved: ...' once your owner approved it."""
            return await tools.commit_to_task(task_id)

        async def report_done(task_id: str, evidence_ref: str) -> str:
            """Report an approved task as done, with a short evidence reference."""
            return await tools.report_done(task_id, evidence_ref)

        agent = LlmAgent(
            name="member_agent",
            model=self.llm,
            instruction=SYSTEM_PROMPT,
            tools=[make_offer, commit_to_task, report_done],
            generate_content_config=self._config(),
        )
        runner = Runner(app=App(name=APP_NAME, root_agent=agent), session_service=self._sessions)
        user = "member"
        session = await self._sessions.create_session(
            app_name=APP_NAME, user_id=user, session_id=f"turn-{next(self._counter)}"
        )
        message = types.Content(role="user", parts=[types.Part(text=instruction)])
        text = ""
        async for event in runner.run_async(
            user_id=user,
            session_id=session.id,
            new_message=message,
            run_config=RunConfig(max_llm_calls=MAX_LLM_CALLS),
        ):
            usage = event.usage_metadata
            if usage is not None and not event.partial:
                on_use(
                    ModelUse(
                        usage.prompt_token_count or 0,
                        usage.candidates_token_count or 0,
                        usage.cached_content_token_count or 0,
                        usage.thoughts_token_count or 0,
                    )
                )
            if event.content and event.content.parts and event.is_final_response():
                text = "".join(p.text or "" for p in event.content.parts)
        await runner.close()
        return BrainResult(text)


__all__ = ["AdkBrain", "meta_model"]
