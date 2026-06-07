"""Unit tests — G1-ENUM UAC validity matrix and accessor.

Tests cover:
  - _INSTRUMENT_TYPE_ALIASES normalization (UPPERCASE shorthands + lowercase)
  - VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE static matrix correctness
  - valid_data_types_for_instrument_type() accessor
  - DeFi derivation from PROTOCOL_CAPABILITIES (lazy-built cache)
  - Unmapped instrument_type returns None (fallback path)

Plan: expected_universe_v2_design_2026_05_08.md Phase 1.C [TEST] P0 (G1-ENUM)
"""

from __future__ import annotations

from unified_api_contracts.registry.market_data_categories import (
    _INSTRUMENT_TYPE_ALIASES,
    VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE,
    valid_data_types_for_instrument_type,
)


class TestInstrumentTypeAliases:
    """_INSTRUMENT_TYPE_ALIASES must normalise all expected tokens."""

    def test_spot_maps_to_spot_pair(self) -> None:
        assert _INSTRUMENT_TYPE_ALIASES["spot"] == "spot_pair"

    def test_perp_maps_to_perpetual(self) -> None:
        assert _INSTRUMENT_TYPE_ALIASES["perp"] == "perpetual"

    def test_perpetual_maps_to_perpetual(self) -> None:
        assert _INSTRUMENT_TYPE_ALIASES["perpetual"] == "perpetual"

    def test_spot_pair_maps_to_spot_pair(self) -> None:
        assert _INSTRUMENT_TYPE_ALIASES["spot_pair"] == "spot_pair"

    def test_options_chain_is_identity(self) -> None:
        assert _INSTRUMENT_TYPE_ALIASES["options_chain"] == "options_chain"

    def test_futures_chain_is_identity(self) -> None:
        assert _INSTRUMENT_TYPE_ALIASES["futures_chain"] == "futures_chain"

    def test_defi_tokens_are_identity(self) -> None:
        for token in ("lending", "pool", "dex_pool", "staking", "yield_bearing"):
            assert _INSTRUMENT_TYPE_ALIASES[token] == token, f"Expected {token}→{token}"


class TestValidDataTypesByAgAndInstrumentType:
    """Static matrix content sanity checks."""

    def test_cefi_spot_pair_has_trades(self) -> None:
        result = VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("cefi", "spot_pair")]
        assert "trades" in result
        assert isinstance(result, frozenset)

    def test_cefi_spot_pair_has_no_derivative_ticker(self) -> None:
        result = VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("cefi", "spot_pair")]
        assert "derivative_ticker" not in result

    def test_cefi_perpetual_has_derivative_ticker(self) -> None:
        result = VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("cefi", "perpetual")]
        assert "derivative_ticker" in result

    def test_cefi_option_is_empty(self) -> None:
        """cefi option leaf → frozenset() so enumerator skips all rows."""
        result = VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("cefi", "option")]
        assert result == frozenset()

    def test_cefi_combo_is_empty(self) -> None:
        result = VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("cefi", "combo")]
        assert result == frozenset()

    def test_cefi_options_chain_bundle(self) -> None:
        result = VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("cefi", "options_chain")]
        assert result == frozenset({"options_chain"})

    def test_cefi_futures_chain_bundle(self) -> None:
        result = VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("cefi", "futures_chain")]
        assert result == frozenset({"futures_chain"})

    def test_tradfi_equity_has_earnings_result(self) -> None:
        result = VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("tradfi", "equity")]
        assert "earnings_result" in result
        assert "corporate_action_confirmed" in result

    def test_tradfi_etf_has_no_earnings_result(self) -> None:
        result = VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("tradfi", "etf")]
        assert "earnings_result" not in result

    def test_tradfi_index_ohlcv_only(self) -> None:
        result = VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("tradfi", "index")]
        assert "trades" not in result
        assert all("ohlcv" in dt for dt in result)

    def test_sports_league_has_odds(self) -> None:
        result = VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("sports", "league")]
        assert "odds" in result
        assert "odds_snapshot" in result


