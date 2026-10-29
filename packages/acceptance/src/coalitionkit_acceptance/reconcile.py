# SPDX-License-Identifier: Apache-2.0
"""Offline reconciliation of the live ledger with Meta usage export.

    python -m coalitionkit_acceptance.reconcile --export usage.csv [--until 2026-10-29T00:00:00Z]

Live runs only collect usage into the ledger. Run this after downloading the export (usage can take
up to an hour to appear). It compares only the window the export covers and reports newer ledger
records as not run. Exit status 1 when a compared metric differs (or exceeds the upper bound).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from .ledger import entries
from .usage_csv import reconcile


def parse_until(text: str | None) -> datetime | None:
    if text is None:
        return None
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="coalitionkit_acceptance.reconcile")
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--until", default=None, help="the export is complete up to this UTC time")
    parser.add_argument("--ledger", type=Path, default=None)
    args = parser.parse_args(argv)
    result = reconcile(args.export, entries(args.ledger), until=parse_until(args.until))
    print(json.dumps(result, indent=2))
    return 1 if result.get("differs") or result.get("exceeds_bound") else 0


if __name__ == "__main__":
    sys.exit(main())
