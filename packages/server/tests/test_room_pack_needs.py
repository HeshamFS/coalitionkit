# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""A room bound to a pack with task templates takes the templates as its needs, once."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from pydantic import SecretStr
from room_rig import RoomModel, engine_of, events, gateway, join, server_of, sign, until

from coalitionkit_contracts import public_key_to_jwk
from coalitionkit_packs import sign_pack
from coalitionkit_server import Settings, create_server

PACK = "pack-templates"
TEMPLATES = """templates:
  - id: list
    title: Shopping list for the group
    description: One list of what to buy.
  - id: where
    title: Where to go for lunch
  - id: costs
    title: Share the costs of lunch
  - id: picture
    title: Poster for the walk
"""
EVAL = """scenario: two-seats
charter: "Agree on one shared thing."
participants:
  - id: p1
    vault: { free: ["slot-a"], canary: "C-TPL-1" }
  - id: p2
    vault: { free: ["slot-a"], canary: "C-TPL-2" }
expect:
  canaries_leaked: 0
  max_messages: 60
"""


@contextmanager
def serve_templates(tmp_path: Path) -> Generator[TestClient]:
    folder = tmp_path / PACK
    (folder / "evals").mkdir(parents=True)
    (folder / "evals" / "one.yaml").write_text(EVAL, encoding="utf-8", newline="\n")
    (folder / "templates.yaml").write_text(TEMPLATES, encoding="utf-8", newline="\n")
    (folder / "pack.yaml").write_text(
        f"name: {PACK}\nversion: 1.0.0\ncore: '>=0.1,<0.2'\n"
        "roles:\n  member: { may: [charter, offer, decide, commit], label: Member }\n"
        "task_templates: templates.yaml\nevals: [evals/one.yaml]\n",
        encoding="utf-8",
        newline="\n",
    )
    key = Ed25519PrivateKey.generate()
    sign_pack(folder, key, "test-author")
    settings = Settings(
        store=SecretStr("sqlite:///" + str(tmp_path / "host.db")),
        host_key_file=tmp_path / "host.key",
        genesis="local",
        public_base_url="http://127.0.0.1:8000",
        room_engine="on",
        packs=[folder],
        pack_trusted_keys={"test-author": public_key_to_jwk(key.public_key(), "test-author")},
    )
    app = create_server(settings, gateway(RoomModel()))
    with TestClient(
        app, client=("127.0.0.1", 12345), headers={"Origin": settings.public_base_url}
    ) as http:
        yield http


def test_a_pack_room_takes_its_templates_as_needs_once(tmp_path: Path) -> None:
    with serve_templates(tmp_path) as client:
        server = server_of(client)
        goal = "Two of us plan a day out with lunch and a walk"
        draft = client.post("/v1/genesis/draft", json={"goal": goal}).json()["draft"]
        draft["roles"] = [{"id": "member", "label": "member", "count": 2}]
        draft["needs"] = ["Something the goal reader found"]
        draft["pack"] = {"name": PACK, "version": "1.0.0"}
        response = client.post(
            "/v1/genesis/start",
            json={"draft": draft},
            headers={"Authorization": "Start " + server.registry.issue_start()},
        )
        assert response.status_code == 200, response.text
        room = response.json()
        cid = room["coalition_id"]
        sign(client, cid, room["owner"]["token"], "p1")
        member = join(client, room)
        sign(client, cid, member["token"], member["participant"])
        until(lambda: len(events(client, cid, "need")) >= 4, what="needs")
        doc = engine_of(client).read(cid)
        assert [(n["title"], n["kind"]) for n in doc["needs"]] == [
            ("Shopping list for the group", "list"),
            ("Where to go for lunch", "place"),
            ("Share the costs of lunch", "budget"),
            ("Poster for the walk", "image"),
        ]
        assert doc["needs"][0]["detail"] == "One list of what to buy."
        assert doc["needs_source"] == "pack"
        # Every seat has signed, and the templates were not drafted a second time.
        until(lambda: server.hosts[cid].state.accepted_charter(member["participant"]), what="sign")
        descriptions = [e["payload"]["description"] for e in events(client, cid, "need")]
        assert sorted(descriptions) == sorted(n["title"] for n in doc["needs"])
