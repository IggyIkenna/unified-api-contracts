"""Unit tests for YAHOO_INDICES registry and DXY source resolver.

Tests:
- YAHOO_INDICES EXCLUDES the retired VIX cash-index (removed 2026-06-25) but keeps DXY (ICE)
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
    US_TREASURY_YIELD_DAILY_FIRST_DATE,
    get_dxy_daily_source,
    get_source_for_instrument,
    get_us_treasury_yield_daily_source,
)
from unified_api_contracts.registry.tradfi_instrument_universe import YAHOO_INDICES

_TREASURY_TENORS = {"US3M": "^IRX", "US2Y": "2YY=F", "US5Y": "^FVX", "US10Y": "^TNX", "US30Y": "^TYX"}


@pytest.mark.unit
def test_yahoo_indices_excludes_retired_vix_cash() -> None:
    """YAHOO_INDICES must NOT include the retired VIX cash-index (removed 2026-06-25).

    The CBOE cash-index is retired (operator 2026-06-23); VIX-15m is aggregated from the
    VX FUTURES front contract (XCBF.PITCH), and CBOE:INDEX:VIX-USD survives only as the
    ohlcv_15m source-resolver key in data_source_continuity — never as a Yahoo daily index.
    """
    symbols = {idx.symbol for idx in YAHOO_INDICES}
    assert "VIX" not in symbols


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


@pytest.mark.unit
def test_yahoo_indices_contains_all_treasury_tenors() -> None:
    """YAHOO_INDICES must include the four CBOE treasury-yield tenors."""
    by_symbol = {idx.symbol: idx for idx in YAHOO_INDICES}
    for symbol, ticker in _TREASURY_TENORS.items():
        assert symbol in by_symbol, f"{symbol} missing from YAHOO_INDICES"
        entry = by_symbol[symbol]
        assert entry.venue == "CBOE"
        assert entry.yahoo_ticker == ticker
        assert entry.asset_group == "fixed_income"


@pytest.mark.unit
def test_get_us_treasury_yield_daily_source_returns_yahoo_on_covered_date() -> None:
    """Dates on or after the first treasury date return YAHOO_FINANCE."""
    assert get_us_treasury_yield_daily_source(US_TREASURY_YIELD_DAILY_FIRST_DATE) == "YAHOO_FINANCE"
    assert get_us_treasury_yield_daily_source(date(2024, 6, 1)) == "YAHOO_FINANCE"


@pytest.mark.unit
def test_get_us_treasury_yield_daily_source_returns_gap_before_coverage() -> None:
    """Dates before the first treasury date return GAP_NO_SOURCE."""
    assert get_us_treasury_yield_daily_source(date(2000, 1, 2)) == "GAP_NO_SOURCE"
    assert get_us_treasury_yield_daily_source(date(1990, 1, 1)) == "GAP_NO_SOURCE"


@pytest.mark.unit
def test_get_source_for_instrument_resolves_all_treasury_tenors() -> None:
    """Every CBOE treasury canonical instrument_key dispatches to the treasury resolver."""
    for symbol in _TREASURY_TENORS:
        result = get_source_for_instrument(f"CBOE:INDEX:{symbol}-USD", "ohlcv_24h", date(2023, 3, 15))
        assert result == "YAHOO_FINANCE", f"{symbol} did not resolve"


# ---------------------------------------------------------------------------
# QG-hardening gate: adding a Yahoo index must be safe-by-construction.
# Every YAHOO_INDICES entry MUST carry a real genesis date AND have a source
# resolver registered under its CANONICAL key ({venue}:INDEX:{base}-USD) — so
# a newly-listed index cannot silently ship without a genesis or a source.
# ---------------------------------------------------------------------------

_CANONICAL_QUOTE = "USD"


@pytest.mark.unit
def test_every_yahoo_index_has_a_plausible_genesis_date() -> None:
    """Each entry declares a real first_available_date (1980 < genesis <= today)."""
    from datetime import date as _date

    floor = _date(1980, 1, 1)
    today = _date.today()
    for idx in YAHOO_INDICES:
        genesis = idx.first_available_date
        assert isinstance(genesis, _date), f"{idx.symbol} genesis must be a date"
        assert floor < genesis <= today, f"{idx.symbol} genesis {genesis} implausible"


@pytest.mark.unit
def test_every_yahoo_index_has_a_source_resolver_under_canonical_key() -> None:
    """Each entry has a _SOURCE_RESOLVERS entry under its canonical -USD key.

    This is the gate that makes adding data safe: list a new index without
    wiring its data-source-continuity resolver and this test fails.
    """
    from unified_api_contracts.registry.data_source_continuity import _SOURCE_RESOLVERS

    resolved_keys = {key for key, _data_type in _SOURCE_RESOLVERS}
    for idx in YAHOO_INDICES:
        canonical = f"{idx.venue}:INDEX:{idx.base_asset}-{_CANONICAL_QUOTE}"
        assert canonical in resolved_keys, (
            f"{idx.symbol}: no source resolver under canonical key {canonical!r} "
            f"— add a ({canonical!r}, <data_type>) entry to _SOURCE_RESOLVERS"
        )
