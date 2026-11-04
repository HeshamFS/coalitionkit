# SPDX-License-Identifier: Apache-2.0
"""Web search providers, scripted: every hit is a real URL the search returned."""

from __future__ import annotations

import json
from typing import Any

import httpx2
import pytest

from coalitionkit_models import (
    BraveSearch,
    CostMeter,
    DdgSearch,
    MetaSearch,
    MissingKeyError,
    ProviderError,
    Settings,
    load_price_table,
    make_search,
)
from coalitionkit_models.search import read_meta_response, web_url

FOUND = ["https://example.org/hall", "https://example.net/garden/"]


def settings(**kw: Any) -> Settings:
    return Settings(_env_file=None, meta_api_key="k", **kw)  # pyright: ignore[reportCallIssue]


def body(told: list[dict[str, str]], sources: list[str] = FOUND) -> dict[str, Any]:
    links = [{"type": "url", "url": u} for u in sources]
    action = {"type": "search", "query": "a hall for twelve", "sources": links}
    return {
        "output": [
            {"type": "reasoning"},
            {
                "type": "message",
                "phase": "commentary",
                "content": [{"type": "output_text", "text": "Searching"}],
            },
            {"type": "web_search_call", "status": "completed", "action": action},
            {"type": "web_search_call", "action": {"type": "open_page", "url": FOUND[0]}},
            {
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps({"hits": told})}],
            },
        ],
        "usage": {
            "input_tokens": 3000,
            "input_tokens_details": {"cached_tokens": 1000},
            "output_tokens": 500,
            "output_tokens_details": {"reasoning_tokens": 300},
        },
    }


def test_a_url_the_search_did_not_return_is_never_a_hit() -> None:
    told = [
        {"title": "The hall", "url": "https://www.example.org/hall/", "snippet": "Seats 40."},
        {"title": "Made up", "url": "https://invented.example/x", "snippet": "Not real."},
    ]
    hits, queries = read_meta_response(body(told), 5)
    assert [h.url for h in hits] == ["https://www.example.org/hall/", FOUND[1]]
    assert hits[0].title == "The hall" and hits[0].snippet == "Seats 40."
    assert hits[1].title == "example.net", "an undescribed page is named by its host"
    assert queries == ["a hall for twelve"]
    assert all(h.source == "meta" for h in hits)


def test_only_http_urls_with_a_host_count() -> None:
    assert web_url("https://example.org/a") == "https://example.org/a"
    for bad in ("javascript:alert(1)", "example.org", "ftp://example.org", "https://", None, 3):
        assert web_url(bad) is None


async def test_meta_asks_the_built_in_tool_and_meters_the_tokens() -> None:
    sent: list[dict[str, Any]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent.append({"url": str(request.url), "json": json.loads(request.content)})
        assert request.headers["authorization"] == "Bearer k"
        return httpx2.Response(200, json=body([]))

    meter = CostMeter(load_price_table())
    search = MetaSearch(
        settings(), meter=meter, http=httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    )
    run = await search.search("a hall for twelve", limit=3, coalition_id="c1", participant="p1")
    request = sent[0]["json"]
    assert sent[0]["url"].endswith("/v1/responses")
    assert request["tools"] == [{"type": "web_search"}]
    assert request["max_tool_calls"] == 2 and request["include"] == [
        "web_search_call.action.sources"
    ]
    assert json.loads(request["input"]) == {"query": "a hall for twelve", "most_results": 3}
    assert [h.url for h in run.hits] == FOUND
    assert run.tokens == (3000, 500) and run.cost_micro_usd > 0
    assert meter.total("c1") == run.cost_micro_usd
    assert meter.records[0].participant == "p1" and meter.records[0].reasoning_tokens == 300


async def test_meta_without_a_key_names_the_variable() -> None:
    search = MetaSearch(Settings(_env_file=None))  # pyright: ignore[reportCallIssue]
    with pytest.raises(MissingKeyError, match="COALITIONKIT_META_API_KEY"):
        await search.search("q", limit=2)


async def test_a_provider_error_never_echoes_the_body() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(400, json={"error": {"message": "secret detail"}})

    search = MetaSearch(
        settings(), http=httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    )
    with pytest.raises(ProviderError) as caught:
        await search.search("q", limit=2)
    assert caught.value.status == 400 and "secret" not in str(caught.value)


class FakeDdgs:
    def __init__(self) -> None:
        self.asked: list[tuple[str, int]] = []

    def text(self, query: str, max_results: int) -> list[dict[str, str]]:
        self.asked.append((query, max_results))
        return [
            {"title": "A hall", "href": "https://example.org/hall", "body": "Seats forty."},
            {"title": "Same hall", "href": "https://example.org/hall/", "body": "Again."},
            {"title": "Bad", "href": "javascript:void(0)", "body": "x"},
            {"title": "A garden", "href": "https://example.net/garden", "body": "Open air."},
        ]


async def test_ddg_is_keyless_and_drops_doubles_and_bad_urls() -> None:
    backend = FakeDdgs()
    run = await DdgSearch(settings(), backend=backend).search("a hall", limit=4)
    assert backend.asked == [("a hall", 4)]
    assert [h.url for h in run.hits] == ["https://example.org/hall", "https://example.net/garden"]
    assert run.cost_micro_usd == 0 and run.queries == ("a hall",)


async def test_brave_reads_its_own_key() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.headers["x-subscription-token"] == "bk"
        assert request.url.params["q"] == "a hall"
        rows = [{"title": "A hall", "url": "https://example.org/hall", "description": "Big."}]
        return httpx2.Response(200, json={"web": {"results": rows}})

    client = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    run = await BraveSearch(settings(brave_api_key="bk"), http=client).search("a hall", limit=2)
    assert [(h.title, h.source) for h in run.hits] == [("A hall", "brave")]
    with pytest.raises(MissingKeyError, match="COALITIONKIT_BRAVE_API_KEY"):
        await BraveSearch(settings()).search("a hall", limit=2)


def test_search_is_off_unless_a_provider_is_named() -> None:
    assert make_search(settings()) is None
    for name, kind in (("meta", MetaSearch), ("ddg", DdgSearch), ("brave", BraveSearch)):
        assert isinstance(make_search(settings(search_provider=name)), kind)
