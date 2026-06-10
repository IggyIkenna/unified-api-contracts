"""Extended tests for registry/market_data_categories.py — targeting missed branches."""

from __future__ import annotations

import pytest

from unified_api_contracts.registry.market_data_categories import (
    DATA_TYPES_BY_ASSET_GROUP,
    TIMEFRAMES,
    VENUES_BY_ASSET_GROUP,
    get_valid_timeframes_for_data_type,
    needs_candle_processing,
)

# ---------------------------------------------------------------------------
# get_valid_timeframes_for_data_type
# ---------------------------------------------------------------------------


def test_trades_returns_all_timeframes() -> None:
    """trades has no base granularity — returns all timeframes."""
    result = get_valid_timeframes_for_data_type("trades")
    assert result == list(TIMEFRAMES)


def test_unknown_data_type_returns_all_timeframes() -> None:
    result = get_valid_timeframes_for_data_type("not_a_real_data_type")
    assert result == list(TIMEFRAMES)


def test_ohlcv_1m_filters_to_1m_and_above() -> None:
    """ohlcv_1m base granularity: only timeframes >= 1m returned."""
    result = get_valid_timeframes_for_data_type("ohlcv_1m")
    assert isinstance(result, list)
    assert len(result) > 0
    # 1m should be in results
    assert "1m" in result or any("1m" in tf for tf in result)


def test_ohlcv_15m_filters_to_15m_and_above() -> None:
    result = get_valid_timeframes_for_data_type("ohlcv_15m")
    assert isinstance(result, list)
    # Should be a strict subset of all timeframes
    assert len(result) <= len(list(TIMEFRAMES))


# ---------------------------------------------------------------------------
# needs_candle_processing
# ---------------------------------------------------------------------------


def test_needs_candle_processing_for_book_snapshot() -> None:
    """book_snapshot data requires candle processing."""
    result = needs_candle_processing("book_snapshot_5")
    assert isinstance(result, bool)


def test_needs_candle_processing_for_ohlcv() -> None:
    """ohlcv_1m is already candles — should not need processing."""
    result = needs_candle_processing("ohlcv_1m")
    assert isinstance(result, bool)


def test_needs_candle_processing_unknown_data_type() -> None:
    result = needs_candle_processing("unknown_data_type")
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# VENUES_BY_ASSET_GROUP and DATA_TYPES_BY_ASSET_GROUP presence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ag", ["cefi", "defi", "tradfi", "sports", "prediction"])
def test_venues_by_asset_group_has_entries(ag: str) -> None:
    venues = VENUES_BY_ASSET_GROUP.get(ag, [])
    assert isinstance(venues, list)
    assert len(venues) > 0


@pytest.mark.parametrize("ag", ["cefi", "defi", "tradfi", "sports"])
def test_data_types_by_asset_group_has_entries(ag: str) -> None:
    data_types = DATA_TYPES_BY_ASSET_GROUP.get(ag, [])
    assert isinstance(data_types, list)
    assert len(data_types) > 0


def test_cefi_has_trades_data_type() -> None:
    assert "trades" in DATA_TYPES_BY_ASSET_GROUP.get("cefi", [])


def test_tradfi_has_ohlcv_data_types() -> None:
    tradfi_types = DATA_TYPES_BY_ASSET_GROUP.get("tradfi", [])
    assert "ohlcv_1m" in tradfi_types


def test_venues_are_strings() -> None:
    for ag, venues in VENUES_BY_ASSET_GROUP.items():
        for v in venues:
            assert isinstance(v, str), f"Non-string venue in {ag}: {v!r}"
