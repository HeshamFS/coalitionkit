# SPDX-License-Identifier: Apache-2.0
"""The same-origin wrapper answers a missing static file with a plain 404."""

from pathlib import Path

from starlette.testclient import TestClient
from starlette.types import Receive, Scope, Send

from coalitionkit_cli.web import Room


async def refuse(scope: Scope, receive: Receive, send: Send) -> None:
    raise RuntimeError("the server was not asked")


def test_a_missing_favicon_is_a_404_not_a_500(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<p>room</p>")
    client = TestClient(Room(refuse, tmp_path), raise_server_exceptions=False)
    assert client.get("/favicon.ico").status_code == 404
    assert client.get("/").status_code == 200
