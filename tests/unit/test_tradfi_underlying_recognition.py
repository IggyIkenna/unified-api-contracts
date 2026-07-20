"""Tests for the TradFi real-product-root recogniser + the MES/XA* resolver additions.

Covers the forward half of the garbage-``underlying=`` fix
(tradfi_canonical_path_migration_design_2026_07_19.md):

* MES + XAB/XAF/XAI/XAK/XAP/XAU/XAV/XAY resolve to a real root (category C — no
  longer over-flagged as garbage).
* :func:`is_recognized_tradfi_underlying` accepts real roots + resolved named-spread
  combos (B/C) and rejects numeric globex group codes + opaque CBOE user-defined
  leg codes (A).
"""

from __future__ import annotations

import pytest

from unified_api_contracts import is_recognized_tradfi_underlying
from unified_api_contracts.internal.reference.ticker_registry import (
    UNDERLYING_NORMALIZATION,
    normalize_underlying,
)
from unified_api_contracts.registry import EXCHANGE_CODE_TO_NAME

_XA_ROOTS = ("XAB", "XAF", "XAI", "XAK", "XAP", "XAU", "XAV", "XAY")


class TestResolverAddsMesAndXaRoots:
    def test_mes_resolves_to_micro_sp500(self) -> None:
        assert EXCHANGE_CODE_TO_NAME["MES"] == "MICRO-SP500"
        assert normalize_underlying("MES") == "MICRO-SP500"

    def test_mes_distinct_from_full_size_es(self) -> None:
        # MES must NOT collapse into ES/SP500 — it is a different contract, its own bundle root.
        assert EXCHANGE_CODE_TO_NAME["MES"] != EXCHANGE_CODE_TO_NAME["ES"]

    @pytest.mark.parametrize("root", _XA_ROOTS)
    def test_xa_roots_present_in_both_registries(self, root: str) -> None:
        assert root in EXCHANGE_CODE_TO_NAME
        assert root in UNDERLYING_NORMALIZATION
        assert normalize_underlying(root)  # strict resolver no longer raises


class TestIsRecognizedTradfiUnderlying:
    @pytest.mark.parametrize(
        "underlying",
        ["ES", "SP500", "MES", "MICRO-SP500", "GOLD", "UST-10Y", "NAT-GAS", "VIX", *_XA_ROOTS],
    )
    def test_real_roots_recognized(self, underlying: str) -> None:
        assert is_recognized_tradfi_underlying(underlying) is True

    @pytest.mark.parametrize("underlying", ["WTI-BZ", "NAT-GAS-HH", "SP500-NASDAQ100"])
    def test_named_spread_combos_recognized(self, underlying: str) -> None:
        assert is_recognized_tradfi_underlying(underlying) is True

    @pytest.mark.parametrize("underlying", ["12", "13", "23", "0"])
    def test_numeric_globex_group_codes_rejected(self, underlying: str) -> None:
        assert is_recognized_tradfi_underlying(underlying) is False

    @pytest.mark.parametrize("underlying", ["GN", "VT", "IC", "3W", "CFO"])
    def test_opaque_cboe_leg_codes_rejected(self, underlying: str) -> None:
        assert is_recognized_tradfi_underlying(underlying) is False

    def test_empty_rejected(self) -> None:
        assert is_recognized_tradfi_underlying("") is False
        assert is_recognized_tradfi_underlying("  ") is False

    def test_case_insensitive(self) -> None:
        assert is_recognized_tradfi_underlying("sp500") is True
        assert is_recognized_tradfi_underlying("mes") is True
