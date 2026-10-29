# SPDX-License-Identifier: Apache-2.0
"""Run acceptance test 1: one zero-pack Coalition, members on three stacks, over A2A.

    uv --directory examples run python -m interop.run --scripted
    COALITIONKIT_META_API_KEY=... uv --directory examples run python -m interop.run --live

The scorecard goes to stdout as JSON and, with --out, to a file (never the key).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from members.kit.redact import scrub

from .coalition import InteropCoalition
from .rig import KEY_VARIABLE, Mode
from .scorecard import build_scorecard

TIME_LIMIT_S = 600.0


async def run_once(
    mode: Mode, run_number: int = 1, time_limit_s: float = TIME_LIMIT_S
) -> dict[str, Any]:
    coalition = InteropCoalition(mode)
    outcome = await coalition.run(time_limit_s)
    card = build_scorecard(outcome, mode.label, run_number)
    # Whatever a framework or server echoed, the key itself never reaches a scorecard.
    key = os.environ.get(KEY_VARIABLE, "")
    return json.loads(scrub(json.dumps(card), [key], patterns=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scripted", action="store_true", help="scripted models, no network")
    group.add_argument("--live", action="store_true", help="live Meta API (key from environment)")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--out", type=Path, help="write each scorecard as JSON in this folder")
    parser.add_argument("--time-limit", type=float, default=TIME_LIMIT_S)
    args = parser.parse_args(argv)
    mode = Mode(live=args.live)
    failed = 0
    for number in range(1, args.runs + 1):
        card = asyncio.run(run_once(mode, number, args.time_limit))
        text = json.dumps(card, indent=2, sort_keys=True)
        print(text)
        if args.out:
            args.out.mkdir(parents=True, exist_ok=True)
            (args.out / f"scorecard-{mode.label}-{number}.json").write_text(text + "\n", "utf-8")
        failed += 0 if card["passed"] else 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
