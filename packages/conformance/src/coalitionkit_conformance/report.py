# SPDX-License-Identifier: Apache-2.0
"""Portable reports: the entire document except signature is covered by detached JWS."""

from datetime import UTC, datetime
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_contracts import (
    canonicalize,
    jwk_to_public_key,
    public_key_to_jwk,
    sign_detached,
    verify_detached,
)

from . import __version__

Document = dict[str, Any]
TITLES = [
    "Signed extension card",
    "Owner join and charter acknowledgement",
    "Envelope and owner consent signatures",
    "Member scope addressing",
    "Payload fields",
    "Bounded vault answers",
    "Private set intersection",
    "Canary isolation",
    "Sequence, chain and receipts",
    "Task stages",
    "Scoped delivery and projections",
    "Steward gate",
    "Duplicate submissions",
    "Authenticated sender binding",
    "Decision lifecycle",
    "Derived scopes",
    "Catalog rendering",
    "Owner consent surface",
    "Viewer scope",
    "Target authorization",
    "Charter revision gate",
]


LEVEL_TESTS = {
    "member": frozenset(range(1, 6)),
    "vault": frozenset({6, 7, 8}),
    "host": frozenset({*range(9, 17), 20, 21}),
    "surface": frozenset({17, 18, 19}),
}


def at_level(level: str, tests: list[Document]) -> list[Document]:
    """Each test belongs to exactly one level (the spec's Level column). Enrolling runs the member
    probes at every level, but a report lists, and is judged on, its own level's tests only."""
    return [t for t in tests if int(str(t["id"])[2:]) in LEVEL_TESTS[level]]


def results(level: str) -> list[Document]:
    selected = list(range(1, 6))
    selected += {
        "member": [],
        "host": [*range(9, 17), 20, 21],
        "vault": [6, 7, 8],
        "surface": [17, 18, 19],
    }[level]
    return [
        {
            "id": f"C-{n:02}",
            "title": TITLES[n - 1],
            "status": "not run",
            "reason": "Required wire fixture is unavailable",
        }
        for n in sorted(selected)
    ]


def signed_report(
    target: str, level: str, tests: list[Document], key: Ed25519PrivateKey
) -> Document:
    report: Document = {
        "runner_version": __version__,
        "target": target,
        "level": level,
        "utc_time": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "tests": tests,
        "public_key": public_key_to_jwk(key.public_key(), "conformance"),
    }
    report["signature"] = sign_detached(canonicalize(report), key, "conformance")
    return report


def verify_report(report: Document) -> None:
    body = {k: v for k, v in report.items() if k != "signature"}
    verify_detached(
        report.get("signature"),
        canonicalize(body),
        jwk_to_public_key(report["public_key"]),
        expected_kid="conformance",
    )


def exit_code(report: Document) -> int:
    return 0 if report["tests"] and all(t["status"] == "pass" for t in report["tests"]) else 1
