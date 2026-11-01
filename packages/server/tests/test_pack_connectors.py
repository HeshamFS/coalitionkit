# SPDX-License-Identifier: Apache-2.0
import json
import shutil
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from google.protobuf.json_format import MessageToDict
from pydantic import SecretStr

from coalitionkit_contracts import public_key_to_jwk
from coalitionkit_packs import sign_pack
from coalitionkit_server import Settings, create_server
from coalitionkit_server.cards import member_card


def test_business_connector_card_and_coalition_boundary(tmp_path: Path) -> None:
    folder = tmp_path / "pack"
    shutil.copytree(Path(__file__).parents[2] / "packs/tests/fixtures/pack-gamma", folder)
    key = Ed25519PrivateKey.generate()
    sign_pack(folder, key, "author")
    app = create_server(
        Settings(
            packs=[folder],
            admin_token=SecretStr("operator"),
            pack_trusted_keys={"author": public_key_to_jwk(key.public_key(), "author")},
            store=SecretStr("sqlite:///:memory:"),
            host_key_file=tmp_path / "host.key",
        )
    )
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer operator"}
        charter = json.loads((Path(__file__).parent / "fixtures/charter.json").read_text())
        plain = client.post("/admin/coalitions", json=charter, headers=headers).json()[
            "coalition_id"
        ]
        ref = {"name": "pack-gamma", "version": "1.0.0"}
        charter["pack"] = ref
        charter["roles"] = [{"id": "helper"}]  # a bound charter uses only the pack's roles
        bound = client.post("/admin/coalitions", json=charter, headers=headers).json()[
            "coalition_id"
        ]
        body = {"pack": ref, "connector": "probe"}
        assert (
            client.post(
                f"/admin/coalitions/{plain}/connectors", json=body, headers=headers
            ).status_code
            == 422
        )
        reply = client.post(f"/admin/coalitions/{bound}/connectors", json=body, headers=headers)
        assert reply.status_code == 200, reply.text
        invitation = reply.json()["invitation"].split("#", 1)[1]
        assert client.post("/invitations/redeem", json={"invitation": invitation}).json()[
            "detail"
        ] == ("business invitation requires a signed card")
        signed = MessageToDict(member_card("http://connector", Ed25519PrivateKey.generate()))
        unsigned = {key: value for key, value in signed.items() if key != "signatures"}
        request = {"invitation": invitation, "card_url": "http://connector/card", "card": unsigned}
        refused = client.post("/invitations/redeem", json=request)
        assert refused.status_code == 400 and refused.json()["detail"] == "card refused: unsigned"
        request["card"] = signed
        accepted = client.post("/invitations/redeem", json=request)
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["coalition_id"] == bound
        assert client.post("/invitations/redeem", json=request).status_code == 400
