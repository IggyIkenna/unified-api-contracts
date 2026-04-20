"""Unit tests for the prediction-market taxonomy classifier.

Covers the 13 categories, 5 market types, 8 resolution periods, and
~40 real-world Polymarket slug patterns. The classifier must be
rule-first (deterministic) and produce ``MISC`` only when the slug,
title, and event slug all fail to match.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.internal.schemas._prediction_market_taxonomy import (
    PredictionShardCategory,
    PredictionShardMarketType,
    PredictionShardResolutionPeriod,
    classify_polymarket_market,
)

# ---------------------------------------------------------------------------
# Enum surface
# ---------------------------------------------------------------------------


def test_category_has_13_values() -> None:
    assert len(PredictionShardCategory) == 13


def test_market_type_has_5_values() -> None:
    assert len(PredictionShardMarketType) == 5


def test_resolution_period_has_8_values() -> None:
    assert len(PredictionShardResolutionPeriod) == 8


def test_category_values_are_canonical() -> None:
    expected = {
        "CRYPTO_PRICE",
        "EQUITY_INDEX",
        "COMMODITY",
        "FX",
        "MACRO",
        "POLITICS_US",
        "POLITICS_INTL",
        "SPORTS_FOOTBALL",
        "SPORTS_OTHER",
        "CULTURE",
        "TECH",
        "WEATHER",
        "MISC",
    }
    assert {c.value for c in PredictionShardCategory} == expected


# ---------------------------------------------------------------------------
# Classifier — the 14 legacy Polymarket "instrument_type" buckets
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("slug", "expected_category", "expected_underlying"),
    [
        ("bnb-up-or-down-april-15", PredictionShardCategory.CRYPTO_PRICE, "BNB"),
        ("btc-up-or-down-april-15", PredictionShardCategory.CRYPTO_PRICE, "BTC"),
        ("bitcoin-100k-by-q2", PredictionShardCategory.CRYPTO_PRICE, "BTC"),
        ("eth-up-or-down-april-15", PredictionShardCategory.CRYPTO_PRICE, "ETH"),
        ("ethereum-5000-by-end-of-2026", PredictionShardCategory.CRYPTO_PRICE, "ETH"),
        ("sol-up-or-down-april-15", PredictionShardCategory.CRYPTO_PRICE, "SOL"),
        ("solana-500-by-end-of-2026", PredictionShardCategory.CRYPTO_PRICE, "SOL"),
        ("doge-up-or-down-april-15", PredictionShardCategory.CRYPTO_PRICE, "DOGE"),
        ("dogecoin-1-by-end-of-2026", PredictionShardCategory.CRYPTO_PRICE, "DOGE"),
        ("xrp-up-or-down-april-15", PredictionShardCategory.CRYPTO_PRICE, "XRP"),
        ("hype-up-or-down-april-15", PredictionShardCategory.CRYPTO_PRICE, "HYPE"),
        ("spx-up-or-down-april-15", PredictionShardCategory.EQUITY_INDEX, "SPX"),
        ("ndx-up-or-down-april-15", PredictionShardCategory.EQUITY_INDEX, "NDX"),
        ("djia-up-or-down-april-15", PredictionShardCategory.EQUITY_INDEX, "DJIA"),
        ("gold-up-or-down-april-15", PredictionShardCategory.COMMODITY, "GOLD"),
        ("silver-up-or-down-april-15", PredictionShardCategory.COMMODITY, "SILVER"),
        ("crude-oil-up-or-down-april-15", PredictionShardCategory.COMMODITY, "CRUDE_OIL"),
    ],
)
def test_classifier_legacy_14_buckets(
    slug: str,
    expected_category: PredictionShardCategory,
    expected_underlying: str,
) -> None:
    category, underlying, _, _ = classify_polymarket_market(title="", slug=slug, event_slug="", outcome="Up")
    assert category is expected_category
    assert underlying == expected_underlying


# ---------------------------------------------------------------------------
# Classifier — tricky cases + beyond the legacy 14
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    (
        "slug",
        "title",
        "event_slug",
        "outcome",
        "expected_category",
        "expected_underlying",
    ),
    [
        # Politics US
        (
            "trump-impeached-2025",
            "Will Trump be impeached in 2025?",
            "",
            "Yes",
            PredictionShardCategory.POLITICS_US,
            "TRUMP",
        ),
        (
            "kamala-pick-vp",
            "Who will Kamala pick as VP?",
            "",
            "Josh Shapiro",
            PredictionShardCategory.POLITICS_US,
            "KAMALA_HARRIS",
        ),
        ("biden-drop-out-2024", "Will Biden drop out?", "", "Yes", PredictionShardCategory.POLITICS_US, "BIDEN"),
        (
            "desantis-wins-primary-2028",
            "DeSantis wins primary",
            "",
            "Yes",
            PredictionShardCategory.POLITICS_US,
            "DESANTIS",
        ),
        (
            "us-president-2028-winner",
            "2028 US President",
            "",
            "Kamala Harris",
            PredictionShardCategory.POLITICS_US,
            "US_ELECTION",
        ),
        (
            "senate-majority-2026",
            "Senate majority 2026",
            "",
            "Democrats",
            PredictionShardCategory.POLITICS_US,
            "US_SENATE",
        ),
        # Politics International
        (
            "uk-election-2029",
            "Next UK general election winner",
            "",
            "Labour",
            PredictionShardCategory.POLITICS_INTL,
            "UK_ELECTION",
        ),
        (
            "macron-approval-2026",
            "Macron approval Q2",
            "",
            "Above 40%",
            PredictionShardCategory.POLITICS_INTL,
            "MACRON",
        ),
        ("india-election-2029", "India PM 2029", "", "Modi", PredictionShardCategory.POLITICS_INTL, "INDIA_ELECTION"),
        # Sports — football
        ("epl-winner-2026", "Premier League winner", "", "Man City", PredictionShardCategory.SPORTS_FOOTBALL, "EPL"),
        ("world-cup-2026-winner", "World Cup 2026", "", "Brazil", PredictionShardCategory.SPORTS_FOOTBALL, "WORLD_CUP"),
        (
            "champions-league-2026-final",
            "UCL 2026 winner",
            "",
            "Real Madrid",
            PredictionShardCategory.SPORTS_FOOTBALL,
            "CHAMPIONS_LEAGUE",
        ),
        (
            "super-bowl-2027-winner",
            "Super Bowl LXI winner",
            "",
            "Chiefs",
            PredictionShardCategory.SPORTS_FOOTBALL,
            "NFL",
        ),
        # Sports — other
        ("nba-finals-2026-mvp", "NBA Finals MVP", "", "SGA", PredictionShardCategory.SPORTS_OTHER, "NBA"),
        (
            "f1-2026-drivers-champion",
            "F1 Drivers Champion 2026",
            "",
            "Verstappen",
            PredictionShardCategory.SPORTS_OTHER,
            "F1",
        ),
        (
            "wimbledon-2026-winner",
            "Wimbledon 2026 champion",
            "",
            "Alcaraz",
            PredictionShardCategory.SPORTS_OTHER,
            "TENNIS",
        ),
        (
            "pga-masters-tournament-2026",
            "Masters 2026 winner",
            "",
            "Scheffler",
            PredictionShardCategory.SPORTS_OTHER,
            "GOLF",
        ),
        ("ufc-300-main-event", "UFC 300 main event winner", "", "Poirier", PredictionShardCategory.SPORTS_OTHER, "UFC"),
        # Culture
        ("oscars-best-picture-2026", "Best Picture 2026", "", "Oppenheimer", PredictionShardCategory.CULTURE, "OSCARS"),
        (
            "grammys-album-of-year-2026",
            "Album of the Year",
            "",
            "Taylor Swift",
            PredictionShardCategory.CULTURE,
            "GRAMMYS",
        ),
        ("emmys-drama-2026", "Outstanding Drama Series", "", "Succession", PredictionShardCategory.CULTURE, "EMMYS"),
        (
            "taylor-swift-tour-2026-gross",
            "Eras Tour gross 2026",
            "",
            "Above 1B",
            PredictionShardCategory.CULTURE,
            "TAYLOR_SWIFT",
        ),
        # Tech
        (
            "will-nvda-announce-jan-15",
            "Will NVDA announce Blackwell Jan 15?",
            "",
            "Yes",
            PredictionShardCategory.TECH,
            "NVDA",
        ),
        (
            "openai-gpt-5-release-2026",
            "GPT-5 release before July 2026",
            "",
            "Yes",
            PredictionShardCategory.TECH,
            "OPENAI",
        ),
        ("chatgpt-5-launch-2026", "ChatGPT-5 launches Q2", "", "Yes", PredictionShardCategory.TECH, "OPENAI"),
        ("claude-5-release-2026", "Claude 5 release", "", "Yes", PredictionShardCategory.TECH, "ANTHROPIC"),
        ("tesla-deliveries-q2-2026", "Tesla Q2 deliveries above 500k", "", "Yes", PredictionShardCategory.TECH, "TSLA"),
        # Weather
        (
            "hurricane-atlantic-2026-season",
            "Atlantic hurricane season 2026",
            "",
            "Above average",
            PredictionShardCategory.WEATHER,
            "HURRICANE",
        ),
        (
            "heat-wave-europe-2026",
            "Europe heat wave summer 2026",
            "",
            "Yes",
            PredictionShardCategory.WEATHER,
            "HEAT_WAVE",
        ),
        ("el-nino-2026", "El Nino continues through 2026", "", "Yes", PredictionShardCategory.WEATHER, "EL_NINO"),
        # Macro
        ("fed-rate-cut-may-2026", "Fed cuts rates in May", "", "Yes", PredictionShardCategory.MACRO, "FED_FUNDS"),
        ("cpi-above-3-may-2026", "May CPI above 3%", "", "Yes", PredictionShardCategory.MACRO, "CPI"),
        ("nfp-above-200k-may-2026", "May NFP above 200k", "", "Yes", PredictionShardCategory.MACRO, "NONFARM_PAYROLLS"),
        (
            "unemployment-above-5-2026",
            "Unemployment rises above 5%",
            "",
            "Yes",
            PredictionShardCategory.MACRO,
            "UNEMPLOYMENT",
        ),
        # FX
        ("usd-jpy-above-160-april", "USD/JPY above 160 end of April", "", "Yes", PredictionShardCategory.FX, "USDJPY"),
    ],
)
def test_classifier_beyond_legacy_buckets(
    slug: str,
    title: str,
    event_slug: str,
    outcome: str,
    expected_category: PredictionShardCategory,
    expected_underlying: str,
) -> None:
    category, underlying, _, _ = classify_polymarket_market(
        title=title, slug=slug, event_slug=event_slug, outcome=outcome
    )
    assert category is expected_category, f"slug={slug!r} → {category}"
    assert underlying == expected_underlying, f"slug={slug!r} → {underlying}"


# ---------------------------------------------------------------------------
# Classifier — market type inference
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("slug", "outcome", "expected"),
    [
        ("bnb-up-or-down-april-15", "Up", PredictionShardMarketType.RANGE_BRACKET),
        ("btc-price-range-april-15", "Between 60k-70k", PredictionShardMarketType.RANGE_BRACKET),
        ("trump-impeached-2025", "Yes", PredictionShardMarketType.BINARY),
        ("oscars-best-picture-2026", "Oppenheimer", PredictionShardMarketType.CATEGORICAL),
        ("us-president-2028-winner", "Kamala Harris", PredictionShardMarketType.CATEGORICAL),
        ("epl-most-goals-2026", "Haaland", PredictionShardMarketType.RANKED),
        ("nba-finals-2026-mvp", "SGA", PredictionShardMarketType.CATEGORICAL),
        ("kamala-pick-vp", "Shapiro", PredictionShardMarketType.CATEGORICAL),
    ],
)
def test_classifier_market_type(slug: str, outcome: str, expected: PredictionShardMarketType) -> None:
    _, _, market_type, _ = classify_polymarket_market(title="", slug=slug, event_slug="", outcome=outcome)
    assert market_type is expected, f"slug={slug!r} outcome={outcome!r} → {market_type}"


# ---------------------------------------------------------------------------
# Classifier — resolution period inference
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("slug", "title", "expected"),
    [
        ("bnb-up-or-down-hour-1400", "Hourly BNB", PredictionShardResolutionPeriod.HOURLY),
        ("btc-up-or-down-minute-6000", "Intraday BTC", PredictionShardResolutionPeriod.INTRADAY),
        ("btc-up-or-down-week-april-15", "Weekly BTC", PredictionShardResolutionPeriod.WEEKLY),
        ("spx-quarterly-q1", "SPX Q1 range", PredictionShardResolutionPeriod.QUARTERLY),
        ("bnb-up-or-down-april-15", "", PredictionShardResolutionPeriod.MONTHLY),
        ("oscars-best-picture-2026", "", PredictionShardResolutionPeriod.YEARLY),
        ("us-president-2028-winner", "", PredictionShardResolutionPeriod.YEARLY),
        ("nba-finals-2026-mvp", "", PredictionShardResolutionPeriod.EVENT),
        ("hurricane-atlantic-2026-season", "", PredictionShardResolutionPeriod.EVENT),
    ],
)
def test_classifier_resolution_period(slug: str, title: str, expected: PredictionShardResolutionPeriod) -> None:
    _, _, _, resolution_period = classify_polymarket_market(title=title, slug=slug, event_slug="", outcome="Up")
    assert resolution_period is expected, f"slug={slug!r} → {resolution_period}"


# ---------------------------------------------------------------------------
# Classifier — MISC fallback
# ---------------------------------------------------------------------------


def test_classifier_misc_fallback() -> None:
    category, underlying, _, _ = classify_polymarket_market(
        title="will this weird thing happen",
        slug="will-this-weird-thing-happen",
        event_slug="",
        outcome="Yes",
    )
    assert category is PredictionShardCategory.MISC
    assert underlying == "UNKNOWN"


def test_classifier_event_slug_fallback() -> None:
    """Empty market slug should fall back to event_slug prefix."""
    category, underlying, _, _ = classify_polymarket_market(
        title="",
        slug="",
        event_slug="trump-vs-kamala-debate",
        outcome="Yes",
    )
    assert category is PredictionShardCategory.POLITICS_US
    assert underlying == "TRUMP"


def test_classifier_title_keyword_fallback() -> None:
    """No slug info — keyword match on title must still classify."""
    category, underlying, _, _ = classify_polymarket_market(
        title="Will Bitcoin reach 200k by end of 2026?",
        slug="",
        event_slug="",
        outcome="Yes",
    )
    assert category is PredictionShardCategory.CRYPTO_PRICE
    assert underlying == "BTC"


def test_classifier_returns_tuple_of_enums() -> None:
    result = classify_polymarket_market(title="", slug="bnb-up-or-down-april-15", event_slug="", outcome="Up")
    assert isinstance(result, tuple)
    assert len(result) == 4
    category, underlying, market_type, resolution_period = result
    assert isinstance(category, PredictionShardCategory)
    assert isinstance(underlying, str)
    assert isinstance(market_type, PredictionShardMarketType)
    assert isinstance(resolution_period, PredictionShardResolutionPeriod)


# ---------------------------------------------------------------------------
# Contract — new required columns
# ---------------------------------------------------------------------------


def test_contract_has_new_shard_columns() -> None:
    from unified_api_contracts.internal.schemas._sports_prediction_contracts import (
        PREDICTION_PREDICTION_MARKET_TRADES,
    )

    by_name = {c.name: c for c in PREDICTION_PREDICTION_MARKET_TRADES.columns}
    for col_name in ("market_category", "market_type", "resolution_period", "underlying"):
        assert col_name in by_name, f"missing {col_name} column"
        assert by_name[col_name].nullable is False, f"{col_name} must be required"
