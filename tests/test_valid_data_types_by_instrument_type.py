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
        # ERA-B: options_chain is an INSTRUMENT_TYPE; its market data_type is trades.
        result = VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("cefi", "options_chain")]
        assert result == frozenset({"trades"})

    def test_cefi_futures_chain_bundle(self) -> None:
        # ERA-B: futures_chain is an INSTRUMENT_TYPE; its market data_type is trades.
        result = VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("cefi", "futures_chain")]
        assert result == frozenset({"trades"})

    def test_tradfi_option_combo_leaf_empty(self) -> None:
        # ERA-B generalisation: tradfi option/combo leaves carry zero per-contract
        # rows (was None → over-fanned ~563K false candidates pre-G1-ENUM).
        assert VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("tradfi", "option")] == frozenset()
        assert VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("tradfi", "combo")] == frozenset()

    def test_tradfi_options_futures_chain_bundle_data_types(self) -> None:
        # T-OLD-2b (operator PRESERVE 2026-06-08, tradfi-owner verified vs the present-set, slot-6):
        # the per-underlying chain bundles admit EXACTLY the captured data_types — NOT just trades.
        # options_chain carries trades/ohlcv_1m + the schema-backed snapshot data_type=options_chain
        # (mark_iv/greeks; the 291 Era-A rows migrate to instrument_type=options_chain/data_type=options_chain).
        # futures_chain carries trades/ohlcv_1m/tbbo (no snapshot data_type observed for futures_chain on
        # tradfi disk → not admitted, to avoid an over-fan).
        assert VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("tradfi", "options_chain")] == frozenset(
            {"trades", "ohlcv_1m", "options_chain"}
        )
        assert VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("tradfi", "futures_chain")] == frozenset(
            {"trades", "ohlcv_1m", "tbbo"}
        )

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

    def test_sports_league_not_in_static_dict(self) -> None:
        # ("sports", "league") is intentionally NOT a static literal — it is derived
        # from SPORTS_DATA_TYPE_TO_SOURCE in the accessor (slot-4 2026-06-07; a literal
        # had silently dropped "ODDS"). The static dict only holds the dormant
        # fixture-grain scaffolding rows.
        assert ("sports", "league") not in VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE

    def test_sports_league_valid_is_reference_data_types(self) -> None:
        # Regression: the league could-exist grain must keep EVERY reference-data
        # provider data_type (SPORTS_DATA_TYPE_TO_SOURCE keys), incl. "ODDS" which a
        # prior literal dropped. It must NOT contain the MTDS odds market-data types.
        from unified_api_contracts.canonical.domain.sports import SPORTS_DATA_TYPE_TO_SOURCE

        result = valid_data_types_for_instrument_type("sports", "league")
        assert result == frozenset(SPORTS_DATA_TYPE_TO_SOURCE)
        assert "ODDS" in result  # the previously-dropped key
        assert "FIXTURES" in result
        assert "odds" not in result  # lowercase MTDS market-data type — not a league reference type

    def test_sports_league_uppercase_token_normalises(self) -> None:
        assert valid_data_types_for_instrument_type("sports", "LEAGUE") == valid_data_types_for_instrument_type(
            "sports", "league"
        )

    def test_prediction_market_slice_present(self) -> None:
        # Defense-in-depth / slice-parity row (slot-5 2026-06-08). Prediction is
        # grain-bound (the enumerator short-circuits on instr.data_type and never
        # consults this matrix), so the row is a WARN-suppressing backstop, not the
        # grain guard. Its valid set = the canonical prediction data_types — so it
        # never filters a real cell (all are attachable to a prediction market).
        result = valid_data_types_for_instrument_type("prediction", "prediction_market")
        assert result == frozenset(
            {"trades", "prediction_canonical_question_group", "market_lifecycle", "MARKET_LIFECYCLE"}
        )
        assert "prediction_canonical_question_group" in result


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
        # ERA-B: the options_chain instrument_type's market data_type is trades.
        result = valid_data_types_for_instrument_type("cefi", "options_chain")
        assert result == frozenset({"trades"})

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
        first_cache = _mdc._defi_valid_data_types

        # Call again — must return same dict object (not rebuilt)
        valid_data_types_for_instrument_type("defi", "POOL")
        second_cache = _mdc._defi_valid_data_types

        assert first_cache is second_cache


# ── G1-ENUM bundle-grain axis (slot-7 2026-06-07) ────────────────────────────
from unified_api_contracts.registry.market_data_categories import (
    GRAIN_BUNDLE_BY_UNDERLYING,
    GRAIN_LEAF,
    grain_for_instrument_type,
)


