# SPDX-License-Identifier: Apache-2.0
"""The message envelope."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import StringConstraints

from ._types import PositiveInt, Rfc3339, Ulid, Uri, WireModel
from .payloads import PAYLOAD_MODELS
from .scope import Scope

#: Fields the host sets on acceptance; they are not covered by the sender's signature.
HOST_FIELDS: tuple[str, ...] = ("seq", "ts", "prev_hash")
#: Fields removed before the signing input is canonicalised: ``sig`` plus the host fields.
UNSIGNED_FIELDS: tuple[str, ...] = ("sig", *HOST_FIELDS)


class Envelope(WireModel):
    ext_version: Literal["0.1"]
    coalition_id: Ulid
    event_id: Ulid
    type: Annotated[str, StringConstraints(pattern=r"^coalition\.[a-z_]+$")]
    sender: Uri
    on_behalf_of: str
    scope: Scope
    causation_id: Ulid | None = None
    correlation_id: Ulid | None = None
    payload: dict[str, Any]
    sig: str
    seq: PositiveInt | None = None
    ts: Rfc3339 | None = None
    prev_hash: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")] | None = None

    def parse_payload(self) -> WireModel:
        """Validate the payload against the model for this envelope's type."""
        model = PAYLOAD_MODELS.get(self.type)
        if model is None:
            raise ValueError(f"unknown message type {self.type!r}")
        return model.model_validate(self.payload)
