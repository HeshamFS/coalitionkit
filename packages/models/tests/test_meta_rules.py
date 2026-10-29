# SPDX-License-Identifier: Apache-2.0
"""Scripted tests for the Meta rules: base URL, reasoning budget, route switch, media, schema."""

from __future__ import annotations

import io
import json
import random
import struct
import wave
from typing import Any

import httpx2
import pytest
from pydantic import BaseModel, ConfigDict

from coalitionkit_models import (
    BudgetExhaustedError,
    CostMeter,
    FakeModel,
    MediaClient,
    MediaInputError,
    ModelGateway,
    ProviderError,
    SamParseError,
    SchemaValidationError,
    ScriptedResponse,
    Settings,
    ToolCall,
    TruncatedReply,
    load_price_table,
    parse_sam_output,
    validate_wav,
)

KEY = "test-not-a-real-key"
COALITION = "01M4XRC000000G40R40M30E209"
USER: Any = [{"role": "user", "content": "x"}]


def _settings(**kw: Any) -> Settings:
    return Settings(_env_file=None, meta_api_key=KEY, **kw)  # pyright: ignore[reportCallIssue]


def _gateway(
    script: list[ScriptedResponse | BaseException], **kw: Any
) -> tuple[ModelGateway, FakeModel, CostMeter]:
    async def sleep(_: float) -> None:
        return None

    meter = CostMeter(load_price_table())
    fake = FakeModel(script)
    gateway = ModelGateway(
        _settings(**kw), transport=fake, meter=meter, sleep=sleep, rng=random.Random(1)
    )
    return gateway, fake, meter


def test_default_base_url_is_the_meta_endpoint() -> None:
    assert _settings().meta_base_url == "https://api.meta.ai/v1"
    assert _settings().route("composer").base_url == "https://api.meta.ai/v1"


def test_steward_route_switch() -> None:
    meta = _settings().route("steward")
    assert (meta.model, meta.key_name) == ("muse-spark-1.3", "meta")
    baseten = _settings(steward_provider="baseten").route("steward")
    assert baseten.key_name == "baseten"
    assert baseten.model == "meta-models/muse-spark-open"
    assert baseten.base_url == "https://inference.baseten.co/v1"


def test_prices_cover_contributors_and_media() -> None:
    table = load_price_table()
    assert table.version == "2026-10-28"
    contributor = "muse-spark-1.3-contributor"
    assert table.cost_micro_usd(contributor, prompt_tokens=1_000_000, completion_tokens=0) == (
        100_000
    )
    assert (
        table.cost_micro_usd(
            contributor,
            prompt_tokens=1_000_000,
            completion_tokens=1_000_000,
            cached_tokens=1_000_000,
        )
        == 2_000 + 200_000
    )
    assert table.media_cost_micro_usd("muse-image-1.0", images=3) == 30_000
    assert table.media_cost_micro_usd("sam-3.1", images=1000) == 2_500_000
    # $0.18 per audio hour: 10.3 s is 515 micro-USD
    assert table.media_cost_micro_usd("muse-voice-transcribe-1.0", audio_ms=10_300) == 515
    assert table.media_cost_micro_usd("muse-voice-transcribe-1.0", audio_ms=1) == 1


async def test_effort_and_budget_are_sent_per_role() -> None:
    gateway, fake, _ = _gateway([ScriptedResponse("a")] * 4)
    for role in ("hosted_agent", "composer", "gardener", "steward"):
        await gateway.complete(role, USER)
    sent = {role: opts for role, _, opts in fake.calls}
    assert sent["hosted_agent"]["reasoning_effort"] == "minimal"
    assert sent["composer"]["reasoning_effort"] == "low"
    assert sent["gardener"]["reasoning_effort"] == "low"
    assert sent["steward"]["reasoning_effort"] == "low"
    assert all(opts["max_completion_tokens"] == 4000 for opts in sent.values())


async def test_budget_and_effort_can_be_overridden_and_legacy_cap_is_dropped() -> None:
    gateway, fake, _ = _gateway(
        [ScriptedResponse("a")], completion_budget={"composer": 900}, reasoning_effort={}
    )
    await gateway.complete("composer", USER, max_tokens=50)
    opts = fake.calls[0][2]
    assert opts["max_completion_tokens"] == 900
    assert "max_tokens" not in opts
    assert "reasoning_effort" not in opts


async def test_no_effort_is_sent_off_the_meta_route() -> None:
    gateway, fake, _ = _gateway([ScriptedResponse("a")], steward_provider="baseten")
    await gateway.complete("steward", USER)
    assert "reasoning_effort" not in fake.calls[0][2]