class TestValidDataTypesForInstrumentTypeAccessor:
    """Public accessor: normalization, matrix look-up, defi derivation, fallback."""

    def test_cefi_spot_uppercase_normalises(self) -> None:
        """SPOT (uppercase as in catalogue) normalizes via alias → spot_pair."""
        result = valid_data_types_for_instrument_type("cefi", "SPOT")
        assert result is not None
        assert "trades" in result
        assert "derivative_ticker" not in result

    def test_cefi_perp_uppercase_normalises(self) -> None:
        """PERP (catalogue shorthand) normalizes → perpetual."""
        result = valid_data_types_for_instrument_type("cefi", "PERP")
        assert result is not None
        assert "derivative_ticker" in result

    def test_cefi_perpetual_uppercase_normalises(self) -> None:
        """PERPETUAL (InstrumentType enum value) normalizes → perpetual."""
        result = valid_data_types_for_instrument_type("cefi", "PERPETUAL")
        assert result is not None
        assert "derivative_ticker" in result

    def test_cefi_option_leaf_returns_empty_frozenset(self) -> None:
        result = valid_data_types_for_instrument_type("cefi", "OPTION")
        assert result == frozenset()

    def test_cefi_options_chain_returns_bundle(self) -> None:
        result = valid_data_types_for_instrument_type("cefi", "options_chain")
        assert result == frozenset({"options_chain"})

    def test_tradfi_etf_uppercase(self) -> None:
        result = valid_data_types_for_instrument_type("tradfi", "ETF")
        assert result is not None
        assert "trades" in result
        assert "earnings_result" not in result

    def test_tradfi_equity_uppercase(self) -> None:
        result = valid_data_types_for_instrument_type("tradfi", "EQUITY")
        assert result is not None
        assert "earnings_result" in result

    def test_asset_group_case_insensitive(self) -> None:
        """asset_group is normalised to lower before look-up."""
        result_lower = valid_data_types_for_instrument_type("cefi", "spot_pair")
        result_upper = valid_data_types_for_instrument_type("CEFI", "spot_pair")
        assert result_lower == result_upper

    def test_unmapped_instrument_type_returns_none(self) -> None:
        """An unknown instrument_type must return None (triggers fallback warning)."""
        result = valid_data_types_for_instrument_type("cefi", "UNKNOWN_INSTRUMENT_XYZ")
        assert result is None

    def test_unmapped_asset_group_returns_none(self) -> None:
        """An unknown asset_group + known instrument_type still returns None."""
        result = valid_data_types_for_instrument_type("unknown_ag", "spot_pair")
        assert result is None

    def test_defi_lending_returns_frozenset(self) -> None:
        """DeFi LENDING must derive a frozenset with lending data_types."""
        result = valid_data_types_for_instrument_type("defi", "LENDING")
        assert result is not None
        assert isinstance(result, frozenset)
        # Must include at least one lending-specific data_type
        assert len(result) > 0

    def test_defi_lending_excludes_perp_funding(self) -> None:
        """DeFi LENDING must NOT include perp_funding (that belongs to PERPETUAL)."""
        result = valid_data_types_for_instrument_type("defi", "LENDING")
        assert result is not None
        assert "perp_funding" not in result

    def test_defi_pool_has_dex_data(self) -> None:
        """DeFi POOL must include DEX data_types (primary pool data types).

        Note: some pool-type protocols (e.g. GMX) also carry perp_funding since
        GMX is a pool-based perp — POOL including perp_funding is therefore
        CORRECT for those protocols. The matrix is the union across all protocols
        using that instrument_type, so we only assert DEX data is present.
        """
        result = valid_data_types_for_instrument_type("defi", "POOL")
        assert result is not None
        assert "dex_pool_state" in result or "dex_pool_swaps" in result

    def test_defi_derivation_is_cached(self) -> None:
        """Repeated calls should return the same dict object (module-level cache)."""
        import unified_api_contracts.registry.market_data_categories as _mdc

        # Warm the cache
        valid_data_types_for_instrument_type("defi", "LENDING")
        first_cache = _mdc._DEFI_VALID_DATA_TYPES

        # Call again — must return same dict object (not rebuilt)
        valid_data_types_for_instrument_type("defi", "POOL")
        second_cache = _mdc._DEFI_VALID_DATA_TYPES

        assert first_cache is second_cache
