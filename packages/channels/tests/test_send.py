# SPDX-License-Identifier: Apache-2.0
"""Outbound rules: the 24-hour window, retries, idempotency, rate limit, counts."""

from __future__ import annotations

import httpx
import pytest
from wa_support import WA_ID, Handler, rig

from coalitionkit_channels.whatsapp import (
    GRAPH_API_VERSION,
    NotBound,
    RateLimited,
    WhatsAppError,
    WindowClosed,
)

DAY = 24 * 3600.0


def status(code: int) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(code, json={"error": {"message": "x"}}, request=request)

    return handler


def test_text_inside_window_goes_to_pinned_endpoint() -> None:
    r = rig()
    r.channel.send("p1", "hello there")
    assert r.fake.kinds() == ["text"]
    req = r.fake.requests[0]
    assert f"/{GRAPH_API_VERSION}/" in str(req.url) and str(req.url).endswith("/messages")
    assert r.fake.bodies()[0]["text"]["body"] == "hello there"
    assert r.fake.bodies()[0]["to"] == WA_ID


def test_free_text_refused_outside_window_and_only_opener_template_sent() -> None:
    r = rig(window_open=False)
    with pytest.raises(WindowClosed):
        r.channel.send("p1", "free text")
    assert r.fake.kinds() == ["template"]
    assert r.fake.bodies()[0]["template"]["name"] == "hello_world"
    assert all("text" not in b for b in r.fake.bodies())


def test_window_closes_after_24_hours() -> None:
    r = rig()
    r.clock.now += DAY - 1
    r.channel.send("p1", "still open")
    r.clock.now += 2
    with pytest.raises(WindowClosed):
        r.channel.send("p1", "now closed")
    assert r.fake.kinds() == ["text", "template"]


def test_opener_sent_once_per_silence_and_reply_reopens_window() -> None:
    r = rig(window_open=False)
    for _ in range(3):
        with pytest.raises(WindowClosed):
            r.channel.send("p1", "x")
    assert r.fake.kinds() == ["template"]
    r.channel.window.inbound(WA_ID, r.clock.now)
    r.channel.send("p1", "x")
    assert r.fake.kinds() == ["template", "text"]


def test_retries_429_and_5xx_with_backoff_then_succeeds() -> None:
    r = rig()
    r.fake.script = [status(429), status(503)]
    r.channel.send("p1", "hi")
    assert len(r.fake.requests) == 3
    assert r.sleeps == [0.5, 1.0]
    assert r.channel.client.usage.retries == 2 and r.channel.client.usage.text == 1


def test_gives_up_after_max_attempts_and_4xx_is_not_retried() -> None:
    r = rig()
    r.fake.script = [status(500)] * 4
    with pytest.raises(WhatsAppError):
        r.channel.send("p1", "hi")
    assert len(r.fake.requests) == 4
    r2 = rig()
    r2.fake.script = [status(400)]
    with pytest.raises(WhatsAppError):
        r2.channel.send("p1", "hi")
    assert len(r2.fake.requests) == 1 and r2.sleeps == []


def test_same_door_message_id_is_sent_once() -> None:
    r = rig()
    r.channel.send_once("p1", "hi", "door-msg-1")
    r.channel.send_once("p1", "hi", "door-msg-1")
    r.channel.send_once("p1", "hi", "door-msg-2")
    assert r.fake.kinds() == ["text", "text"]


def test_failed_send_retried_by_door_sends_exactly_once_more() -> None:
    r = rig(max_attempts=1)
    r.fake.script = [status(500)]
    with pytest.raises(WhatsAppError):
        r.channel.send("p1", "same text")
    r.channel.send("p1", "same text")
    assert r.fake.kinds() == ["text", "text"]  # one failed attempt, one delivery
    r.channel.send("p1", "same text")  # a deliberate repeat is a new message
    assert len(r.fake.requests) == 3


def test_per_recipient_rate_limit() -> None:
    r = rig(max_per_minute=2)
    r.channel.send("p1", "a")
    r.channel.send("p1", "b")
    with pytest.raises(RateLimited):
        r.channel.send("p1", "c")
    r.clock.now += 61
    r.channel.send("p1", "c")
    assert len(r.fake.requests) == 3


def test_viewer_without_link_cannot_be_sent_to() -> None:
    r = rig(bound=False)
    with pytest.raises(NotBound):
        r.channel.send("p9", "hi")
    assert r.fake.requests == []
