"""Per-instrument Kalshi ↔ Polymarket same-market matcher tests.

Fixtures use the REAL prediction ``InstrumentRecord`` field shapes written by the
live instruments-service adapters (verified 2026-06-24):

* both venues write ``instrument_type=PREDICTION_MARKET``, ``strike=None`` (the
  Decimal field is unused for predictions), and a populated ``expiry``;
* Kalshi ``instrument_key`` = the MARKET ticker (``KXBTCD-26JUN24-T95000``),
  ``raw_symbol`` = the EVENT ticker (``KXBTCD-26JUN24``);
* Polymarket ``instrument_key`` = ``condition_id``, ``raw_symbol`` = slug.
* The canonical record carries NO title field, so sports tests pass the human
  "Away vs Home" title via the ``titles=`` map.

So the matcher PARSES the strike from the ticker (Kalshi) / slug (Polymarket) and
joins on ``(underlying, bet_type, settlement, strike)`` — never on the
always-``None`` record strike. The same-settlement guard (different strike OR
different settlement date ⇒ NO pair) is exercised explicitly.
"""

from __future__ import annotations

from datetime import UTC, datetime

from unified_api_contracts.internal.reference.instrument import (
    InstrumentRecord,
    InstrumentType,
)
from unified_api_contracts.predictions import build_cross_venue_mapping, match_key


def _kalshi(
    *,
    market_ticker: str,
    event_ticker: str,
    title: str = "",
    expiry: datetime | None,
    base_asset: str = "",
    af_fixture_id: int | None = None,
) -> InstrumentRecord:
    """A Kalshi prediction InstrumentRecord in the real adapter shape.

    NOTE: the canonical ``InstrumentRecord`` has NO ``symbol``/title field, so
    ``title`` here is documentation only (sports tests pass it via ``titles=``).
    ``af_fixture_id`` defaults to ``None`` (honest absence) — set it to exercise
    the fixture-id-primary sports key.
    """
    return InstrumentRecord(
        instrument_key=market_ticker,
        venue="KALSHI",
        instrument_type=InstrumentType.PREDICTION_MARKET,
        raw_symbol=event_ticker,
        base_asset=base_asset,
        quote_asset="USD",
        settle_asset="USD",
        expiry=expiry,
        strike=None,
        af_fixture_id=af_fixture_id,
    )


def _polymarket(
    *,
    condition_id: str,
    slug: str,
    title: str = "",
    expiry: datetime | None,
    base_asset: str = "",
    af_fixture_id: int | None = None,
) -> InstrumentRecord:
    """A Polymarket prediction InstrumentRecord in the real adapter shape."""
    return InstrumentRecord(
        instrument_key=condition_id,
        venue="POLYMARKET",
        instrument_type=InstrumentType.PREDICTION_MARKET,
        raw_symbol=slug,
        base_asset=base_asset,
        quote_asset="USD",
        settle_asset="USD",
        expiry=expiry,
        strike=None,
        af_fixture_id=af_fixture_id,
    )


# ---------------------------------------------------------------------------
# Crypto price pair — same BTC strike + same settlement on both venues → 1 row.
# ---------------------------------------------------------------------------


def test_crypto_price_range_pair_same_strike_and_expiry() -> None:
    expiry = datetime(2026, 6, 24, 21, 0, tzinfo=UTC)
    kalshi = _kalshi(
        market_ticker="KXBTC-26JUN24-T95000",
        event_ticker="KXBTC-26JUN24",
        title="Bitcoin price on Jun 24?",
        expiry=expiry,
    )
    poly = _polymarket(
        condition_id="0xBTC95000",
        slug="will-bitcoin-reach-95000-by-june-24",
        title="Will Bitcoin reach $95,000 by June 24?",
        expiry=expiry,
    )

    mappings = build_cross_venue_mapping([kalshi], [poly])

    assert len(mappings) == 1
    row = mappings[0]
    assert row.kalshi_market_ticker == "KXBTC-26JUN24-T95000"
    assert row.kalshi_event_ticker == "KXBTC-26JUN24"
    assert row.polymarket_condition_id == "0xBTC95000"
    assert row.underlying == "BTC"
    assert row.strike == 95000.0
    assert row.expiry_utc == expiry


