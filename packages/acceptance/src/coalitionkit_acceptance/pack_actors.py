# SPDX-License-Identifier: Apache-2.0
"""Signed, connector-free businesses and fixed-template Mint acceptance actors."""

from __future__ import annotations

import json
import tempfile
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from google.protobuf.json_format import MessageToDict
from mcp import Client

from coalitionkit_contracts import public_key_to_jwk, sign_owner_proof
from coalitionkit_contracts.signing import sign_detached
from coalitionkit_edges.a2a.identity import sign_card
from coalitionkit_mcp.ports import HostedParticipant
from coalitionkit_mint.artifact import connect, consent_payload, generate
from coalitionkit_mint.catalog import PackTemplate, TemplateRegistry
from coalitionkit_mint.process import Sandbox
from coalitionkit_mint.prove import AttackResult, run_suite
from coalitionkit_mint.publish import Minted, publish
from coalitionkit_mint.schema import Attacks, Config, DeviceConfig, ResourceConfig
from coalitionkit_mint.worker import Operations
from coalitionkit_packs.files import take_snapshot
from coalitionkit_server.cards import member_card

from .harness import Member

if TYPE_CHECKING:
    from .pack_acceptance import Journey


class RecordingSandbox(Sandbox):
    """Retain every proof/control/tool exchange, including refused calls, for the leak scan."""

    def __init__(self, folder: Path, channels: list[Any]) -> None:
        super().__init__(folder)
        self.channels = channels

    @asynccontextmanager
    async def client(self, *, proving: bool = False) -> AsyncGenerator[Client]:
        async with super().client(proving=proving) as client:
            original = client.call_tool

            async def recorded(*args: Any, **kwargs: Any) -> Any:
                self.channels.append({"arguments": args, "options": kwargs})
                try:
                    result = await original(*args, **kwargs)
                except Exception as exc:
                    self.channels.append(str(exc))
                    raise
                self.channels.append(result)
                return result

            client.call_tool = recorded
            yield client


async def recorded_proof(
    folder: Path, config: Config, tests: Attacks, channels: list[Any]
) -> list[AttackResult]:
    # Mint's proof uses a disposable clone so attacks cannot modify the published artifact.
    with tempfile.TemporaryDirectory(dir=folder.parent) as temporary:
        clone = Path(temporary) / "proof"
        owner = Ed25519PrivateKey.generate()
        digest = generate(clone, config, owner.public_key(), "proof_owner")
        sandbox = RecordingSandbox(clone, channels)
        try:
            await sandbox.start()
            return await run_suite(sandbox, config, tests, owner, digest)
        finally:
            sandbox.stop()


async def join_businesses(run: Journey) -> None:
    for index, entry in enumerate(run.scenario.businesses):
        agent, owner = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
        base = f"https://member-{index}.example"
        card = member_card(base, agent)
        card.name = entry.card.name
        card = sign_card(card, agent, "agent")
        invite = run.server.registry.issue_invitation(run.cid, "business")
        redeemed = run.server.registry.redeem(
            invite["link"].split("#", 1)[1], run.server.ports, base + "/card", MessageToDict(card)
        )
        name = redeemed["participant"]
        member = Member(
            name,
            redeemed["token"],
            HostedParticipant(name, base + "/card", agent, "agent", owner, "owner"),
            run.cid,
        )
        jwk = public_key_to_jwk(owner.public_key(), "owner")
        envelope = member.envelope(
            "join",
            {
                "card_url": member.person.card_url,
                "owner_key": jwk,
                "owner_proof": sign_owner_proof(run.cid, name, member.person.card_url, jwk, owner),
                "roles_requested": [entry.role],
                "surfaces": [],
                "vault": "local",
            },
        )
        reply = await run.server.accept(envelope, member.person.card_url)
        run.channels.extend((MessageToDict(card), envelope, reply))
        assert "error" not in reply, "business join refused"
        # A business signs its own charter acknowledgement, through the same owner proof.
        consent = member.decision_envelope("charter", run.cid, 1)
        reply = await run.server.accept(consent, member.person.card_url)
        run.channels.extend((consent, reply))
        assert "error" not in reply, "business charter refused"
        run.businesses.append(member)
        run.check(
            f"business_join.{index}",
            name in run.host.state.members,
            "business invitation redeemed with a signed card",
        )


