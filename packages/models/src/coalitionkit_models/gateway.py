# SPDX-License-Identifier: Apache-2.0
"""The one model gateway. Every model call in the system goes through ``ModelGateway.complete``.

It speaks the OpenAI chat-completions dialect through the ``openai`` SDK, with a ``base_url``
per role (see ``Settings.route``). It retries transient failures with exponential backoff and
full jitter, never retries a client error (4xx other than 408, 409 and 429), limits each role's
request rate, checks the Coalition's budget before a call and meters the usage after it.
Reasoning models are handled here: a per-role effort and completion budget, and one retry with
a doubled budget when reasoning ate the whole budget.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Protocol, TypedDict

import httpx2
import openai
from openai import AsyncOpenAI
from pydantic import BaseModel

from ._resilience import RETRYABLE_STATUS, Retrier
from .errors import TruncatedReply
from .meter import SYSTEM_PARTICIPANT, CostMeter
from .settings import Role, Route, Settings
from .structured import ToolCall, parse_tool_calls, response_format, validate_reply


class ChatMessage(TypedDict):
    role: str
    content: str | list[dict[str, Any]]


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int = 0
    reasoning_tokens: int = 0  # already inside completion_tokens


@dataclass(frozen=True)
class RawCompletion:
    text: str
    usage: Usage
    finish_reason: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()


@dataclass(frozen=True)
class Completion:
    role: Role
    model: str
    text: str
    usage: Usage
    cost_micro_usd: int
    tool_calls: tuple[ToolCall, ...] = ()
    finish_reason: str | None = None
    parsed: BaseModel | None = None


class Transport(Protocol):
    """Sends one request to one route. The retry policy lives in the gateway, not here."""

    async def create(
        self, route: Route, messages: Sequence[ChatMessage], opts: Mapping[str, Any]
    ) -> RawCompletion: ...


class Completer(Protocol):
    """What callers (the Steward, the Gardener) need from the gateway."""

    async def complete(
        self,
        role: Role,
        messages: Sequence[ChatMessage],
        *,
        coalition_id: str | None = None,
        participant: str = SYSTEM_PARTICIPANT,
        **opts: Any,
    ) -> Completion: ...


class OpenAITransport:
    """The real transport: the OpenAI SDK with its own retries switched off."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._clients: dict[tuple[str, str], AsyncOpenAI] = {}

    def _client(self, route: Route) -> AsyncOpenAI:
        key = (route.base_url, route.key_name)
        client = self._clients.get(key)
        if client is None:
            client = AsyncOpenAI(
                api_key=self._settings.api_key(route),
                base_url=route.base_url,
                max_retries=0,
                timeout=self._settings.request_timeout_s,
            )
            self._clients[key] = client
        return client

    async def aclose(self) -> None:
        for client in self._clients.values():
            await client.close()
        self._clients.clear()

    async def create(
        self, route: Route, messages: Sequence[ChatMessage], opts: Mapping[str, Any]
    ) -> RawCompletion:
        create: Any = self._client(route).chat.completions.create
        response: Any = await create(model=route.model, messages=list(messages), **opts)
        choice = response.choices[0] if response.choices else None
        text = (choice.message.content if choice else None) or ""
        finish = getattr(choice, "finish_reason", None)
        calls = parse_tool_calls(getattr(choice.message, "tool_calls", None)) if choice else ()
        usage = response.usage
        if usage is None:
            return RawCompletion(text, Usage(0, 0, 0), finish, calls)
        details = getattr(usage, "prompt_tokens_details", None)
        cached = int(getattr(details, "cached_tokens", 0) or 0)
        out_details = getattr(usage, "completion_tokens_details", None)
        reasoning = int(getattr(out_details, "reasoning_tokens", 0) or 0)
        return RawCompletion(
            text,
            Usage(usage.prompt_tokens, usage.completion_tokens, cached, reasoning),
            finish,
            calls,
        )


@dataclass
class ScriptedResponse:
    text: str
    prompt_tokens: int = 10
    completion_tokens: int = 10
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    finish_reason: str | None = "stop"
    tool_calls: tuple[ToolCall, ...] = ()


@dataclass
class FakeModel:
    """A scripted transport for tests: replays responses (or raises exceptions) in order."""

    script: list[ScriptedResponse | BaseException]
    calls: list[tuple[Role, list[ChatMessage], dict[str, Any]]] = field(default_factory=lambda: [])

    async def create(
        self, route: Route, messages: Sequence[ChatMessage], opts: Mapping[str, Any]
    ) -> RawCompletion:
        self.calls.append((route.role, list(messages), dict(opts)))
        if not self.script:
            raise AssertionError("FakeModel script is empty")
        item = self.script.pop(0)
        if isinstance(item, BaseException):
            raise item
        usage = Usage(
            item.prompt_tokens, item.completion_tokens, item.cached_tokens, item.reasoning_tokens
        )
        return RawCompletion(item.text, usage, item.finish_reason, item.tool_calls)


def status_error(status: int) -> openai.APIStatusError:
    """An SDK status error for tests (``httpx`` request and response are synthetic)."""
    request = httpx2.Request("POST", "https://fake.invalid/v1/chat/completions")
    response = httpx2.Response(status, request=request, json={"error": {"message": "fake"}})
    return openai.APIStatusError("fake", response=response, body=None)


