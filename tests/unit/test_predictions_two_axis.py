"""Unit tests for the two-axis canonical decomposition of cqg.

Plan ``prediction_venue_perps_and_live_clob_depth_2026_06_20.md`` items
#559 / #684 / #692. Completeness is the point: every CanonicalQuestionGroup —
current AND future — must categorise to an Axis-1 underlying and an Axis-2
bet-type (no silent gaps).
"""

from __future__ import annotations

from unified_api_contracts.predictions import (
    CANONICAL_GROUP_TO_BET_TYPE,
    CANONICAL_GROUP_TO_UNDERLYING,
    CanonicalQuestionGroup,
    PredictionBetType,
    PredictionUnderlying,
    bet_type_for_group,
    cross_venue_underlying_overlap,
    underlying_for_group,
)


def test_underlying_map_covers_every_cqg() -> None:
    """EVERY cqg must have an Axis-1 underlying — no silent gap."""
    assert set(CANONICAL_GROUP_TO_UNDERLYING) == set(CanonicalQuestionGroup)


def test_bet_type_map_covers_every_cqg() -> None:
    """EVERY cqg must have an Axis-2 bet-type — no silent gap."""
    assert set(CANONICAL_GROUP_TO_BET_TYPE) == set(CanonicalQuestionGroup)


def test_top_level_facade_exports_symbols() -> None:
    """The two-axis symbols reach the top-level UAC facade."""
    import unified_api_contracts as uac

    assert uac.PredictionUnderlying is PredictionUnderlying
    assert uac.PredictionBetType is PredictionBetType
    assert uac.underlying_for_group is underlying_for_group
    assert uac.bet_type_for_group is bet_type_for_group
    assert uac.cross_venue_underlying_overlap is cross_venue_underlying_overlap
    assert uac.CANONICAL_GROUP_TO_UNDERLYING is CANONICAL_GROUP_TO_UNDERLYING
    assert uac.CANONICAL_GROUP_TO_BET_TYPE is CANONICAL_GROUP_TO_BET_TYPE


def test_crude_oil_up_down_and_price_level_share_underlying() -> None:
    """CRUDE_OIL up/down and price-level both map to CRUDE_OIL (overlap is at
    the underlying level, stripping bet-type)."""
    up_down = CanonicalQuestionGroup.CRUDE_OIL_UP_DOWN_DAILY
    price_level = CanonicalQuestionGroup.CRUDE_OIL_PRICE_LEVEL
    assert underlying_for_group(up_down) is PredictionUnderlying.CRUDE_OIL
    assert underlying_for_group(price_level) is PredictionUnderlying.CRUDE_OIL
    # …but they are DIFFERENT bet-types (the downstream arb layer cares).
    assert bet_type_for_group(up_down) is PredictionBetType.UP_DOWN
    assert bet_type_for_group(price_level) is PredictionBetType.PRICE_LEVEL


def test_btc_up_down_daily_decomposition() -> None:
    cqg = CanonicalQuestionGroup.BTC_UP_DOWN_DAILY
    assert underlying_for_group(cqg) is PredictionUnderlying.BTC
    assert bet_type_for_group(cqg) is PredictionBetType.UP_DOWN


def test_gold_up_down_and_price_level_share_underlying() -> None:
    assert underlying_for_group(CanonicalQuestionGroup.GOLD_UP_DOWN_DAILY) is PredictionUnderlying.GOLD
    assert underlying_for_group(CanonicalQuestionGroup.GOLD_PRICE_LEVEL) is PredictionUnderlying.GOLD


def test_mlb_match_spread_total_share_underlying() -> None:
    """SPORTS_MLB_MATCH / SPREAD / TOTAL all collapse to SPORTS_MLB on Axis-1."""
    for cqg in (
        CanonicalQuestionGroup.SPORTS_MLB_MATCH,
        CanonicalQuestionGroup.SPORTS_MLB_SPREAD,
        CanonicalQuestionGroup.SPORTS_MLB_TOTAL,
        CanonicalQuestionGroup.SPORTS_MLB_NRFI,
    ):
        assert underlying_for_group(cqg) is PredictionUnderlying.SPORTS_MLB
    # …with distinct bet-types.
    assert bet_type_for_group(CanonicalQuestionGroup.SPORTS_MLB_MATCH) is PredictionBetType.MATCH
    assert bet_type_for_group(CanonicalQuestionGroup.SPORTS_MLB_SPREAD) is PredictionBetType.SPREAD
    assert bet_type_for_group(CanonicalQuestionGroup.SPORTS_MLB_TOTAL) is PredictionBetType.TOTAL
    assert bet_type_for_group(CanonicalQuestionGroup.SPORTS_MLB_NRFI) is PredictionBetType.NRFI


def test_other_and_misc_route_to_other_underlying() -> None:
    assert underlying_for_group(CanonicalQuestionGroup.OTHER) is PredictionUnderlying.OTHER
    assert underlying_for_group(CanonicalQuestionGroup.MISC_NOVELTY) is PredictionUnderlying.OTHER
    assert bet_type_for_group(CanonicalQuestionGroup.OTHER) is PredictionBetType.OTHER


def test_cross_venue_underlying_overlap_smoke() -> None:
    """Overlap helper returns shared / venue-only underlyings at Axis-1."""
    kalshi = [
        CanonicalQuestionGroup.CRUDE_OIL_PRICE_LEVEL,  # CRUDE_OIL
        CanonicalQuestionGroup.BTC_UP_DOWN_DAILY,  # BTC
        CanonicalQuestionGroup.SPORTS_NFL_MATCH,  # SPORTS_NFL
    ]
    polymarket = [
        CanonicalQuestionGroup.CRUDE_OIL_UP_DOWN_DAILY,  # CRUDE_OIL (shared via underlying)
        CanonicalQuestionGroup.BTC_PRICE_RANGE_DAILY,  # BTC (shared)
        CanonicalQuestionGroup.GEO_ISRAEL_IRAN,  # GEO_ISRAEL_IRAN (poly-only)
    ]
    result = cross_venue_underlying_overlap(kalshi, polymarket)
    assert result["shared_underlyings"] == {PredictionUnderlying.BTC, PredictionUnderlying.CRUDE_OIL}
    assert result["kalshi_only"] == {PredictionUnderlying.SPORTS_NFL}
    assert result["polymarket_only"] == {PredictionUnderlying.GEO_ISRAEL_IRAN}


def test_cross_venue_overlap_handles_empty() -> None:
    result = cross_venue_underlying_overlap([], [])
    assert result == {
        "shared_underlyings": set(),
        "kalshi_only": set(),
        "polymarket_only": set(),
    }