async def test_truncated_reply_retries_once_with_double_budget() -> None:
    cut = ScriptedResponse("", 10, 4000, reasoning_tokens=4000, finish_reason="length")
    gateway, fake, meter = _gateway([cut, ScriptedResponse("done", 10, 900, reasoning_tokens=700)])
    result = await gateway.complete("composer", USER, coalition_id=COALITION)
    assert result.text == "done"
    assert [c[2]["max_completion_tokens"] for c in fake.calls] == [4000, 8000]
    assert meter.reasoning_tokens(COALITION) == 4700  # both calls are metered
    assert len(meter.records) == 2


async def test_truncated_twice_raises_typed_error() -> None:
    cut = ScriptedResponse("", 10, 100, finish_reason="length")
    gateway, fake, _ = _gateway([cut, cut, ScriptedResponse("never")])
    with pytest.raises(TruncatedReply) as info:
        await gateway.complete("composer", USER)
    assert info.value.budget == 8000
    assert isinstance(info.value, ProviderError)
    assert len(fake.calls) == 2


async def test_text_cut_by_length_is_not_retried_and_tool_calls_are_not_empty() -> None:
    partial = ScriptedResponse("half an ans", finish_reason="length")
    gateway, fake, _ = _gateway([partial])
    assert (await gateway.complete("composer", USER)).text == "half an ans"
    call = ToolCall("c1", "lookup", {"q": "a"}, '{"q": "a"}')
    gateway, fake, _ = _gateway([ScriptedResponse("", tool_calls=(call,), finish_reason="length")])
    assert (await gateway.complete("composer", USER)).tool_calls == (call,)
    assert len(fake.calls) == 1


async def test_tools_are_passed_and_calls_come_back_typed() -> None:
    call = ToolCall("c1", "lookup", {"q": "a"}, '{"q": "a"}')
    reply = ScriptedResponse("", tool_calls=(call,), finish_reason="tool_calls")
    gateway, fake, _ = _gateway([reply])
    tools = [{"type": "function", "function": {"name": "lookup", "parameters": {"type": "object"}}}]
    result = await gateway.complete("composer", USER, tools=tools, tool_choice="auto")
    assert fake.calls[0][2]["tools"] == tools
    assert result.tool_calls[0].name == "lookup"
    assert result.tool_calls[0].arguments == {"q": "a"}


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    word: str
    count: int = 0


