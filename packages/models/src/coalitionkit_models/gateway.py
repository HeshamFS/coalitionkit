# SPDX-License-Identifier: Apache-2.0
"""The one model gateway. Every model call in the system goes through ``ModelGateway.complete``.

It speaks the OpenAI chat-completions dialect through the ``openai`` SDK, with a ``base_url``
per role (see ``Settings.route``). It retries transient failures with exponential backoff and
full jitter, never retries a client error (4xx other than 408, 409 and 429), limits each role's
request rate, checks the Coalition's budget before a call and meters the usage after it.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections import deque
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, TypedDict

import httpx2
import openai
from openai import AsyncOpenAI

from .errors import ProviderError
from .meter import SYSTEM_PARTICIPANT, CostMeter
from .settings import Role, Route, Settings

RETRYABLE_STATUS = frozenset({408, 409, 429})


class ChatMessage(TypedDict):
    role: str
    content: str


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int = 0


@dataclass(frozen=True)
class RawCompletion:
    text: str
    usage: Usage


@dataclass(frozen=True)
class Completion:
    role: Role
    model: str
    text: str
    usage: Usage
    cost_micro_usd: int


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

    async def create(
        self, route: Route, messages: Sequence[ChatMessage], opts: Mapping[str, Any]
    ) -> RawCompletion:
        create: Any = self._client(route).chat.completions.create
        response: Any = await create(model=route.model, messages=list(messages), **opts)
        choice = response.choices[0] if response.choices else None
        text = (choice.message.content if choice else None) or ""
        usage = response.usage
        details = getattr(usage, "prompt_tokens_details", None) if usage else None
        cached = int(getattr(details, "cached_tokens", 0) or 0)
        if usage is None:
            return RawCompletion(text, Usage(0, 0, 0))
        return RawCompletion(text, Usage(usage.prompt_tokens, usage.completion_tokens, cached))


@dataclass
class ScriptedResponse:
    text: str
    prompt_tokens: int = 10
    completion_tokens: int = 10
    cached_tokens: int = 0


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
        return RawCompletion(
            item.text, Usage(item.prompt_tokens, item.completion_tokens, item.cached_tokens)
        )


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


class RateLimiter:
    """At most ``per_minute`` requests in any 60 second window; waits instead of failing."""

    def __init__(
        self,
        per_minute: int,
        clock: Callable[[], float],
        sleep: Callable[[float], Awaitable[None]],
    ) -> None:
        self._per_minute = per_minute
        self._clock = clock
        self._sleep = sleep
        self._stamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = self._clock()
                while self._stamps and now - self._stamps[0] >= 60.0:
                    self._stamps.popleft()
                if len(self._stamps) < self._per_minute:
                    self._stamps.append(now)
                    return
                await self._sleep(60.0 - (now - self._stamps[0]))


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
        self._sleep = sleep
        self._clock = clock
        self._rng = rng or random.Random()
        self._base = base_delay_s
        self._max = max_delay_s
        self._limiters: dict[Role, RateLimiter] = {}

    def _limiter(self, role: Role) -> RateLimiter:
        limiter = self._limiters.get(role)
        if limiter is None:
            per_minute = self.settings.rate_limit_per_minute.get(role, 60)
            limiter = RateLimiter(per_minute, self._clock, self._sleep)
            self._limiters[role] = limiter
        return limiter

    def _backoff(self, attempt: int) -> float:
        """Full jitter: a random delay up to the capped exponential."""
        return self._rng.uniform(0.0, min(self._max, self._base * 2**attempt))

    async def complete(
        self,
        role: Role,
        messages: Sequence[ChatMessage],
        *,
        coalition_id: str | None = None,
        participant: str = SYSTEM_PARTICIPANT,
        **opts: Any,
    ) -> Completion:
        """One chat completion for a role.

        Raises BudgetExhaustedError before any request when the Coalition's budget is spent,
        and ProviderError when the call fails for good.
        """
        route = self.settings.route(role)
        if self.meter is not None and coalition_id is not None:
            self.meter.check(coalition_id)
        attempts = self.settings.max_attempts
        for attempt in range(attempts):
            await self._limiter(role).acquire()
            try:
                raw = await self._transport.create(route, messages, opts)
            except Exception as exc:
                if not is_transient(exc):
                    raise _provider_error(exc, attempt + 1) from exc
                if attempt + 1 >= attempts:
                    raise _provider_error(exc, attempt + 1) from exc
                await self._sleep(self._backoff(attempt))
                continue
            return self._finish(role, route, raw, coalition_id, participant)
        raise AssertionError("unreachable")  # pragma: no cover

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
            )
            cost = record.cost_micro_usd
        return Completion(role, route.model, raw.text, raw.usage, cost)


def _provider_error(exc: Exception, attempts: int) -> ProviderError:
    status = exc.status_code if isinstance(exc, openai.APIStatusError) else None
    return ProviderError(
        f"{type(exc).__name__} after {attempts} attempt(s)", status=status, attempts=attempts
    )