def test_polymarket_k_suffix_strike_normalises() -> None:
    """``95k`` in a Polymarket slug normalises to 95000 and pairs the Kalshi T95000."""
    expiry = datetime(2026, 6, 24, 21, 0, tzinfo=UTC)
    kalshi = _kalshi(
        market_ticker="KXBTC-26JUN24-T95000",
        event_ticker="KXBTC-26JUN24",
        title="Bitcoin price on Jun 24?",
        expiry=expiry,
    )
    poly = _polymarket(
        condition_id="0xBTC95k",
        slug="will-bitcoin-reach-95k-by-june-24",
        title="Will Bitcoin reach 95k by June 24?",
        expiry=expiry,
    )

    mappings = build_cross_venue_mapping([kalshi], [poly])

    assert len(mappings) == 1
    assert mappings[0].strike == 95000.0


def test_kalshi_bare_numeric_suffix_without_t_or_b() -> None:
    """``KXBTCMAXY-26DEC31-99999.99`` (no T/B prefix) pairs Polymarket 100k market.

    Long-horizon Kalshi series (e.g. yearly max) use bare numeric suffixes without
    a T/B direction letter. The .99-ending is normalised to the next whole number
    so it matches the Polymarket round-number slug target.
    """
    expiry = datetime(2027, 1, 1, 4, 59, tzinfo=UTC)
    kalshi = _kalshi(
        market_ticker="KXBTCMAXY-26DEC31-99999.99",
        event_ticker="KXBTCMAXY-26DEC31",
        expiry=expiry,
    )
    poly = _polymarket(
        condition_id="0xBTC100k2026",
        slug="will-bitcoin-reach-100000-by-december-31-2026",
        expiry=datetime(2027, 1, 1, 0, 0, tzinfo=UTC),
    )

    mappings = build_cross_venue_mapping([kalshi], [poly])

    assert len(mappings) == 1
    row = mappings[0]
    assert row.strike == 100000.0
    assert row.kalshi_market_ticker == "KXBTCMAXY-26DEC31-99999.99"
    assert row.polymarket_condition_id == "0xBTC100k2026"


def test_kalshi_dot99_normalises_to_round_number() -> None:
    """``109999.99`` normalises to ``110000.0`` to match Polymarket 110k target."""
    expiry = datetime(2027, 1, 1, 4, 59, tzinfo=UTC)
    kalshi = _kalshi(
        market_ticker="KXBTCMAXY-26DEC31-109999.99",
        event_ticker="KXBTCMAXY-26DEC31",
        expiry=expiry,
    )
    poly = _polymarket(
        condition_id="0xBTC110k2026",
        slug="will-bitcoin-reach-110000-by-december-31-2026",
        expiry=datetime(2027, 1, 1, 0, 0, tzinfo=UTC),
    )

    mappings = build_cross_venue_mapping([kalshi], [poly])

    assert len(mappings) == 1
    assert mappings[0].strike == 110000.0


# ---------------------------------------------------------------------------
# NON-pair — same underlying (BTC), DIFFERENT strike → NO row (honest absence).
# ---------------------------------------------------------------------------


def test_same_underlying_different_strike_is_no_pair() -> None:
    expiry = datetime(2026, 6, 24, 21, 0, tzinfo=UTC)
    kalshi = _kalshi(
        market_ticker="KXBTC-26JUN24-T95000",
        event_ticker="KXBTC-26JUN24",
        title="Bitcoin price on Jun 24?",
        expiry=expiry,
    )
    poly = _polymarket(
        condition_id="0xBTC100000",
        slug="will-bitcoin-reach-100000-by-june-24",
        title="Will Bitcoin reach $100,000 by June 24?",
        expiry=expiry,
    )

    mappings = build_cross_venue_mapping([kalshi], [poly])

    assert mappings == []


# ---------------------------------------------------------------------------
# Same-settlement guard — same strike, DIFFERENT settlement date → NO row.
# ---------------------------------------------------------------------------


def test_same_strike_different_settlement_date_is_no_pair() -> None:
    kalshi = _kalshi(
        market_ticker="KXBTC-26JUN24-T95000",
        event_ticker="KXBTC-26JUN24",
        title="Bitcoin price on Jun 24?",
        expiry=datetime(2026, 6, 24, 21, 0, tzinfo=UTC),
    )
    poly = _polymarket(
        condition_id="0xBTC95000-25",
        slug="will-bitcoin-reach-95000-by-june-25",
        title="Will Bitcoin reach $95,000 by June 25?",
        expiry=datetime(2026, 6, 25, 21, 0, tzinfo=UTC),
    )

    mappings = build_cross_venue_mapping([kalshi], [poly])

    assert mappings == []


# ---------------------------------------------------------------------------
# Macro pair — CPI per-month + same threshold, same release month → 1 row.
# ---------------------------------------------------------------------------


