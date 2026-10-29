# SPDX-License-Identifier: Apache-2.0
"""Turn one finished run into a scorecard: goal, validity, refusals, latency, tokens, cost."""

from __future__ import annotations

import json
import statistics
from datetime import UTC, datetime
from typing import Any

from coalitionkit_contracts import (
    SchemaValidationError,
    SignatureError,
    genesis_hash,
    prev_hash,
    validate_envelope,
    verify_envelope,
)
from coalitionkit_models import UnpricedModelError, load_price_table

from .coalition import Outcome

HOST = "host"


def _spread(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"count": 0, "mean_s": 0.0, "p50_s": 0.0, "max_s": 0.0}
    return {
        "count": len(values),
        "mean_s": round(statistics.fmean(values), 3),
        "p50_s": round(statistics.median(values), 3),
        "max_s": round(max(values), 3),
    }


def _check_log(outcome: Outcome, events: list[dict[str, Any]]) -> dict[str, Any]:
    host = outcome.host
    bad_schema: list[str] = []
    host_invalid = 0
    bad_sig: list[str] = []
    for event in events:
        try:
            validate_envelope(event)
        except SchemaValidationError as exc:
            bad_schema.append(f"{event['type']}: {str(exc)[:120]}")
            host_invalid += event["on_behalf_of"] == HOST
        try:
            if event["on_behalf_of"] == HOST:
                verify_envelope(event, outcome.host_key.public_key(), expected_kid=host.kid)
            else:
                key, kid = outcome.pins[event["on_behalf_of"]]
                verify_envelope(event, key, expected_kid=kid)
        except SignatureError as exc:
            bad_sig.append(f"{event['type']}: {exc}")
    chain = all(e["seq"] == i + 1 for i, e in enumerate(events))
    created = events[0]["payload"]["created_at"] if events else ""
    previous = genesis_hash(host.coalition_id, host.card_url, created)
    for event in events:
        chain = chain and event["prev_hash"] == previous
        previous = prev_hash(event)
    return {
        "events": len(events),
        "host_originated": sum(1 for e in events if e["on_behalf_of"] == HOST),
        "host_schema_invalid": host_invalid,
        "schema_valid": len(events) - len(bad_schema),
        "schema_errors": bad_schema,
        "signatures_ok": not bad_sig,
        "signature_errors": bad_sig,
        "chain_ok": chain,
    }


def _goal(outcome: Outcome, events: list[dict[str, Any]]) -> dict[str, Any]:
    state = outcome.host.state
    names = list(outcome.members)
    accepted = {n: state.accepted_charter(n) for n in names}
    plans = [s for s in state.subjects.values() if s["kind"] == "plan"]
    dissolved = [e for e in events if e["type"] == "coalition.dissolve"]
    done = {t["description"].split(":")[0]: t["status"] for t in state.tasks.values()}
    reached = (
        all(accepted.values())
        and bool(done)
        and all(status == "done" for status in done.values())
        and any(p.get("status") == "decided" for p in plans)
        and bool(dissolved)
        and dissolved[-1]["payload"]["reason"] == "completed"
        and not outcome.timed_out
    )
    return {
        "reached": reached,
        "charter_accepted": accepted,
        "tasks": done,
        "plan_status": [p.get("status") for p in plans],
        "dissolve": dissolved[-1]["payload"]["reason"] if dissolved else None,
        "assignees": {t["description"].split(":")[0]: t["assignee"] for t in state.tasks.values()},
    }


def _cost_usd(model: str, prompt: int, completion: int, cached: int) -> float | None:
    try:
        micro = load_price_table().cost_micro_usd(
            model, prompt_tokens=prompt, completion_tokens=completion, cached_tokens=cached
        )
    except UnpricedModelError:
        return None
    return round(micro / 1_000_000, 6)


def _member(name: str, outcome: Outcome) -> dict[str, Any]:
    member = outcome.members[name]
    log = member.core.log
    prompt = sum(u.prompt_tokens for u in log.uses)
    completion = sum(u.completion_tokens for u in log.uses)
    cached = sum(u.cached_tokens for u in log.uses)
    model_turns = [t.latency_s for t in log.turns if t.model_calls or t.kind in {"offers", "work"}]
    return {
        "framework": member.built.brain.framework,
        "model": member.built.brain.model,
        "messages_sent": len(log.sent),
        "messages_valid": sum(1 for s in log.sent if s.valid),
        "sent_by_type": _count(s.type for s in log.sent),
        "refusals": log.refusals(),
        "received": log.received,
        "received_invalid": log.received_invalid,
        "peer_originals_unverified": log.unverified_peer_originals,
        "turns": _spread([t.latency_s for t in log.turns]),
        "model_turns": _spread(model_turns),
        "model_calls": len(log.uses),
        "tokens": {
            "prompt": prompt,
            "completion": completion,
            "cached": cached,
            "reasoning": sum(u.reasoning_tokens for u in log.uses),
        },
        "cost_usd": _cost_usd(member.built.brain.model, prompt, completion, cached),
        "gateway_meter_micro_usd": _meter(member),
        "turn_errors": log.turn_errors,
    }


def _meter(member: Any) -> int | None:
    meter = member.built.meter
    return sum(r.cost_micro_usd for r in meter.records) if meter is not None else None


def _count(items: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    return dict(sorted(counts.items()))


def build_scorecard(outcome: Outcome, mode_label: str, run_number: int = 1) -> dict[str, Any]:
    events = outcome.host.store.read(outcome.host.coalition_id)
    log = _check_log(outcome, events)
    members = {name: _member(name, outcome) for name in outcome.members}
    sent = sum(m["messages_sent"] for m in members.values())
    sent_valid = sum(m["messages_valid"] for m in members.values())
    total = sent + log["host_originated"]
    valid = sent_valid + (log["host_originated"] - log["host_schema_invalid"])
    refusals: dict[str, int] = {}
    for m in members.values():
        for code, n in m["refusals"].items():
            refusals[code] = refusals.get(code, 0) + n
    goal = _goal(outcome, events)
    leaks = _leaks(outcome, events)
    cost = [m["cost_usd"] for m in members.values()]
    return {
        "run": run_number,
        "mode": mode_label,
        "finished_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "wall_s": round(outcome.wall_s, 2),
        "goal": goal,
        "messages": {
            "total": total,
            "valid": valid,
            "valid_share": round(valid / total, 4) if total else 0.0,
            "sent_by_members": sent,
            "host_originated": log["host_originated"],
            "deliveries_host_to_members": outcome.deliveries,
            "delivery_failures": outcome.delivery_failures,
        },
        "log": log,
        "refusals_by_code": dict(sorted(refusals.items())),
        "canary_leaks": leaks,
        "members": members,
        "totals": {
            "model_calls": sum(m["model_calls"] for m in members.values()),
            "prompt_tokens": sum(m["tokens"]["prompt"] for m in members.values()),
            "completion_tokens": sum(m["tokens"]["completion"] for m in members.values()),
            "cost_usd": round(sum(c for c in cost if c is not None), 6)
            if mode_label == "live"
            else 0.0,
        },
        "passed": goal["reached"] and valid == total and log["signatures_ok"] and log["chain_ok"],
    }


def _leaks(outcome: Outcome, events: list[dict[str, Any]]) -> int:
    text = json.dumps(events)
    for member in outcome.members.values():
        text += "".join(member.core.log.prompts)
    return sum(1 for m in outcome.members.values() if m.core.vault.private_note in text)
