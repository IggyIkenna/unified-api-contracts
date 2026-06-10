"""Tests for external/kalshi/crypto_macro_mappings.py — Kalshi ticker builders."""

from __future__ import annotations

import pytest

from unified_api_contracts.external.kalshi.crypto_macro_mappings import (
    KALSHI_CRYPTO_SERIES,
    KALSHI_MACRO_SERIES,
    build_kalshi_crypto_ticker,
    build_kalshi_macro_ticker,
    parse_kalshi_ticker,
)


class TestKalshiCryptoSeries:
    def test_btc_has_kxbtc(self) -> None:
        assert KALSHI_CRYPTO_SERIES["BTC"] == "KXBTC"

    def test_eth_has_kxeth(self) -> None:
        assert KALSHI_CRYPTO_SERIES["ETH"] == "KXETH"

    def test_sol_has_kxsol(self) -> None:
        assert KALSHI_CRYPTO_SERIES["SOL"] == "KXSOL"

    def test_three_entries(self) -> None:
        assert len(KALSHI_CRYPTO_SERIES) == 3


class TestKalshiMacroSeries:
    def test_spx_has_kxspy(self) -> None:
        assert KALSHI_MACRO_SERIES["SPX"] == "KXSPY"

    def test_fed_has_kxfed(self) -> None:
        assert KALSHI_MACRO_SERIES["FED"] == "KXFED"

    def test_cpi_has_kxcpi(self) -> None:
        assert KALSHI_MACRO_SERIES["CPI"] == "KXCPI"

    def test_gdp_has_kxgdp(self) -> None:
        assert KALSHI_MACRO_SERIES["GDP"] == "KXGDP"

    def test_nasdaq_has_kxndx(self) -> None:
        assert KALSHI_MACRO_SERIES["NASDAQ"] == "KXNDX"

    def test_five_entries(self) -> None:
        assert len(KALSHI_MACRO_SERIES) == 5


class TestBuildKalshiCryptoTicker:
    def test_btc_ticker(self) -> None:
        result = build_kalshi_crypto_ticker("BTC", "21MAR26", 95000)
        assert result == "KXBTC-21MAR26-T95000"

    def test_eth_ticker(self) -> None:
        result = build_kalshi_crypto_ticker("ETH", "28JUN26", 4000)
        assert result == "KXETH-28JUN26-T4000"

    def test_sol_ticker(self) -> None:
        result = build_kalshi_crypto_ticker("SOL", "31DEC26", 500)
        assert result == "KXSOL-31DEC26-T500"

    def test_unknown_underlying_returns_none(self) -> None:
        result = build_kalshi_crypto_ticker("DOGE", "21MAR26", 1)
        assert result is None

    def test_case_insensitive_underlying(self) -> None:
        result = build_kalshi_crypto_ticker("btc", "21MAR26", 95000)
        assert result == "KXBTC-21MAR26-T95000"

    def test_strike_zero(self) -> None:
        result = build_kalshi_crypto_ticker("BTC", "21MAR26", 0)
        assert result == "KXBTC-21MAR26-T0"

    def test_large_strike(self) -> None:
        result = build_kalshi_crypto_ticker("BTC", "21MAR26", 1000000)
        assert result == "KXBTC-21MAR26-T1000000"


class TestBuildKalshiMacroTicker:
    def test_spx_ticker(self) -> None:
        result = build_kalshi_macro_ticker("SPX", "21MAR26", 5800)
        assert result == "KXSPY-21MAR26-T5800"

    def test_fed_ticker(self) -> None:
        result = build_kalshi_macro_ticker("FED", "19MAR26", 525)
        assert result == "KXFED-19MAR26-T525"

    def test_cpi_ticker(self) -> None:
        result = build_kalshi_macro_ticker("CPI", "15APR26", 320)
        assert result == "KXCPI-15APR26-T320"

    def test_gdp_ticker(self) -> None:
        result = build_kalshi_macro_ticker("GDP", "30JUN26", 150)
        assert result == "KXGDP-30JUN26-T150"

    def test_nasdaq_ticker(self) -> None:
        result = build_kalshi_macro_ticker("NASDAQ", "21MAR26", 20000)
        assert result == "KXNDX-21MAR26-T20000"

    def test_unknown_underlying_returns_none(self) -> None:
        result = build_kalshi_macro_ticker("GOLD", "21MAR26", 2500)
        assert result is None

    def test_case_insensitive_underlying(self) -> None:
        result = build_kalshi_macro_ticker("spx", "21MAR26", 5800)
        assert result == "KXSPY-21MAR26-T5800"