async def business_hold(run: Journey) -> None:
    case = run.scenario.expect.distinguishing.business_holds
    assert case is not None
    business = run.businesses[case.business]
    folder = run.directory / f"business-{case.business}"
    config = ResourceConfig.model_validate(
        {
            "template": "resource",
            "name": "Slot",
            "windows": [{"start": 0, "end": 1}],
            "duration": 1,
            "limit": 1,
            "prerequisites": [],
        }
    )
    generate(folder, config, business.person.owner_key.public_key(), business.name)
    operation = Operations(folder)
    args: dict[str, Any] = {"start": 0, "end": 1, "prerequisites": []}
    held = operation.invoke("hold_slot", args)
    run.channels.extend((args, held))
    body = {"source": "chat", "content": json.dumps({"need": run.needs[case.need], "hold": held})}
    envelope = business.envelope("observe", body)
    reply = await run.server.accept(envelope, business.person.card_url)
    run.channels.extend((envelope, reply))
    assert "error" not in reply, "business hold observation refused"
    with connect(folder) as db:
        state = db.execute("SELECT state FROM bookings WHERE id=?", (held["id"],)).fetchone()
    run.check(
        "business_holds",
        state == ("held",),
        "joined business holds a real slot for the indexed need",
    )


async def minted_reading(run: Journey) -> None:
    case = run.scenario.expect.distinguishing.minted_reading
    assert case is not None
    snapshot = take_snapshot(run.pack.root)
    registry = TemplateRegistry()
    registry.register(
        run.cid,
        {
            entry.template: PackTemplate(
                snapshot.files[entry.template].decode(), snapshot.files[entry.tests].decode()
            )
            for entry in run.pack.manifest.mint or []
        },
    )
    entry = registry.resolve(run.cid, case.template)
    config = entry.config()
    assert isinstance(config, DeviceConfig), "minted_reading requires a reading template"
    owner = run.members["p1"].person.owner_key
    folder = run.directory / "minted"
    manifest_hash = generate(folder, config, owner.public_key(), "p1")
    sandbox = RecordingSandbox(folder, run.channels)
    try:
        await sandbox.start()
        attacks = await recorded_proof(folder, config, entry.tests(), run.channels)
        assert attacks and all(
            a.passed and not a.log.startswith("not an attack:") for a in attacks
        ), "Mint proof suite failed"
        publish(folder, sandbox, config)
        minted = Minted(
            folder,
            sandbox,
            manifest_hash,
            attacks,
            0,
            0,
            0,
            coalition_id=run.cid,
            template_name=case.template,
        )
        minted.approve(
            sign_detached(consent_payload(manifest_hash, "approve", {}), owner, "owner"), owner
        )
        enrolled = run.server.enroll_minted(run.cid, minted)
        run.channels.append(enrolled)
        # The scripted sensor is the trusted input boundary; serving reads use the real MCP tool.
        with connect(folder) as db:
            db.execute(
                "INSERT INTO readings VALUES (?, ?, ?, ?)",
                (config.fields[0].id, float(case.value), time.time(), 1.0),
            )
        async with sandbox.client() as client:
            reply = await client.call_tool("read_" + config.fields[0].id, {})
            data = dict(reply.structured_content or {})
            run.channels.extend(({"tool": "read_" + config.fields[0].id}, data))
            assert not reply.is_error and data.get("value") == float(case.value), (
                "Mint reading differs"
            )
        before = {i: dict(run.host.state.tasks[run.needs[i]]) for i in case.changes_needs}
        await run.send(
            "p1",
            "ripple",
            {
                "change": json.dumps({"reading": data["value"]}),
                "invalidates": [run.needs[i] for i in case.changes_needs],
            },
        )
        run.check(
            "minted_reading",
            all(run.host.state.tasks[run.needs[i]] != state for i, state in before.items()),
            "proved, approved Mint reading changed the indexed needs",
        )
    finally:
        sandbox.stop()
