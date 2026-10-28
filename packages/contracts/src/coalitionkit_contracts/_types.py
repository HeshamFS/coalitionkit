# SPDX-License-Identifier: Apache-2.0
"""Shared field types and the base model for every wire object."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Any
from urllib.parse import urlparse

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

#: Crockford base32, 26 characters. Identical to the pattern in the JSON Schemas.
ULID_PATTERN = r"^[0-9A-HJKMNP-TV-Z]{26}$"

#: Largest integer JCS (RFC 8785) can carry exactly: 2**53 - 1.
MAX_SAFE_INT = 2**53 - 1

_RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$",
)


def _check_rfc3339(value: str) -> str:
    if _RFC3339.fullmatch(value) is None:
        raise ValueError("not an RFC 3339 date-time")
    try:
        parsed = datetime.fromisoformat(value.upper())
    except ValueError as exc:
        raise ValueError("not an RFC 3339 date-time") from exc
    if parsed.tzinfo is None:  # pragma: no cover - the regex already requires an offset
        raise ValueError("date-time needs an offset")
    return value


def _check_uri(value: str) -> str:
    parts = urlparse(value)
    if not parts.scheme or not parts.netloc or any(c.isspace() for c in value):
        raise ValueError("not an absolute URI")
    return value


def _check_unique(value: list[str]) -> list[str]:
    if len(set(value)) != len(value):
        raise ValueError("items must be unique")
    return value


Ulid = Annotated[str, StringConstraints(pattern=ULID_PATTERN)]
Id = Annotated[str, StringConstraints(min_length=1, max_length=128)]
Text = Annotated[str, StringConstraints(min_length=1)]
Rfc3339 = Annotated[str, AfterValidator(_check_rfc3339)]
Uri = Annotated[str, AfterValidator(_check_uri)]
SafeInt = Annotated[int, Field(ge=0, le=MAX_SAFE_INT)]
PositiveInt = Annotated[int, Field(ge=1, le=MAX_SAFE_INT)]
Revision = PositiveInt
Money = SafeInt
UniqueIds = Annotated[list[Id], AfterValidator(_check_unique)]


class WireModel(BaseModel):
    """Base of every protocol object: strict, immutable, no extra fields, no nulls."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    @model_validator(mode="before")
    @classmethod
    def _reject_null(cls, data: Any) -> Any:
        # The schemas have no nullable fields, so an explicit null is invalid, not "absent".
        if isinstance(data, dict) and any(v is None for v in data.values()):  # pyright: ignore[reportUnknownVariableType]
            raise ValueError("null is not allowed; omit the field")
        return data  # pyright: ignore[reportUnknownVariableType]

    def to_wire(self) -> dict[str, Any]:
        """The JSON-ready dict, with unset optional fields left out."""
        return self.model_dump(mode="json", exclude_none=True)
