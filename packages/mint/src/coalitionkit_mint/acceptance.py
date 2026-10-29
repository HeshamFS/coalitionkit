# SPDX-License-Identifier: Apache-2.0
"""Acceptance 6: measure upload-to-pending latency, attacks, tokens and meter cost."""

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any, Literal

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_models.gateway import ModelGateway
from coalitionkit_models.media import MediaClient
from coalitionkit_models.meter import CostMeter
from coalitionkit_models.prices import load_price_table
from coalitionkit_models.settings import load_settings

from .perceive import Media
from .pipeline import MintFailure, mint
from .publish import Minted


async def run_one(
    video: Path,
    voice: Path,
    output: Path,
    scorecard: Path,
    *,
    template: Literal["resource", "device"],
    gateway: ModelGateway,
    media: Media,
    owner: Ed25519PrivateKey,
) -> Minted:
    scorecard = scorecard.resolve()
    scorecard.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = await mint(
            video,
            voice,
            output,
            template=template,
            owner=owner.public_key(),
            owner_id="owner",
            gateway=gateway,
            media=media,
        )
    except MintFailure as exc:
        scorecard.write_text(json.dumps(exc.scorecard, indent=2), encoding="utf-8", newline="\n")
        raise
    try:
        scorecard.write_text(
            json.dumps(result.scorecard(), indent=2), encoding="utf-8", newline="\n"
        )
    except BaseException:
        result.close()
        raise
    return result


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resource-video", type=Path, required=True)
    parser.add_argument("--resource-voice", type=Path, required=True)
    parser.add_argument("--device-video", type=Path, required=True)
    parser.add_argument("--device-voice", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get("COALITIONKIT_META_API_KEY"):
        parser.exit(2, "no key\n")
    if os.environ.get("COALITIONKIT_LIVE") != "1":
        parser.exit(2, "set COALITIONKIT_LIVE=1\n")
    settings = load_settings()
    meter = CostMeter(load_price_table())
    gateway = ModelGateway(settings, meter=meter)
    media = MediaClient(settings, meter=meter)
    reports: list[dict[str, Any]] = []
    try:
        for template in ("resource", "device"):
            try:
                result = await run_one(
                    getattr(args, template + "_video"),
                    getattr(args, template + "_voice"),
                    args.output / template,
                    args.output.resolve() / f"scorecard-{template}.json",
                    template=template,
                    gateway=gateway,
                    media=media,
                    owner=Ed25519PrivateKey.generate(),
                )
                try:
                    report = result.scorecard()
                finally:
                    result.close()
            except Exception as exc:
                reports.append(
                    exc.scorecard
                    if isinstance(exc, MintFailure)
                    else {"passed": False, "failure": str(exc), "template": template}
                )
                continue
            reports.append(report)
        print(json.dumps(reports, indent=2))
        if not all(report["passed"] for report in reports):
            raise SystemExit(1)
    finally:
        await gateway.aclose()
        await media.aclose()


if __name__ == "__main__":
    asyncio.run(main())
