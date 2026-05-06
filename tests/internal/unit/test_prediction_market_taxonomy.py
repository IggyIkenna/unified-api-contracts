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
    for col_name in ("asset_group", "market_type", "resolution_period", "underlying"):
        assert col_name in by_name, f"missing {col_name} column"
        assert by_name[col_name].nullable is False, f"{col_name} must be required"


# ---------------------------------------------------------------------------
# Edge-case regression tests — surfaced by Phase 0 classifier audit 2026-05-06
# (see predictions_canonical_question_group_polymarket_migration_2026_05_06
# plan §Phase 0 audit findings — existing UAC classifier §Section E).
#
# The instruments-service-side question-text classifier had two known
# false-positive classes that motivated commits b336834 + d7bd17f:
#  * "abnb" (Airbnb ticker) → `bnb` substring hit → false BNB
#  * "solar" → `sol` substring hit → false SOL
#  * "archBitcoin" → `bitcoin` substring → still legit BTC (long-form safe)
#
# The UAC slug-prefix classifier here does NOT use bare substring matching,
# so the Airbnb/solar false-positives don't reproduce on the slug path —
# these tests lock that in as regression coverage. The first three tests
# assert MISC fallback; the last three document genuine false-positives in
# the current SLUG_PREFIX_MAP that should be cleaned up by a follow-up
# false-positive guard plan (not in scope for this commit).
# ---------------------------------------------------------------------------


def test_classifier_airbnb_does_not_false_positive_to_bnb() -> None:
    """Airbnb slug must NOT classify as CRYPTO_PRICE/BNB.

    Regression for the instruments-service-side b336834 fix carried over to
    UAC. The slug-based classifier here is structurally safe (slug delimiter
    is "-", so `airbnb-` doesn't match `bnb-` prefix) — this test locks
    that in.
    """
    category, underlying, _, _ = classify_polymarket_market(
        title="Airbnb (ABNB) Up or Down on October 16?",
        slug="airbnb-up-or-down-oct-16",
        event_slug="",
        outcome="Yes",
    )
    assert category is PredictionShardCategory.MISC
    assert underlying == "UNKNOWN"


def test_classifier_solar_does_not_false_positive_to_sol() -> None:
    """Solar slug must NOT classify as CRYPTO_PRICE/SOL.

    Same regression class as the Airbnb test — the slug-based classifier is
    structurally safe (slug `solar-` doesn't match `sol-` prefix).
    """
    category, underlying, _, _ = classify_polymarket_market(
        title="Solar panel adoption above 50% by 2026?",
        slug="solar-panel-adoption-2026",
        event_slug="",
        outcome="Yes",
    )
    assert category is PredictionShardCategory.MISC
    assert underlying == "UNKNOWN"


def test_classifier_archbitcoin_keyword_match_via_title() -> None:
    """archBitcoin / archEthereum / archXRP markets use long-form keywords
    in the title and should classify correctly via the title-keyword fallback.

    Slug starts with `archbitcoin-` which doesn't match any prefix; token
    scan of `archbitcoin` (length ≥ 3) doesn't hit either. The keyword
    fallback runs against the title which contains the long-form `bitcoin`,
    so it should return CRYPTO_PRICE/BTC.
    """
    category, underlying, _, _ = classify_polymarket_market(
        title="Will archBitcoin price exceed $100k?",
        slug="archbitcoin-price-above-100k",
        event_slug="",
        outcome="Yes",
    )
    # Long-form keyword "bitcoin" in title triggers CRYPTO_PRICE/BTC via
    # KEYWORD_TO_CATEGORY substring match. This is the intended behaviour
    # per d7bd17f (long forms are safe; short tickers need word boundary).
    assert category is PredictionShardCategory.CRYPTO_PRICE
    assert underlying == "BTC"


def test_classifier_bnb_up_down_may_resolves_to_monthly() -> None:
    """`bnb-up-or-down-may-15` should resolve to MONTHLY resolution_period.

    `may` IS in `_MONTHLY_TOKENS` (3-letter abbreviation set, line 374 of
    `_prediction_market_taxonomy.py`). With no year marker (`-2025`/`-2026`)
    in the slug, the year-marker branch at line 511-523 is skipped and we
    fall through to the bare `tokens & _MONTHLY_TOKENS` check at line 533,
    which returns MONTHLY.
    """
    category, underlying, _, resolution_period = classify_polymarket_market(
        title="BNB Up or Down on May 15?",
        slug="bnb-up-or-down-may-15",
        event_slug="",
        outcome="Up",
    )
    assert category is PredictionShardCategory.CRYPTO_PRICE
    assert underlying == "BNB"
    assert resolution_period is PredictionShardResolutionPeriod.MONTHLY


@pytest.mark.xfail(
    reason=(
        "KNOWN FALSE-POSITIVE: `house-` prefix in SLUG_PREFIX_MAP catches "
        "`house-price-above-500k` (real-estate prediction market) and "
        "misclassifies it as POLITICS_US/US_HOUSE. Cleanup deferred to a "
        "future false-positive-guard plan."
    ),
    strict=True,
)
def test_classifier_house_price_should_not_match_us_house() -> None:
    """`house-price-*` slugs are real-estate, not US House of Representatives."""
    category, _, _, _ = classify_polymarket_market(
        title="House price above $500k?",
        slug="house-price-above-500k",
        event_slug="",
        outcome="Yes",
    )
    assert category is PredictionShardCategory.MISC


@pytest.mark.xfail(
    reason=(
        "KNOWN FALSE-POSITIVE: `fed-` prefix in SLUG_PREFIX_MAP catches "
        "`fed-ex-delivery-2026` (FedEx package delivery) and misclassifies "
        "it as MACRO/FED_FUNDS. Cleanup deferred to a future false-positive-"
        "guard plan (could require word-boundary on `fed-` or override map)."
    ),
    strict=True,
)
def test_classifier_fed_ex_should_not_match_fed_funds() -> None:
    """`fed-ex-*` slugs are FedEx, not Fed Funds."""
    category, _, _, _ = classify_polymarket_market(
        title="FedEx delivery above 5M packages by 2026?",
        slug="fed-ex-delivery-2026",
        event_slug="",
        outcome="Yes",
    )
    assert category is PredictionShardCategory.MISC


@pytest.mark.xfail(
    reason=(
        "KNOWN FALSE-POSITIVE: `fear-` prefix in SLUG_PREFIX_MAP catches "
        "`fear-factor-reboot` (TV show) and misclassifies it as "
        "MACRO/FEAR_GREED. Cleanup deferred to a future false-positive-"
        "guard plan (could require `fear-and-greed-` or `fear-greed-` only)."
    ),
    strict=True,
)
def test_classifier_fear_factor_should_not_match_fear_greed() -> None:
    """`fear-factor-*` slugs are TV-show, not Fear & Greed Index."""
    category, _, _, _ = classify_polymarket_market(
        title="Will Fear Factor reboot in 2026?",
        slug="fear-factor-reboot",
        event_slug="",
        outcome="Yes",
    )
    assert category is PredictionShardCategory.MISC
