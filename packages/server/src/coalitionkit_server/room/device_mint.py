# SPDX-License-Identifier: Apache-2.0
"""Run the Mint on the host for a seated person, then wait for their signed approval.

The video and voice note are written to a working folder under the data directory for the
pipeline and removed when it ends. Progress is the public ``stages`` list of the device. When
every attack passes the device waits in ``approve``: only its owner's press-and-hold sends the
approval, and the host then signs ``consent_payload(hash, "approve", {})`` with that person's own
owner key. Nothing else approves it, and approval is never a boolean argument.
"""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..adapter import Document
from .devices import STAGES, devices, enrol, hub, next_id, put, report, serves

if TYPE_CHECKING:
    from .engine import RoomEngine

LOG = logging.getLogger(__name__)
FAMILIES = {"resource", "device"}


def mint_root(engine: RoomEngine) -> Path:
    return engine.server.settings.host_key_file.parent / "mint"


def clients(engine: RoomEngine) -> tuple[Any, Any]:
    """The Mint's model gateway and media client: the hub's, else the server's settings."""
    h = hub(engine)
    gateway = h.gateway or engine.server.gateway
    if h.media is None:
        from coalitionkit_models.media import MediaClient

        h.media = MediaClient(gateway.settings, meter=gateway.meter)
    return gateway, h.media


def stages(current: str | None, took: dict[str, float]) -> list[Document]:
    out: list[Document] = []
    reached = current is None
    for name in STAGES:
        if name == current:
            reached = True
            state = "running"
        elif name in took:
            state = "done"
        else:
            state = "pending" if reached else "done"
        out.append({"name": name, "state": state, "took": took.get(name)})
    return out


def start(
    engine: RoomEngine,
    coalition: str,
    owner: str,
    video: bytes,
    voice: bytes,
    template: str,
    label: str,
    needs: list[str] | None,
) -> str:
    """Record a new device in ``minting`` and run the pipeline beside the room's step."""
    doc = engine.read(coalition)
    pid = next_id(doc)
    work = mint_root(engine) / coalition / f"{pid}-upload"
    work.mkdir(parents=True, exist_ok=True)
    (work / "video.mp4").write_bytes(video)
    (work / "voice.wav").write_bytes(voice)
    put(
        engine,
        coalition,
        pid,
        label=label,
        template=template,
        owner=owner,
        state="minting",
        stages=stages("capture", {}),
        asked=needs or [],
        needs=[],
        error=None,
    )
    engine.note(coalition, "minting", f"Minting {label} from a video and a voice note", seat=owner)
    engine.spawn(coalition, f"mint:{pid}", lambda: run(engine, coalition, pid, work))
    return pid


async def run(engine: RoomEngine, coalition: str, pid: str, work: Path) -> None:
    from coalitionkit_mint.pipeline import MintFailure, mint

    entry = devices(engine.read(coalition))[pid]
    owner = str(entry["owner"])
    person = await engine.thread(engine.server.registry.hosted_for, coalition, owner)
    gateway, media = clients(engine)
    template = str(entry["template"])
    templates = None
    if template not in FAMILIES:
        try:
            templates = await engine.thread(engine.server.mint_templates, coalition)
        except ValueError as exc:
            fail(engine, coalition, pid, str(exc))
            return

    def progress(name: str) -> None:
        put(engine, coalition, pid, stages=stages(name, {}))

    started = time.monotonic()
    await report(engine, coalition, owner, "mint:pipeline", template, "", "started", 0)
    try:
        minted = await mint(
            work / "video.mp4",
            work / "voice.wav",
            mint_root(engine) / coalition / pid,
            template=template,
            owner=person.owner_key.public_key(),
            owner_id=owner,
            gateway=gateway,
            media=media,
            coalition_id=coalition,
            templates=templates,
            on_stage=progress,
        )
    except MintFailure as exc:
        ms = round((time.monotonic() - started) * 1000)
        await report(engine, coalition, owner, "mint:pipeline", template, str(exc), "failed", ms)
        fail(engine, coalition, pid, str(exc), exc.scorecard)
        return
    finally:
        shutil.rmtree(work, ignore_errors=True)
    ms = round((time.monotonic() - started) * 1000)
    hub(engine).running[(coalition, pid)] = minted
    data = minted.catalog_data()
    config = data["MintedAgentCard"]
    passed = sum(1 for a in minted.attacks if a.passed)
    await report(
        engine,
        coalition,
        owner,
        "mint:pipeline",
        template,
        f"{passed} of {len(minted.attacks)} attacks refused",
        "done",
        ms,
    )
    label = str(entry["label"] or config["agent"]["name"])
    put(
        engine,
        coalition,
        pid,
        state="approve",
        label=label,
        stages=stages("publish", minted.stage_seconds),
        tools=config["tools"],
        attacks={"passed": passed, "total": len(minted.attacks)},
        manifest_hash=minted.manifest_hash,
        cost_micro_usd=minted.cost_micro_usd,
        tokens=minted.tokens,
        elapsed=round(minted.elapsed_seconds, 2),
        family=family_of(minted),
        fields=fields_of(minted),
        needs=serves(engine.read(coalition), label, entry.get("asked")),
    )
    engine.note(
        coalition,
        "minting",
        f"{label} passed {passed} attacks and waits for its owner's hold",
        seat=owner,
    )


