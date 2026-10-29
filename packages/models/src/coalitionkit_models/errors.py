# SPDX-License-Identifier: Apache-2.0
"""Errors raised by the model gateway, the settings and the cost meter."""

from __future__ import annotations


class SettingsError(RuntimeError):
    """The configuration is unusable. The message names variables, never their values."""


class MissingKeyError(SettingsError):
    """A role needs an API key that is not set."""


class UnpricedModelError(LookupError):
    """The price table has no entry for the model, so its cost cannot be metered."""


class BudgetExhaustedError(RuntimeError):
    """The Coalition's model budget is spent (protocol error ``budget_exhausted``)."""

    code = "budget_exhausted"

    def __init__(self, coalition_id: str, spent: int, limit: int) -> None:
        super().__init__(f"model budget spent for {coalition_id}: {spent} of {limit} micro-USD")
        self.coalition_id = coalition_id
        self.spent = spent
        self.limit = limit


class ProviderError(RuntimeError):
    """A provider call failed for good: not retryable, or retries ran out."""

    def __init__(self, message: str, *, status: int | None = None, attempts: int = 1) -> None:
        super().__init__(message)
        self.status = status
        self.attempts = attempts


class TruncatedReply(ProviderError):
    """The reply was cut off by the completion budget before any answer text came out.

    Raised after one retry with a doubled budget also came back empty with
    ``finish_reason == "length"`` (reasoning tokens used the whole budget).
    """

    def __init__(self, budget: int, *, attempts: int = 2) -> None:
        super().__init__(
            f"reply truncated with no content at a budget of {budget} tokens", attempts=attempts
        )
        self.budget = budget


class SchemaValidationError(ProviderError):
    """The reply did not match the response schema the caller asked for."""

    def __init__(self, detail: str, text: str) -> None:
        super().__init__(f"reply does not match the response schema: {detail}")
        self.text = text


class MediaInputError(ValueError):
    """A media input is unusable (for example a WAV that is not mono 16-bit PCM)."""
