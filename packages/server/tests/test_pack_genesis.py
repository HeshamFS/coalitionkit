# SPDX-License-Identifier: Apache-2.0
"""Pack installation and the Genesis public contract."""

import asyncio
import json
import shutil
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from coalitionkit_contracts import new_ulid, public_key_to_jwk
from coalitionkit_mcp.gateway import build_envelope
from coalitionkit_packs import sign_pack
from coalitionkit_runtime import Acknowledgement
from coalitionkit_server import Settings, create_server
from coalitionkit_server.adapter import Document
from coalitionkit_server.app import Server
from coalitionkit_server.genesis import enroll_member


@pytest.fixture
def pack_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> Iterator[TestClient]:
    monkeypatch.delenv("COALITIONKIT_META_API_KEY", raising=False)
    key = Ed25519PrivateKey.generate()
    folders: list[Path] = []
    fixtures = Path(__file__).parents[2] / "packs" / "tests" / "fixtures"
    for name, hints in [
        ("pack-alpha", "keywords: [alpha, shared], examples: [Finish together]"),
        ("pack-beta", "keywords: [beta, shared], examples: []"),
    ]:
        folder = tmp_path / name
        shutil.copytree(fixtures / name, folder)
        if name == "pack-alpha":
            manifest = folder / "pack.yaml"
            manifest.write_text(
                manifest.read_text().replace(
                    "schemas: { need: schemas/need-ext.json }",
                    "schemas: { need: schemas/need-ext.json, offer: schemas/offer-ext.json }",
                )
            )
            (folder / "schemas/offer-ext.json").write_text(
                json.dumps(
                    {
                        "type": "object",
                        "required": ["count"],
                        "properties": {"count": {"$ref": "count.json"}},
                    }
                )
            )
            (folder / "schemas/count.json").write_text('{"type": "integer", "x-private": true}')
        with (folder / "pack.yaml").open("a", encoding="utf-8") as stream:
            stream.write("\nsuggest: {" + hints + "}\n")
        sign_pack(folder, key, "test-author")
        folders.append(folder)
    broken = tmp_path / "broken"
    shutil.copytree(folders[0], broken)
    (broken / "pack.yaml").write_text("name: invalid\n", encoding="utf-8")
    sign_pack(broken, key, "test-author")
    app = create_server(
        Settings(
            packs=[*folders, folders[0], broken],
            pack_trusted_keys={"test-author": public_key_to_jwk(key.public_key(), "test-author")},
            store=SecretStr("sqlite:///:memory:"),
            host_key_file=tmp_path / "host.key",
            genesis="local",
        )
    )
    output = capsys.readouterr().out
    assert "Pack: pack-alpha 1.0.0 installed" in output
    assert "Pack refused:" in output and "duplicate" in output and "[manifest]" in output
    assert len(output.splitlines()) == 4
    with TestClient(
        app, client=("127.0.0.1", 1000), headers={"Origin": "http://127.0.0.1:8000"}
    ) as client:
        yield client


def test_install_and_public_metadata(pack_client: TestClient) -> None:
    response = pack_client.get("/v1/packs")
    assert response.status_code == 200
    packs = response.json()
    assert [p["name"] for p in packs] == ["pack-alpha", "pack-beta"]
    for pack in packs:
        assert set(pack) == {"name", "version", "roles", "vocabulary", "suggest"}
    assert "pack.yaml" not in response.text and "policies/" not in response.text
    server: Server = cast(FastAPI, pack_client.app).state.server
    for pack in server.packs.values():
        assert str(pack.root) not in response.text
        for policy in pack.manifest.policies or []:
            assert (pack.root / policy).read_text(encoding="utf-8") not in response.text
        assert set(pack.manifest.roles) == set(
            next(item for item in packs if item["name"] == pack.name)["roles"]
        )
    assert len(server.packs) == 2
    assert pack_client.get("/v1/packs", headers={"Origin": "http://other"}).status_code == 403


@pytest.mark.parametrize(
    "goal,expected",
    [
        ("ALPHA please", "pack-alpha"),
        ("beta please", "pack-beta"),
        ("no match", None),
        ("shared", None),
        ("alpha beta", None),
        ("alpha shared", "pack-alpha"),
        ("FINISH TOGETHER", "pack-alpha"),
        ("alphabet", None),
    ],
)
def test_suggestions(pack_client: TestClient, goal: str, expected: str | None) -> None:
    result = pack_client.post("/v1/genesis/draft", json={"goal": goal})
    assert result.status_code == 200
    suggestion = result.json()["suggested"]
    assert (suggestion["name"] if suggestion else None) == expected
    assert result.json()["draft"]["pack"] is None
    if suggestion:
        assert suggestion["why"]


