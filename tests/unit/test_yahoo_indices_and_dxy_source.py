"""Unit tests for YAHOO_INDICES registry and DXY source resolver.

Tests:
- YAHOO_INDICES contains both VIX (CBOE) and DXY (ICE)
- VIX entry fields are correct
- DXY entry fields are correct
- get_dxy_daily_source: returns YAHOO_FINANCE for a date >= DXY_DAILY_FIRST_DATE
- get_dxy_daily_source: returns GAP_NO_SOURCE for a date before DXY_DAILY_FIRST_DATE
- get_source_for_instrument resolves DXY via the central registry
"""

from __future__ import annotations

from datetime import date

import pytest

from unified_api_contracts.registry.data_source_continuity import (
    DXY_DAILY_FIRST_DATE,
    get_dxy_daily_source,
    get_source_for_instrument,
)
from unified_api_contracts.registry.tradfi_instrument_universe import YAHOO_INDICES


@pytest.mark.unit
def test_yahoo_indices_contains_vix() -> None:
    """YAHOO_INDICES must include the CBOE VIX entry."""
    symbols = {idx.symbol for idx in YAHOO_INDICES}
    assert "VIX" in symbols


@pytest.mark.unit
def test_yahoo_indices_contains_dxy() -> None:
    """YAHOO_INDICES must include the ICE DXY entry."""
    symbols = {idx.symbol for idx in YAHOO_INDICES}
    assert "DXY" in symbols


@pytest.mark.unit
def test_dxy_entry_fields() -> None:
    """DXY entry must have the correct venue, ticker, and asset_group."""
    (dxy,) = [idx for idx in YAHOO_INDICES if idx.symbol == "DXY"]
    assert dxy.venue == "ICE"
    assert dxy.yahoo_ticker == "DX-Y.NYB"
    assert dxy.base_asset == "DXY"
    assert dxy.asset_group == "fx"


@pytest.mark.unit
def test_vix_entry_fields() -> None:
    """VIX entry must retain its correct venue and ticker."""
    (vix,) = [idx for idx in YAHOO_INDICES if idx.symbol == "VIX"]
    assert vix.venue == "CBOE"
    assert vix.yahoo_ticker == "^VIX"


@pytest.mark.unit
def test_get_dxy_daily_source_returns_yahoo_on_covered_date() -> None:
    """Dates on or after DXY_DAILY_FIRST_DATE return YAHOO_FINANCE."""
    assert get_dxy_daily_source(DXY_DAILY_FIRST_DATE) == "YAHOO_FINANCE"
    assert get_dxy_daily_source(date(2024, 6, 1)) == "YAHOO_FINANCE"


@pytest.mark.unit
def test_get_dxy_daily_source_returns_gap_before_coverage() -> None:
    """Dates before DXY_DAILY_FIRST_DATE return GAP_NO_SOURCE."""
    assert get_dxy_daily_source(date(2018, 12, 31)) == "GAP_NO_SOURCE"
    assert get_dxy_daily_source(date(2000, 1, 1)) == "GAP_NO_SOURCE"


@pytest.mark.unit
def test_get_source_for_instrument_resolves_dxy() -> None:
    """get_source_for_instrument dispatches to get_dxy_daily_source via the registry."""
    result = get_source_for_instrument("ICE:INDEX:DXY-USD", "ohlcv_24h", date(2023, 3, 15))
    assert result == "YAHOO_FINANCE"


@pytest.mark.unit
def test_get_source_for_instrument_returns_none_for_unknown() -> None:
    """Unregistered instrument+data_type pairs return None (no resolver)."""
    result = get_source_for_instrument("ICE:INDEX:DXY-USD", "ohlcv_1h", date(2023, 3, 15))
    assert result is None