def test_macro_cpi_pair_same_month_and_threshold() -> None:
    # Kalshi CPI close-time vs Polymarket resolution can differ by day within the
    # same release month → the macro key is YYYY-MM, so they still pair.
    kalshi = _kalshi(
        market_ticker="KXCPIYOY-26APR-T3.2",
        event_ticker="KXCPIYOY-26APR",
        title="CPI year-over-year for April?",
        expiry=datetime(2026, 5, 13, 13, 30, tzinfo=UTC),
    )
    poly = _polymarket(
        condition_id="0xCPI32",
        slug="cpi-above-3.2-april-2026",
        title="Will April CPI be above 3.2%?",
        expiry=datetime(2026, 5, 12, 23, 59, tzinfo=UTC),
    )

    mappings = build_cross_venue_mapping([kalshi], [poly])

    assert len(mappings) == 1
    row = mappings[0]
    assert row.underlying == "CPI"
    assert row.strike == 3.2
    assert row.kalshi_market_ticker == "KXCPIYOY-26APR-T3.2"
    assert row.polymarket_condition_id == "0xCPI32"


# ---------------------------------------------------------------------------
# Sports pair — same fixture (via SportsFixtureKey.pairing_key) + bet-type → 1 row.
# ---------------------------------------------------------------------------


def test_sports_fixture_pair_via_pairing_key() -> None:
    expiry = datetime(2026, 6, 26, 23, 10, tzinfo=UTC)
    kalshi = _kalshi(
        market_ticker="KXMLBGAME-26JUN261910SEACLE-SEA",
        event_ticker="KXMLBGAME-26JUN261910SEACLE",
        title="Seattle vs Cleveland",
        expiry=expiry,
    )
    poly = _polymarket(
        condition_id="0xMLBSEACLE",
        slug="mlb-sea-cle-2026-06-26",
        expiry=expiry,
    )
    titles = {
        "KXMLBGAME-26JUN261910SEACLE-SEA": "Seattle vs Cleveland",
        "0xMLBSEACLE": "Seattle vs. Cleveland",
    }

    mappings = build_cross_venue_mapping([kalshi], [poly], titles=titles)

    assert len(mappings) == 1
    row = mappings[0]
    assert row.kalshi_market_ticker == "KXMLBGAME-26JUN261910SEACLE-SEA"
    assert row.polymarket_condition_id == "0xMLBSEACLE"
    # Sports rows carry no underlying/strike (the fixture is the identity).
    assert row.underlying is None
    assert row.strike is None
    assert "SPORTS" in row.canonical_event_id


def test_sports_team_order_independent_pairing() -> None:
    """A venue listing the pair in the opposite order still pairs (sorted teams)."""
    expiry = datetime(2026, 6, 26, 23, 10, tzinfo=UTC)
    kalshi = _kalshi(
        market_ticker="KXMLBGAME-26JUN261910SEACLE-SEA",
        event_ticker="KXMLBGAME-26JUN261910SEACLE",
        title="Seattle vs Cleveland",
        expiry=expiry,
    )
    poly = _polymarket(
        condition_id="0xMLBCLESEA",
        slug="mlb-cle-sea-2026-06-26",
        expiry=expiry,
    )
    titles = {
        "KXMLBGAME-26JUN261910SEACLE-SEA": "Seattle vs Cleveland",
        "0xMLBCLESEA": "Cleveland vs. Seattle",  # opposite order
    }

    mappings = build_cross_venue_mapping([kalshi], [poly], titles=titles)

    assert len(mappings) == 1


def test_sports_season_future_is_no_pair() -> None:
    """A Kalshi season-future (no GAME token) has no fixture → no false pair."""
    expiry = datetime(2027, 6, 1, 0, 0, tzinfo=UTC)
    kalshi = _kalshi(
        market_ticker="KXNBA-27-LAL",
        event_ticker="KXNBA-27",
        title="2027 Pro Basketball Champion",
        expiry=expiry,
    )
    poly = _polymarket(
        condition_id="0xNBAchamp",
        slug="nba-champion-2027",
        expiry=expiry,
    )
    # Even a 2-team title supplied for both must not pair a season future
    # (the Kalshi side has no GAME/MATCH fixture token → no fixture key).
    titles = {
        "KXNBA-27-LAL": "Los Angeles vs Boston",
        "0xNBAchamp": "Los Angeles vs. Boston",
    }

    mappings = build_cross_venue_mapping([kalshi], [poly], titles=titles)

    assert mappings == []


# ---------------------------------------------------------------------------
# Honest absence — a price market with no parseable strike yields no key.
# ---------------------------------------------------------------------------


