"""Unit tests for the predictions canonical-question-group SSOT.

Predictions plan
``predictions_canonical_question_group_polymarket_migration_2026_05_06.md``
Phase 1A.
"""

from __future__ import annotations

import datetime as _dt

import pytest

from unified_api_contracts.canonical.crosscutting.honest_coverage import (
    BUNDLED_DATA_TYPES,
    DATA_TYPE_TO_CLUSTER_REGISTRY,
    PREDICTION_GROUPS,
)
from unified_api_contracts.predictions import (
    CANONICAL_GROUP_METADATA,
    CLASSIFIER_STABILITY_HASH,
    KALSHI_TICKER_PREFIX_TO_GROUP,
    KALSHI_TICKER_TO_GROUP,
    POLYMARKET_CONDITION_ID_TO_GROUP,
    CanonicalGroupMetadata,
    CanonicalQuestionGroup,
    MarketLifecycle,
    classify_kalshi_to_canonical_group,
    classify_polymarket_to_canonical_group,
    expected_market_ids_for_canonical_group,
    is_market_active_at,
)

# ---------------------------------------------------------------------------
# CanonicalQuestionGroup + CanonicalGroupMetadata
# ---------------------------------------------------------------------------


def test_every_canonical_group_has_metadata() -> None:
    """Every enum member is keyed in CANONICAL_GROUP_METADATA."""
    for group in CanonicalQuestionGroup:
        assert group in CANONICAL_GROUP_METADATA
        meta = CANONICAL_GROUP_METADATA[group]
        assert isinstance(meta, CanonicalGroupMetadata)
        assert meta.group == group
        assert meta.expected_market_ids_per_day >= 0


def test_metadata_cadence_lit_set() -> None:
    """Cadence values are within the documented literal set."""
    valid = {"1min", "5min", "15min", "intraday", "hourly", "daily", "weekly", "monthly", "irregular", "single"}
    for meta in CANONICAL_GROUP_METADATA.values():
        assert meta.cadence in valid


def test_hourly_groups_expect_24_per_day() -> None:
    assert CANONICAL_GROUP_METADATA[CanonicalQuestionGroup.BTC_UP_DOWN_HOURLY].expected_market_ids_per_day == 24
    assert CANONICAL_GROUP_METADATA[CanonicalQuestionGroup.ETH_UP_DOWN_HOURLY].expected_market_ids_per_day == 24


def test_daily_groups_expect_1_per_day() -> None:
    for group in (
        CanonicalQuestionGroup.BTC_UP_DOWN_DAILY,
        CanonicalQuestionGroup.ETH_UP_DOWN_DAILY,
        CanonicalQuestionGroup.SPX_UP_DOWN_DAILY,
    ):
        assert CANONICAL_GROUP_METADATA[group].expected_market_ids_per_day == 1


# ---------------------------------------------------------------------------
# Classifier — rule-based mapping for the canonical happy paths
# ---------------------------------------------------------------------------


def test_classify_btc_hourly_range_bracket() -> None:
    """``btc-up-or-down-hourly-april-15`` slug maps to BTC_UP_DOWN_HOURLY."""
    group = classify_polymarket_to_canonical_group(
        title="Will BTC be up or down at 12pm UTC?",
        slug="btc-up-or-down-hourly-april-15",
        event_slug="btc-price-hourly",
        outcome="Up",
    )
    assert group == CanonicalQuestionGroup.BTC_UP_DOWN_HOURLY


def test_classify_eth_daily_range_bracket() -> None:
    """``eth-up-or-down-daily`` slug maps to ETH_UP_DOWN_DAILY."""
    group = classify_polymarket_to_canonical_group(
        title="Will ETH be up or down today?",
        slug="eth-up-or-down-daily",
        event_slug="eth-price-daily",
        outcome="Down",
    )
    assert group == CanonicalQuestionGroup.ETH_UP_DOWN_DAILY


def test_classify_cme_linked_groups_daily() -> None:
    """7 CME-linked groups (predictions_master Phase 5) classify from real Polymarket slugs."""
    cases: list[tuple[str, str, str, str, CanonicalQuestionGroup]] = [
        # (title, slug, event_slug, outcome, expected_group)
        (
            "Will NDX be up or down today?",
            "ndx-daily-up-or-down",
            "ndx-price-daily",
            "Up",
            CanonicalQuestionGroup.NDX_UP_DOWN_DAILY,
        ),
        (
            "Will DJIA be up or down today?",
            "dow-jones-daily-up-or-down",
            "djia-price-daily",
            "Down",
            CanonicalQuestionGroup.DJIA_UP_DOWN_DAILY,
        ),
        (
            "Will Russell 2000 be up or down?",
            "rut-daily-up-or-down",
            "rut-price-daily",
            "Up",
            CanonicalQuestionGroup.RUT_UP_DOWN_DAILY,
        ),
        (
            "Will Gold be up or down today?",
            "gold-daily-up-or-down",
            "gold-price-daily",
            "Up",
            CanonicalQuestionGroup.GOLD_UP_DOWN_DAILY,
        ),
        (
            "Will Crude Oil be up or down today?",
            "crude-oil-daily-up-or-down",
            "oil-price-daily",
            "Down",
            CanonicalQuestionGroup.CRUDE_OIL_UP_DOWN_DAILY,
        ),
        (
            "Will Natural Gas be up or down today?",
            "nat-gas-daily-up-or-down",
            "natgas-price-daily",
            "Up",
            CanonicalQuestionGroup.NATGAS_UP_DOWN_DAILY,
        ),
        (
            "Will EUR/USD be up or down today?",
            "eur-usd-daily-up-or-down",
            "eurusd-price-daily",
            "Down",
            CanonicalQuestionGroup.EUR_UP_DOWN_DAILY,
        ),
    ]
    for title, slug, event_slug, outcome, expected in cases:
        group = classify_polymarket_to_canonical_group(
            title=title,
            slug=slug,
            event_slug=event_slug,
            outcome=outcome,
        )
        assert group == expected, f"Expected {expected} for slug={slug!r}, got {group!r}"


def test_classify_russell_2000_slug_variant() -> None:
    """russell-2000- slug prefix also maps to RUT_UP_DOWN_DAILY."""
    group = classify_polymarket_to_canonical_group(
        title="Will Russell 2000 be up or down at close?",
        slug="russell-2000-daily-up-or-down",
        event_slug="russell-2000-price-daily",
        outcome="Up",
    )
    assert group == CanonicalQuestionGroup.RUT_UP_DOWN_DAILY


