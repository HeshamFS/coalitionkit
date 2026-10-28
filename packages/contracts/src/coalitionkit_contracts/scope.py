# SPDX-License-Identifier: Apache-2.0
"""Visibility scope: who may see an envelope."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import AfterValidator, model_validator

from ._types import UniqueIds, WireModel

Audience = Literal["coalition", "roles", "participants", "self", "host"]


def _check_redact(value: list[str]) -> list[str]:
    if not all(path.startswith("payload.") for path in value):
        raise ValueError("redact paths start with 'payload.'")
    return value


class Scope(WireModel):
    audience: Audience
    participants: UniqueIds | None = None
    roles: UniqueIds | None = None
    redact: Annotated[list[str], AfterValidator(_check_redact)] | None = None

    @model_validator(mode="after")
    def _audience_needs_list(self) -> Self:
        if self.audience == "participants" and not self.participants:
            raise ValueError("audience 'participants' needs a non-empty participants list")
        if self.audience == "roles" and not self.roles:
            raise ValueError("audience 'roles' needs a non-empty roles list")
        return self


__all__ = ["Audience", "Scope"]