async def test_response_schema_is_strict_and_reply_is_validated() -> None:
    gateway, fake, _ = _gateway([ScriptedResponse('{"word": "hi", "count": 2}')])
    result = await gateway.complete("composer", USER, response_schema=Answer)
    fmt = fake.calls[0][2]["response_format"]
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["strict"] is True
    schema = fmt["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["word", "count"]
    assert result.parsed == Answer(word="hi", count=2)


@pytest.mark.parametrize("reply", ['{"word": 3}', "not json", '{"word": "a", "extra": 1}'])
async def test_response_schema_validation_failure(reply: str) -> None:
    gateway, _, _ = _gateway([ScriptedResponse(reply)])
    with pytest.raises(SchemaValidationError) as info:
        await gateway.complete("composer", USER, response_schema=Answer)
    assert info.value.text == reply


# SAM output recorded from sam-3.1 (mask payloads shortened; the grammar is unchanged).
SAM_TWO = (
    "<0f>0<|box;x1=1029;y1=876;x2=1532;y2=1380;w=1600;h=1600;c=0.976608157157898|>"
    "<|mask;x=0;y=0;c=0.976608157157898;data=505,504,~!!$!H#K{$XQ{k$`p`T46R3^g|>,"
    "1<|box;x1=408;y1=1146;x2=592;y2=1329;w=1600;h=1600;c=0.9649122953414917|>"
    "<|mask;x=0;y=0;c=0.9649122953414917;data=184,185,!!!Bq#K{$]^xJQMT$u%LZ|>"
)


def test_sam_parser_boxes_masks_and_ordinals() -> None:
    first, second = parse_sam_output(SAM_TWO)
    assert (first.ordinal, second.ordinal) == (0, 1)
    assert (first.box.x1, first.box.y1, first.box.x2, first.box.y2) == (1029, 876, 1532, 1380)
    assert (first.box.width, first.box.height) == (1600, 1600)
    assert first.confidence == pytest.approx(0.976608157157898)
    assert first.mask_kind == "lossless"
    assert first.mask_payload.startswith("505,504,~!!$!H")
    assert first.mask is not None
    assert (first.mask.width, first.mask.height) == (505, 504)
    assert second.mask_kind == "one_bit"


def test_sam_parser_without_confidence_empty_and_video_frames() -> None:
    plain = "<0f>0<|box;x1=1;y1=2;x2=3;y2=4;w=10;h=20|><|mask;x=0;y=0;data=3,3,~abc|>"
    (only,) = parse_sam_output(plain)
    assert only.confidence is None
    assert parse_sam_output("<0f>") == []
    video = plain + "\n" + plain.replace("<0f>", "<1f>")
    assert [s.frame for s in parse_sam_output(video)] == [0, 1]


@pytest.mark.parametrize(
    "bad", ["no frame marker", "<0f>garbage", "<0f>0<|box;x1=1;y1=2|>", "<0f>0<|box;x1=a|>"]
)
def test_sam_parser_rejects_malformed(bad: str) -> None:
    with pytest.raises(SamParseError):
        parse_sam_output(bad)


def _wav(channels: int = 1, width: int = 2, rate: int = 16_000, frames: int = 160) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(b"\0" * frames * width * channels)
    return buf.getvalue()


def test_wav_validation() -> None:
    assert validate_wav(_wav()).duration_ms == 10
    assert validate_wav(_wav(rate=24_000)).sample_rate == 24_000
    assert struct.calcsize("<h") == 2
    for bad in (_wav(channels=2), _wav(width=1), _wav(rate=8_000), b"RIFFnope", b""):
        with pytest.raises(MediaInputError):
            validate_wav(bad)


def _media(handler: Any, meter: CostMeter | None = None) -> MediaClient:
    async def sleep(_: float) -> None:
        return None

    http = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    return MediaClient(_settings(), meter=meter, http=http, sleep=sleep, rng=random.Random(1))


async def test_media_image_generation_request_and_cost() -> None:
    seen: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(200, json={"data": [{"b64_json": "aGk="}]})

    meter = CostMeter(load_price_table())
    data = await _media(handler, meter).generate_image("a plain shape", coalition_id=COALITION)
    assert data == b"hi"
    request = seen[0]
    assert str(request.url) == "https://api.meta.ai/v1/images/generations"
    assert request.headers["authorization"] == f"Bearer {KEY}"
    assert json.loads(request.content)["model"] == "muse-image-1.0"
    assert meter.total(COALITION) == 10_000


async def test_media_segment_request_and_parse() -> None:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(json.loads(request.content))
        text = {"output": [{"content": [{"type": "output_text", "text": SAM_TWO}]}]}
        return httpx2.Response(200, json=text)

    meter = CostMeter(load_price_table())
    out = await _media(handler, meter).segment(b"\x89PNGxxxx", "circle", coalition_id=COALITION)
    assert len(out) == 2
    body = seen[0]
    parts = body["input"][0]["content"]
    assert parts[0] == {"type": "input_text", "text": "circle"}
    assert parts[1]["image_url"].startswith("data:image/png;base64,")
    assert body["metadata"] == {"include_confidence": "true"}
    assert meter.total(COALITION) == 2_500


async def test_media_transcribe_validates_before_sending_and_meters_audio() -> None:
    calls: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request)
        reply = {
            "transcript": "hello there",
            "audioDurationMs": 10_300,
            "turns": [{"turnId": 0, "startMs": 5, "endMs": 900, "transcript": "hello there"}],
        }
        return httpx2.Response(200, json=reply)

    meter = CostMeter(load_price_table())
    client = _media(handler, meter)
    with pytest.raises(MediaInputError):
        await client.transcribe(_wav(channels=2), "PUSH_TO_TALK")
    assert calls == []
    result = await client.transcribe(_wav(), "ENDPOINTING", coalition_id=COALITION)
    assert result.text == "hello there"
    assert (result.turns[0].start_ms, result.turns[0].end_ms) == (5, 900)
    assert calls[0].url.path == "/v1/asr/transcribe"
    assert b'"mode": "ENDPOINTING"' in calls[0].content
    assert b'name="audio"' in calls[0].content
    assert meter.total(COALITION) == 515


async def test_media_retries_transient_and_not_client_errors() -> None:
    hits = [0]

    def flaky(request: httpx2.Request) -> httpx2.Response:
        hits[0] += 1
        if hits[0] < 3:
            return httpx2.Response(503, json={})
        return httpx2.Response(200, json={"data": [{"b64_json": "aGk="}]})

    assert await _media(flaky).generate_image("p") == b"hi"
    assert hits[0] == 3

    def denied(request: httpx2.Request) -> httpx2.Response:
        hits[0] += 100
        return httpx2.Response(401, json={})

    with pytest.raises(ProviderError) as info:
        await _media(denied).generate_image("p")
    assert info.value.status == 401
    assert hits[0] == 103


async def test_budget_is_rechecked_before_the_truncation_retry() -> None:
    cut = ScriptedResponse("", 1000, 4000, reasoning_tokens=4000, finish_reason="length")
    gateway, fake, meter = _gateway([cut, ScriptedResponse("never")])
    meter.set_budget(COALITION, 100)
    with pytest.raises(BudgetExhaustedError):
        await gateway.complete("composer", USER, coalition_id=COALITION)
    assert len(fake.calls) == 1  # the doubled-budget retry never reached the transport


