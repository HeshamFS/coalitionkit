# SPDX-License-Identifier: Apache-2.0
"""A real ``coalitionkit-server`` on a local port, and scripted members that reach it over A2A.

The server runs either in a thread of this process (so a scenario can also reach the host to
publish needs and plans, as the Gardener does) or as a child process that can be killed.
Members are the hosted participants the server created for them; they sign their own envelopes.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import httpx
import uvicorn
from pydantic import SecretStr

from coalitionkit_contracts import public_key_to_jwk, sign_owner_proof
from coalitionkit_edges.a2a import MemberClient
from coalitionkit_mcp import HostedParticipant
from coalitionkit_mcp.elicit import sign_decision
from coalitionkit_mcp.gateway import build_envelope
from coalitionkit_models import ModelGateway
from coalitionkit_runtime import Acknowledgement, CoalitionHost
from coalitionkit_runtime.host import utc_now
from coalitionkit_server import Settings, create_server, hook
from coalitionkit_server.app import Server

Document = dict[str, Any]
PUBLIC: Document = {"audience": "coalition"}
HOST_ONLY: Document = {"audience": "host"}
FAR = "2099-01-01T00:00:00Z"
ADMIN = "admin-acceptance"


def emitted(reply: Acknowledgement | Document) -> Document | None:
    """The event a host accepted, or None when the host refused."""
    if isinstance(reply, Acknowledgement):
        return reply.accepted
    return None


def emit(
    host: CoalitionHost, kind: str, payload: Document, scope: Document | None = None
) -> Document:
    """Publish as the host; return the accepted event or raise with the refusal code."""
    reply = host.host_emit(kind, payload, scope or PUBLIC)
    event = emitted(reply)
    if event is None:
        refusal = cast(Document, reply)
        raise AssertionError(f"host refused {kind}: {refusal['payload']['code']}")
    return event


def new_need(host: CoalitionHost) -> str:
    """Publish one open task as the host; return its ID."""
    body: Document = {
        "description": "Shared task",
        "requirements": [],
        "window": {"start": "2026-01-01T00:00:00Z", "end": FAR},
    }
    return str(emit(host, "need", body)["payload"]["need_id"])


def scoped(*participants: str) -> Document:
    """A scope that names exactly these participants (the sender always sees its own event)."""
    return {"audience": "participants", "participants": sorted(set(participants))}


class HookChannel:
    """The side channel of the server's acceptance hook (``coalitionkit_server.hook``)."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.file = directory / "boundaries.jsonl"

    def lines(self) -> list[Document]:
        if not self.file.exists():
            return []
        text = self.file.read_text(encoding="utf-8")
        return [json.loads(line) for line in text.splitlines() if line.strip().endswith("}")]

    def at(self, event_id: str, stage: str) -> float | None:
        """The ``perf_counter`` reading when the server reached ``stage`` for the event."""
        for line in self.lines():
            if line["event_id"] == event_id and line["stage"] == stage:
                return float(line["t"])
        return None

    def wait_for(self, event_id: str, stage: str, timeout: float = 30.0) -> float:
        until = time.monotonic() + timeout
        while time.monotonic() < until:
            found = self.at(event_id, stage)
            if found is not None:
                return found
            time.sleep(0.01)
        raise AssertionError(f"the server never reached {stage} for {event_id}")

    def environment(self) -> dict[str, str]:
        return {hook.DIR_VAR: str(self.directory)}


def make_settings(store_url: str, directory: Path, port: int) -> Settings:
    return Settings(
        store=SecretStr(store_url),
        host_key_file=directory / "keys" / "host.key",
        bind_port=port,
        public_base_url=f"http://127.0.0.1:{port}",
        admin_token=SecretStr(ADMIN),
    )


class Instance:
    """The server in a thread of this process."""

    def __init__(
        self,
        settings: Settings,
        model_gateway: ModelGateway | None = None,
        channel: HookChannel | None = None,
    ) -> None:
        self.channel = channel
        self.settings = settings
        self.base = settings.public_base_url
        self.app = create_server(settings, model_gateway)
        self.state: Server = self.app.state.server
        self.worker = uvicorn.Server(
            uvicorn.Config(
                self.app,
                host="127.0.0.1",
                port=settings.bind_port,
                log_level="warning",
                access_log=False,
                timeout_keep_alive=30,
            )
        )
        self.thread = threading.Thread(target=self.worker.run, daemon=True)

    def __enter__(self) -> Instance:
        if self.channel is not None:
            os.environ.update(self.channel.environment())
        self.thread.start()
        until = time.monotonic() + 30
        while not self.worker.started:
            if not self.thread.is_alive() or time.monotonic() > until:
                raise RuntimeError("the server did not start")
            time.sleep(0.02)
        return self

    def __exit__(self, *args: object) -> None:
        # The Steward's HTTP clients belong to the server's audit loop: close them there.
        closing = asyncio.run_coroutine_threadsafe(
            self.state.gateway.aclose(), self.state.runner.loop
        )
        closing.result(30)
        if self.channel is not None:
            os.environ.pop(hook.DIR_VAR, None)
        self.worker.should_exit = True
        self.thread.join(30)
        if self.thread.is_alive():
            raise RuntimeError("the server did not stop")

    def host(self, coalition_id: str) -> CoalitionHost:
        return self.state.hosts[coalition_id]