def family_of(minted: Minted) -> str:
    from coalitionkit_mint.artifact import load

    return load(minted.folder)[0].template


def fields_of(minted: Minted) -> list[Document]:
    from coalitionkit_mint.artifact import load
    from coalitionkit_mint.schema import DeviceConfig

    config = load(minted.folder)[0]
    if not isinstance(config, DeviceConfig):
        return []
    return [f.model_dump() for f in config.fields]


def fail(
    engine: RoomEngine, coalition: str, pid: str, why: str, card: Document | None = None
) -> None:
    attacks: list[Document] = (card or {}).get("attacks") or []
    put(
        engine,
        coalition,
        pid,
        state="failed",
        error=why[:300],
        stages=stages(None, {}),
        attacks={"passed": sum(1 for a in attacks if a.get("passed")), "total": len(attacks)},
    )
    engine.note(coalition, "minting", f"The Mint stopped: {why[:120]}", seat=pid)


class NotYours(PermissionError):
    pass


async def approve(engine: RoomEngine, coalition: str, who: str, pid: str) -> None:
    """The owner's hold: sign the approval with their own key, then seat the device."""
    from coalitionkit_contracts.signing import sign_detached
    from coalitionkit_mint.artifact import consent_payload

    entry = devices(engine.read(coalition)).get(pid)
    if entry is None or entry.get("owner") != who:
        raise NotYours(pid)
    if entry.get("state") != "approve":
        raise LookupError(pid)
    minted = hub(engine).running.get((coalition, pid))
    if minted is None:
        raise LookupError(pid)
    person = await engine.thread(engine.server.registry.hosted_for, coalition, who)
    signature = sign_detached(
        consent_payload(minted.manifest_hash, "approve", {}), person.owner_key, "owner"
    )
    started = time.monotonic()
    await engine.thread(minted.approve, signature, person.owner_key)
    ms = round((time.monotonic() - started) * 1000)
    await report(engine, coalition, who, "mint:approve", pid, "owner signed", "done", ms)
    put(engine, coalition, pid, stages=stages(None, minted.stage_seconds), card=card_of(minted))
    await enrol(engine, coalition, pid)


def card_of(minted: Minted) -> Document:
    data = minted.catalog_data()["MintedAgentCard"]
    return {**data["agent"], "health": data["health"]}


def stop_all(engine: RoomEngine, coalition: str) -> None:
    """Stop the room's minted processes (the room has ended or the host is closing)."""
    running = hub(engine).running
    for key in [k for k in running if k[0] == coalition]:
        try:
            running.pop(key).close()
        except Exception:
            LOG.exception("Stopping a minted device failed")


if TYPE_CHECKING:
    from coalitionkit_mint.publish import Minted