def test_classify_eth_monthly_falls_back_to_daily_canonical_group() -> None:
    """ETH slugs with MONTHLY resolution fall back to ETH_UP_DOWN_DAILY.

    Polymarket daily price markets use month-only or month+day slugs
    (e.g. "eth-up-or-down-april", "eth-up-or-down-may-22"). The taxonomy
    assigns MONTHLY resolution; classify_polymarket_to_canonical_group falls
    back to DAILY so these route to ETH_UP_DOWN_DAILY instead of None.
    """
    group = classify_polymarket_to_canonical_group(
        title="Will ETH be up or down by end of April?",
        slug="eth-up-or-down-april",
        event_slug="eth-monthly",
        outcome="Up",
    )
    assert group == CanonicalQuestionGroup.ETH_UP_DOWN_DAILY


def test_classify_altcoin_up_down_daily() -> None:
    """Alt-coin up-or-down markets map to {COIN}_UP_DOWN_DAILY (decision 338).

    Mirrors BTC/ETH: range_bracket + month-token → MONTHLY → DAILY fallback.
    """
    cases: list[tuple[str, str, CanonicalQuestionGroup]] = [
        ("solana-up-or-down-august-15", "Solana", CanonicalQuestionGroup.SOL_UP_DOWN_DAILY),
        ("xrp-up-or-down-september-3", "XRP", CanonicalQuestionGroup.XRP_UP_DOWN_DAILY),
        ("dogecoin-up-or-down-july-1", "Dogecoin", CanonicalQuestionGroup.DOGE_UP_DOWN_DAILY),
        ("bnb-up-or-down-june-12", "BNB", CanonicalQuestionGroup.BNB_UP_DOWN_DAILY),
        ("link-up-or-down-october-2", "Chainlink", CanonicalQuestionGroup.LINK_UP_DOWN_DAILY),
    ]
    for slug, name, expected in cases:
        group = classify_polymarket_to_canonical_group(
            title=f"Will {name} be up or down?",
            slug=slug,
            event_slug=f"{name.lower()}-price-daily",
            outcome="Up",
        )
        assert group == expected, f"Expected {expected} for slug={slug!r}, got {group!r}"


def test_classify_fed_market_groups_not_other() -> None:
    """FED markets now group (decision 338 — the (MACRO, FED_RATE) key was dead).

    The taxonomy emits underlying ``FED_FUNDS``; the event key was ``FED_RATE``
    so every FED market fell to OTHER. The corrected ``FED_FUNDS`` key routes
    them to FED_RATE_DECISION_PER_FOMC.
    """
    group = classify_polymarket_to_canonical_group(
        title="Will the Fed cut rates at the June meeting?",
        slug="fed-rate-decision-june",
        event_slug="fomc-june",
        outcome="Yes",
    )
    assert group == CanonicalQuestionGroup.FED_RATE_DECISION_PER_FOMC


def test_classify_macro_release_groups() -> None:
    """Recurring macro prints route to their per-release groups (decision 338)."""
    cases: list[tuple[str, str, CanonicalQuestionGroup]] = [
        (
            "unemployment-rate-may-2025",
            "May unemployment rate ≥4.6%?",
            CanonicalQuestionGroup.UNEMPLOYMENT_RATE_PER_MONTH,
        ),
        (
            "nonfarm-payrolls-june",
            "June nonfarm payrolls above 150k?",
            CanonicalQuestionGroup.NONFARM_PAYROLLS_PER_MONTH,
        ),
        ("ppi-print-march", "March PPI above 0.3%?", CanonicalQuestionGroup.PPI_PRINT_PER_MONTH),
        (
            "treasury-10-year-yield-friday",
            "10-year Treasury yield >4.5% Friday?",
            CanonicalQuestionGroup.TREASURY_YIELD_PER_PRINT,
        ),
        (
            "fear-greed-index-march-31",
            'Fear & Greed Index "Fear" on March 31?',
            CanonicalQuestionGroup.CRYPTO_FEAR_GREED_INDEX,
        ),
    ]
    for slug, title, expected in cases:
        group = classify_polymarket_to_canonical_group(
            title=title,
            slug=slug,
            event_slug="",
            outcome="Yes",
        )
        assert group == expected, f"Expected {expected} for slug={slug!r}, got {group!r}"


def test_classify_weather_temperature_groups() -> None:
    """Daily highest-temperature markets route to WEATHER_TEMP_DAILY (decision 338).

    Covers both the range_bracket ("between N-Nf") and binary ("Nf or higher")
    variants — the underlying ``TEMPERATURE`` is matched via the slug-token path.
    """
    range_group = classify_polymarket_to_canonical_group(
        title="Will the highest temperature in London be between 52-53°F on March 16?",
        slug="will-the-highest-temperature-in-london-be-between-52-53f-on-march-16",
        event_slug="london-temperature",
        outcome="Yes",
    )
    assert range_group == CanonicalQuestionGroup.WEATHER_TEMP_DAILY
    binary_group = classify_polymarket_to_canonical_group(
        title="Will the highest temperature in NYC be 83°F or higher on March 29?",
        slug="will-the-highest-temperature-in-nyc-be-83f-or-higher-on-march-29",
        event_slug="nyc-temperature",
        outcome="Yes",
    )
    assert binary_group == CanonicalQuestionGroup.WEATHER_TEMP_DAILY


def test_classify_unknown_returns_misc_novelty() -> None:
    """A genuinely-uncategorised slug (taxonomy → MISC/UNKNOWN) → MISC_NOVELTY.

    Decision 338 pass 2: the explicit novelty residual replaces OTHER for
    category=MISC so OTHER stops being a silent catch-all.
    """
    group = classify_polymarket_to_canonical_group(
        title="Will Mars be colonised by 2030?",
        slug="mars-colonised-by-2030",
        event_slug="space-colonisation",
        outcome="Yes",
    )
    assert group == CanonicalQuestionGroup.MISC_NOVELTY


