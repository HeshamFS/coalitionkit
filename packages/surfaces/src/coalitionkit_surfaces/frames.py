# SPDX-License-Identifier: Apache-2.0
"""Frames on an SSE stream: AG-UI events, keep-alive comments, and JSON Patch deltas."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, cast

import jsonpatch  # pyright: ignore[reportMissingTypeStubs]
from ag_ui.core import BaseEvent
from ag_ui.encoder import EventEncoder

Document = dict[str, Any]


@dataclass(frozen=True)
class KeepAlive:
    """An SSE comment line. It carries no data and exists only to hold the connection open."""


Frame = BaseEvent | KeepAlive

_ENCODER = EventEncoder()


def encode(frame: Frame) -> str:
    """The SSE text of one frame."""
    if isinstance(frame, KeepAlive):
        return ": keep-alive\n\n"
    return _ENCODER.encode(frame)


def json_patch(previous: Document, current: Document) -> list[Document]:
    """An RFC 6902 patch that turns ``previous`` into ``current`` (empty when equal)."""
    if previous == current:
        return []
    made: Any = jsonpatch.make_patch(previous, current)  # pyright: ignore[reportUnknownMemberType]
    return cast(list[Document], made.patch)


def apply_patch(document: Document, ops: list[Document]) -> Document:
    """Apply a patch to a copy of ``document``; used by renderers' tests and the property test."""
    applied = jsonpatch.apply_patch(deepcopy(document), ops)  # pyright: ignore
    return cast(Document, applied)