def _tool_calls(raw: Any) -> Any:
    from coalitionkit_models.structured import parse_tool_calls

    return parse_tool_calls(raw)


@pytest.mark.parametrize("text", ["", "   ", '{"q": ', "not json", "[1, 2]", '"text"', "3", "null"])
def test_invalid_tool_arguments_are_marked_never_an_empty_object(text: str) -> None:
    (call,) = _tool_calls([{"id": "c1", "function": {"name": "lookup", "arguments": text}}])
    assert call.arguments is None
    assert call.error
    assert call.raw_arguments == text
    assert not call.executable


def test_valid_tool_arguments_are_executable() -> None:
    (call,) = _tool_calls([{"id": "c1", "function": {"name": "lookup", "arguments": "{}"}}])
    assert call.arguments == {} and call.error is None and call.executable


@pytest.mark.parametrize(
    "bad",
    [
        "<0f>0<|box;x1=1;y1=2;x2=3;y2=4;w=10;h=20|><|mask;x=0;y=0;data=3,3,~ab",  # cut mask
        "<0f>0<|box;x1=1;y1=2;x2=3;y2=4;w=10;h=20|>junk",  # trailing garbage
        "<0f>0<|box;x1=1;y1=2;x2=3;y2=4;w=10;h=20|>,",  # separator with no record
        "<0f>0<|box;x1=1;y1=2;x2=3;y2=4;w=10;h=20|>1<|box;x1=1;y1=2;x2=3;y2=4;w=1;h=1|>",
        "<0f>0<|box;x1=1;y1=2;x2=3;y2=4;w=10;h=20|>,1<|oops",  # unmatched second record
        "<0f>0<|mask;x=0;y=0;data=3,3,~ab|>",  # mask with no box
        "<0f>0<|box;x1=1;y1=2;x2=3;y2=4;w=10;h=20|><|mask;x=0;y=0;data=3,~ab|>",  # bad dims
    ],
)
def test_sam_parser_rejects_partial_or_corrupt_output(bad: str) -> None:
    with pytest.raises(SamParseError):
        parse_sam_output(bad)


async def test_media_is_billed_even_when_the_reply_is_unusable() -> None:
    def junk_sam(request: httpx2.Request) -> httpx2.Response:
        text = {"output_text": "<0f>0<|box;x1=1;y1=2;x2=3;y2=4;w=1;h=1|><|mask;x=0"}
        return httpx2.Response(200, json=text)

    meter = CostMeter(load_price_table())
    with pytest.raises(SamParseError):
        await _media(junk_sam, meter).segment(b"\x89PNGxxxx", "circle", coalition_id=COALITION)
    assert meter.total(COALITION) == 2_500

    def no_image(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json={"data": []})

    meter = CostMeter(load_price_table())
    with pytest.raises(ProviderError):
        await _media(no_image, meter).generate_image("p", coalition_id=COALITION)
    assert meter.total(COALITION) == 10_000

    def not_json(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, content=b"<html>")

    meter = CostMeter(load_price_table())
    with pytest.raises(ProviderError):
        await _media(not_json, meter).generate_image("p", coalition_id=COALITION)
    assert meter.total(COALITION) == 10_000


@pytest.mark.parametrize("reply", [{"transcript": "x"}, {"transcript": "x", "audioDurationMs": 1}])
async def test_transcription_bills_at_least_the_audio_sent(reply: dict[str, Any]) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json=reply)

    meter = CostMeter(load_price_table())
    audio = _wav(frames=16_000)  # one second: 50 micro-USD at $0.18 per hour
    result = await _media(handler, meter).transcribe(audio, coalition_id=COALITION)
    assert meter.total(COALITION) == 50
    assert result.audio_ms == 1000


async def test_transcription_is_billed_when_fields_are_malformed() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        reply = {"transcript": "x", "audioDurationMs": "n/a", "turns": [{"startMs": "bad"}]}
        return httpx2.Response(200, json=reply)

    meter = CostMeter(load_price_table())
    await _media(handler, meter).transcribe(_wav(frames=16_000), coalition_id=COALITION)
    assert meter.total(COALITION) == 50


async def test_transcription_is_billed_when_the_duration_overflows() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        body = b'{"transcript": "x", "audioDurationMs": 1e309, "turns": []}'
        return httpx2.Response(200, content=body, headers={"content-type": "application/json"})

    meter = CostMeter(load_price_table())
    await _media(handler, meter).transcribe(_wav(frames=16_000), coalition_id=COALITION)
    assert meter.total(COALITION) == 50