def test_classify_pass2_subtype_routing() -> None:
    """decision 338 pass 2 — granular sub-type routing across categories."""
    cases: list[tuple[str, str, str, CanonicalQuestionGroup]] = [
        # (slug, title, outcome, expected)
        # Crypto PRICE-RANGE split from UP_DOWN — incl. BTC/ETH retrofit.
        (
            "will-the-price-of-bitcoin-be-between-90000-and-95000-on-september-15",
            "BTC between $90k-$95k?",
            "Yes",
            CanonicalQuestionGroup.BTC_PRICE_RANGE_DAILY,
        ),
        (
            "will-the-price-of-solana-be-between-180-and-185-on-september-3",
            "SOL between $180-$185?",
            "Yes",
            CanonicalQuestionGroup.SOL_PRICE_RANGE_DAILY,
        ),
        ("sol-multistrike-3h", "SOL multistrike", "Yes", CanonicalQuestionGroup.SOL_PRICE_RANGE_DAILY),
        # Political-figure split.
        (
            "will-trumps-approval-rating-be-between-46-and-47-on-march-21",
            "Trump approval 46-47%?",
            "Yes",
            CanonicalQuestionGroup.TRUMP_APPROVAL_RATING,
        ),
        (
            "will-trump-sign-an-executive-order-on-march-15",
            "Trump exec order March 15?",
            "Yes",
            CanonicalQuestionGroup.TRUMP_EXEC_ORDER,
        ),
        (
            "will-trump-say-epstein-during-doj-appearance",
            'Trump say "Epstein"?',
            "Yes",
            CanonicalQuestionGroup.TRUMP_STATEMENTS,
        ),
        (
            "will-elon-tweet-775-799-times-march-7-14",
            "Elon tweet 775-799 times?",
            "Yes",
            CanonicalQuestionGroup.ELON_TWEET_COUNT,
        ),
        (
            "will-elon-musk-net-worth-be-less-than-330b-on-march-31",
            "Elon net worth <$330b?",
            "Yes",
            CanonicalQuestionGroup.ELON_NET_WORTH,
        ),
        # Geopolitics conflict-by-date.
        (
            "israeli-military-action-against-iran-by-friday",
            "Israeli military action vs Iran by Friday?",
            "Yes",
            CanonicalQuestionGroup.GEO_ISRAEL_IRAN,
        ),
        (
            "russia-ukraine-ceasefire-in-march",
            "Russia/Ukraine ceasefire in March?",
            "Yes",
            CanonicalQuestionGroup.GEO_RUSSIA_UKRAINE,
        ),
        (
            "will-china-invade-taiwan-before-july",
            "China invade Taiwan before July?",
            "Yes",
            CanonicalQuestionGroup.GEO_OTHER_BY_DATE,
        ),
        # Culture box-office + commodity price-level.
        (
            "will-superman-opening-weekend-box-office-be-more-than-124m",
            "Superman opening weekend >$124m?",
            "Yes",
            CanonicalQuestionGroup.BOX_OFFICE_OPENING_WEEKEND,
        ),
        (
            "will-gold-be-above-3000-by-end-of-year",
            "Gold above $3000 by EOY?",
            "Yes",
            CanonicalQuestionGroup.GOLD_PRICE_LEVEL,
        ),
    ]
    for slug, title, outcome, expected in cases:
        group = classify_polymarket_to_canonical_group(
            title=title,
            slug=slug,
            event_slug="",
            outcome=outcome,
        )
        assert group == expected, f"Expected {expected} for slug={slug!r}, got {group!r}"


def test_classify_sports_league_bettype() -> None:
    """decision 338 pass 2 — sports SPORTS_{LEAGUE}_{BETTYPE} routing.

    league = taxonomy underlying; bet-type from slug; per-league MATCH fallback.
    """
    cases: list[tuple[str, str, CanonicalQuestionGroup]] = [
        # (slug, event_slug, expected)
        ("mlb-mia-tex-2025-08-15-nrfi", "mlb", CanonicalQuestionGroup.SPORTS_MLB_NRFI),
        ("mlb-nyy-bos-2025-08-15-spread", "mlb", CanonicalQuestionGroup.SPORTS_MLB_SPREAD),
        ("nfl-lv-was-2025-week-3-spread", "nfl", CanonicalQuestionGroup.SPORTS_NFL_SPREAD),
        ("nba-orl-phi-2025-total-220-5", "nba", CanonicalQuestionGroup.SPORTS_NBA_TOTAL),
        ("nhl-bos-tor-2025-moneyline", "nhl", CanonicalQuestionGroup.SPORTS_NHL_MATCH),
        ("epl-chelsea-arsenal-2025-winner", "epl", CanonicalQuestionGroup.SPORTS_EPL_MATCH),
        ("uefa-real-bayern-2025-total-goals", "uefa", CanonicalQuestionGroup.SPORTS_UEFA_TOTAL),
        ("f1-chinese-grand-prix-winner-2025", "f1", CanonicalQuestionGroup.SPORTS_F1_GP_WINNER),
        ("f1-australian-gp-constructor-highest-2025", "f1", CanonicalQuestionGroup.SPORTS_F1_CONSTRUCTOR),
        ("ufc-tybura-vs-parkin-winner", "ufc", CanonicalQuestionGroup.SPORTS_UFC_MATCH),
        ("golf-masters-2025-winner", "golf", CanonicalQuestionGroup.SPORTS_GOLF_MATCH),
    ]
    for slug, event_slug, expected in cases:
        group = classify_polymarket_to_canonical_group(
            title="Sports market",
            slug=slug,
            event_slug=event_slug,
            outcome="Yes",
        )
        assert group == expected, f"Expected {expected} for slug={slug!r}, got {group!r}"


def test_classify_crypto_up_down_still_routes_after_pass2() -> None:
    """Pass 2 must NOT regress UP_DOWN routing — direction bets stay UP_DOWN."""
    group = classify_polymarket_to_canonical_group(
        title="Will BTC be up or down today?",
        slug="btc-up-or-down-may-22",
        event_slug="btc-price-daily",
        outcome="Up",
    )
    assert group == CanonicalQuestionGroup.BTC_UP_DOWN_DAILY


def test_classify_polymarket_condition_id_override_wins() -> None:
    """A conditionId in the override dict bypasses rule-classification."""
    fake_id = "0xfake_condition_id_for_btc_up_down_hourly_test"
    POLYMARKET_CONDITION_ID_TO_GROUP[fake_id] = CanonicalQuestionGroup.BTC_UP_DOWN_HOURLY
    try:
        group = classify_polymarket_to_canonical_group(
            title="totally unrelated question",
            slug="something-else-entirely",
            event_slug="off-topic",
            outcome="Yes",
            condition_id=fake_id,
        )
        assert group == CanonicalQuestionGroup.BTC_UP_DOWN_HOURLY
    finally:
        del POLYMARKET_CONDITION_ID_TO_GROUP[fake_id]


def test_classify_kalshi_unknown_returns_other() -> None:
    assert classify_kalshi_to_canonical_group(ticker="UNKNOWN-TICKER-001") == CanonicalQuestionGroup.OTHER


def test_classify_kalshi_override_wins() -> None:
    fake_ticker = "FAKEFEDDEC25"
    KALSHI_TICKER_TO_GROUP[fake_ticker] = CanonicalQuestionGroup.FED_RATE_DECISION_PER_FOMC
    try:
        assert (
            classify_kalshi_to_canonical_group(ticker=fake_ticker) == CanonicalQuestionGroup.FED_RATE_DECISION_PER_FOMC
        )
    finally:
        del KALSHI_TICKER_TO_GROUP[fake_ticker]