class TestParseKalshiTicker:
    def test_btc_ticker_parses(self) -> None:
        result = parse_kalshi_ticker("KXBTC-26MAR21-T95000")
        assert result is not None
        assert result["series"] == "KXBTC"
        assert result["underlying"] == "BTC"
        assert result["date"] == "26MAR21"
        assert result["strike"] == 95000

    def test_spx_ticker_parses(self) -> None:
        result = parse_kalshi_ticker("KXSPY-21MAR26-T5800")
        assert result is not None
        assert result["series"] == "KXSPY"
        assert result["underlying"] == "SPX"
        assert result["date"] == "21MAR26"
        assert result["strike"] == 5800

    def test_fed_ticker_parses(self) -> None:
        result = parse_kalshi_ticker("KXFED-19MAR26-T525")
        assert result is not None
        assert result["underlying"] == "FED"
        assert result["strike"] == 525

    def test_eth_ticker_parses(self) -> None:
        result = parse_kalshi_ticker("KXETH-28JUN26-T4000")
        assert result is not None
        assert result["underlying"] == "ETH"
        assert result["strike"] == 4000

    def test_unknown_series_returns_none(self) -> None:
        result = parse_kalshi_ticker("KXGOLD-21MAR26-T2500")
        assert result is None

    def test_malformed_ticker_returns_none(self) -> None:
        result = parse_kalshi_ticker("NOT_A_TICKER")
        assert result is None

    def test_empty_string_returns_none(self) -> None:
        result = parse_kalshi_ticker("")
        assert result is None

    def test_missing_t_prefix_returns_none(self) -> None:
        result = parse_kalshi_ticker("KXBTC-21MAR26-95000")
        assert result is None

    def test_strike_is_int(self) -> None:
        result = parse_kalshi_ticker("KXBTC-21MAR26-T95000")
        assert result is not None
        assert isinstance(result["strike"], int)

    def test_roundtrip_btc(self) -> None:
        ticker = build_kalshi_crypto_ticker("BTC", "21MAR26", 95000)
        assert ticker is not None
        parsed = parse_kalshi_ticker(ticker)
        assert parsed is not None
        assert parsed["underlying"] == "BTC"
        assert parsed["strike"] == 95000

    def test_roundtrip_spx(self) -> None:
        ticker = build_kalshi_macro_ticker("SPX", "21MAR26", 5800)
        assert ticker is not None
        parsed = parse_kalshi_ticker(ticker)
        assert parsed is not None
        assert parsed["underlying"] == "SPX"
        assert parsed["strike"] == 5800


@pytest.mark.parametrize(
    ("underlying", "date_str", "strike", "expected"),
    [
        ("BTC", "21MAR26", 95000, "KXBTC-21MAR26-T95000"),
        ("ETH", "28JUN26", 4000, "KXETH-28JUN26-T4000"),
        ("SOL", "31DEC26", 500, "KXSOL-31DEC26-T500"),
        ("DOGE", "21MAR26", 1, None),
    ],
)
def test_build_crypto_ticker_parametrized(
    underlying: str,
    date_str: str,
    strike: int,
    expected: str | None,
) -> None:
    assert build_kalshi_crypto_ticker(underlying, date_str, strike) == expected


@pytest.mark.parametrize(
    ("underlying", "date_str", "strike", "expected"),
    [
        ("SPX", "21MAR26", 5800, "KXSPY-21MAR26-T5800"),
        ("FED", "19MAR26", 525, "KXFED-19MAR26-T525"),
        ("CPI", "15APR26", 320, "KXCPI-15APR26-T320"),
        ("GOLD", "21MAR26", 2500, None),
    ],
)
def test_build_macro_ticker_parametrized(
    underlying: str,
    date_str: str,
    strike: int,
    expected: str | None,
) -> None:
    assert build_kalshi_macro_ticker(underlying, date_str, strike) == expected