def test_choice_and_start(pack_client: TestClient) -> None:
    ref = {"name": "pack-alpha", "version": "1.0.0"}
    result = pack_client.post(
        "/v1/genesis/draft",
        json={
            "goal": "Two coordinators and 3 helpers need agreement",
            "pack": ref,
        },
    ).json()
    assert result["draft"]["pack"] == ref
    assert [(r["id"], r["count"]) for r in result["draft"]["roles"]] == [
        ("coordinator", 2),
        ("helper", 3),
    ]
    assert result["vocabulary"] == pack_client.get("/v1/packs").json()[0]["vocabulary"]
    default = pack_client.post("/v1/genesis/draft", json={"goal": "Agree", "pack": ref}).json()
    assert [r["count"] for r in default["draft"]["roles"]] == [1, 1]
    server: Server = cast(FastAPI, pack_client.app).state.server
    code = server.registry.issue_start()
    headers = {"Authorization": "Start " + code}
    draft = result["draft"]
    draft["pack"] = {**ref, "version": "9.0.0"}
    assert (
        pack_client.post("/v1/genesis/start", json={"draft": draft}, headers=headers).status_code
        == 422
    )
    assert (
        pack_client.post(
            "/v1/genesis/draft", json={"goal": "Agree", "pack": draft["pack"]}
        ).status_code
        == 422
    )
    draft["pack"] = ref
    draft["roles"][0]["id"] = "other"
    assert (
        pack_client.post("/v1/genesis/start", json={"draft": draft}, headers=headers).status_code
        == 422
    )
    draft["roles"][0]["id"] = "coordinator"
    started = pack_client.post("/v1/genesis/start", json={"draft": draft}, headers=headers)
    assert started.status_code == 200, started.text
    charter = server.store.read(started.json()["coalition_id"])[0]["payload"]
    assert charter["pack"] == ref
    assert charter["roles"] == [{"id": "coordinator"}, {"id": "helper"}]


@pytest.mark.parametrize("mode", ["off", "admin"])
def test_pack_listing_gate(tmp_path: Path, mode: str) -> None:
    settings = Settings.model_validate(
        {
            "store": "sqlite:///:memory:",
            "host_key_file": tmp_path / "host.key",
            "genesis": mode,
            "admin_token": "secret",
        }
    )
    with TestClient(create_server(settings)) as client:
        assert client.get("/v1/packs").status_code == (404 if mode == "off" else 401)
        if mode == "admin":
            assert client.get("/v1/packs", headers={"Authorization": "Bearer secret"}).json() == []


