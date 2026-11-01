# SPDX-License-Identifier: Apache-2.0
"""Settings, prices, meter and gateway. No network: a scripted FakeModel stands in."""

from __future__ import annotations

import random

import pytest

from coalitionkit_models import (
    BudgetExhaustedError,
    CostMeter,
    FakeModel,
    MissingKeyError,
    ModelGateway,
    ProviderError,
    ScriptedResponse,
    Settings,
    SettingsError,
    UnpricedModelError,
    connection_error,
    load_price_table,
    load_settings,
    status_error,
)

FAKE_KEY = "test-not-a-real-key"
COALITION = "01M4XRC000000G40R40M30E209"


def _env(monkeypatch: pytest.MonkeyPatch, **values: str) -> None:
    for name in ("META_API_KEY", "BASETEN_API_KEY", "ENV", "META_BASE_URL", "STEWARD_PROVIDER"):
        monkeypatch.delenv(f"COALITIONKIT_{name}", raising=False)
    for name, value in values.items():
        monkeypatch.setenv(f"COALITIONKIT_{name}", value)


def test_production_refuses_to_start_without_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch, ENV="production", STEWARD_PROVIDER="baseten")
    with pytest.raises(MissingKeyError) as info:
        load_settings()
    assert "COALITIONKIT_META_API_KEY" in str(info.value)
    assert "COALITIONKIT_BASETEN_API_KEY" in str(info.value)


def test_production_on_the_meta_steward_route_needs_only_the_meta_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _env(monkeypatch, ENV="production", META_API_KEY=FAKE_KEY, STEWARD_PROVIDER="meta")
    assert load_settings().route("steward").key_name == "meta"


def test_production_with_one_key_still_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch, ENV="production", META_API_KEY=FAKE_KEY)
    with pytest.raises(MissingKeyError) as info:
        load_settings()
    assert FAKE_KEY not in str(info.value)
    assert "BASETEN" in str(info.value)


