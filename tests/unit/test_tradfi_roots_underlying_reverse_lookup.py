"""Unit tests for root_for_underlying_name() — TradFi COMBO underlying-naming
reverse lookup (query-time reconciliation half of the naming mismatch found
while quantifying the G1-ENUM present-set symmetric-rollup fix).

Covers: exact registry match, hyphen/underscore/space normalization, the
already-a-root-code shortcut, the real-manifest alias table (verified via a
live probe of the prod market-data-tick-tradfi manifest's
`_index/availability_index.parquet` on 2026-07-28), and honest-absence
(None) for unknown/unresolvable values.

Issue: tradfi_combo_underlying_naming_mismatch_blocks_g1_enum_present_rollup_2026_07_28.md
"""

from __future__ import annotations

import pytest

from unified_api_contracts.canonical.domain.derivatives.tradfi_roots import (
    root_for_underlying_name,
)


@pytest.mark.unit
class TestRootForUnderlyingName:
    """Tests for root_for_underlying_name()."""

    # -- exact registry ``underlying`` match (already normalized-clean) -----

    def test_exact_registry_underlying_match(self) -> None:
        """A registry underlying value, verbatim, resolves to its root."""
        assert root_for_underlying_name("GOLD") == "GC"
        assert root_for_underlying_name("SILVER") == "SI"
        assert root_for_underlying_name("SP500") == "ES"

    # -- normalization: hyphen / underscore / mixed-space / case ------------

    def test_hyphen_normalizes_to_registry_underscore_form(self) -> None:
        """ "HEATING-OIL" (real manifest spelling) folds onto the registry's
        "HEATING_OIL" underlying value for root "HO" with no alias needed."""
        assert root_for_underlying_name("HEATING-OIL") == "HO"

    def test_underscore_form_matches_directly(self) -> None:
        assert root_for_underlying_name("HEATING_OIL") == "HO"

    def test_mixed_case_and_space_normalizes(self) -> None:
        assert root_for_underlying_name("Heating Oil") == "HO"
        assert root_for_underlying_name("heating-oil") == "HO"

    # -- already-a-root-code shortcut (real manifest rows carry this too) ---

    def test_already_correct_root_code_resolves_to_itself(self) -> None:
        """Real manifest COMBO rows sometimes already carry the correct short
        root code (e.g. "CL", "NG") as their underlying value."""
        assert root_for_underlying_name("CL") == "CL"
        assert root_for_underlying_name("NG") == "NG"
        assert root_for_underlying_name("cl") == "CL"

    # -- real manifest alias-table cases --------------------------------

    def test_nat_gas_hh_alias(self) -> None:
        """The exact near-miss the issue doc flagged: real manifest value
        "NAT-GAS-HH" (Henry Hub) doesn't fold onto registry "NATGAS" for
        root "NG" even after normalization; requires the explicit alias."""
        assert root_for_underlying_name("NAT-GAS-HH") == "NG"

    def test_nat_gas_family_aliases(self) -> None:
        assert root_for_underlying_name("NAT-GAS") == "NG"
        assert root_for_underlying_name("NAT-GAS-MNG") == "NG"
        assert root_for_underlying_name("NAT-GAS-QG") == "NG"
        assert root_for_underlying_name("NAT-GAS-NN") == "NG"

    def test_livestock_alias(self) -> None:
        assert root_for_underlying_name("LIVE-CATTLE") == "LE"
        assert root_for_underlying_name("LEAN-HOG") == "HE"

    def test_soy_family_alias(self) -> None:
        assert root_for_underlying_name("SOYBEAN") == "ZS"
        assert root_for_underlying_name("SOYOIL") == "ZL"
        assert root_for_underlying_name("SOYMEAL") == "ZM"

    def test_treasury_alias(self) -> None:
        assert root_for_underlying_name("UST-10Y") == "ZN"
        assert root_for_underlying_name("UST-30Y") == "ZB"
        assert root_for_underlying_name("UST-5Y") == "ZF"
        assert root_for_underlying_name("UST-2Y") == "ZT"

    def test_fx_pair_alias(self) -> None:
        assert root_for_underlying_name("EURUSD") == "6E"
        assert root_for_underlying_name("GBPUSD") == "6B"
        assert root_for_underlying_name("JPYUSD") == "6J"

    def test_rbob_gas_alias(self) -> None:
        assert root_for_underlying_name("RBOB-GAS") == "RB"

    # -- honest absence: None, never a guess ---------------------------------

    def test_unknown_value_returns_none(self) -> None:
        assert root_for_underlying_name("NOT_A_REAL_UNDERLYING") is None

    def test_empty_string_returns_none(self) -> None:
        assert root_for_underlying_name("") is None

    def test_composite_spread_value_returns_none(self) -> None:
        """A value naming TWO roots at once (a calendar/crack spread) is not
        a single-root concept — honest None, not a guessed pick of one leg."""
        assert root_for_underlying_name("WTI-BZ") is None
        assert root_for_underlying_name("RBOB-GAS-HEATING-OIL") is None

    def test_spread_type_code_returns_none(self) -> None:
        """Non-commodity spread-structure codes seen leaking into the real
        manifest's underlying column (not aliasable — not a commodity name)."""
        assert root_for_underlying_name("GN") is None
        assert root_for_underlying_name("CFO") is None

    # -- micro / options-sub-series / event-contract underlyings still ------
    # -- resolve (via the plain registry match, not the primary-root index) -

    def test_micro_root_code_still_resolves_to_itself(self) -> None:
        """MES is itself a valid TRADFI_ROOTS key (self-root shortcut) even
        though it's excluded as an INDEX VALUE when building the reverse
        name->root map (it's a micro contract, not a primary root)."""
        assert root_for_underlying_name("MES") == "MES"
