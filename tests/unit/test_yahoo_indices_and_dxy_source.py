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

    The CBOE cash-index is retired (operator 2026-06-23); VIX-15m is now solely the
    VX FUTURES front contract (XCBF.PITCH / CBOE:FUTURE:VX) aggregated downstream.
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

# ---------------------------------------------------------------------------
# FX spot pair enumeration tests (added 2026-06-26)
# ---------------------------------------------------------------------------

_FX_G10_MAJORS = {
    "EURUSD=X": ("EUR", "USD"),
    "GBPUSD=X": ("GBP", "USD"),
    "USDJPY=X": ("USD", "JPY"),
    "AUDUSD=X": ("AUD", "USD"),
    "USDCAD=X": ("USD", "CAD"),
    "USDCHF=X": ("USD", "CHF"),
    "NZDUSD=X": ("NZD", "USD"),
    "EURGBP=X": ("EUR", "GBP"),
    "EURJPY=X": ("EUR", "JPY"),
    "USDMXN=X": ("USD", "MXN"),
    "KRWUSD=X": ("KRW", "USD"),
}


@pytest.mark.unit
def test_fx_spot_pairs_contains_g10_majors() -> None:
    """FX_SPOT_PAIRS must enumerate all G10 FX majors + KRW/USD.

    Added 2026-06-26: G10 crosses are cefi features (DXY context, polymarket
    EUR/USD arb, macro signals). They were missing; only KRW/USD was listed.
    Codex SSOT: codex/02-data/tradfi-data-types-catalog.md (FX G10 crosses).
    """
    from unified_api_contracts.registry.tradfi_instrument_universe import FX_SPOT_PAIRS

    tickers_by_yahoo = {fx.yahoo_ticker: (fx.base, fx.quote) for fx in FX_SPOT_PAIRS}
    for yahoo_ticker, (expected_base, expected_quote) in _FX_G10_MAJORS.items():
        assert yahoo_ticker in tickers_by_yahoo, (
            f"Yahoo ticker {yahoo_ticker!r} missing from FX_SPOT_PAIRS — "
            f"add FxSpotPairDef({expected_base!r}, {expected_quote!r}, {yahoo_ticker!r})"
        )
        actual_base, actual_quote = tickers_by_yahoo[yahoo_ticker]
        assert actual_base == expected_base, f"{yahoo_ticker}: base mismatch ({actual_base!r} != {expected_base!r})"
        assert actual_quote == expected_quote, (
            f"{yahoo_ticker}: quote mismatch ({actual_quote!r} != {expected_quote!r})"
        )


@pytest.mark.unit
def test_fx_spot_pairs_no_duplicates() -> None:
    """FX_SPOT_PAIRS must not have duplicate Yahoo tickers."""
    from unified_api_contracts.registry.tradfi_instrument_universe import FX_SPOT_PAIRS

    tickers = [fx.yahoo_ticker for fx in FX_SPOT_PAIRS]
    assert len(tickers) == len(set(tickers)), f"Duplicate tickers: {[t for t in tickers if tickers.count(t) > 1]}"


@pytest.mark.unit
def test_fx_spot_pairs_tickers_end_with_equals_x() -> None:
    """All FX_SPOT_PAIRS tickers must end with '=X' (Yahoo FX pair convention)."""
    from unified_api_contracts.registry.tradfi_instrument_universe import FX_SPOT_PAIRS

    for fx in FX_SPOT_PAIRS:
        assert fx.yahoo_ticker.endswith("=X"), (
            f"FX pair {fx.base}/{fx.quote} ticker {fx.yahoo_ticker!r} must end with '=X'"
        )


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


# ---------------------------------------------------------------------------
# KRX KOSPI / KOSPI 200 index enumeration (added 2026-06-27)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_yahoo_indices_contains_kospi_and_kospi200() -> None:
    """YAHOO_INDICES must include the KRX KOSPI and KOSPI200 index entries.

    Added 2026-06-27: operator directed 'daily KOSPI prices from Yahoo Finance'.
    The KOSPI composite (^KS11) and KOSPI 200 (^KS200) are the KRX benchmark
    indices; they are INDEX instruments (non-tradeable), distinct from the 3
    KRX single-stock EQUITYs in KRX_EQUITIES.
    """
    by_symbol = {idx.symbol: idx for idx in YAHOO_INDICES}
    assert "KOSPI" in by_symbol, "KOSPI (^KS11) missing from YAHOO_INDICES"
    assert "KOSPI200" in by_symbol, "KOSPI200 (^KS200) missing from YAHOO_INDICES"