def test_classify_kalshi_real_live_tickers_to_shared_groups() -> None:
    """Representative REAL Kalshi event tickers (from the live /series catalogue,
    probed 2026-06-23) classify to the SHARED canonical groups — never OTHER for
    the cross-venue-relevant crypto-daily / macro / equity-index families. This is
    the cross-venue arb premise: a Kalshi crypto-daily must land in the same group
    Polymarket's crypto-daily lands in."""
    cases: list[tuple[str, CanonicalQuestionGroup]] = [
        # Crypto daily directional — same groups Polymarket BTC/ETH/SOL/XRP/DOGE daily hit.
        ("KXBTCD-26JUN23", CanonicalQuestionGroup.BTC_UP_DOWN_DAILY),
        ("KXETHD-26JUN23", CanonicalQuestionGroup.ETH_UP_DOWN_DAILY),
        ("KXSOLD-26JUN23", CanonicalQuestionGroup.SOL_UP_DOWN_DAILY),
        ("KXXRPD-26JUN23", CanonicalQuestionGroup.XRP_UP_DOWN_DAILY),
        ("KXDOGED-26JUN23", CanonicalQuestionGroup.DOGE_UP_DOWN_DAILY),
        # XRP under Kalshi's legacy "RIPPLE" stem — the 2026-06-23 gap fix.
        ("KXRIPPLED-26JUN23", CanonicalQuestionGroup.XRP_UP_DOWN_DAILY),
        ("KXRIPPLE-26JUN23", CanonicalQuestionGroup.XRP_PRICE_RANGE_DAILY),
        # Macro releases — shared with Polymarket.
        ("KXCPIYOY-26JUN", CanonicalQuestionGroup.CPI_PRINT_PER_MONTH),
        ("KXFEDDECISION-26JUL", CanonicalQuestionGroup.FED_RATE_DECISION_PER_FOMC),
        ("KXGDP-26Q2", CanonicalQuestionGroup.GDP_PRINT_PER_QUARTER),
        ("KXPAYROLLS-26JUN", CanonicalQuestionGroup.NONFARM_PAYROLLS_PER_MONTH),
        # Equity indices.
        ("KXINXU-26JUN23", CanonicalQuestionGroup.SPX_UP_DOWN_DAILY),
        ("KXNASDAQ100U-26JUN23", CanonicalQuestionGroup.NDX_UP_DOWN_DAILY),
    ]
    for ticker, expected in cases:
        assert classify_kalshi_to_canonical_group(ticker=ticker) == expected, ticker


def test_kalshi_polymarket_cross_venue_same_canonical_group() -> None:
    """The same real-world question on BOTH venues resolves to the IDENTICAL
    CanonicalQuestionGroup — the cross-venue arb invariant. BTC/ETH daily directional
    + CPI + Fed-rate trade on both Kalshi and Polymarket; both must agree on the group
    so arbitrage_price_dispersion compares fair-value without a translation layer."""
    pairs: list[tuple[str, dict[str, str], CanonicalQuestionGroup]] = [
        (
            "KXBTCD-26JUN23",
            {"title": "Bitcoin price today", "slug": "btc-up-or-down-june-23", "event_slug": "btc", "outcome": "Up"},
            CanonicalQuestionGroup.BTC_UP_DOWN_DAILY,
        ),
        (
            "KXETHD-26JUN23",
            {"title": "Ethereum price today", "slug": "eth-up-or-down-june-23", "event_slug": "eth", "outcome": "Up"},
            CanonicalQuestionGroup.ETH_UP_DOWN_DAILY,
        ),
    ]
    for kalshi_ticker, poly_kwargs, expected in pairs:
        kalshi_group = classify_kalshi_to_canonical_group(ticker=kalshi_ticker)
        poly_group = classify_polymarket_to_canonical_group(**poly_kwargs)
        assert kalshi_group == expected, kalshi_ticker
        assert poly_group == expected, poly_kwargs["slug"]
        assert kalshi_group == poly_group  # the cross-venue invariant


def test_classify_kalshi_sports_per_game_markets_to_shared_groups() -> None:
    """Kalshi per-GAME sports markets (KX{LEAGUE}…GAME / *SPREAD / *TOTAL / *NRFI)
    map to the SAME SPORTS_{LEAGUE}_{BETTYPE} groups Polymarket uses — so same-game
    instruments pair cross-venue. Verified ticker stems from the live catalogue."""
    cases: list[tuple[str, CanonicalQuestionGroup]] = [
        ("KXNHLGAME-26JUN23", CanonicalQuestionGroup.SPORTS_NHL_MATCH),
        ("KXNFLGAME-26SEP-X", CanonicalQuestionGroup.SPORTS_NFL_MATCH),
        ("KXEPLGAME-26AUG-X", CanonicalQuestionGroup.SPORTS_EPL_MATCH),
        ("KXUCLGAME-26FEB-X", CanonicalQuestionGroup.SPORTS_CHAMPIONS_LEAGUE_MATCH),
        ("KXMLBGAME-26JUN23", CanonicalQuestionGroup.SPORTS_MLB_MATCH),
        ("KXNFLTOTAL-26SEP-X", CanonicalQuestionGroup.SPORTS_NFL_TOTAL),
        ("KXNFLSPREAD-26SEP-X", CanonicalQuestionGroup.SPORTS_NFL_SPREAD),
        ("KXMLBNRFI-26JUN23", CanonicalQuestionGroup.SPORTS_MLB_NRFI),
        ("KXNBASPREAD-26JAN-X", CanonicalQuestionGroup.SPORTS_NBA_SPREAD),
    ]
    for ticker, expected in cases:
        assert classify_kalshi_to_canonical_group(ticker=ticker) == expected, ticker


def test_classify_kalshi_sports_props_and_minor_leagues_stay_other() -> None:
    """Season-futures / draft / award / within-match props + minor world leagues are
    NOT cleanly arbable (Polymarket rarely lists an identical contract) → OTHER, never
    a false MATCH pairing."""
    for ticker in [
        "KXNFLDRAFTQB-26",  # draft prop
        "KXNFLEXACTWINSLA-26",  # season win total
        "KXNBADRAFT10-26",  # draft pick
        "KXMLBWINS-COL-26",  # season wins
        "KXATPGAMETOTAL-26",  # tennis total-games — no SPORTS_TENNIS_TOTAL group → not forced to MATCH
        "KXWCMESSIMBAPPE-26",  # within-tournament prop
        "KXLIIGAGAME-26",  # minor world league (no canonical group)
        "KXKHLGAME-26",  # minor world league
    ]:
        assert classify_kalshi_to_canonical_group(ticker=ticker) == CanonicalQuestionGroup.OTHER, ticker