def test_untrusted_pack_refused(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fixtures = Path(__file__).parents[2] / "packs" / "tests" / "fixtures"
    folder = tmp_path / "unsigned"
    shutil.copytree(fixtures / "pack-alpha", folder)
    settings = Settings(
        packs=[folder],
        store=SecretStr("sqlite:///:memory:"),
        host_key_file=tmp_path / "host.key",
        genesis="local",
    )
    with TestClient(create_server(settings)) as client:
        assert client.get("/healthz").status_code == 200
        server: Server = cast(FastAPI, client.app).state.server
        assert not server.packs
    assert "[signature] pack.sig: the pack is not signed" in capsys.readouterr().out


def test_multiline_loader_report_is_one_startup_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fixtures = Path(__file__).parents[2] / "packs" / "tests" / "fixtures"
    folder = tmp_path / "broken"
    shutil.copytree(fixtures / "pack-alpha", folder)
    (folder / "pack.yaml").write_text("name: [\n", encoding="utf-8")
    key = Ed25519PrivateKey.generate()
    sign_pack(folder, key, "test-author")
    settings = Settings(
        packs=[folder],
        pack_trusted_keys={"test-author": public_key_to_jwk(key.public_key(), "test-author")},
        store=SecretStr("sqlite:///:memory:"),
        host_key_file=tmp_path / "host.key",
    )
    with TestClient(create_server(settings)) as client:
        assert client.get("/healthz").status_code == 200
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    assert lines[0].startswith(f"Pack refused: {folder}: [yaml]")
    assert "not valid YAML" in lines[0]


def test_bound_runtime(pack_client: TestClient) -> None:
    server: Server = cast(FastAPI, pack_client.app).state.server
    key = ("pack-alpha", "1.0.0")
    pack = server.packs[key]
    # Keep the installed fixture's closed registry; constrain an existing core field.
    server.packs[key] = replace(
        pack, schemas={"need": {"properties": {"description": {"const": "Allowed"}}}}
    )
    charter: Document = {
        "goal": "Coordinate",
        "roles": [{"id": "coordinator"}],
        "rules": [],
        "deadline": "2099-01-01T00:00:00Z",
        "deciders": ["one"],
        "pack": {"name": key[0], "version": key[1]},
    }
    created = server.create(charter)
    cid = created["coalition_id"]
    redeemed = server.registry.redeem(
        created["invitations"][0]["invitation"], server.ports, None, None
    )
    asyncio.run(enroll_member(server, redeemed, "coordinator"))
    host = server.hosts[cid]
    assert [s["text"] for s in host.skills("one")] == list(pack.skills.values())
    person = server.registry.hosted_for(cid, "one")
    join_event = next(e for e in host.state.events.values() if e["type"] == "coalition.join")
    reply = asyncio.run(server.accept(join_event, person.card_url))
    assert reply["skills"] == host.skills("one")
    body: Document = {
        "description": "Need",
        "ext": {"description": "Wrong"},
        "requirements": [],
        "window": {"start": "2026-11-01T00:00:00Z", "end": "2099-01-01T00:00:00Z"},
    }
    refused = host.host_emit("need", body, {"audience": "coalition"})
    assert isinstance(refused, dict) and refused["payload"]["code"] == "schema_invalid"
    accepted = host.host_emit(
        "need", {**body, "ext": {"description": "Allowed"}}, {"audience": "coalition"}
    )
    assert isinstance(accepted, Acknowledgement) and accepted.accepted is not None
    role = pack.manifest.roles["coordinator"].model_copy(update={"may": ["decide"]})
    server.packs[key] = replace(
        server.packs[key],
        manifest=pack.manifest.model_copy(update={"roles": {"coordinator": role}}),
    )
    offer = build_envelope(
        person,
        cid,
        "coalition.offer",
        {
            "offer_id": new_ulid(),
            "target": {"kind": "need", "id": accepted.accepted["payload"]["need_id"]},
            "capacity": 1,
            "cost": {"minutes": 1, "money": 0, "effort": "low"},
            "valid_until": "2099-01-01T00:00:00Z",
        },
        scope={"audience": "coalition"},
    )
    assert asyncio.run(server.accept(offer, person.card_url))["error"]["code"] == "not_authorized"
    for ref in (
        None,
        {"name": "pack-beta", "version": "0.2.0"},
        {**charter["pack"], "version": "2.0.0"},
    ):
        revision = {**charter, "pack": ref}
        if ref is None:
            revision.pop("pack")
        refused = host.host_emit("charter", revision, {"audience": "coalition"})
        assert isinstance(refused, dict) and refused["payload"]["code"] == "not_authorized"
    assert isinstance(
        host.host_emit("charter", charter, {"audience": "coalition"}), Acknowledgement
    )


@pytest.mark.parametrize("reference", [None, {"name": "pack-alpha", "version": "1.0.0"}])
def test_pack_feed_for_every_viewer(
    pack_client: TestClient, reference: dict[str, str] | None
) -> None:
    server: Server = cast(FastAPI, pack_client.app).state.server
    draft = pack_client.post("/v1/genesis/draft", json={"goal": "Agree", "pack": reference}).json()[
        "draft"
    ]
    response = pack_client.post(
        "/v1/genesis/start",
        json={"draft": draft},
        headers={"Authorization": "Start " + server.registry.issue_start()},
    )
    assert response.status_code == 200, response.text
    coalition = response.json()["coalition_id"]
    hub = server.surfaces[coalition].state.hub
    for viewer in [*server.hosts[coalition].state.members, "another-viewer"]:
        # State metadata is not dependent on the viewer's hosted signing credentials.
        session = hub.feed_session(viewer)
        state = session.start()[1].snapshot
        if reference:
            assert state["pack"]["name"] == reference["name"]
            assert "need" in state["pack"]["schemas"]
            offer = state["pack"]["schemas"]["offer"]
            assert offer["properties"]["count"] == {"type": "integer", "x-private": True}
            fixture = Path(__file__).parents[3] / "apps/web/src/room/fixtures/bundled-offer.json"
            assert offer == json.loads(fixture.read_text(encoding="utf-8"))
            assert "pack-snapshot.invalid" not in json.dumps(state["pack"]["schemas"])
            assert state["pack"]["vocabulary"] and state["pack"]["views"]["order"]
        else:
            assert "pack" not in state
    assert "vocabulary" not in str(server.store.read(coalition))


def test_zero_pack_does_not_require_pack_catalog(tmp_path: Path) -> None:
    server = Server(
        Settings(
            store=SecretStr("sqlite:///:memory:"),
            host_key_file=tmp_path / "host.key",
            catalog_file=tmp_path / "absent.json",
        )
    )
    try:
        charter = json.loads((Path(__file__).parent / "fixtures/charter.json").read_text())
        coalition = server.create(charter)["coalition_id"]
        hub = server.surfaces[coalition].state.hub
        assert "pack" not in hub.feed_session("p1").start()[1].snapshot
    finally:
        server.close()