def test_price_range_without_strike_is_no_pair() -> None:
    expiry = datetime(2026, 6, 24, 21, 0, tzinfo=UTC)
    # Both classify to BTC PRICE_RANGE, but the Polymarket slug carries NO numeric
    # strike token ("a new all-time high") → no strike → no honest pair (the matcher
    # never collapses a strikeless market onto an arbitrary strike).
    kalshi = _kalshi(
        market_ticker="KXBTC-26JUN24-T95000",
        event_ticker="KXBTC-26JUN24",
        title="Bitcoin price on Jun 24?",
        expiry=expiry,
    )
    poly = _polymarket(
        condition_id="0xBTCath",
        slug="will-bitcoin-reach-a-new-all-time-high",
        title="Will Bitcoin reach a new all-time high?",
        expiry=expiry,
    )

    mappings = build_cross_venue_mapping([kalshi], [poly])

    assert mappings == []


def test_match_key_is_order_independent_for_crypto() -> None:
    """The bare match_key helper returns the SAME key for both venues' sides."""
    from unified_api_contracts.predictions import (
        PredictionBetType,
        PredictionUnderlying,
    )

    expiry = datetime(2026, 6, 24, 21, 0, tzinfo=UTC)
    common = {
        "expiry": expiry,
        "underlying": PredictionUnderlying.BTC,
        "bet_type": PredictionBetType.PRICE_LEVEL,
        "strike": 95000.0,
        "sports_pairing_key": None,
    }
    k = match_key(
        venue="KALSHI", instrument_key="KXBTC-26JUN24-T95000", raw_symbol="KXBTC-26JUN24", symbol="x", **common
    )
    p = match_key(venue="POLYMARKET", instrument_key="0xBTC", raw_symbol="bitcoin-above-95000", symbol="y", **common)
    assert k == p
    assert k is not None


# ---------------------------------------------------------------------------
# af_fixture_id-primary sports key — a resolved API-Football fixture id is a
# strong EXACT key (same fixture + bet-type ⇒ same market), preferred over the
# fuzzy team-name pairing. None (or absent) ⇒ the fuzzy path is used, unchanged.
# ---------------------------------------------------------------------------


def test_match_key_prefers_af_fixture_id_for_sports() -> None:
    """Same af_fixture_id + bet-type ⇒ SAME key across venues; a different fixture ⇒ different key."""
    from unified_api_contracts.predictions import (
        PredictionBetType,
        PredictionUnderlying,
    )

    common = {
        "expiry": datetime(2026, 6, 26, 23, 10, tzinfo=UTC),
        "underlying": PredictionUnderlying.SPORTS_MLB,
        "bet_type": PredictionBetType.MATCH,
        "strike": None,
        # Deliberately None: the af_fixture_id path must NOT depend on the fuzzy
        # pairing key (that is the whole reliability win).
        "sports_pairing_key": None,
    }
    kalshi = match_key(
        venue="KALSHI",
        instrument_key="KXMLBGAME-26JUN261910SEACLE-SEA",
        raw_symbol="KXMLBGAME-26JUN261910SEACLE",
        symbol="Seattle vs Cleveland",
        af_fixture_id=99001,
        **common,
    )
    poly = match_key(
        venue="POLYMARKET",
        instrument_key="0xMLBSEACLE",
        raw_symbol="mlb-sea-cle-2026-06-26",
        symbol="Seattle vs. Cleveland",
        af_fixture_id=99001,
        **common,
    )
    other_fixture = match_key(
        venue="POLYMARKET",
        instrument_key="0xMLBOTHER",
        raw_symbol="mlb-sea-cle-2026-06-26-game2",
        symbol="Seattle vs. Cleveland (game 2)",
        af_fixture_id=99002,
        **common,
    )
    assert kalshi == poly == "SPORTS_FIX::99001::MATCH"
    assert kalshi != other_fixture


def test_match_key_falls_back_to_fuzzy_pairing_when_af_fixture_id_none() -> None:
    """af_fixture_id=None (or omitted) ⇒ the fuzzy sports_pairing_key path is used, unchanged."""
    from unified_api_contracts.predictions import (
        PredictionBetType,
        PredictionUnderlying,
    )

    common = {
        "venue": "KALSHI",
        "instrument_key": "KXMLBGAME-26JUN261910SEACLE-SEA",
        "raw_symbol": "KXMLBGAME-26JUN261910SEACLE",
        "symbol": "Seattle vs Cleveland",
        "expiry": datetime(2026, 6, 26, 23, 10, tzinfo=UTC),
        "underlying": PredictionUnderlying.SPORTS_MLB,
        "bet_type": PredictionBetType.MATCH,
        "strike": None,
        "sports_pairing_key": ("MLB", "CLE", "SEA", "2026-06-26"),
    }
    explicit_none = match_key(af_fixture_id=None, **common)
    default_omitted = match_key(**common)  # param defaults to None
    assert explicit_none == default_omitted == "SPORTS::MLB::MATCH::CLE::SEA::2026-06-26"