class ChildServer:
    """The server as a child process, so it can be killed the hard way."""

    def __init__(self, settings: Settings, channel: HookChannel | None = None) -> None:
        self.settings = settings
        self.channel = channel
        self.pause = ""
        self.base = settings.public_base_url
        self.process: subprocess.Popen[bytes] | None = None

    def environment(self) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if "KEY" not in k.upper()}
        env.update(
            COALITIONKIT_STORE=self.settings.store.get_secret_value(),
            COALITIONKIT_HOST_KEY_FILE=str(self.settings.host_key_file),
            COALITIONKIT_PUBLIC_BASE_URL=self.settings.public_base_url,
            COALITIONKIT_BIND_PORT=str(self.settings.bind_port),
            COALITIONKIT_ADMIN_TOKEN=ADMIN,
        )
        if self.channel is not None:
            env.update(self.channel.environment())
            if self.pause:
                env[hook.PAUSE_VAR] = self.pause
        return env

    def start(self, timeout: float = 60.0) -> float:
        """Start the process; return the seconds until ``/healthz`` answered."""
        started = time.perf_counter()
        code = "from coalitionkit_server.cli import main; main()"
        self.process = subprocess.Popen(
            [sys.executable, "-c", code, "serve"],
            env=self.environment(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        until = time.monotonic() + timeout
        while time.monotonic() < until:
            if self.process.poll() is not None:
                raise RuntimeError("the server process exited while starting")
            try:
                if httpx.get(self.base + "/healthz", timeout=2).status_code == 200:
                    return time.perf_counter() - started
            except httpx.HTTPError:
                time.sleep(0.05)
        raise RuntimeError("the server process did not become healthy")

    def kill(self) -> None:
        """Terminate without any shutdown work (no lifespan, no flush)."""
        if self.process is not None and self.process.poll() is None:
            self.process.kill()
            self.process.wait(30)

    def __enter__(self) -> ChildServer:
        return self

    def __exit__(self, *args: object) -> None:
        self.kill()


@dataclass
class Member:
    name: str
    token: str
    person: HostedParticipant
    coalition_id: str
    client: MemberClient | None = field(default=None, repr=False)

    def envelope(self, kind: str, body: Document, scope: Document | None = None) -> Document:
        return build_envelope(
            self.person, self.coalition_id, f"coalition.{kind}", body, scope=scope or PUBLIC
        )

    def join_envelope(self) -> Document:
        person = self.person
        jwk = public_key_to_jwk(person.owner_key.public_key(), person.owner_kid)
        body: Document = {
            "card_url": person.card_url,
            "owner_key": jwk,
            "owner_proof": sign_owner_proof(
                self.coalition_id, self.name, person.card_url, jwk, person.owner_key
            ),
            "roles_requested": ["member"],
            "surfaces": ["web"],
            "vault": "hosted",
        }
        return self.envelope("join", body)

    def decision_envelope(
        self,
        kind: str,
        subject: str,
        revision: int,
        choice: str | None = None,
        scope: Document | None = None,
    ) -> Document:
        ref = {"kind": kind, "id": subject, "revision": revision}
        body = sign_decision(
            self.person, self.coalition_id, ref, choice or subject, True, utc_now()
        )
        return self.envelope("decide", body, scope)

    def offer_envelope(
        self, task: str, minutes: int, money: int, offer_id: str, scope: Document | None = None
    ) -> Document:
        body: Document = {
            "offer_id": offer_id,
            "target": {"kind": "need", "id": task},
            "capacity": 1,
            "cost": {"minutes": minutes, "money": money, "effort": "low"},
            "valid_until": FAR,
        }
        return self.envelope("offer", body, scope)

    def observe_envelope(self, content: str) -> Document:
        return self.envelope("observe", {"source": "chat", "content": content})

    async def connect(self, http: httpx.AsyncClient, state: Server) -> MemberClient:
        self.client = await MemberClient.connect(
            http, state.signer.card_url, self.token, state.key.public_key(), "host"
        )
        return self.client

    async def send(self, envelope: Document) -> Any:
        assert self.client is not None, "connect the member first"
        return await self.client.send(envelope)


def charter(deciders: list[str]) -> Document:
    return {
        "goal": "Coordinate shared tasks",
        "roles": [{"id": "member"}],
        "rules": [],
        "deadline": FAR,
        "deciders": deciders,
    }


def provision(
    base: str, state: Server, names: list[str], deciders: list[str], http: httpx.Client
) -> tuple[str, dict[str, Member]]:
    """Create a Coalition through the admin API and redeem an invitation for every name."""
    auth = {"Authorization": f"Bearer {ADMIN}"}
    created = http.post(f"{base}/admin/coalitions", json=charter(deciders), headers=auth)
    created.raise_for_status()
    body = created.json()
    coalition = body["coalition_id"]
    tokens = {item["participant"]: item["invitation"] for item in body["invitations"]}
    for name in names:
        if name not in tokens:
            issued = http.post(
                f"{base}/admin/coalitions/{coalition}/invitations",
                json={"participant": name},
                headers=auth,
            )
            issued.raise_for_status()
            tokens[name] = issued.json()["invitation"]
    members: dict[str, Member] = {}
    for name in names:
        redeemed = http.post(f"{base}/invitations/redeem", json={"invitation": tokens[name]})
        redeemed.raise_for_status()
        token = redeemed.json()["token"]
        members[name] = Member(name, token, state.registry.hosted_for(coalition, name), coalition)
    return coalition, members
