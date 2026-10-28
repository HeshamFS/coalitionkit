# SPDX-License-Identifier: Apache-2.0
"""Strict JSON-schema response formats and typed tool calls."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from .errors import SchemaValidationError


@dataclass(frozen=True)
class ToolCall:
    """One tool call the model asked for. ``arguments`` is the parsed JSON object."""

    id: str
    name: str
    arguments: dict[str, Any]
    raw_arguments: str = ""


def _get(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    return getattr(obj, name, None)


def parse_tool_calls(raw: Any) -> tuple[ToolCall, ...]:
    """Type the ``tool_calls`` of an OpenAI-style message (SDK objects or dicts)."""
    out: list[ToolCall] = []
    for item in raw or ():
        function = _get(item, "function")
        text = str(_get(function, "arguments") or "")
        try:
            loaded: Any = json.loads(text) if text else {}
        except json.JSONDecodeError:
            loaded = {}
        arguments: dict[str, Any] = loaded if isinstance(loaded, dict) else {}  # pyright: ignore[reportUnknownVariableType]
        out.append(
            ToolCall(
                str(_get(item, "id") or ""), str(_get(function, "name") or ""), arguments, text
            )
        )
    return tuple(out)


def strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Make every object in a JSON schema strict: all properties required, no extras."""

    def walk(node: Any) -> Any:
        if isinstance(node, list):
            return [walk(x) for x in node]  # pyright: ignore[reportUnknownVariableType]
        if not isinstance(node, dict):
            return node
        out: dict[str, Any] = {k: walk(v) for k, v in node.items()}  # pyright: ignore[reportUnknownVariableType]
        props = out.get("properties")
        if out.get("type") == "object" and isinstance(props, dict):
            out["additionalProperties"] = False
            out["required"] = list(props)  # pyright: ignore[reportUnknownArgumentType]
        return out

    return walk(schema)


def response_format(model: type[BaseModel]) -> dict[str, Any]:
    """The ``response_format`` for a strict ``json_schema`` reply shaped like ``model``."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": model.__name__,
            "strict": True,
            "schema": strict_schema(model.model_json_schema()),
        },
    }


def validate_reply[M: BaseModel](model: type[M], text: str) -> M:
    """Parse the reply text against the model or raise SchemaValidationError."""
    try:
        return model.model_validate_json(text)
    except ValidationError as exc:
        fields = sorted({".".join(str(p) for p in e["loc"]) or "<root>" for e in exc.errors()})
        raise SchemaValidationError("invalid fields: " + ", ".join(fields), text) from None