def test_build_cross_venue_mapping_pairs_on_shared_af_fixture_id() -> None:
    """End-to-end: both venues threading the SAME af_fixture_id pair EXACTLY on it."""
    expiry = datetime(2026, 6, 26, 23, 10, tzinfo=UTC)
    kalshi = _kalshi(
        market_ticker="KXMLBGAME-26JUN261910SEACLE-SEA",
        event_ticker="KXMLBGAME-26JUN261910SEACLE",
        title="Seattle vs Cleveland",
        expiry=expiry,
        af_fixture_id=99001,
    )
    poly = _polymarket(
        condition_id="0xMLBSEACLE",
        slug="mlb-sea-cle-2026-06-26",
        expiry=expiry,
        af_fixture_id=99001,
    )
    # Titles make the fuzzy pairing FULLY available on both sides; the shared
    # af_fixture_id is still PREFERRED (SPORTS_FIX:: key, not SPORTS::) — the win.
    titles = {
        "KXMLBGAME-26JUN261910SEACLE-SEA": "Seattle vs Cleveland",
        "0xMLBSEACLE": "Seattle vs. Cleveland",
    }
    mappings = build_cross_venue_mapping([kalshi], [poly], titles=titles)

    assert len(mappings) == 1
    row = mappings[0]
    assert row.kalshi_market_ticker == "KXMLBGAME-26JUN261910SEACLE-SEA"
    assert row.polymarket_condition_id == "0xMLBSEACLE"
    assert row.canonical_event_id == "SPORTS_FIX::99001::MATCH"
    assert row.underlying is None
    assert row.strike is None


def test_build_cross_venue_mapping_different_af_fixture_id_is_no_pair() -> None:
    """Distinct af_fixture_ids ⇒ genuinely different fixtures ⇒ NO pair (no false merge)."""
    expiry = datetime(2026, 6, 26, 23, 10, tzinfo=UTC)
    kalshi = _kalshi(
        market_ticker="KXMLBGAME-26JUN261910SEACLE-SEA",
        event_ticker="KXMLBGAME-26JUN261910SEACLE",
        title="Seattle vs Cleveland",
        expiry=expiry,
        af_fixture_id=99001,
    )
    poly = _polymarket(
        condition_id="0xMLBSEACLE2",
        slug="mlb-sea-cle-2026-06-26-game2",
        expiry=expiry,
        af_fixture_id=99002,  # second leg of a double-header — a different fixture
    )
    # Same teams/date on both titles ⇒ the FUZZY pairing WOULD match; the distinct
    # af_fixture_ids correctly keep the two legs apart (no false merge).
    titles = {
        "KXMLBGAME-26JUN261910SEACLE-SEA": "Seattle vs Cleveland",
        "0xMLBSEACLE2": "Seattle vs. Cleveland",
    }
    mappings = build_cross_venue_mapping([kalshi], [poly], titles=titles)

    assert mappings == []


# ---------------------------------------------------------------------------
# category_for_group — public facade composition of underlying_for_group +
# the internal underlying→category classifier, one representative cqg per
# PredictionMarketCategory bucket (P3 data-status prediction catalogue browser).
# ---------------------------------------------------------------------------


def test_category_for_group_composes_across_all_categories() -> None:
    """One representative cqg per category resolves to the expected coarse bucket."""
    from unified_api_contracts.predictions import (
        CanonicalQuestionGroup,
        PredictionMarketCategory,
        category_for_group,
    )

    cases = {
        CanonicalQuestionGroup.BTC_UP_DOWN_DAILY: PredictionMarketCategory.CRYPTO,
        CanonicalQuestionGroup.SPX_UP_DOWN_DAILY: PredictionMarketCategory.FINANCIAL,
        CanonicalQuestionGroup.SPORTS_MLB_MATCH: PredictionMarketCategory.SPORTS,
        CanonicalQuestionGroup.WEATHER_TEMP_DAILY: PredictionMarketCategory.WEATHER,
        CanonicalQuestionGroup.OSCARS_BEST_PICTURE: PredictionMarketCategory.ENTERTAINMENT,
        CanonicalQuestionGroup.ELECTION_PRESIDENT_2028: PredictionMarketCategory.POLITICS,
        CanonicalQuestionGroup.OTHER: PredictionMarketCategory.OTHER,
    }
    for cqg, expected in cases.items():
        assert category_for_group(cqg) is expected, f"{cqg} expected {expected}, got {category_for_group(cqg)}"
