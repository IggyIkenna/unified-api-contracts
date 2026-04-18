"""Tests for ``unified_api_contracts.internal.reference.ticker_registry``.

Covers:

* Every CME ticker in ``UNDERLYING_NORMALIZATION`` resolves to a
  human-readable name via :func:`normalize_underlying`.
* Every ticker in the current ``TRADFI_TICKER_UNIVERSE`` (SP500, NASDAQ,
  ETFs) resolves to a concrete listing exchange via
  :func:`resolve_exchange` — no ``UNKNOWN`` sentinel.
* Unknown inputs raise ``ValueError`` — strict, no fuzzy matching.
* Top-level ``unified_api_contracts`` re-exports the registry API.
"""

from __future__ import annotations

import pytest

from unified_api_contracts import (
    EXCHANGE_BY_TICKER,
    TRADFI_TICKER_UNIVERSE,
    UNDERLYING_NORMALIZATION,
    normalize_underlying,
    resolve_exchange,
)


class TestUnderlyingNormalization:
    def test_es_normalises_to_sp500(self) -> None:
        assert normalize_underlying("ES") == "SP500"

    def test_nq_normalises_to_nasdaq100(self) -> None:
        assert normalize_underlying("NQ") == "NASDAQ100"

    def test_cl_normalises_to_wti(self) -> None:
        assert normalize_underlying("CL") == "WTI"

    def test_zn_normalises_to_ust_10y(self) -> None:
        assert normalize_underlying("ZN") == "UST-10Y"

    def test_6a_normalises_to_audusd(self) -> None:
        assert normalize_underlying("6A") == "AUDUSD"

    def test_6e_normalises_to_eurusd(self) -> None:
        assert normalize_underlying("6E") == "EURUSD"

    def test_lowercase_input_is_normalised(self) -> None:
        assert normalize_underlying("es") == "SP500"

    def test_whitespace_is_stripped(self) -> None:
        assert normalize_underlying("  ES  ") == "SP500"

    def test_unknown_code_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown underlying code"):
            normalize_underlying("ZZZ")

    def test_empty_code_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            normalize_underlying("")

    @pytest.mark.parametrize("code", list(UNDERLYING_NORMALIZATION.keys()))
    def test_every_registered_code_resolves(self, code: str) -> None:
        # Ensures no dead keys — every key in the registry resolves via
        # the public helper.
        result = normalize_underlying(code)
        assert result
        assert result == UNDERLYING_NORMALIZATION[code]


class TestResolveExchange:
    def test_aapl_lists_on_nasdaq(self) -> None:
        assert resolve_exchange("AAPL") == "NASDAQ"

    def test_mmm_lists_on_nyse(self) -> None:
        assert resolve_exchange("MMM") == "NYSE"

    def test_spy_lists_on_arca(self) -> None:
        assert resolve_exchange("SPY") == "ARCA"

    def test_lowercase_is_normalised(self) -> None:
        assert resolve_exchange("aapl") == "NASDAQ"

    def test_unknown_ticker_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown ticker"):
            resolve_exchange("XYZ_NOT_REAL")

    def test_empty_ticker_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            resolve_exchange("")


class TestUniverseCoverage:
    def test_every_sp500_ticker_resolves_to_exchange(self) -> None:
        # Every SP500 ticker must have an exchange — no "UNKNOWN" bucket.
        sp500 = TRADFI_TICKER_UNIVERSE["sp500_tickers"]
        unresolved = [t for t in sp500 if t not in EXCHANGE_BY_TICKER]
        assert not unresolved, (
            f"SP500 tickers missing from EXCHANGE_BY_TICKER: {unresolved}. "
            "Add them to _NASDAQ/_NYSE/_ARCA in ticker_registry.py."
        )

    def test_every_nasdaq_ticker_resolves(self) -> None:
        nasdaq = TRADFI_TICKER_UNIVERSE["nasdaq_tickers"]
        unresolved = [t for t in nasdaq if t not in EXCHANGE_BY_TICKER]
        assert not unresolved, f"NASDAQ tickers missing from EXCHANGE_BY_TICKER: {unresolved}"

    def test_every_etf_ticker_resolves(self) -> None:
        etfs = TRADFI_TICKER_UNIVERSE["etf_tickers"]
        unresolved = [t for t in etfs if t not in EXCHANGE_BY_TICKER]
        assert not unresolved, f"ETF tickers missing from EXCHANGE_BY_TICKER: {unresolved}"

    def test_every_nasdaq_ticker_resolves_to_nasdaq(self) -> None:
        # Sanity: all NASDAQ-universe tickers resolve to the NASDAQ venue
        # (they are not mistakenly placed in NYSE/ARCA).
        nasdaq = TRADFI_TICKER_UNIVERSE["nasdaq_tickers"]
        mis_routed = [t for t in nasdaq if t in EXCHANGE_BY_TICKER and EXCHANGE_BY_TICKER[t] != "NASDAQ"]
        assert not mis_routed, f"NASDAQ-universe tickers routed to wrong venue: {mis_routed}"

    def test_every_etf_universe_ticker_resolves_to_arca(self) -> None:
        etfs = TRADFI_TICKER_UNIVERSE["etf_tickers"]
        mis_routed = [t for t in etfs if t in EXCHANGE_BY_TICKER and EXCHANGE_BY_TICKER[t] != "ARCA"]
        assert not mis_routed, f"ETF-universe tickers routed to wrong venue: {mis_routed}"


class TestTopLevelReExport:
    def test_normalize_underlying_re_exported(self) -> None:
        from unified_api_contracts import normalize_underlying as top_level
        from unified_api_contracts.internal.reference.ticker_registry import (
            normalize_underlying as module_level,
        )

        assert top_level is module_level

    def test_resolve_exchange_re_exported(self) -> None:
        from unified_api_contracts import resolve_exchange as top_level
        from unified_api_contracts.internal.reference.ticker_registry import (
            resolve_exchange as module_level,
        )

        assert top_level is module_level