def test_production_requires_https(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(
        monkeypatch,
        ENV="production",
        META_API_KEY=FAKE_KEY,
        BASETEN_API_KEY=FAKE_KEY,
        META_BASE_URL="http://insecure.invalid/v1",
    )
    with pytest.raises(SettingsError):
        load_settings()


def test_secrets_are_never_printed(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(
        monkeypatch,
        ENV="production",
        META_API_KEY=FAKE_KEY,
        BASETEN_API_KEY=FAKE_KEY,
        STEWARD_PROVIDER="baseten",
    )
    settings = load_settings()
    assert FAKE_KEY not in repr(settings)
    assert FAKE_KEY not in str(settings)
    assert FAKE_KEY not in repr(settings.route("steward"))
    assert settings.api_key(settings.route("steward")) == FAKE_KEY


def test_development_starts_without_keys_and_fails_at_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _env(monkeypatch)
    settings = load_settings()
    with pytest.raises(MissingKeyError):
        settings.api_key(settings.route("gardener"))
    assert settings.api_key(settings.route("vault")) == "ollama"


def test_routing_per_role() -> None:
    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert settings.route("gardener").model == "muse-wonder-1.0"
    assert settings.route("composer").model == "muse-spark-1.3"
    assert settings.route("hosted_agent").model == "muse-spark-1.3"
    assert settings.route("steward").model == "meta-models/muse-spark-open"
    assert settings.route("steward").base_url == settings.baseten_base_url
    assert settings.route("vault").model == "muse-glimmer"
    assert "11434" in settings.route("vault").base_url


def test_price_table_fixed_usage_to_the_micro_dollar() -> None:
    table = load_price_table()
    assert table.version == "2026-10-28"
    # 800 uncached * 1.25 + 200 cached * 0.15 + 500 out * 4.25 = 1000 + 30 + 2125
    assert (
        table.cost_micro_usd(
            "muse-spark-1.3", prompt_tokens=1000, completion_tokens=500, cached_tokens=200
        )
        == 3155
    )
    # Wonder: 1000 * 4 + 1000 * 20
    assert table.cost_micro_usd("muse-wonder-1.0", prompt_tokens=1000, completion_tokens=1000) == (
        24000
    )
    # 1M cached tokens at $0.20
    assert (
        table.cost_micro_usd(
            "muse-wonder-1.0", prompt_tokens=1_000_000, completion_tokens=0, cached_tokens=1_000_000
        )
        == 200_000
    )
    assert table.cost_micro_usd("muse-glimmer", prompt_tokens=5000, completion_tokens=5000) == 0
    # Rounds up once: 1 token at 1.25 micro-USD is 2.
    assert table.cost_micro_usd("muse-spark-1.3", prompt_tokens=1, completion_tokens=0) == 2


def test_baseten_price_is_the_published_one() -> None:
    table = load_price_table()
    spark_open = table.price("meta-models/muse-spark-open")
    assert spark_open.verified
    assert "baseten.co/library/muse-spark-open" in spark_open.source
    assert spark_open.input == table.price("muse-spark-1.3").input
    assert table.price("muse-wonder-1.0").verified


def test_unknown_model_is_unpriced() -> None:
    with pytest.raises(UnpricedModelError):
        load_price_table().price("nope")


def test_meter_totals_per_coalition_and_participant() -> None:
    meter = CostMeter(load_price_table())
    meter.record(COALITION, "p1", "muse-spark-1.3", prompt_tokens=1000, completion_tokens=500)
    meter.record(COALITION, "p2", "muse-spark-1.3", prompt_tokens=1000, completion_tokens=0)
    meter.record("other", "p1", "muse-spark-1.3", prompt_tokens=1000, completion_tokens=0)
    assert meter.participant_total(COALITION, "p1") == 1250 + 2125
    assert meter.participant_total(COALITION, "p2") == 1250
    assert meter.total(COALITION) == 1250 + 2125 + 1250
    assert meter.total("other") == 1250
    assert meter.participant_totals(COALITION) == {"p1": 3375, "p2": 1250}


def test_meter_warns_at_80_percent_and_stops_at_100() -> None:
    seen: list[str] = []
    meter = CostMeter(load_price_table(), on_event=lambda e: seen.append(e.kind))
    meter.set_budget(COALITION, 10_000)

    def spend(prompt_tokens: int) -> None:
        meter.record(
            COALITION, "p1", "muse-spark-1.3", prompt_tokens=prompt_tokens, completion_tokens=0
        )

    spend(6400)  # 8000 micro-USD: exactly 80 percent
    assert seen == ["budget_warning"]
    meter.check(COALITION)
    spend(1)  # no repeat of the warning
    assert seen == ["budget_warning"]
    spend(1599)  # 2 more: 100 percent (8000 + 2 + 1999 would overshoot; check below)
    assert meter.total(COALITION) >= 10_000
    assert seen == ["budget_warning", "budget_exhausted"]
    with pytest.raises(BudgetExhaustedError) as info:
        meter.check(COALITION)
    assert info.value.code == "budget_exhausted"


def test_meter_just_under_80_percent_is_quiet() -> None:
    meter = CostMeter(load_price_table())
    meter.set_budget(COALITION, 10_000)
    meter.record(COALITION, "p1", "muse-spark-1.3", prompt_tokens=6399, completion_tokens=0)
    assert meter.events == []


def _gateway(
    script: list[ScriptedResponse | BaseException], meter: CostMeter | None = None
) -> tuple[ModelGateway, FakeModel, list[float]]:
    sleeps: list[float] = []

    async def sleep(seconds: float) -> None:
        sleeps.append(seconds)

    fake = FakeModel(script)
    gateway = ModelGateway(
        Settings(_env_file=None),  # pyright: ignore[reportCallIssue]
        transport=fake,
        meter=meter,
        sleep=sleep,
        rng=random.Random(7),
    )
    return gateway, fake, sleeps


async def test_gateway_returns_text_usage_and_cost() -> None:
    meter = CostMeter(load_price_table())
    gateway, fake, _ = _gateway([ScriptedResponse("hello", 1000, 500, 200)], meter)
    result = await gateway.complete(
        "composer", [{"role": "user", "content": "hi"}], coalition_id=COALITION, participant="p1"
    )
    assert result.text == "hello"
    assert result.model == "muse-spark-1.3"
    assert result.cost_micro_usd == 3155
    assert meter.participant_total(COALITION, "p1") == 3155
    assert fake.calls[0][0] == "composer"


async def test_gateway_retries_transient_errors_with_backoff() -> None:
    gateway, fake, sleeps = _gateway(
        [status_error(503), connection_error(), status_error(429), ScriptedResponse("ok")]
    )
    result = await gateway.complete("steward", [{"role": "user", "content": "x"}])
    assert result.text == "ok"
    assert len(fake.calls) == 4
    assert len(sleeps) == 3
    assert all(0.0 <= s <= 8.0 for s in sleeps)


async def test_gateway_gives_up_after_max_attempts() -> None:
    gateway, fake, _ = _gateway([status_error(500)] * 4)
    with pytest.raises(ProviderError) as info:
        await gateway.complete("steward", [{"role": "user", "content": "x"}])
    assert info.value.attempts == 4
    assert info.value.status == 500
    assert len(fake.calls) == 4


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
async def test_gateway_does_not_retry_client_errors(status: int) -> None:
    gateway, fake, sleeps = _gateway([status_error(status), ScriptedResponse("never")])
    with pytest.raises(ProviderError) as info:
        await gateway.complete("gardener", [{"role": "user", "content": "x"}])
    assert info.value.status == status
    assert len(fake.calls) == 1
    assert sleeps == []


async def test_gateway_refuses_new_calls_when_budget_is_spent() -> None:
    meter = CostMeter(load_price_table())
    meter.set_budget(COALITION, 100)
    gateway, fake, _ = _gateway([ScriptedResponse("a", 1000, 0), ScriptedResponse("b")], meter)
    await gateway.complete("composer", [{"role": "user", "content": "x"}], coalition_id=COALITION)
    with pytest.raises(BudgetExhaustedError):
        await gateway.complete(
            "composer", [{"role": "user", "content": "x"}], coalition_id=COALITION
        )
    assert len(fake.calls) == 1


async def test_gateway_rate_limits_per_role() -> None:
    now = [0.0]
    sleeps: list[float] = []

    async def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        now[0] += seconds

    settings = Settings(_env_file=None, rate_limit_per_minute={"steward": 2})  # pyright: ignore[reportCallIssue]
    fake = FakeModel([ScriptedResponse("1"), ScriptedResponse("2"), ScriptedResponse("3")])
    gateway = ModelGateway(settings, transport=fake, sleep=sleep, clock=lambda: now[0])
    for _ in range(3):
        await gateway.complete("steward", [{"role": "user", "content": "x"}])
    assert sleeps == [60.0]


def test_steward_defaults_to_muse_spark_open_on_baseten_when_its_key_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _env(monkeypatch, BASETEN_API_KEY=FAKE_KEY)
    settings = load_settings()
    route = settings.route("steward")
    assert settings.steward_host == "baseten"
    assert (route.model, route.key_name) == ("meta-models/muse-spark-open", "baseten")
    assert route.base_url == "https://inference.baseten.co/v1"


def test_steward_requires_baseten_key_without_silent_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _env(monkeypatch, META_API_KEY=FAKE_KEY)
    settings = load_settings()
    assert settings.steward_host == "baseten"
    assert settings.route("steward").model == "meta-models/muse-spark-open"
    with pytest.raises(MissingKeyError, match="COALITIONKIT_BASETEN_API_KEY"):
        settings.api_key(settings.route("steward"))


def test_an_explicit_steward_provider_beats_the_key_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _env(monkeypatch, BASETEN_API_KEY=FAKE_KEY, STEWARD_PROVIDER="meta")
    assert load_settings().steward_host == "meta"