class TestInstrumentGrainAxis:
    """grain_for_instrument_type() — leaf vs bundle-by-underlying (G1-ENUM rollup).

    The bundle-grain SSOT: leaf OPTION/COMBO roll UP into a per-underlying
    options_chain/futures_chain bundle (one candidate per underlying, NOT one
    per leaf contract). The validity matrix zeroes the leaf per-contract rows
    (frozenset()); this axis is the declarative companion so a consumer can ask
    the grain directly.
    """

    def test_cefi_option_is_bundle_grain(self) -> None:
        assert grain_for_instrument_type("cefi", "option") == GRAIN_BUNDLE_BY_UNDERLYING

    def test_cefi_option_uppercase_token_normalises(self) -> None:
        assert grain_for_instrument_type("cefi", "OPTION") == GRAIN_BUNDLE_BY_UNDERLYING

    def test_cefi_combo_is_bundle_grain(self) -> None:
        assert grain_for_instrument_type("cefi", "COMBO") == GRAIN_BUNDLE_BY_UNDERLYING

    def test_cefi_options_chain_is_bundle_grain(self) -> None:
        assert grain_for_instrument_type("cefi", "options_chain") == GRAIN_BUNDLE_BY_UNDERLYING

    def test_cefi_futures_chain_is_bundle_grain(self) -> None:
        assert grain_for_instrument_type("cefi", "futures_chain") == GRAIN_BUNDLE_BY_UNDERLYING

    def test_cefi_spot_is_leaf(self) -> None:
        assert grain_for_instrument_type("cefi", "SPOT") == GRAIN_LEAF

    def test_cefi_perpetual_is_leaf(self) -> None:
        assert grain_for_instrument_type("cefi", "PERP") == GRAIN_LEAF

    def test_tradfi_equity_is_leaf(self) -> None:
        assert grain_for_instrument_type("tradfi", "equity") == GRAIN_LEAF

    def test_unmapped_defaults_to_leaf(self) -> None:
        assert grain_for_instrument_type("tradfi", "totally_unknown_xyz") == GRAIN_LEAF

    def test_bundle_grain_leaf_types_have_empty_valid_set(self) -> None:
        """A bundle-by-underlying LEAF type (option/combo) must carry zero valid
        per-contract data_types — the two halves of G1-ENUM agree (no per-leaf fan)."""
        for itype in ("option", "combo"):
            assert grain_for_instrument_type("cefi", itype) == GRAIN_BUNDLE_BY_UNDERLYING
            assert valid_data_types_for_instrument_type("cefi", itype) == frozenset()


class TestFutureVenueAwareGrain:
    """F2 (slot-7 2026-06-07) — FUTURE leaf grain is VENUE-aware: DERIBIT/OKX
    capture futures as a per-underlying futures_chain bundle; BYBIT (and every
    other per-contract venue, and venue-unknown) captures each future per-contract.
    """

    def test_cefi_future_no_venue_is_leaf(self) -> None:
        # Venue-unknown → safe per-contract leaf default (never over-bundle).
        assert grain_for_instrument_type("cefi", "future") == GRAIN_LEAF
        assert grain_for_instrument_type("cefi", "FUTURE") == GRAIN_LEAF

    def test_cefi_future_deribit_is_bundle(self) -> None:
        assert grain_for_instrument_type("cefi", "future", "DERIBIT") == GRAIN_BUNDLE_BY_UNDERLYING

    def test_cefi_future_okx_is_bundle_with_suffix(self) -> None:
        # OKX / OKX-FUTURES / OKX-SWAP all resolve via the base venue token.
        assert grain_for_instrument_type("cefi", "FUTURE", "OKX") == GRAIN_BUNDLE_BY_UNDERLYING
        assert grain_for_instrument_type("cefi", "future", "OKX-FUTURES") == GRAIN_BUNDLE_BY_UNDERLYING

    def test_cefi_future_bybit_stays_leaf(self) -> None:
        assert grain_for_instrument_type("cefi", "future", "BYBIT") == GRAIN_LEAF
        assert grain_for_instrument_type("cefi", "future", "BYBIT-FUTURES") == GRAIN_LEAF

    def test_venue_does_not_affect_option_combo_bundle(self) -> None:
        # option/combo bundle everywhere — venue arg is ignored for them.
        for venue in ("BYBIT", "DERIBIT", "OKX", None):
            assert grain_for_instrument_type("cefi", "option", venue) == GRAIN_BUNDLE_BY_UNDERLYING
            assert grain_for_instrument_type("cefi", "combo", venue) == GRAIN_BUNDLE_BY_UNDERLYING

    def test_cefi_future_deribit_rolls_to_futures_chain(self) -> None:
        assert bundle_instrument_type_for_leaf("cefi", "future", "DERIBIT") == "futures_chain"
        assert bundle_instrument_type_for_leaf("cefi", "FUTURE", "OKX-SWAP") == "futures_chain"

    def test_cefi_future_bybit_no_bundle(self) -> None:
        assert bundle_instrument_type_for_leaf("cefi", "future", "BYBIT") is None
        assert bundle_instrument_type_for_leaf("cefi", "future") is None


from unified_api_contracts.registry.market_data_categories import (
    bundle_instrument_type_for_leaf,
)


class TestBundleInstrumentTypeForLeaf:
    """bundle_instrument_type_for_leaf() — which bundle INSTRUMENT_TYPE a LEAF
    option/combo rolls up into (ERA-B G1-ENUM rollup driver). The returned value
    is the bundle instrument_type (options_chain); the rolled-up candidate's
    data_type is then trades (resolved via the validity matrix)."""

    def test_cefi_option_rolls_to_options_chain(self) -> None:
        assert bundle_instrument_type_for_leaf("cefi", "OPTION") == "options_chain"

    def test_cefi_combo_rolls_to_options_chain(self) -> None:
        assert bundle_instrument_type_for_leaf("cefi", "combo") == "options_chain"

    def test_tradfi_option_rolls_to_options_chain(self) -> None:
        assert bundle_instrument_type_for_leaf("tradfi", "OPTION") == "options_chain"

    def test_bundle_type_itself_returns_none(self) -> None:
        # options_chain / futures_chain ARE the per-underlying bundle entry — they
        # do not roll up further (pass through the enumerator unchanged).
        assert bundle_instrument_type_for_leaf("cefi", "options_chain") is None
        assert bundle_instrument_type_for_leaf("cefi", "futures_chain") is None

    def test_leaf_non_bundle_returns_none(self) -> None:
        assert bundle_instrument_type_for_leaf("cefi", "SPOT") is None
        assert bundle_instrument_type_for_leaf("cefi", "PERP") is None
