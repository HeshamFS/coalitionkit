# SPDX-License-Identifier: Apache-2.0
"""How a Coalition envelope rides inside an A2A message (spec: Binding to A2A)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, cast

from a2a.helpers.proto_helpers import new_data_part
from a2a.types import Message, Part
from google.protobuf.json_format import MessageToDict

#: The extension URI; the A2A-Extensions header must carry it to activate Coalition data.
EXTENSION_URI = "https://coalitionkit.dev/ext/coalition/v0"
#: Media type of a Part whose ``data`` is an envelope.
ENVELOPE_MEDIA_TYPE = "application/vnd.coalitionkit.envelope+json"
#: Largest integer JCS carries exactly.
_MAX_SAFE = 2**53 - 1


def restore_ints(value: Any) -> Any:
    """Turn whole floats back into ints.

    A2A data parts are ``google.protobuf.Value``, which stores every number as a double, so the
    envelope's ``seq`` or a payload's ``minutes`` comes back as ``7.0``. The contracts' models
    are strict about integers; JCS prints 7.0 as 7, so signatures are unaffected either way.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        if value.is_integer() and abs(value) <= _MAX_SAFE:
            return int(value)
        return value
    if isinstance(value, dict):
        return {k: restore_ints(v) for k, v in cast("dict[str, Any]", value).items()}
    if isinstance(value, list):
        return [restore_ints(v) for v in cast("list[Any]", value)]
    return value


def envelope_part(envelope: dict[str, Any]) -> Part:
    """A data Part carrying one envelope."""
    return new_data_part(envelope, media_type=ENVELOPE_MEDIA_TYPE)


def envelope_parts(parts: Iterable[Part]) -> list[dict[str, Any]]:
    """The envelopes in a message's parts, in order. Other parts are ignored."""
    found: list[dict[str, Any]] = []
    for part in parts:
        if part.media_type != ENVELOPE_MEDIA_TYPE or not part.HasField("data"):
            continue
        data: Any = restore_ints(MessageToDict(part.data))
        if isinstance(data, dict):
            found.append(cast("dict[str, Any]", data))
    return found


def message_envelopes(message: Message) -> list[dict[str, Any]]:
    return envelope_parts(message.parts)