def test_classify_kalshi_euro_basketball_not_misclassified_as_fx() -> None:
    """Regression: the FX EUR prefix must not catch EuroLeague/EuroCup basketball or
    Eurovision (the greedy bare 'KXEURO' prefix was dropped 2026-06-23). Real EUR/USD
    (KXEURUSD*, KXEUROIMF) still maps to EUR_UP_DOWN_DAILY."""
    assert classify_kalshi_to_canonical_group(ticker="KXEUROLEAGUEGAME-26") == CanonicalQuestionGroup.OTHER
    assert classify_kalshi_to_canonical_group(ticker="KXEUROCUPTOTAL-26") == CanonicalQuestionGroup.OTHER
    assert classify_kalshi_to_canonical_group(ticker="KXEUROVISIONISRAELBAN-26") == CanonicalQuestionGroup.OTHER
    assert classify_kalshi_to_canonical_group(ticker="KXEURUSDD-26") == CanonicalQuestionGroup.EUR_UP_DOWN_DAILY
    assert classify_kalshi_to_canonical_group(ticker="KXEUROIMF-26") == CanonicalQuestionGroup.EUR_UP_DOWN_DAILY


# ---------------------------------------------------------------------------
# Stability hash
# ---------------------------------------------------------------------------


def test_classifier_stability_hash_is_deterministic() -> None:
    """Re-import yields the same hash (regex + override sources unchanged)."""
    from unified_api_contracts.predictions import (
        CLASSIFIER_STABILITY_HASH as SECOND_READ,
    )

    assert SECOND_READ == CLASSIFIER_STABILITY_HASH


def test_classifier_stability_hash_is_hex() -> None:
    """SHA-256 truncated hexdigest — 16 lowercase hex characters."""
    assert len(CLASSIFIER_STABILITY_HASH) == 16
    int(CLASSIFIER_STABILITY_HASH, 16)  # raises ValueError if non-hex


# ---------------------------------------------------------------------------
# Lifecycle helpers
# ---------------------------------------------------------------------------


_UTC = _dt.UTC


def _make_lifecycle(
    *,
    market_id: str = "MKT-1",
    canonical_group: CanonicalQuestionGroup = CanonicalQuestionGroup.BTC_UP_DOWN_HOURLY,
    created: _dt.datetime,
    resolved: _dt.datetime,
    settled: _dt.datetime,
    status: str = "active",
) -> MarketLifecycle:
    return MarketLifecycle(
        market_id=market_id,
        venue="POLYMARKET",
        canonical_group=canonical_group,
        market_created_at=created,
        resolution_time=resolved,
        settlement_time=settled,
        current_status=status,  # pyright: ignore[reportArgumentType]
    )


def test_is_market_active_at_during_window() -> None:
    lc = _make_lifecycle(
        created=_dt.datetime(2026, 5, 6, 10, 0, tzinfo=_UTC),
        resolved=_dt.datetime(2026, 5, 6, 11, 0, tzinfo=_UTC),
        settled=_dt.datetime(2026, 5, 6, 13, 0, tzinfo=_UTC),
    )
    assert is_market_active_at(lc, _dt.datetime(2026, 5, 6, 10, 30, tzinfo=_UTC))


def test_is_market_active_at_before_creation() -> None:
    lc = _make_lifecycle(
        created=_dt.datetime(2026, 5, 6, 10, 0, tzinfo=_UTC),
        resolved=_dt.datetime(2026, 5, 6, 11, 0, tzinfo=_UTC),
        settled=_dt.datetime(2026, 5, 6, 13, 0, tzinfo=_UTC),
    )
    assert not is_market_active_at(lc, _dt.datetime(2026, 5, 6, 9, 59, tzinfo=_UTC))


def test_is_market_active_at_after_settlement() -> None:
    lc = _make_lifecycle(
        created=_dt.datetime(2026, 5, 6, 10, 0, tzinfo=_UTC),
        resolved=_dt.datetime(2026, 5, 6, 11, 0, tzinfo=_UTC),
        settled=_dt.datetime(2026, 5, 6, 13, 0, tzinfo=_UTC),
    )
    assert not is_market_active_at(lc, _dt.datetime(2026, 5, 6, 13, 1, tzinfo=_UTC))


def test_expected_market_ids_for_canonical_group_overlap() -> None:
    """Lifecycle whose [created, settled) overlaps the day → market_id included."""
    day = _dt.date(2026, 5, 6)
    lifecycles = [
        _make_lifecycle(
            market_id="MKT-OVERLAP",
            created=_dt.datetime(2026, 5, 5, 23, 30, tzinfo=_UTC),
            resolved=_dt.datetime(2026, 5, 6, 0, 30, tzinfo=_UTC),
            settled=_dt.datetime(2026, 5, 6, 2, 30, tzinfo=_UTC),
        ),
        _make_lifecycle(
            market_id="MKT-BEFORE",
            created=_dt.datetime(2026, 5, 4, 10, 0, tzinfo=_UTC),
            resolved=_dt.datetime(2026, 5, 4, 11, 0, tzinfo=_UTC),
            settled=_dt.datetime(2026, 5, 5, 13, 0, tzinfo=_UTC),
        ),
        _make_lifecycle(
            market_id="MKT-AFTER",
            created=_dt.datetime(2026, 5, 7, 10, 0, tzinfo=_UTC),
            resolved=_dt.datetime(2026, 5, 7, 11, 0, tzinfo=_UTC),
            settled=_dt.datetime(2026, 5, 7, 13, 0, tzinfo=_UTC),
        ),
    ]
    result = expected_market_ids_for_canonical_group(CanonicalQuestionGroup.BTC_UP_DOWN_HOURLY, day, lifecycles)
    assert result == {"MKT-OVERLAP"}


def test_expected_market_ids_filters_by_canonical_group() -> None:
    day = _dt.date(2026, 5, 6)
    lifecycles = [
        _make_lifecycle(
            market_id="BTC-MKT",
            canonical_group=CanonicalQuestionGroup.BTC_UP_DOWN_HOURLY,
            created=_dt.datetime(2026, 5, 6, 10, 0, tzinfo=_UTC),
            resolved=_dt.datetime(2026, 5, 6, 11, 0, tzinfo=_UTC),
            settled=_dt.datetime(2026, 5, 6, 13, 0, tzinfo=_UTC),
        ),
        _make_lifecycle(
            market_id="ETH-MKT",
            canonical_group=CanonicalQuestionGroup.ETH_UP_DOWN_HOURLY,
            created=_dt.datetime(2026, 5, 6, 10, 0, tzinfo=_UTC),
            resolved=_dt.datetime(2026, 5, 6, 11, 0, tzinfo=_UTC),
            settled=_dt.datetime(2026, 5, 6, 13, 0, tzinfo=_UTC),
        ),
    ]
    btc_only = expected_market_ids_for_canonical_group(CanonicalQuestionGroup.BTC_UP_DOWN_HOURLY, day, lifecycles)
    assert btc_only == {"BTC-MKT"}


