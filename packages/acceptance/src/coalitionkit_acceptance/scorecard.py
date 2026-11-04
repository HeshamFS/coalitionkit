# SPDX-License-Identifier: Apache-2.0
"""The scorecard: run every available acceptance runner and print what was measured.

    uv run python -m coalitionkit_acceptance.scorecard

Writes ``scorecard-<date>.json`` (gitignored) and prints a markdown table of measured values
only. A test that did not run says "not run" and why. Live parts run only with
``COALITIONKIT_LIVE=1`` and ``COALITIONKIT_META_API_KEY``; the key is never printed or stored.
``COALITIONKIT_ACCEPTANCE_FULL=1`` selects the full sizes.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import chaos, chaos_server
from .config import database_url, full_run, scale_size
from .cost import default_usage_file, run_cost
from .cost_live import export_comparison, reconcile, run_live_cost
from .doors_message import run_message_door
from .ledger import record_run
from .live import close_kit, live_enabled, live_kit, live_skip_reason
from .metrics import Recorder, percentile
from .postgres import PostgresContainer, docker_missing_reason
from .privacy import PrivacyResult, record, run_privacy, totals
from .ripple_server import run_ripple_server
from .scale_server import run_scale_server

REPO = Path(os.environ.get("COALITIONKIT_SOURCE_DIR", Path.cwd())).resolve()


class NotRun(Exception):
    """A test (or part of one) that could not run, with the reason."""


@dataclass
class Row:
    number: int
    name: str
    status: str = "not run"
    reason: str = ""
    measured: dict[str, Any] = field(default_factory=lambda: dict[str, Any]())
    parts: list[str] = field(default_factory=lambda: list[str]())


def p95(result: dict[str, Any], key: str) -> float | None:
    found = result.get("timings", {}).get(key)
    return None if found is None else found["p95_s"]


async def run_1() -> Row:
    row = Row(1, "Interop: three stacks over A2A")
    if not (REPO / "examples/pyproject.toml").is_file():
        raise NotRun("interop requires a source checkout; set COALITIONKIT_SOURCE_DIR")
    uv = shutil.which("uv") or str(Path.home() / ".local" / "bin" / "uv.exe")
    if not Path(uv).exists() and shutil.which("uv") is None:
        raise NotRun("uv was not found to run the examples project")
    command = [uv, "--directory", str(REPO / "examples"), "run"]
    command += ["python", "-m", "interop.run", "--live" if live_enabled() else "--scripted"]
    done = await asyncio.to_thread(
        subprocess.run, command, capture_output=True, text=True, timeout=1500, check=False
    )
    start = done.stdout.find("{")
    if done.returncode not in (0, 1) or start < 0:
        tail = done.stderr.strip().splitlines()[-1:] or ["no error output"]
        key = os.environ.get("COALITIONKIT_META_API_KEY", "")
        note = tail[0][:200].replace(key, "[key]") if key else tail[0][:200]
        raise NotRun(
            f"the interop runner did not produce a scorecard (exit {done.returncode}): {note}"
        )
    card = json.loads(done.stdout[start:])
    row.measured = {
        "passed": card["passed"],
        "goal_reached": card["goal"]["reached"],
        "valid_message_share": card["messages"]["valid_share"],
        "canary_leaks": card["canary_leaks"],
        "members": len(card["members"]),
    }
    row.status = "measured"
    row.parts = ["live: three stacks on Muse Spark" if live_enabled() else "scripted"]
    return row


async def run_2() -> Row:
    row = Row(2, "Privacy canaries")
    runs = 100 if full_run() else 10
    recorder = Recorder("privacy")
    outcomes: list[PrivacyResult] = []
    for seed in range(runs):
        outcome = await run_privacy(seed)
        record(recorder, outcome)
        outcomes.append(outcome)
    row.measured = {
        "runs": runs,
        "canaries": recorder.counter("canaries"),
        "found_outside_vault": recorder.counter("canaries_found_outside_vault"),
    }
    row.measured["totals"] = totals(outcomes)["scanned"]
    row.status = "measured"
    row.parts = ["scripted adversaries (the live adversary is tests/test_privacy_live.py)"]
    return row


def _paint_report() -> dict[str, Any]:
    """The doors test: the room, the lens and the MCP App view paint one accepted change."""
    npm = shutil.which("npm")
    web = REPO / "apps" / "web"
    if npm is None or not (web / "node_modules").is_dir():
        raise NotRun("npm or the web dependencies are missing (npm ci in apps/web)")
    report = web / "test-results" / "doors-latency.json"
    report.unlink(missing_ok=True)
    done = subprocess.run(
        [npm, "--prefix", str(web), "run", "test:doors"],
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    if not report.is_file():
        tail = done.stdout.strip().splitlines()[-1:] or ["no output"]
        raise NotRun(f"the doors test wrote no report (exit {done.returncode}): {tail[0][:200]}")
    return {**json.loads(report.read_text(encoding="utf-8")), "exit": done.returncode}


async def run_3() -> Row:
    row = Row(3, "Generative UI: change to paint on every surface")
    paint = await asyncio.to_thread(_paint_report)
    door = await asyncio.to_thread(run_message_door)
    delivery = door.recorder.result()["timings"]["delivery_s"]
    surfaces = ("web", "lens", "mcp")
    row.measured = {
        **{f"{s}_p95_ms": round(paint[s]["p95"], 1) for s in surfaces},
        **{f"{s}_min_ms": round(paint[s]["min"], 1) for s in surfaces},
        "samples_per_surface": paint["samplesPerSurface"],
        "message_delivery_p95_ms": round(delivery["p95_s"] * 1000, 1),
        "message_scope_leaks": len(door.leaks),
        "message_replies_that_signed": door.decisions_from_replies,
    }
    under = all(paint[s]["p95"] < paint["passMarkP95Ms"] for s in surfaces)
    clean = paint["exit"] == 0 and not door.leaks and door.decisions_from_replies == 0
    row.status = "measured" if under and clean else "failed"
    row.parts = [
        "web, lens and MCP App in Chromium against a real server (the MCP App in the test host, "
        "not a commercial host); message door in process",
        "a negative minimum is clock resolution between the host stamp and the browser",
    ]
    return row


def _mint_cards(stdout: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        start = line.find("{")  # pytest may print its progress mark on the same line
        if start >= 0 and '"attacks"' in line:
            cards.append(json.loads(line[start:]))
    return cards


async def run_6() -> Row:
    row = Row(6, "Mint: upload to pending, attacks, cost")
    if not live_enabled():
        raise NotRun(live_skip_reason() + "; the Mint runs on the live models only")
    if not (REPO / "packages/mint/tests/test_live.py").is_file():
        raise NotRun("Mint live acceptance requires COALITIONKIT_SOURCE_DIR")
    uv = shutil.which("uv") or str(Path.home() / ".local" / "bin" / "uv.exe")
    with tempfile.TemporaryDirectory() as directory:
        command = [uv, "--directory", str(REPO), "run", "pytest", "-m", "live", "-s", "-q"]
        command += ["packages/mint/tests/test_live.py", "--basetemp", directory]
        command += ["-k", "test_live_mint", "-p", "no:cacheprovider"]
        done = await asyncio.to_thread(
            subprocess.run, command, capture_output=True, text=True, timeout=1500, check=False
        )
    cards = _mint_cards(done.stdout)
    if not cards:
        tail = done.stdout.strip().splitlines()[-1:] or ["no output"]
        raise NotRun(f"the Mint run printed no scorecard (exit {done.returncode}): {tail[0][:200]}")
    row.measured = {
        "templates": len(cards),
        "passed": sum(1 for c in cards if c["passed"]),
        "max_elapsed_s": max(c["elapsed_seconds"] for c in cards),
        "attacks": sum(len(c["attacks"]) for c in cards),
        "attacks_passed": sum(1 for c in cards for a in c["attacks"] if a["passed"]),
        "cost_micro_usd": sum(c["cost_micro_usd"] for c in cards),
    }
    passed = done.returncode == 0 and all(c["passed"] for c in cards)
    row.status = "measured" if passed else "failed"
    row.parts = ["live: resource and device templates, synthetic video and Windows speech"]
    return row


async def run_4() -> Row:
    row = Row(4, "Ripple over the real server")
    with tempfile.TemporaryDirectory() as directory:
        result = await run_ripple_server(Path(directory))
    row.measured = {
        "affected_tasks": len(result.affected),
        "renegotiated_only_affected": result.renegotiated == result.affected,
        "viewers": result.viewers,
        "unaffected_viewers": len(result.unaffected),
        "unaffected_deltas": result.unaffected_deltas,
        "lost_events": result.lost_events,
        "accept_to_surface_p95_s": p95(result.metrics, "accept_to_delta_s"),
        "change_to_surface_p95_s": p95(result.metrics, "change_to_surface_s"),
        "samples": result.samples,
    }
    row.status = "measured"
    row.parts = ["scripted"]
    return row


async def run_5() -> Row:
    row = Row(5, "Scale over the real server")
    size = scale_size()
    with tempfile.TemporaryDirectory() as directory:
        result = await run_scale_server(
            Path(directory),
            agents=size.big_agents,
            coalitions=size.coalitions,
            coalition_agents=size.coalition_agents,
            tasks=size.tasks,
            big_viewers=10,
            small_viewers=2,
            concurrency=size.workers,
        )
    counts = result["counts"]
    row.measured = {
        "agents": counts["agents_total"],
        "coalitions": counts["coalitions"],
        "events": counts["events_total"],
        "lost_events": counts["lost_events"],
        "viewer_lost_events": counts["viewer_lost_events"],
        "send_p95_s": p95(result, "send_s"),
        "big_send_p95_s": p95(result["big"], "send_s"),
        "concurrent_send_p95_s": p95(result["concurrent"], "send_s"),
        "scripted_cost_micro_usd": result["values"]["cost_micro_usd_metered"],
    }
    row.status = "measured"
    row.parts = ["scripted"]
    if live_enabled():
        row.measured["live"] = await _scale_live(size.big_agents, size.coalition_agents, size.tasks)
        row.parts.append("live: 20 agents on Muse Spark 1.3 (contributor)")
    else:
        row.parts.append(f"live: not run ({live_skip_reason()})")
    return row


async def _scale_live(agents: int, coalition_agents: int, tasks: int) -> dict[str, Any]:
    kit = live_kit()
    with tempfile.TemporaryDirectory() as directory:
        try:
            result = await run_scale_server(
                Path(directory), agents=agents, coalitions=0, coalition_agents=coalition_agents,
                tasks=tasks, big_viewers=10, small_viewers=0, concurrency=10, live=20, kit=kit,
            )  # fmt: skip
        finally:
            await close_kit(kit)
    recorder = Recorder("scale_live")
    reconciled = reconcile(kit.meter, recorder)
    record_run("scale_live", kit.meter)
    latencies = sorted(x for t in kit.transports for x in t.latencies)
    return {
        "lost_events": result["counts"]["lost_events"],
        "decided": result["counts"]["coalitions_decided"],
        "live_calls": len(latencies),
        "live_call_p95_s": percentile(latencies, 0.95) if latencies else None,
        "send_p95_s": p95(result, "send_s"),
        "cost_micro_usd": reconciled["meter_micro_usd"],
        "cost_gap_micro_usd": reconciled["gap_micro_usd"],
    }


async def run_7() -> Row:
    row = Row(7, "Chaos")
    measured: dict[str, Any] = {}
    parts: list[str] = []
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        runs: dict[str, Callable[[Path], Awaitable[Recorder]]] = {
            "kill_server_sqlite_persisted": lambda d: chaos_server.kill_server(
                d, f"sqlite:///{d / 'host.db'}", "sqlite", boundary="persisted"
            ),
            "kill_server_sqlite_received": lambda d: chaos_server.kill_server(
                d, f"sqlite:///{d / 'host.db'}", "sqlite", boundary="received"
            ),
            "concurrent_deciders": chaos_server.concurrent_deciders,
            "viewer_disconnect": chaos_server.viewer_disconnect,
        }
        for name, run in runs.items():
            (base / name).mkdir()
            measured[name] = summary(await run(base / name))
        measured["in_process_kill_restart"] = summary(chaos.kill_and_restart(base))
        measured["in_process_drop_connection"] = summary(chaos.drop_connection())
        reason = docker_missing_reason()
        if reason is None and database_url() is None:
            with PostgresContainer() as container:
                for mode in ("kill", "drop"):
                    (base / mode).mkdir()
                    got = await chaos_server.database_fault(base / mode, container, mode)
                    measured[f"postgres_{mode}"] = summary(got)
                (base / "pgproc").mkdir()
                measured["postgres_kill_server"] = summary(
                    await chaos_server.kill_server(
                        base / "pgproc", container.new_database(), "postgres"
                    )
                )
            parts.append("postgres:18 in Docker")
        else:
            parts.append(f"postgres: not run ({reason or 'COALITIONKIT_TEST_DATABASE_URL set'})")
    row.measured = measured
    row.status = "measured"
    row.parts = [*parts, "live variant: tests/test_chaos_server.py (pytest -m live)"]
    return row


def summary(recorder: Recorder) -> dict[str, Any]:
    result = recorder.result()
    keep = (
        "lost_events", "duplicate_events", "max_decisions_per_revision", "plan_decided",
        "boundary_reached", "persisted_before_retry",
    )  # fmt: skip
    out: dict[str, Any] = {k: v for k, v in result["counts"].items() if k in keep}
    for name in ("recovery_s", "restart_s", "database_restart_s"):
        if name in result["timings"]:
            out[name] = result["timings"][name]["max_s"]
    if "server_healed_without_restart" in result["counts"]:
        out["server_healed_without_restart"] = result["counts"]["server_healed_without_restart"]
    return out


async def run_8() -> Row:
    row = Row(8, "Cost against the provider")
    recorder, report = await asyncio.to_thread(run_cost, None)
    values = recorder.result()["values"]
    row.measured = {
        "fixture_replay": {
            "calls": recorder.counter("calls"),
            "coalitions": len(report),
            "cents_mismatches": values["cents_mismatches"],
            "max_gap_micro_usd": values["max_gap_micro_usd"],
            "source": f"recorded fixture {default_usage_file().name} (not a provider download)",
        }
    }
    row.status = "measured"
    row.parts = ["fixture replay"]
    if not live_enabled():
        # No live run happened, so there is nothing to compare with the provider.
        row.parts.append(f"live: not run ({live_skip_reason()}); provider export: not run")
        return row
    live = await run_live_cost(12)
    row.measured["live"] = {"reconciliation": live.result()["values"]["reconciliation"]}
    row.parts.append("live reconciliation against provider-reported usage")
    add_export(row, export_comparison(Recorder("cost_export")))
    return row


def add_export(row: Row, export: dict[str, Any]) -> None:
    """Put the provider-export result on the row; a result that ran has no reason."""
    if export.get("ran"):
        row.measured["provider_export"] = {
            k: v for k, v in export.items() if k not in ("comparisons", "reason")
        }
        row.parts.append(
            f"provider export: {export.get('mode', 'checked')} check per day and metric"
        )
        if export.get("mode") != "exact":
            row.parts.append(str(export.get("exact_match", "exact match not run")))
    else:
        row.parts.append(f"provider export: {export.get('reason', 'not run')}")
    row.measured["provider_export_comparisons"] = export.get("comparisons", [])


def not_run(number: int, name: str, reason: str) -> Row:
    return Row(number, name, "not run", reason)


async def collect() -> list[Row]:
    rows: list[Row] = []
    plan: list[tuple[int, str, Callable[[], Awaitable[Row]] | None, str]] = [
        (1, "Interop: three stacks over A2A", run_1, ""),
        (2, "Privacy canaries", run_2, ""),
        (3, "Generative UI: change to paint on every surface", run_3, ""),
        (4, "Ripple over the real server", run_4, ""),
        (5, "Scale over the real server", run_5, ""),
        (6, "Mint: upload to pending, attacks, cost", run_6, ""),
        (7, "Chaos", run_7, ""),
        (8, "Cost against the provider", run_8, ""),
    ]
    for number, name, runner, reason in plan:
        if runner is None:
            rows.append(not_run(number, name, reason))
            continue
        try:
            rows.append(await runner())
        except NotRun as why:
            rows.append(not_run(number, name, str(why)))
        except Exception as error:  # a failing runner is a result, not a crash
            rows.append(Row(number, name, "failed", f"{type(error).__name__}: {str(error)[:300]}"))
    return rows


def flat(value: Any, prefix: str = "") -> list[str]:
    if isinstance(value, dict):
        return [x for k, v in value.items() for x in flat(v, f"{prefix}{k}.")]  # pyright: ignore[reportUnknownVariableType]
    return [f"{prefix[:-1]}={value}"]


def table(rows: list[Row]) -> str:
    lines = ["| # | Test | Status | Measured | Notes |", "|---|---|---|---|---|"]
    for row in rows:
        measured = "; ".join(flat(row.measured)) if row.measured else ""
        notes = "; ".join([*([row.reason] if row.reason else []), *row.parts])
        lines.append(f"| {row.number} | {row.name} | {row.status} | {measured} | {notes} |")
    return "\n".join(lines)


def main() -> int:
    rows = asyncio.run(collect())
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    out = Path.cwd() / f"scorecard-{stamp}.json"
    out.write_text(
        json.dumps(
            {
                "date": stamp,
                "full": full_run(),
                "live": live_enabled(),
                "rows": [r.__dict__ for r in rows],
            },
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    print(table(rows))
    print(f"\nwritten to {out}")
    return 1 if any(r.status == "failed" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
