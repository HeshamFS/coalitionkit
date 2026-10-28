# SPDX-License-Identifier: Apache-2.0
"""Contracts for the Coalition Protocol v0.1: models, JCS, signing, IDs and schema validation."""

from .canonical import canonicalize, prev_hash, sha256_hex
from .consent import consent_payload, sign_consent, verify_consent, verify_decision
from .decisions import NotADeciderError, record_answer, tally
from .envelope import HOST_FIELDS, UNSIGNED_FIELDS, Envelope
from .idempotency import (
    StoredSubmission,
    classify_submission,
    idempotency_key,
    submission_digest,
)
from .ids import is_ulid, new_ulid, ulid_timestamp_ms
from .log import (
    LogIntegrityError,
    LogStub,
    ReceiptInfo,
    check_receipts,
    entry_hash,
    genesis_hash,
    receipt_payload,
    verify_chain,
    verify_receipt,
)
from .owner import (
    jwk_to_public_key,
    owner_proof_payload,
    public_key_to_jwk,
    sign_owner_proof,
    verify_owner_proof,
)
from .payloads import HOST_ONLY_TYPES, MEMBER_TYPES, MESSAGE_TYPES, PAYLOAD_MODELS
from .revisions import StaleSubjectError, check_revision, is_current, is_superseded, next_revision
from .scope import Scope
from .scope_resolve import Membership, ScopeSource, principals, resolve_narrowest
from .signing import (
    SignatureError,
    is_valid_signature,
    sign_detached,
    sign_envelope,
    signing_payload,
    verify_detached,
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
    "HOST_ONLY_TYPES",
    "MEMBER_TYPES",
    "MESSAGE_TYPES",
    "PAYLOAD_MODELS",
    "UNSIGNED_FIELDS",
    "Envelope",
    "LogIntegrityError",
    "LogStub",
    "Membership",
    "NotADeciderError",
    "ReceiptInfo",
    "SchemaValidationError",
    "Scope",
    "ScopeSource",
    "SignatureError",
    "StaleSubjectError",
    "StoredSubmission",
    "canonicalize",
    "check_receipts",
    "check_revision",
    "classify_submission",
    "consent_payload",
    "entry_hash",
    "genesis_hash",
    "idempotency_key",
    "is_current",
    "is_superseded",
    "is_ulid",
    "is_valid_signature",
    "jwk_to_public_key",
    "new_ulid",
    "next_revision",
    "owner_proof_payload",
    "prev_hash",
    "principals",
    "public_key_to_jwk",
    "receipt_payload",
    "record_answer",
    "resolve_narrowest",
    "schema_dir",
    "sha256_hex",
    "sign_consent",
    "sign_detached",
    "sign_envelope",
    "sign_owner_proof",
    "signing_payload",
    "submission_digest",
    "tally",
    "ulid_timestamp_ms",
    "validate_envelope",
    "validate_payload",
    "validate_scope",
    "verify_chain",
    "verify_consent",
    "verify_decision",
    "verify_detached",
    "verify_envelope",
    "verify_owner_proof",
    "verify_receipt",
]