# ---------------------------------------------------------------------------
# PREDICTION_GROUPS registry consistency with CanonicalQuestionGroup
# ---------------------------------------------------------------------------


def test_prediction_groups_registry_keys_match_canonical_enum() -> None:
    """Every PREDICTION_GROUPS key matches a CanonicalQuestionGroup enum value."""
    enum_values = {g.value for g in CanonicalQuestionGroup}
    registry_keys = set(PREDICTION_GROUPS.keys())
    assert registry_keys <= enum_values


def test_prediction_canonical_question_group_in_bundled_data_types() -> None:
    """The bundled-data_type set names the prediction shard data_type."""
    assert "prediction_canonical_question_group" in BUNDLED_DATA_TYPES
    assert DATA_TYPE_TO_CLUSTER_REGISTRY["prediction_canonical_question_group"] == "PREDICTION_GROUPS"


def test_prediction_groups_have_per_market_min_rows() -> None:
    """Every populated PREDICTION_GROUPS entry carries the min-rows floor."""
    for group_name, registry in PREDICTION_GROUPS.items():
        assert "_per_market_min_rows" in registry, group_name
        assert registry["_per_market_min_rows"] > 0


# ---------------------------------------------------------------------------
# _MONTHLY_TOKENS bug fix — "may" full-name now in the set
# ---------------------------------------------------------------------------


def test_other_bucket_member_added_logged_on_unknown_polymarket(caplog: pytest.LogCaptureFixture) -> None:
    """Unmatched Polymarket market emits OTHER_BUCKET_MEMBER_ADDED at INFO."""
    import logging

    with caplog.at_level(logging.INFO, logger="unified_api_contracts.canonical.domain.predictions.classifiers"):
        group = classify_polymarket_to_canonical_group(
            title="Will Mars be colonised by 2030?",
            slug="mars-colonised-by-2030",
            event_slug="space-colonisation",
            outcome="Yes",
            condition_id="0xdeadbeef",
        )
    # decision 338 pass 2: genuinely-uncategorised → MISC_NOVELTY (the log still
    # fires so operators can audit the residual).
    assert group == CanonicalQuestionGroup.MISC_NOVELTY
    assert any("OTHER_BUCKET_MEMBER_ADDED" in r.message for r in caplog.records)


def test_other_bucket_member_added_logged_on_unknown_kalshi(caplog: pytest.LogCaptureFixture) -> None:
    """Unmatched Kalshi ticker emits OTHER_BUCKET_MEMBER_ADDED at INFO."""
    import logging

    with caplog.at_level(logging.INFO, logger="unified_api_contracts.canonical.domain.predictions.classifiers"):
        group = classify_kalshi_to_canonical_group(ticker="UNKNOWN-TICKER-001")
    assert group == CanonicalQuestionGroup.OTHER
    assert any("OTHER_BUCKET_MEMBER_ADDED" in r.message for r in caplog.records)


def test_other_in_prediction_groups_registry() -> None:
    """OTHER is a first-class entry in PREDICTION_GROUPS (task -002 gate)."""
    assert "OTHER" in PREDICTION_GROUPS
    assert PREDICTION_GROUPS["OTHER"]["_per_market_min_rows"] >= 1


def test_other_in_bundled_data_types_coverage() -> None:
    """prediction_canonical_question_group bundles OTHER like any curated group (task -004 gate)."""
    assert "prediction_canonical_question_group" in BUNDLED_DATA_TYPES
    assert "OTHER" in PREDICTION_GROUPS


def test_monthly_tokens_includes_may_full_name() -> None:
    """2026-05-06 bug fix: "may" was missing from the full-name set."""
    from unified_api_contracts.internal.schemas._prediction_market_taxonomy import (
        _MONTHLY_TOKENS,
    )

    assert "may" in _MONTHLY_TOKENS
    # Sanity: full names alongside "may"
    assert "april" in _MONTHLY_TOKENS
    assert "june" in _MONTHLY_TOKENS


# ---------------------------------------------------------------------------
# Kalshi prefix-rule classifier (2026-06-20)
# ---------------------------------------------------------------------------


def test_kalshi_prefix_table_exported_from_facade() -> None:
    """KALSHI_TICKER_PREFIX_TO_GROUP is re-exported from the public facade."""
    assert isinstance(KALSHI_TICKER_PREFIX_TO_GROUP, dict)
    assert len(KALSHI_TICKER_PREFIX_TO_GROUP) >= 50  # sanity floor


def test_kalshi_prefix_table_all_valid_groups() -> None:
    """Every value in the prefix table is a valid CanonicalQuestionGroup member."""
    for prefix, group in KALSHI_TICKER_PREFIX_TO_GROUP.items():
        assert isinstance(group, CanonicalQuestionGroup), (
            f"prefix {prefix!r} maps to {group!r} which is not a CanonicalQuestionGroup"
        )


def test_kalshi_prefix_rule_btc_daily_directional() -> None:
    """KXBTCD-* → BTC_UP_DOWN_DAILY (shared arb target with Polymarket)."""
    assert classify_kalshi_to_canonical_group(ticker="KXBTCD-26JUN20") == CanonicalQuestionGroup.BTC_UP_DOWN_DAILY
    assert classify_kalshi_to_canonical_group(ticker="KXBTCD-B") == CanonicalQuestionGroup.BTC_UP_DOWN_DAILY


def test_kalshi_prefix_rule_btc_price_range() -> None:
    """KXBTC-DDMMMYYHH → BTC_PRICE_RANGE_DAILY (date-keyed range bracket)."""
    # The generic KXBTC prefix beats the absent KXBTCD-specific ticker for a range contract
    assert classify_kalshi_to_canonical_group(ticker="KXBTC-26JUN2617") == CanonicalQuestionGroup.BTC_PRICE_RANGE_DAILY
    assert classify_kalshi_to_canonical_group(ticker="KXBTC-26JUN2006") == CanonicalQuestionGroup.BTC_PRICE_RANGE_DAILY


def test_kalshi_prefix_rule_btc_15m() -> None:
    """KXBTC15M-* → BTC_UP_DOWN_15MIN (longer prefix wins over KXBTC)."""
    assert classify_kalshi_to_canonical_group(ticker="KXBTC15M-26JUN2014") == CanonicalQuestionGroup.BTC_UP_DOWN_15MIN


