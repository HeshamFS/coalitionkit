# SPDX-License-Identifier: Apache-2.0
"""Validate envelopes and payloads against the JSON Schemas in spec/schemas (no network)."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from functools import cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from .resources import spec_path

SCHEMA_BASE = "https://coalitionkit.dev/schemas/coalition/v0/"
SCHEMA_DIR_ENV = "COALITIONKIT_SCHEMA_DIR"

#: Message types that have a schema file named after the type's last segment.
SCHEMA_FILES: Mapping[str, str] = {
    "coalition.charter": "charter",
    "coalition.join": "join",
    "coalition.leave": "leave",
    "coalition.observe": "observe",
    "coalition.need": "need",
    "coalition.offer": "offer",
    "coalition.query": "query",
    "coalition.answer": "answer",
    "coalition.match": "match",
    "coalition.propose": "propose",
    "coalition.tension": "tension",
    "coalition.decide": "decide",
    "coalition.commit": "commit",
    "coalition.ripple": "ripple",
    "coalition.done": "done",
    "coalition.dissolve": "dissolve",
    "coalition.projection": "projection",
    "coalition.receipt": "receipt",
    "coalition.tool": "tool",
    "coalition.error": "error",
}


class SchemaValidationError(Exception):
    """The data fails its JSON Schema. ``errors`` lists one line per problem."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


def schema_dir() -> Path:
    """An explicit schema override, or the schemas shipped in this distribution."""
    override = os.environ.get(SCHEMA_DIR_ENV)
    return Path(override) if override else spec_path("schemas", "coalition", "v0")


def load_schemas() -> dict[str, dict[str, Any]]:
    """Every schema file, keyed by ``$id``."""
    schemas: dict[str, dict[str, Any]] = {}
    for path in sorted(schema_dir().glob("*.json")):
        schema: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        schemas[schema["$id"]] = schema
    return schemas


@cache
def _registry() -> Registry[Any]:
    registry: Registry[Any] = Registry()
    for uri, schema in load_schemas().items():
        registry = registry.with_resource(uri, Resource.from_contents(schema, DRAFT202012))
    return registry


def _validator(name: str) -> Draft202012Validator:
    schema = _registry().get_or_retrieve(SCHEMA_BASE + name + ".json").value.contents
    return Draft202012Validator(
        schema,
        registry=_registry(),
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )


def _errors(name: str, data: Any, prefix: str = "") -> list[str]:
    validator = _validator(name)
    raw: list[Any] = list(validator.iter_errors(data))  # pyright: ignore[reportUnknownMemberType]
    found = sorted(raw, key=lambda e: list(e.absolute_path))
    return [
        f"{prefix}{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in found
    ]


def validate_scope(data: object) -> None:
    errors = _errors("scope", data)
    if errors:
        raise SchemaValidationError(errors)


def validate_payload(message_type: str, payload: object) -> None:
    """Validate a payload against the schema for its message type."""
    name = SCHEMA_FILES.get(message_type)
    if name is None:
        raise SchemaValidationError([f"type: unknown message type {message_type!r}"])
    errors = _errors(name, payload, prefix="payload/")
    if errors:
        raise SchemaValidationError(errors)


def validate_envelope(data: object) -> None:
    """Validate an envelope, then its payload by ``type``."""
    errors = _errors("envelope", data)
    if not errors and isinstance(data, Mapping):
        fields: Mapping[str, Any] = data  # pyright: ignore[reportUnknownVariableType]
        name = SCHEMA_FILES.get(fields["type"])
        if name is None:
            errors = [f"type: unknown message type {fields['type']!r}"]
        else:
            errors = _errors(name, fields["payload"], prefix="payload/")
    if errors:
        raise SchemaValidationError(errors)