@pytest.mark.unit
def test_kospi_entry_fields() -> None:
    """KOSPI entry must have the correct venue, ticker, and asset_group."""
    (kospi,) = [idx for idx in YAHOO_INDICES if idx.symbol == "KOSPI"]
    assert kospi.venue == "KRX"
    assert kospi.yahoo_ticker == "^KS11"
    assert kospi.base_asset == "KOSPI"
    assert kospi.asset_group == "equity"
    assert kospi.first_available_date.year == 2019


@pytest.mark.unit
def test_kospi200_entry_fields() -> None:
    """KOSPI200 entry must have the correct venue, ticker, and asset_group."""
    (k200,) = [idx for idx in YAHOO_INDICES if idx.symbol == "KOSPI200"]
    assert k200.venue == "KRX"
    assert k200.yahoo_ticker == "^KS200"
    assert k200.base_asset == "KOSPI200"
    assert k200.asset_group == "equity"
    assert k200.first_available_date.year == 2019


@pytest.mark.unit
def test_get_krx_index_daily_source_returns_yahoo_on_covered_date() -> None:
    """Dates on or after KRX_INDEX_DAILY_FIRST_DATE return YAHOO_FINANCE."""
    from unified_api_contracts.registry.data_source_continuity import (
        KRX_INDEX_DAILY_FIRST_DATE,
        get_krx_index_daily_source,
    )

    assert get_krx_index_daily_source(KRX_INDEX_DAILY_FIRST_DATE) == "YAHOO_FINANCE"
    assert get_krx_index_daily_source(date(2024, 6, 1)) == "YAHOO_FINANCE"


@pytest.mark.unit
def test_get_krx_index_daily_source_returns_gap_before_coverage() -> None:
    """Dates before KRX_INDEX_DAILY_FIRST_DATE return GAP_NO_SOURCE."""
    from unified_api_contracts.registry.data_source_continuity import get_krx_index_daily_source

    assert get_krx_index_daily_source(date(2018, 12, 31)) == "GAP_NO_SOURCE"
    assert get_krx_index_daily_source(date(2000, 1, 1)) == "GAP_NO_SOURCE"


@pytest.mark.unit
def test_get_source_for_instrument_resolves_kospi() -> None:
    """get_source_for_instrument dispatches to get_krx_index_daily_source for KOSPI."""
    from unified_api_contracts.registry.data_source_continuity import get_source_for_instrument

    result = get_source_for_instrument("KRX:INDEX:KOSPI-USD", "ohlcv_24h", date(2023, 3, 15))
    assert result == "YAHOO_FINANCE"


@pytest.mark.unit
def test_get_source_for_instrument_resolves_kospi200() -> None:
    """get_source_for_instrument dispatches to get_krx_index_daily_source for KOSPI200."""
    from unified_api_contracts.registry.data_source_continuity import get_source_for_instrument

    result = get_source_for_instrument("KRX:INDEX:KOSPI200-USD", "ohlcv_24h", date(2023, 3, 15))
    assert result == "YAHOO_FINANCE"


# ---------------------------------------------------------------------------
# ICE routing — no Databento dataset (regression guard, 2026-06-27)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ice_not_in_venue_to_databento() -> None:
    """ICE must NOT appear in VenueMapping.venue_to_databento.

    ICE Databento datasets (IFUS.IMPACT / IFEU.IMPACT) are outside the 3-dataset
    paid subscription. Previously venue_to_databento['ICE'] = 'IFUS.IMPACT' caused
    DatabentoDatasetNotAllowedError on enumeration → 32 absent ICE days. The fix
    routes ICE exclusively via Yahoo Finance (DXY index only). Re-adding any ICE
    Databento dataset without an explicit ICE subscription MUST be review-blocking.
    """
    from unified_api_contracts.registry.venue_mapping import VenueMapping

    vm = VenueMapping()
    assert "ICE" not in vm.venue_to_databento, (
        "ICE must NOT be in venue_to_databento — IFUS/IFEU datasets are outside the "
        "paid subscription (would raise DatabentoDatasetNotAllowedError). "
        "Remove it (done 2026-06-27). Re-adding requires an explicit ICE subscription."
    )


@pytest.mark.unit
def test_ice_routes_to_yahoo_finance_in_venue_to_data_provider() -> None:
    """ICE must route to yahoo_finance via venue_to_data_provider (for DXY).

    After removing ICE from venue_to_databento, the parity gate
    (test_tradfi_venue_resolves_to_a_data_source) must still see ICE as a
    valid-sourced venue — ensured by venue_to_data_provider['ICE'] = 'yahoo_finance'.
    """
    from unified_api_contracts.registry.venue_mapping import VenueMapping

    vm = VenueMapping()
    assert vm.venue_to_data_provider.get("ICE") == "yahoo_finance", (
        "ICE must have venue_to_data_provider['ICE'] = 'yahoo_finance' so the DXY "
        "Yahoo-sourced index is correctly attributed and the parity gate passes."
    )