def test_kalshi_prefix_rule_eth() -> None:
    """KXETH* family correctly disambiguated."""
    assert classify_kalshi_to_canonical_group(ticker="KXETHD-26JUN20") == CanonicalQuestionGroup.ETH_UP_DOWN_DAILY
    assert classify_kalshi_to_canonical_group(ticker="KXETH15M-26JUN2014") == CanonicalQuestionGroup.ETH_UP_DOWN_15MIN
    assert classify_kalshi_to_canonical_group(ticker="KXETH-26JUN2017") == CanonicalQuestionGroup.ETH_PRICE_RANGE_DAILY


def test_kalshi_prefix_rule_sol() -> None:
    """KXSOL* — daily directional and range bracket."""
    assert classify_kalshi_to_canonical_group(ticker="KXSOLD-26JUN20") == CanonicalQuestionGroup.SOL_UP_DOWN_DAILY
    assert classify_kalshi_to_canonical_group(ticker="KXSOL15M-26JUN20") == CanonicalQuestionGroup.SOL_UP_DOWN_DAILY
    assert classify_kalshi_to_canonical_group(ticker="KXSOL-26JUN20") == CanonicalQuestionGroup.SOL_PRICE_RANGE_DAILY


def test_kalshi_prefix_rule_xrp() -> None:
    """KXXRP* — daily directional and range bracket."""
    assert classify_kalshi_to_canonical_group(ticker="KXXRPD-26JUN20") == CanonicalQuestionGroup.XRP_UP_DOWN_DAILY
    assert classify_kalshi_to_canonical_group(ticker="KXXRP15M-26JUN20") == CanonicalQuestionGroup.XRP_UP_DOWN_DAILY
    assert classify_kalshi_to_canonical_group(ticker="KXXRP-26JUN20") == CanonicalQuestionGroup.XRP_PRICE_RANGE_DAILY


def test_kalshi_prefix_rule_doge() -> None:
    """KXDOGE* — directional and range bracket."""
    assert classify_kalshi_to_canonical_group(ticker="KXDOGED-26JUN20") == CanonicalQuestionGroup.DOGE_UP_DOWN_DAILY
    assert classify_kalshi_to_canonical_group(ticker="KXDOGE15M-26JUN") == CanonicalQuestionGroup.DOGE_UP_DOWN_DAILY
    assert classify_kalshi_to_canonical_group(ticker="KXDOGE-26JUN20") == CanonicalQuestionGroup.DOGE_PRICE_RANGE_DAILY


def test_kalshi_prefix_rule_spx_inx() -> None:
    """KXINX* → SPX_UP_DOWN_DAILY — same group as Polymarket (cross-venue arb)."""
    assert classify_kalshi_to_canonical_group(ticker="KXINX-26JUN20") == CanonicalQuestionGroup.SPX_UP_DOWN_DAILY
    assert classify_kalshi_to_canonical_group(ticker="KXINXI-26JUN20") == CanonicalQuestionGroup.SPX_UP_DOWN_DAILY
    assert classify_kalshi_to_canonical_group(ticker="KXINXU-26JUN20") == CanonicalQuestionGroup.SPX_UP_DOWN_DAILY
    assert classify_kalshi_to_canonical_group(ticker="KXINXB-26JUN20") == CanonicalQuestionGroup.SPX_UP_DOWN_DAILY


def test_kalshi_prefix_rule_nasdaq_ndx() -> None:
    """KXNASDAQ100* → NDX_UP_DOWN_DAILY — shared with Polymarket."""
    assert classify_kalshi_to_canonical_group(ticker="KXNASDAQ100-26JUN20") == CanonicalQuestionGroup.NDX_UP_DOWN_DAILY
    assert classify_kalshi_to_canonical_group(ticker="KXNASDAQ100U-26JUN") == CanonicalQuestionGroup.NDX_UP_DOWN_DAILY


def test_kalshi_prefix_rule_djia() -> None:
    """KXDJIA-* → DJIA_UP_DOWN_DAILY."""
    assert classify_kalshi_to_canonical_group(ticker="KXDJIA-26JUN20") == CanonicalQuestionGroup.DJIA_UP_DOWN_DAILY


def test_kalshi_prefix_rule_rut() -> None:
    """KXRUT-* → RUT_UP_DOWN_DAILY."""
    assert classify_kalshi_to_canonical_group(ticker="KXRUT-26JUN20") == CanonicalQuestionGroup.RUT_UP_DOWN_DAILY


def test_kalshi_prefix_rule_gold() -> None:
    """KXGOLDD → daily; KXGOLD generic → price level."""
    assert classify_kalshi_to_canonical_group(ticker="KXGOLDD-26JUN20") == CanonicalQuestionGroup.GOLD_UP_DOWN_DAILY
    assert classify_kalshi_to_canonical_group(ticker="KXGOLD-26JUN20") == CanonicalQuestionGroup.GOLD_PRICE_LEVEL


def test_kalshi_prefix_rule_macro_fed() -> None:
    """KXFED* → FED_RATE_DECISION_PER_FOMC — shared with Polymarket (cross-venue arb)."""
    assert (
        classify_kalshi_to_canonical_group(ticker="KXFEDDECISION-25DEC")
        == CanonicalQuestionGroup.FED_RATE_DECISION_PER_FOMC
    )
    assert classify_kalshi_to_canonical_group(ticker="KXFED-25JAN") == CanonicalQuestionGroup.FED_RATE_DECISION_PER_FOMC


def test_kalshi_prefix_rule_macro_cpi() -> None:
    """KXCPI* → CPI_PRINT_PER_MONTH — shared with Polymarket (cross-venue arb)."""
    assert classify_kalshi_to_canonical_group(ticker="KXCPI-26JUN") == CanonicalQuestionGroup.CPI_PRINT_PER_MONTH
    assert classify_kalshi_to_canonical_group(ticker="KXCPIYOY-26JUN") == CanonicalQuestionGroup.CPI_PRINT_PER_MONTH
    assert classify_kalshi_to_canonical_group(ticker="KXCPICORE-26JUN") == CanonicalQuestionGroup.CPI_PRINT_PER_MONTH


def test_kalshi_prefix_rule_macro_payrolls() -> None:
    """KXPAYROLLS-* → NONFARM_PAYROLLS_PER_MONTH — shared with Polymarket."""
    assert (
        classify_kalshi_to_canonical_group(ticker="KXPAYROLLS-26JUN")
        == CanonicalQuestionGroup.NONFARM_PAYROLLS_PER_MONTH
    )


def test_kalshi_prefix_rule_macro_gdp() -> None:
    """KXGDP-* → GDP_PRINT_PER_QUARTER — shared with Polymarket."""
    assert classify_kalshi_to_canonical_group(ticker="KXGDP-26Q2") == CanonicalQuestionGroup.GDP_PRINT_PER_QUARTER


