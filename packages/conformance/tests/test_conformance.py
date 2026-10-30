# SPDX-License-Identifier: Apache-2.0
"""Exercise the public runner against a real TCP server and faulty client responses."""

from copy import deepcopy
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
from coalitionkit_conformance.probes import chain, run_probe, scope_ack
from coalitionkit_conformance.report import exit_code, signed_report, verify_report
from coalitionkit_conformance.runner import run
from coalitionkit_conformance.wire import Participant
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from test_server import CHARTER, Running

from coalitionkit_contracts import SignatureError, new_ulid
from coalitionkit_edges.a2a import Ack
from coalitionkit_edges.a2a.identity import CardKey


async def test_reference_host(running: Running) -> None:
    async with httpx.AsyncClient(base_url=running.base) as http:
        auth = {"Authorization": "Bearer admin-test"}
        response = await http.post("/admin/coalitions", json=CHARTER, headers=auth)
        response.raise_for_status()
        created: dict[str, Any] = response.json()
        second = await http.post(
            f"/admin/coalitions/{created['coalition_id']}/invitations",
            json={"participant": "p2"},
            headers=auth,
        )
        second.raise_for_status()
    report = await run(
        created["host_card_url"],
        "host",
        [created["invitations"][0]["invitation"], second.json()["invitation"]],
        redeem_url=running.base + "/invitations/redeem",
    )
    verify_report(report)
    by_id = {t["id"]: t for t in report["tests"]}
    assert not [t for t in report["tests"] if t["status"] == "fail"], str(report["tests"])
    for test_id in ("C-01", "C-13", "C-14"):
        assert by_id[test_id]["status"] == "pass", by_id[test_id]
    for test_id in ("C-05", "C-09", "C-11", "C-20"):
        assert by_id[test_id].get("evidence"), by_id[test_id]
    assert all(t.get("reason") for t in report["tests"] if t["status"] == "not run")
    assert exit_code(report) == 1


def test_report_signature_and_tampering() -> None:
    report = signed_report(
        "https://target.invalid/card", "member", [], Ed25519PrivateKey.generate()
    )
    verify_report(report)
    for field, value in (
        ("target", "changed"),
        ("tests", [{"status": "pass"}]),
        ("level", "host"),
        ("runner_version", "other"),
    ):
        modified = deepcopy(report)
        modified[field] = value
        with pytest.raises(SignatureError):
            verify_report(modified)
    assert exit_code(report) == 1


def participant(client: Any) -> Participant:
    return Participant(
        client,
        Ed25519PrivateKey.generate(),
        Ed25519PrivateKey.generate(),
        new_ulid(),
        "p1",
        "https://p1.invalid/card",
    )


async def test_scope_leak_fails_c11() -> None:
    client = AsyncMock()
    client.send.return_value = Ack({"payload": {"content": "hidden-marker"}}, {}, "t", "c")
    result: dict[str, Any] = {"id": "C-11"}
    await run_probe(result, lambda: scope_ack(participant(client)))
    assert result["status"] == "fail"
    assert "host-only content" in result["reason"]


async def test_reused_sequence_fails_c09() -> None:
    from coalitionkit_contracts import receipt_payload, sign_envelope

    key = Ed25519PrivateKey.generate()
    client = AsyncMock()
    person = participant(client)
    accepted = person.event("observe", {"source": "device", "content": "chain"})
    accepted.update(seq=1, ts="2026-01-01T00:00:00Z", prev_hash="0" * 64)
    receipt = person.event("receipt", receipt_payload(person.coalition, accepted))
    receipt["sig"] = sign_envelope(receipt, key, "host")
    client.send.return_value = Ack(accepted, receipt, "t", "c")
    result: dict[str, Any] = {"id": "C-09"}
    await run_probe(result, lambda: chain([person], CardKey("host", key.public_key())))
    assert result["status"] == "fail"
    assert "gap" in result["reason"]


async def test_bad_card_still_produces_signed_failure() -> None:
    report = await run("http://127.0.0.1:1/card", "member", [], timeout=0.1)
    verify_report(report)
    assert report["tests"][0]["status"] == "fail"
    assert exit_code(report) == 1


async def test_reference_operator_cli(running: Running, tmp_path: Any) -> None:
    import asyncio
    import json
    import subprocess

    token = tmp_path / "admin-token"
    token.write_text("admin-test\n", encoding="utf-8")
    result = await asyncio.to_thread(
        subprocess.run,
        [
            "uv",
            "run",
            "coalitionkit-conform",
            "--target",
            running.base + "/.well-known/agent-card.json",
            "--level",
            "host",
            "--operator",
            "reference",
            "--admin-token-file",
            str(token),
        ],
        capture_output=True,
        text=True,
        timeout=45,
    )
    report = json.loads(result.stdout)
    verify_report(report)
    by_id = {t["id"]: t for t in report["tests"]}
    for test_id in ("C-01", "C-02", "C-09", "C-11", "C-12", "C-13", "C-14", "C-16"):
        assert by_id[test_id]["status"] == "pass", by_id[test_id]
    for test_id in ("C-10", "C-15", "C-20", "C-21"):
        assert by_id[test_id]["status"] == "fail", by_id[test_id]
        assert "steward_blocked" in by_id[test_id]["reason"], by_id[test_id]
    assert by_id["C-16"]["evidence"].startswith("20 local scope vectors")
    assert result.returncode == 1
    assert not ({"C-06", "C-07", "C-08", "C-17", "C-18", "C-19"} & by_id.keys())
    assert "admin-test" not in result.stdout + result.stderr


async def test_host_only_acceptance_fails_c20() -> None:
    from coalitionkit_conformance.probes import authorization

    client = AsyncMock()
    result: dict[str, Any] = {"id": "C-20"}
    await run_probe(result, lambda: authorization(participant(client)))
    assert result["status"] == "fail"
    assert "accepted an event requiring not_authorized" in result["reason"]