def connection_error() -> openai.APIConnectionError:
    return openai.APIConnectionError(
        request=httpx2.Request("POST", "https://fake.invalid/v1/chat/completions")
    )


def is_transient(exc: BaseException) -> bool:
    if isinstance(exc, openai.APIConnectionError):  # includes timeouts
        return True
    if isinstance(exc, openai.APIStatusError):
        return exc.status_code in RETRYABLE_STATUS or exc.status_code >= 500
    return False


def _classify(exc: Exception) -> tuple[bool, int | None]:
    status = exc.status_code if isinstance(exc, openai.APIStatusError) else None
    return is_transient(exc), status


def _truncated(raw: RawCompletion) -> bool:
    return not raw.text.strip() and not raw.tool_calls and raw.finish_reason == "length"


class ModelGateway:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: Transport | None = None,
        meter: CostMeter | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
        rng: random.Random | None = None,
        base_delay_s: float = 0.5,
        max_delay_s: float = 8.0,
    ) -> None:
        self.settings = settings
        self.meter = meter
        self._transport: Transport = transport or OpenAITransport(settings)
        self._retrier = Retrier(
            settings.max_attempts,
            sleep=sleep,
            clock=clock,
            rng=rng,
            base_delay_s=base_delay_s,
            max_delay_s=max_delay_s,
        )

    async def aclose(self) -> None:
        """Close the transport's connections (a no-op for transports that hold none)."""
        closer = getattr(self._transport, "aclose", None)
        if closer is not None:
            await closer()

    async def complete(
        self,
        role: Role,
        messages: Sequence[ChatMessage],
        *,
        coalition_id: str | None = None,
        participant: str = SYSTEM_PARTICIPANT,
        response_schema: type[BaseModel] | None = None,
        **opts: Any,
    ) -> Completion:
        """One chat completion for a role.

        The completion budget (the role setting, or ``max_completion_tokens``) covers reasoning
        plus the answer; ``reasoning_effort`` defaults per role on Meta routes. An empty reply
        cut by ``finish_reason == "length"`` is retried once with double the budget, then raises
        TruncatedReply. ``response_schema`` (a pydantic model) asks for a strict JSON reply and
        validates it (SchemaValidationError); ``tools=`` passes OpenAI-style tools and the calls
        come back typed in ``Completion.tool_calls``.

        Raises BudgetExhaustedError before any request when the Coalition's budget is spent,
        and ProviderError when the call fails for good.
        """
        route = self.settings.route(role)
        budget = self._budget(role, opts)
        base = self._base_opts(role, route, opts, response_schema)
        for tries in (1, 2):
            if self.meter is not None and coalition_id is not None:
                self.meter.check(coalition_id)  # before every billed request, retry included
            request = {**base, "max_completion_tokens": budget}
            raw = await self._call(role, route, messages, request)
            done = self._finish(role, route, raw, coalition_id, participant)
            if not _truncated(raw):
                return self._typed(done, response_schema)
            if tries == 2:
                raise TruncatedReply(budget, attempts=2)
            budget *= 2
        raise AssertionError("unreachable")  # pragma: no cover

    def _budget(self, role: Role, opts: dict[str, Any]) -> int:
        opts.pop("max_tokens", None)  # an answer-only cap: the role budget replaces it
        given = opts.pop("max_completion_tokens", None)
        return int(given) if given else self.settings.completion_budget.get(role, 4000)

    def _base_opts(
        self,
        role: Role,
        route: Route,
        opts: dict[str, Any],
        response_schema: type[BaseModel] | None,
    ) -> dict[str, Any]:
        base = dict(opts)
        if route.key_name == "meta" and "reasoning_effort" not in base:
            effort = self.settings.reasoning_effort.get(role)
            if effort is not None:
                base["reasoning_effort"] = effort
        if response_schema is not None:
            base["response_format"] = response_format(response_schema)
        return base

    async def _call(
        self, role: Role, route: Route, messages: Sequence[ChatMessage], opts: Mapping[str, Any]
    ) -> RawCompletion:
        return await self._retrier.run(
            role,
            self.settings.rate_limit_per_minute.get(role, 60),
            lambda: self._transport.create(route, messages, opts),
            _classify,
        )

    @staticmethod
    def _typed(done: Completion, schema: type[BaseModel] | None) -> Completion:
        if schema is None or done.tool_calls:
            return done
        return replace(done, parsed=validate_reply(schema, done.text))

    def _finish(
        self, role: Role, route: Route, raw: RawCompletion, coalition_id: str | None, who: str
    ) -> Completion:
        cost = 0
        if self.meter is not None:
            record = self.meter.record(
                coalition_id or "_unattributed",
                who,
                route.model,
                prompt_tokens=raw.usage.prompt_tokens,
                completion_tokens=raw.usage.completion_tokens,
                cached_tokens=raw.usage.cached_tokens,
                reasoning_tokens=raw.usage.reasoning_tokens,
            )
            cost = record.cost_micro_usd
        return Completion(
            role,
            route.model,
            raw.text,
            raw.usage,
            cost,
            tool_calls=raw.tool_calls,
            finish_reason=raw.finish_reason,
        )
