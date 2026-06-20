"""Unit tests for the net-profitable equity-perp single-stock hedge legs.

Added 2026-06-20: Phase 1d of
``cryptovenue_equity_perps_and_tokenized_stocks_2026_06_20.md``.

Verifies that the 12 net-profitable single-stock crypto-venue perps (NET > 5%
annualized after subtracting IBKR stock-borrow costs) are correctly wired in
``tradfi_instrument_universe.py`` with the right Databento DBEQ.BASIC entries,
and that the rejected/SLIM symbols are absent.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.registry.tradfi_instrument_universe import (
    _NET_PROFITABLE_EQUITY_PERP_SINGLES,
    TRADFI_DATABENTO_INSTRUMENTS,
    DatabentoInstrumentDef,
    get_databento_symbols_for_dataset,
)

# ---------------------------------------------------------------------------
# Expected set — 12 TRADEABLE symbols from the NET-basis backtest
# ---------------------------------------------------------------------------

# Mean NET (gross perp funding - IBKR borrow est.) from the 2026-06-20 backtest.
# All > 5% annualized.  MSTR (+4.1%), COIN (+4.2%), PLTR (+1.7%) were BELOW 5%.
_EXPECTED_SINGLES: frozenset[str] = frozenset(
    {
        "NVDA",  # NET +21.6%
        "MSFT",  # NET +15.4%
        "CRCL",  # NET +21.3%
        "INTC",  # NET +17.7%
        "GOOGL",  # NET +17.6%
        "AMD",  # NET +23.9%
        "TSLA",  # NET  +8.9%
        "AMZN",  # NET  +5.4%
        "META",  # NET +11.4%
        "HOOD",  # NET  +7.1%
        "AAPL",  # NET  +6.5%
        "BABA",  # NET  +5.2% (mean; 1-mo -8.3% — monitor)
    }
)

# Symbols that were MARGINAL/SLIM/NEGATIVE — must NOT be in the singles list
_EXCLUDED_SINGLES: frozenset[str] = frozenset({"MSTR", "COIN", "PLTR"})

# Commodity perp hedge symbols that were SLIM/NEGATIVE — NOT added
_EXCLUDED_COMMODITIES: frozenset[str] = frozenset({"XAU", "XAG", "COPPER"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _singles_by_symbol() -> dict[str, DatabentoInstrumentDef]:
    return {d.symbol: d for d in _NET_PROFITABLE_EQUITY_PERP_SINGLES}


# ---------------------------------------------------------------------------
# Presence tests
# ---------------------------------------------------------------------------


def test_all_expected_singles_present() -> None:
    """All 12 net-profitable tickers must appear in the private list."""
    symbols_in_list = frozenset(d.symbol for d in _NET_PROFITABLE_EQUITY_PERP_SINGLES)
    missing = _EXPECTED_SINGLES - symbols_in_list
    assert not missing, f"Net-profitable tickers missing from singles list: {sorted(missing)}"


def test_all_expected_singles_in_tradfi_databento_instruments() -> None:
    """All 12 tickers must be included in the aggregate TRADFI_DATABENTO_INSTRUMENTS."""
    all_symbols = frozenset(d.symbol for d in TRADFI_DATABENTO_INSTRUMENTS)
    missing = _EXPECTED_SINGLES - all_symbols
    assert not missing, f"Net-profitable tickers missing from aggregate universe: {sorted(missing)}"


# ---------------------------------------------------------------------------
# Exclusion tests
# ---------------------------------------------------------------------------


def test_marginal_symbols_excluded() -> None:
    """MSTR / COIN / PLTR (below 5% NET threshold) must NOT be in singles list."""
    symbols_in_list = frozenset(d.symbol for d in _NET_PROFITABLE_EQUITY_PERP_SINGLES)
    present_but_should_not_be = _EXCLUDED_SINGLES & symbols_in_list
    assert not present_but_should_not_be, (
        f"Below-threshold symbols incorrectly added: {sorted(present_but_should_not_be)}"
    )


def test_commodity_perp_symbols_not_in_singles() -> None:
    """Commodity perp base symbols (XAU/XAG/COPPER) must not appear in singles list."""
    symbols_in_list = frozenset(d.symbol for d in _NET_PROFITABLE_EQUITY_PERP_SINGLES)
    overlap = _EXCLUDED_COMMODITIES & symbols_in_list
    assert not overlap, f"Commodity symbols in equity singles list: {sorted(overlap)}"


# ---------------------------------------------------------------------------
# Dataset + field shape tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ticker", sorted(_EXPECTED_SINGLES))
def test_single_uses_dbeq_basic(ticker: str) -> None:
    """Every net-profitable single must use DBEQ.BASIC dataset."""
    entry = _singles_by_symbol().get(ticker)
    assert entry is not None, f"{ticker} not found in _NET_PROFITABLE_EQUITY_PERP_SINGLES"
    assert entry.dataset == "DBEQ.BASIC", f"{ticker}: expected DBEQ.BASIC, got {entry.dataset!r}"


@pytest.mark.parametrize("ticker", sorted(_EXPECTED_SINGLES))
def test_single_uses_raw_symbol_stype(ticker: str) -> None:
    """Every net-profitable single must use raw_symbol stype_in (not parent)."""
    entry = _singles_by_symbol().get(ticker)
    assert entry is not None
    assert entry.stype_in == "raw_symbol", f"{ticker}: expected raw_symbol, got {entry.stype_in!r}"


@pytest.mark.parametrize("ticker", sorted(_EXPECTED_SINGLES))
def test_single_instrument_type_is_stock(ticker: str) -> None:
    """Every entry must declare STOCK instrument_type."""
    entry = _singles_by_symbol().get(ticker)
    assert entry is not None
    assert entry.instrument_type == "STOCK", f"{ticker}: expected STOCK, got {entry.instrument_type!r}"


@pytest.mark.parametrize("ticker", sorted(_EXPECTED_SINGLES))
def test_single_asset_group_is_cefi(ticker: str) -> None:
    """Net-profitable equity-perp hedge legs belong to cefi asset_group."""
    entry = _singles_by_symbol().get(ticker)
    assert entry is not None
    assert entry.asset_group == "cefi", f"{ticker}: expected cefi, got {entry.asset_group!r}"


# ---------------------------------------------------------------------------
# get_databento_symbols_for_dataset helper
# ---------------------------------------------------------------------------


def test_get_databento_symbols_for_dataset_includes_singles() -> None:
    """get_databento_symbols_for_dataset('DBEQ.BASIC') must include the new singles."""
    dbeq_symbols = frozenset(d.symbol for d in get_databento_symbols_for_dataset("DBEQ.BASIC"))
    missing = _EXPECTED_SINGLES - dbeq_symbols
    assert not missing, f"DBEQ.BASIC filter missing net-profitable tickers: {sorted(missing)}"


# ---------------------------------------------------------------------------
# No duplicate symbols in aggregate list
# ---------------------------------------------------------------------------


def test_no_duplicate_symbols_in_tradfi_databento_instruments() -> None:
    """TRADFI_DATABENTO_INSTRUMENTS must not contain duplicate (symbol, dataset) pairs."""
    pairs = [(d.symbol, d.dataset) for d in TRADFI_DATABENTO_INSTRUMENTS]
    seen: set[tuple[str, str]] = set()
    dups = []
    for p in pairs:
        if p in seen:
            dups.append(p)
        seen.add(p)
    assert not dups, f"Duplicate (symbol, dataset) pairs: {dups}"
