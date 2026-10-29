# SPDX-License-Identifier: Apache-2.0
"""A member brain on LangGraph: a two-node graph (model, tools) looping until no tool call.

The chat model is any LangChain chat model that supports bind_tools: ChatOpenAI on the Meta API
in a live run, a scripted model in CI.
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from members.kit.brain import SYSTEM_PROMPT, BrainResult, ModelUse, Toolbox, UseSink

RECURSION_LIMIT = 30


def meta_chat_model(
    api_key: str, base_url: str, model: str, max_tokens: int, effort: str
) -> BaseChatModel:
    """ChatOpenAI on an OpenAI-compatible endpoint (the Meta API)."""
    import httpx
    from langchain_openai import ChatOpenAI
    from pydantic import SecretStr

    return ChatOpenAI(
        model=model,
        api_key=SecretStr(api_key),
        base_url=base_url,
        max_completion_tokens=max_tokens,
        reasoning_effort=effort,
        max_retries=2,
        timeout=120,
        # langchain-openai shares one cached async HTTP client per process; it binds to the first
        # event loop that uses it, so a second run in the same process dies with "Event loop is
        # closed". An own client per model avoids that.
        http_async_client=httpx.AsyncClient(timeout=120),
    )


def _tools(box: Toolbox) -> list[StructuredTool]:
    async def make_offer(need_id: str, minutes: int, money: int, effort: str) -> str:
        """Offer to do one published task. effort is one of low, medium, high."""
        return await box.make_offer(need_id, minutes, money, effort)

    async def commit_to_task(task_id: str) -> str:
        """Commit to an assigned task; returns 'approved: ...' once your owner approved it."""
        return await box.commit_to_task(task_id)

    async def report_done(task_id: str, evidence_ref: str) -> str:
        """Report an approved task as done, with a short evidence reference."""
        return await box.report_done(task_id, evidence_ref)

    return [
        StructuredTool.from_function(coroutine=fn, name=fn.__name__, description=fn.__doc__ or "")
        for fn in (make_offer, commit_to_task, report_done)
    ]


class LangGraphBrain:
    framework = "langgraph"

    def __init__(self, chat: BaseChatModel, model_name: str) -> None:
        self.chat = chat
        self.model = model_name

    async def run(self, instruction: str, tools: Toolbox, on_use: UseSink) -> BrainResult:
        listed = _tools(tools)
        bound = self.chat.bind_tools(listed)

        async def call_model(state: MessagesState) -> dict[str, list[BaseMessage]]:
            reply = await bound.ainvoke(state["messages"])
            meta: Any = getattr(reply, "usage_metadata", None)
            if meta:
                details: dict[str, int] = meta.get("output_token_details") or {}
                cached: dict[str, int] = meta.get("input_token_details") or {}
                on_use(
                    ModelUse(
                        meta.get("input_tokens", 0),
                        meta.get("output_tokens", 0),
                        cached.get("cache_read", 0),
                        details.get("reasoning", 0),
                    )
                )
            return {"messages": [reply]}

        def route(state: MessagesState) -> str:
            last = state["messages"][-1]
            return "tools" if isinstance(last, AIMessage) and last.tool_calls else END

        builder = StateGraph(MessagesState)
        builder.add_node("model", call_model)
        builder.add_node("tools", ToolNode(listed))
        builder.add_edge(START, "model")
        builder.add_conditional_edges("model", route, ["tools", END])
        builder.add_edge("tools", "model")
        graph = builder.compile()
        result = await graph.ainvoke(
            {"messages": [SystemMessage(SYSTEM_PROMPT), HumanMessage(instruction)]},
            {"recursion_limit": RECURSION_LIMIT},
        )
        last = result["messages"][-1]
        text = last.content if isinstance(last.content, str) else str(last.content)
        return BrainResult(text)
