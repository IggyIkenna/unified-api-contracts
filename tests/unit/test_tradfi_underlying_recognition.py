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

from unified_api_contracts import is_recognized_tradfi_underlying, resolve_tradfi_underlying_to_root
from unified_api_contracts.internal.reference.ticker_registry import (
    UNDERLYING_NORMALIZATION,
    normalize_underlying,
)
from unified_api_contracts.registry import EXCHANGE_CODE_TO_NAME

_XA_ROOTS = ("XAB", "XAF", "XAI", "XAK", "XAP", "XAU", "XAV", "XAY")
_CME_CRYPTO_FUTURES_ROOTS = ("BTC", "ETH", "MBT", "MET")


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

    @pytest.mark.parametrize("root", _CME_CRYPTO_FUTURES_ROOTS)
    def test_cme_crypto_futures_roots_present_in_both_registries(self, root: str) -> None:
        # BTC/ETH/MBT/MET (operator 2026-07-21) — added to the MVP tradfi FUTURE
        # download scope; must also be recognised roots so the write-time
        # canonical-path guard accepts their futures_chain shards.
        assert root in EXCHANGE_CODE_TO_NAME
        assert root in UNDERLYING_NORMALIZATION

    @pytest.mark.parametrize("root", _CME_CRYPTO_FUTURES_ROOTS)
    def test_cme_crypto_futures_roots_identity_mapped(self, root: str) -> None:
        # Identity map keeps the canonical id ``CME:FUTURE:BTC-USD@LIN-…`` — the
        # root is NOT remapped to a different human name (catalogue uses the raw
        # root), and MBT/MET are never folded into BTC/ETH.
        assert EXCHANGE_CODE_TO_NAME[root] == root
        assert normalize_underlying(root) == root


class TestIsRecognizedTradfiUnderlying:
    @pytest.mark.parametrize(
        "underlying",
        [
            "ES",
            "SP500",
            "MES",
            "MICRO-SP500",
            "GOLD",
            "UST-10Y",
            "NAT-GAS",
            "VIX",
            *_XA_ROOTS,
            *_CME_CRYPTO_FUTURES_ROOTS,
        ],
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

    @pytest.mark.parametrize("underlying", ["BTCF3-BTCG3", "ETHF3-ETHG3", "MBTF3-MBTG3"])
    def test_opaque_crypto_calendar_spread_legs_rejected(self, underlying: str) -> None:
        # A ``-``-joined pair of dated leg symbols has no resolvable single root
        # and MUST stay quarantined even though the crypto root (``BTC``) is a
        # substring of the leg token (``BTCF3``). Regression for the substring
        # fallback that would otherwise spuriously whitelist the combo. SSOT:
        # tradfi_canonical_path_migration_design_2026_07_19.md.
        assert is_recognized_tradfi_underlying(underlying) is False

    def test_empty_rejected(self) -> None:
        assert is_recognized_tradfi_underlying("") is False
        assert is_recognized_tradfi_underlying("  ") is False

    def test_case_insensitive(self) -> None:
        assert is_recognized_tradfi_underlying("sp500") is True
        assert is_recognized_tradfi_underlying("mes") is True


class TestResolveTradfiUnderlyingToRoot:
    """Reverse (spelled-name -> short root) half of the fix, added for
    tradfi_combo_underlying_naming_mismatch_blocks_g1_enum_present_rollup_2026_07_28.md
    — real captured tradfi COMBO/futures_chain/options_chain manifest rows carry an
    ``underlying`` VALUE spelled out ("HEATING-OIL", "PLATINUM", "CRUDE") instead of
    the catalog's short-root convention ("HO", "PL", "CL")."""

    @pytest.mark.parametrize(
        ("spelled", "root"),
        [
            ("HEATING-OIL", "HO"),
            ("HEATINGOIL", "HO"),
            ("HEATING_OIL", "HO"),
            ("PLATINUM", "PL"),
            ("CRUDE", "CL"),
            ("GOLD", "GC"),
            ("SILVER", "SI"),
            ("COPPER", "HG"),
            ("NATGAS", "NG"),
            ("NAT-GAS", "NG"),
        ],
    )
    def test_spelled_name_resolves_to_root(self, spelled: str, root: str) -> None:
        assert resolve_tradfi_underlying_to_root(spelled) == root

    def test_henry_hub_basis_suffix_trims_to_root(self) -> None:
        # "NAT-GAS-HH" is a real recognised named-spread (Henry Hub basis on NG) —
        # is_recognized_tradfi_underlying already accepts it; the reverse-lookup
        # must resolve the ROOT by progressively trimming the trailing "-HH" token.
        assert resolve_tradfi_underlying_to_root("NAT-GAS-HH") == "NG"

    def test_already_a_root_resolves_to_itself(self) -> None:
        assert resolve_tradfi_underlying_to_root("HO") == "HO"
        assert resolve_tradfi_underlying_to_root("cl") == "CL"

    def test_case_insensitive(self) -> None:
        assert resolve_tradfi_underlying_to_root("heating-oil") == "HO"
        assert resolve_tradfi_underlying_to_root("platinum") == "PL"

    def test_empty_returns_none(self) -> None:
        assert resolve_tradfi_underlying_to_root("") is None
        assert resolve_tradfi_underlying_to_root("   ") is None

    @pytest.mark.parametrize("garbage", ["12", "13", "GN", "VT", "3W"])
    def test_opaque_garbage_returns_none(self, garbage: str) -> None:
        assert resolve_tradfi_underlying_to_root(garbage) is None

    def test_unresolvable_multi_root_spread_returns_none(self) -> None:
        # WTI-BZ is a genuine 2-leg spread with no single resolvable root — the
        # reverse-lookup must not guess; caller keeps the original value unchanged.
        assert resolve_tradfi_underlying_to_root("WTI-BZ") is None
