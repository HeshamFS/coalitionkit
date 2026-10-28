# SPDX-License-Identifier: Apache-2.0
"""Contracts for the Coalition Protocol v0.1: models, JCS, signing, IDs and schema validation."""

from .canonical import canonicalize, prev_hash, sha256_hex
from .envelope import HOST_FIELDS, UNSIGNED_FIELDS, Envelope
from .ids import is_ulid, new_ulid, ulid_timestamp_ms
from .payloads import MESSAGE_TYPES, PAYLOAD_MODELS
from .scope import Scope
from .signing import (
    SignatureError,
    is_valid_signature,
    sign_envelope,
    signing_payload,
    verify_envelope,
)
from .validate import (
    SchemaValidationError,
    schema_dir,
    validate_envelope,
    validate_payload,
    validate_scope,
)

__all__ = [
    "HOST_FIELDS",
    "MESSAGE_TYPES",
    "PAYLOAD_MODELS",
    "UNSIGNED_FIELDS",
    "Envelope",
    "SchemaValidationError",
    "Scope",
    "SignatureError",
    "canonicalize",
    "is_ulid",
    "is_valid_signature",
    "new_ulid",
    "prev_hash",
    "schema_dir",
    "sha256_hex",
    "sign_envelope",
    "signing_payload",
    "ulid_timestamp_ms",
    "validate_envelope",
    "validate_payload",
    "validate_scope",
    "verify_envelope",
]
