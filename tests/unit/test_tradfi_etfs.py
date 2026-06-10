"""Tests for canonical/domain/derivatives/tradfi_etfs.py — ETF SSOT (Phase 5A)."""

from __future__ import annotations

from datetime import date

import pytest

from unified_api_contracts.canonical.domain.derivatives.tradfi_etfs import (
    ALL_ETF_TICKERS,
    BTC_ETF_TICKERS,
    CATEGORY_COMMODITY,
    CATEGORY_CRYPTO_FUTURES,
    CATEGORY_CRYPTO_SPOT,
    CATEGORY_EQUITY,
    CATEGORY_FIXED_INCOME,
    CATEGORY_INTERNATIONAL,
    CATEGORY_SECTOR,
    CRYPTO_ETF_TICKERS,
    ETF_LISTING_DATES,
    ETH_ETF_TICKERS,
    KNOWN_ETFS_TICKERS,
    TRADFI_ETFS,
    ETFMetadata,
    get_crypto_etfs,
    get_etf_category,
    get_etf_listing_date,
    is_etf,
)

# ---------------------------------------------------------------------------
# is_etf
# ---------------------------------------------------------------------------


def test_is_etf_known_ticker() -> None:
    assert is_etf("SPY") is True
    assert is_etf("QQQ") is True
    assert is_etf("IBIT") is True


def test_is_etf_unknown_ticker() -> None:
    assert is_etf("AAPL") is False
    assert is_etf("BTCUSDT") is False
    assert is_etf("") is False


# ---------------------------------------------------------------------------
# get_etf_category
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("ticker", "expected"),
    [
        ("SPY", CATEGORY_EQUITY),
        ("EEM", CATEGORY_INTERNATIONAL),
        ("TLT", CATEGORY_FIXED_INCOME),
        ("GLD", CATEGORY_COMMODITY),
        ("XLF", CATEGORY_SECTOR),
        ("IBIT", CATEGORY_CRYPTO_SPOT),
        ("BITO", CATEGORY_CRYPTO_FUTURES),
    ],
)
def test_get_etf_category_known(ticker: str, expected: str) -> None:
    assert get_etf_category(ticker) == expected


def test_get_etf_category_unknown_returns_none() -> None:
    assert get_etf_category("NOTANETF") is None
    assert get_etf_category("AAPL") is None


# ---------------------------------------------------------------------------
# get_etf_listing_date
# ---------------------------------------------------------------------------


def test_get_etf_listing_date_with_date() -> None:
    assert get_etf_listing_date("IBIT") == date(2024, 1, 11)
    assert get_etf_listing_date("FBTC") == date(2024, 1, 11)
    assert get_etf_listing_date("ETHA") == date(2024, 7, 23)
    assert get_etf_listing_date("BITO") == date(2021, 10, 19)


def test_get_etf_listing_date_none_for_legacy_etfs() -> None:
    assert get_etf_listing_date("SPY") is None
    assert get_etf_listing_date("QQQ") is None
    assert get_etf_listing_date("GLD") is None


def test_get_etf_listing_date_unknown_returns_none() -> None:
    assert get_etf_listing_date("AAPL") is None


# ---------------------------------------------------------------------------
# get_crypto_etfs
# ---------------------------------------------------------------------------


def test_get_crypto_etfs_all() -> None:
    result = get_crypto_etfs()
    assert "IBIT" in result
    assert "FBTC" in result
    assert "ETHA" in result
    assert "BITO" in result
    # non-crypto ETFs excluded
    assert "SPY" not in result
    assert "TLT" not in result


def test_get_crypto_etfs_btc_filter() -> None:
    result = get_crypto_etfs(underlying="BTC")
    assert all(TRADFI_ETFS[t].crypto_underlying == "BTC" for t in result)
    assert "IBIT" in result
    assert "FBTC" in result
    assert "BITO" in result
    assert "ETHA" not in result


def test_get_crypto_etfs_eth_filter() -> None:
    result = get_crypto_etfs(underlying="ETH")
    assert all(TRADFI_ETFS[t].crypto_underlying == "ETH" for t in result)
    assert "ETHA" in result
    assert "FETH" in result
    assert "IBIT" not in result


def test_get_crypto_etfs_unknown_underlying_empty() -> None:
    assert get_crypto_etfs(underlying="SOL") == []
    assert get_crypto_etfs(underlying="UNKNOWN") == []


# ---------------------------------------------------------------------------
# Derived frozensets
# ---------------------------------------------------------------------------


def test_all_etf_tickers_is_frozenset_of_all_keys() -> None:
    assert frozenset(TRADFI_ETFS.keys()) == ALL_ETF_TICKERS
    assert isinstance(ALL_ETF_TICKERS, frozenset)


def test_known_etfs_tickers_subset() -> None:
    assert KNOWN_ETFS_TICKERS.issubset(ALL_ETF_TICKERS)
    assert "SPY" in KNOWN_ETFS_TICKERS
    # VIG has in_known_etfs=False
    assert "VIG" not in KNOWN_ETFS_TICKERS


def test_crypto_etf_tickers() -> None:
    assert isinstance(CRYPTO_ETF_TICKERS, frozenset)
    for t in CRYPTO_ETF_TICKERS:
        assert TRADFI_ETFS[t].category in (CATEGORY_CRYPTO_SPOT, CATEGORY_CRYPTO_FUTURES)


def test_btc_eth_etf_tickers_disjoint() -> None:
    assert BTC_ETF_TICKERS.isdisjoint(ETH_ETF_TICKERS)
    assert "IBIT" in BTC_ETF_TICKERS
    assert "ETHA" in ETH_ETF_TICKERS


def test_etf_listing_dates_only_has_entries_with_dates() -> None:
    for ticker, listing_date in ETF_LISTING_DATES.items():
        assert listing_date is not None
        assert TRADFI_ETFS[ticker].listing_date == listing_date
    # Legacy ETFs with no listing date must not appear
    assert "SPY" not in ETF_LISTING_DATES


# ---------------------------------------------------------------------------
# ETFMetadata dataclass invariants
# ---------------------------------------------------------------------------


def test_etfmetadata_is_frozen() -> None:
    meta = ETFMetadata("TEST", CATEGORY_EQUITY, "TEST_UNDERLYING")
    with pytest.raises((AttributeError, TypeError)):
        meta.ticker = "OTHER"  # type: ignore[misc]


def test_etfmetadata_defaults() -> None:
    meta = ETFMetadata("TST", CATEGORY_EQUITY, "IDX")
    assert meta.listing_date is None
    assert meta.issuer is None
    assert meta.in_known_etfs is True
    assert meta.crypto_underlying is None