def test_kalshi_prefix_rule_macro_pce() -> None:
    """KXPCECORE-* → PCE_PRINT_PER_MONTH."""
    assert classify_kalshi_to_canonical_group(ticker="KXPCECORE-26JUN") == CanonicalQuestionGroup.PCE_PRINT_PER_MONTH


def test_kalshi_prefix_rule_treasury_yields() -> None:
    """KX10Y* → TREASURY_YIELD_PER_PRINT — shared with Polymarket."""
    assert (
        classify_kalshi_to_canonical_group(ticker="KX10YUSTSRY-26JUN20")
        == CanonicalQuestionGroup.TREASURY_YIELD_PER_PRINT
    )
    assert (
        classify_kalshi_to_canonical_group(ticker="KX10Y2Y-26JUN20") == CanonicalQuestionGroup.TREASURY_YIELD_PER_PRINT
    )


def test_kalshi_prefix_rule_oil() -> None:
    """KXOIL* → CRUDE_OIL_PRICE_LEVEL."""
    assert classify_kalshi_to_canonical_group(ticker="KXOIL-26JUN") == CanonicalQuestionGroup.CRUDE_OIL_PRICE_LEVEL
    assert classify_kalshi_to_canonical_group(ticker="KXOILW-26JUN") == CanonicalQuestionGroup.CRUDE_OIL_PRICE_LEVEL


def test_kalshi_prefix_rule_natgas() -> None:
    """KXGAS* → NATGAS_UP_DOWN_DAILY."""
    assert classify_kalshi_to_canonical_group(ticker="KXGAS-26JUN") == CanonicalQuestionGroup.NATGAS_UP_DOWN_DAILY
    assert classify_kalshi_to_canonical_group(ticker="KXGASD-26JUN") == CanonicalQuestionGroup.NATGAS_UP_DOWN_DAILY


def test_kalshi_prefix_longest_prefix_wins() -> None:
    """Longest-prefix wins: KXBTCD beats KXBTC; KXBTC15M beats KXBTC."""
    # KXBTCD (len 6) > KXBTC (len 5)
    assert classify_kalshi_to_canonical_group(ticker="KXBTCD-26JUN20") == CanonicalQuestionGroup.BTC_UP_DOWN_DAILY
    # KXBTC15M (len 8) > KXBTC (len 5)
    assert classify_kalshi_to_canonical_group(ticker="KXBTC15M-26JUN2014") == CanonicalQuestionGroup.BTC_UP_DOWN_15MIN
    # KXFEDDECISION (len 13) > KXFED (len 5)
    assert (
        classify_kalshi_to_canonical_group(ticker="KXFEDDECISION-25MAR")
        == CanonicalQuestionGroup.FED_RATE_DECISION_PER_FOMC
    )


def test_kalshi_override_wins_over_prefix_rule() -> None:
    """Exact-override dict beats the prefix rule for the same ticker."""
    # Temporarily inject a BTC-range ticker into the override dict pointing to ETH_UP_DOWN_DAILY
    # (nonsensical semantically but tests the priority order).
    fake_ticker = "KXBTC-OVERRIDETEST"
    KALSHI_TICKER_TO_GROUP[fake_ticker] = CanonicalQuestionGroup.ETH_UP_DOWN_DAILY
    try:
        result = classify_kalshi_to_canonical_group(ticker=fake_ticker)
        assert result == CanonicalQuestionGroup.ETH_UP_DOWN_DAILY, "override dict should win over the KXBTC prefix rule"
    finally:
        del KALSHI_TICKER_TO_GROUP[fake_ticker]


def test_kalshi_prefix_rule_case_insensitive() -> None:
    """Lower-case ticker input is handled — function upper-cases internally."""
    assert classify_kalshi_to_canonical_group(ticker="kxbtcd-26jun20") == CanonicalQuestionGroup.BTC_UP_DOWN_DAILY
    assert classify_kalshi_to_canonical_group(ticker="kxcpi-26jun") == CanonicalQuestionGroup.CPI_PRINT_PER_MONTH


def test_kalshi_shared_group_equals_polymarket_group() -> None:
    """Kalshi+Polymarket same real-world questions → identical CanonicalQuestionGroup value.

    This is the cross-venue arb invariant: the ``arbitrage_price_dispersion``
    strategy can compare fair-value by looking up the canonical group on both
    sides without any translation layer.
    """
    # BTC daily up/down
    kalshi_btc = classify_kalshi_to_canonical_group(ticker="KXBTCD-26JUN20")
    poly_btc = classify_polymarket_to_canonical_group(
        title="Will BTC be up or down today?",
        slug="btc-up-or-down-may-22",
        event_slug="btc-price-daily",
        outcome="Up",
    )
    assert kalshi_btc == poly_btc == CanonicalQuestionGroup.BTC_UP_DOWN_DAILY

    # FED rate decision
    kalshi_fed = classify_kalshi_to_canonical_group(ticker="KXFED-25JAN")
    poly_fed = classify_polymarket_to_canonical_group(
        title="Will the Fed cut rates at the June meeting?",
        slug="fed-rate-decision-june",
        event_slug="fomc-june",
        outcome="Yes",
    )
    assert kalshi_fed == poly_fed == CanonicalQuestionGroup.FED_RATE_DECISION_PER_FOMC

    # CPI monthly print
    kalshi_cpi = classify_kalshi_to_canonical_group(ticker="KXCPI-26JUN")
    poly_cpi = classify_polymarket_to_canonical_group(
        title="Will US CPI be above 3.5% YoY?",
        slug="cpi-above-3-5-june",
        event_slug="cpi-june",
        outcome="Yes",
    )
    assert kalshi_cpi == poly_cpi == CanonicalQuestionGroup.CPI_PRINT_PER_MONTH


def test_kalshi_copper_routes_to_other() -> None:
    """KXCOPPERD has no dedicated group yet → OTHER (copper group is a TODO)."""
    result = classify_kalshi_to_canonical_group(ticker="KXCOPPERD-26JUN20")
    assert result == CanonicalQuestionGroup.OTHER


def test_kalshi_novel_ticker_routes_to_other() -> None:
    """Completely unknown tickers (KXELONMARS, pop-culture, etc.) → OTHER."""
    for ticker in ("KXELONMARS-99", "KXNEWPOPE-70", "KXMRBEASTVIDEOLENGTH", "KXFUSION"):
        result = classify_kalshi_to_canonical_group(ticker=ticker)
        assert result == CanonicalQuestionGroup.OTHER, f"Expected OTHER for {ticker!r}, got {result!r}"
