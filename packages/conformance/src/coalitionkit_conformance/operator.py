# SPDX-License-Identifier: Apache-2.0
"""Explicit setup boundary; adapters never provide protocol assertions."""

from typing import Protocol
from urllib.parse import urlsplit

import httpx

from .report import Document


class OperatorUnavailable(Exception):
    """The operator cannot provision a required fixture."""


class Operator(Protocol):
    redeem_url: str
    feed_url: str

    async def create(self, charter: Document) -> Document: ...
    async def invite(self, coalition: str, participant: str) -> str: ...
    async def emit(
        self,
        coalition: str,
        kind: str,
        payload: Document,
        scope: Document | None = None,
        *,
        sources: list[str] | None = None,
    ) -> Document: ...


class ReferenceOperator:
    """Reference admin HTTP adapter; unsupported setup is never simulated."""

    def __init__(self, target: str, token: str, timeout: float = 20) -> None:
        if not token.strip():
            raise ValueError("admin token file is empty")
        url = urlsplit(target)
        self.base = f"{url.scheme}://{url.netloc}"
        self.redeem_url = self.base + "/invitations/redeem"
        self.feed_url = self.base + "/v1/feed"
        self._token, self.timeout = token.strip(), timeout

    async def _post(self, path: str, body: Document) -> Document:
        async with httpx.AsyncClient(timeout=self.timeout) as http:
            response = await http.post(
                self.base + path,
                json=body,
                headers={"Authorization": "Bearer " + self._token},
            )
            if response.status_code != 200:
                raise OperatorUnavailable(f"POST {path}: HTTP {response.status_code}")
            result: Document = response.json()
            return result

    async def create(self, charter: Document) -> Document:
        return await self._post("/admin/coalitions", charter)

    async def invite(self, coalition: str, participant: str) -> str:
        result = await self._post(
            f"/admin/coalitions/{coalition}/invitations", {"participant": participant}
        )
        return str(result["invitation"])

    async def emit(
        self,
        coalition: str,
        kind: str,
        payload: Document,
        scope: Document | None = None,
        *,
        sources: list[str] | None = None,
    ) -> Document:
        body: Document = {"type": kind, "payload": payload}
        if scope is not None:
            body["scope"] = scope
        if sources is not None:
            body["sources"] = sources
        return await self._post(f"/admin/coalitions/{coalition}/host-events", body)
