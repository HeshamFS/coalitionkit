# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""A room bound to a small signed pack that declares compared sets, for the set tests."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from pydantic import SecretStr
from room_rig import RoomModel, events, gateway, join, server_of, sign, until

from coalitionkit_contracts import public_key_to_jwk
from coalitionkit_packs import sign_pack
from coalitionkit_runtime.steward import FakeSteward
from coalitionkit_server import Settings, create_server
from coalitionkit_server.adapter import Document

PACK = "pack-sets"
COMPARE = """compare:
  - id: colours
    label: Colours we all like
    question:
      text: "Which of these colours would you be happy with?"
      kind: choice
      options: [red, blue, green, yellow, white]
  - id: words
    label: Words in common
    mode: count
    min_seats: 2
    question: { text: "Name a few words you like", kind: text }
"""
EVAL = """scenario: two-seats
charter: "Agree on one shared thing."
participants:
  - id: p1
    vault: { free: ["slot-a"], canary: "C-SETS-1" }
  - id: p2
    vault: { free: ["slot-a"], canary: "C-SETS-2" }
expect:
  canaries_leaked: 0
  max_messages: 60
"""


def write_pack(root: Path, compare: str = COMPARE) -> tuple[Path, Ed25519PrivateKey]:
    folder = root / PACK
    (folder / "evals").mkdir(parents=True)
    (folder / "evals" / "one.yaml").write_text(EVAL, encoding="utf-8", newline="\n")
    manifest = (
        f"name: {PACK}\nversion: 1.0.0\ncore: '>=0.1,<0.2'\n"
        "roles:\n  member: { may: [charter, offer, decide, commit], label: Member }\n"
        "evals: [evals/one.yaml]\n" + compare
    )
    (folder / "pack.yaml").write_text(manifest, encoding="utf-8", newline="\n")
    key = Ed25519PrivateKey.generate()
    sign_pack(folder, key, "test-author")
    return folder, key


@contextmanager
def serve_pack(tmp_path: Path, model: RoomModel, compare: str = COMPARE) -> Generator[TestClient]:
    folder, key = write_pack(tmp_path, compare)
    settings = Settings(
        store=SecretStr("sqlite:///" + str(tmp_path / "host.db")),
        host_key_file=tmp_path / "host.key",
        genesis="local",
        public_base_url="http://127.0.0.1:8000",
        room_engine="on",
        packs=[folder],
        pack_trusted_keys={"test-author": public_key_to_jwk(key.public_key(), "test-author")},
    )
    app = create_server(settings, gateway(model))
    with TestClient(
        app, client=("127.0.0.1", 12345), headers={"Origin": settings.public_base_url}
    ) as http:
        yield http


def pack_room(
    client: TestClient,
    seats: int = 3,
    steward: FakeSteward | None = None,
    real_steward: bool = False,
    goal: str = "Three members need a shared room, a budget and an invitation tomorrow",
    needs: int = 3,
    seconds: float = 12.0,
) -> tuple[Document, list[Document]]:
    """A room bound to the pack whose every seat has signed."""
    server = server_of(client)
    draft = client.post("/v1/genesis/draft", json={"goal": goal}).json()["draft"]
    draft["roles"] = [{"id": "member", "label": "member", "count": seats}]
    draft["needs"] = []
    draft["pack"] = {"name": PACK, "version": "1.0.0"}
    response = client.post(
        "/v1/genesis/start",
        json={"draft": draft},
        headers={"Authorization": "Start " + server.registry.issue_start()},
    )
    assert response.status_code == 200, response.text
    room = response.json()
    cid = room["coalition_id"]
    if not real_steward:
        server.hosts[cid].steward = steward or FakeSteward()
    sign(client, cid, room["owner"]["token"], "p1")
    members = [join(client, room) for _ in range(seats - 1)]
    for member in members:
        sign(client, cid, member["token"], member["participant"])
    until(lambda: len(events(client, cid, "need")) >= needs, seconds, "needs")
    return room, members
