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
    GRAIN_BUNDLE_BY_UNDERLYING,
    GRAIN_LEAF,
    VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE,
    bundle_instrument_type_for_leaf,
    grain_for_instrument_type,
    valid_data_types_for_instrument_type,
    valid_data_types_for_venue_instrument_type,
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

    def test_tradfi_option_leaf_empty(self) -> None:
        # ERA-B generalisation: the tradfi option LEAF carries zero per-contract rows
        # (was None → over-fanned ~563K false candidates pre-G1-ENUM); it rolls up to
        # options_chain. (combo is now its OWN bundle type — see test below.)
        assert VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("tradfi", "option")] == frozenset()

    def test_tradfi_combo_drives_its_own_bundle_data_types(self) -> None:
        # 2026-06-22 writer-grain alignment: tradfi COMBO rolls up to instrument_type=combo
        # (the MTDS writer keeps a distinct combo partition), so — unlike option — the
        # ("tradfi","combo") row IS consulted (it drives the synthetic bundle entry's
        # data_types). It mirrors the outright-futures OHLCV stream the combo legs reference.
        assert VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("tradfi", "combo")] == frozenset(
            {"trades", "ohlcv_1s", "ohlcv_1m", "tbbo"}
        )

    def test_tradfi_options_futures_chain_bundle_data_types(self) -> None:
        # T-OLD-2b (operator PRESERVE 2026-06-08, tradfi-owner verified vs the present-set, slot-6):
        # the per-underlying chain bundles admit EXACTLY the captured data_types — NOT just trades.
        # options_chain carries trades/ohlcv_1m + the schema-backed snapshot data_type=options_chain
        # (mark_iv/greeks; the 291 Era-A rows migrate to instrument_type=options_chain/data_type=options_chain).
        # futures_chain carries trades/ohlcv_1s/ohlcv_1m/tbbo (ohlcv_1s added 2026-06-22 — the writer
        # captures CME/ICE chain cells with ohlcv_1s alongside ohlcv_1m; both L0/free GLBX.MDP3 fetches).
        assert VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("tradfi", "options_chain")] == frozenset(
            {"trades", "ohlcv_1m", "options_chain"}
        )
        assert VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("tradfi", "futures_chain")] == frozenset(
            {"trades", "ohlcv_1s", "ohlcv_1m", "tbbo"}
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
        # had silently dropped keys). The static dict only holds the dormant
        # fixture-grain scaffolding rows.
        assert ("sports", "league") not in VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE

    def test_sports_league_valid_is_reference_data_types(self) -> None:
        # Regression: the league could-exist grain must keep EVERY reference-data
        # provider data_type (SPORTS_DATA_TYPE_TO_SOURCE keys).
        # ODDS was removed 2026-06-25 (#6) then RESTORED 2026-06-27 (operator reversal):
        # footystats ODDS = pre-match snapshot reference data (IS); raw bookmaker tick
        # data = MTDS odds-api. They coexist; see codex sports-data-source-coverage-matrix §4.
        # It must NOT contain the MTDS odds market-data types.
        from unified_api_contracts.canonical.domain.sports import SPORTS_DATA_TYPE_TO_SOURCE

        result = valid_data_types_for_instrument_type("sports", "league")
        assert result == frozenset(SPORTS_DATA_TYPE_TO_SOURCE)
        assert "ODDS" in result  # footystats pre-match snapshot — IS reference data (#6 REVERSED)
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


class TestTradfiBundleGrainWriterAlignment:
    """The IS expected-universe SEED must roll TradFi FUTURE/COMBO leaves up to the
    SAME ``instrument_type`` the MTDS writer (``symbol_rules``) captures them at
    (writer-grain alignment 2026-06-22). The bundle map is NOT shared with the
    writer — MTDS imports only VENUE_DATA_TYPE_CAPABILITIES / the DERIBIT MVP map —
    so re-graining here only affects the enumerator seed, never capture behaviour."""

    def test_tradfi_future_at_cme_bundles_to_futures_chain(self) -> None:
        # CME outright FUTURE leaf → writer stamps instrument_type=futures_chain
        # (venue default), so the seed must too. Catalogue UPPERCASE token resolves.
        assert bundle_instrument_type_for_leaf("tradfi", "FUTURE", "CME") == "futures_chain"
        assert grain_for_instrument_type("tradfi", "FUTURE", "CME") == GRAIN_BUNDLE_BY_UNDERLYING

    def test_tradfi_future_at_ice_bundles_to_futures_chain(self) -> None:
        assert bundle_instrument_type_for_leaf("tradfi", "FUTURE", "ICE") == "futures_chain"
        assert grain_for_instrument_type("tradfi", "FUTURE", "ICE") == GRAIN_BUNDLE_BY_UNDERLYING

    def test_tradfi_future_at_non_futures_venue_stays_leaf(self) -> None:
        # A FUTURE leaf at a NON-CME/ICE venue (or venue-unknown) stays per-contract
        # (returns None) — the overlay is precisely venue-gated, never a blanket
        # tradfi FUTURE→futures_chain (which would over-seed any future-typed leaf).
        assert bundle_instrument_type_for_leaf("tradfi", "FUTURE", "NASDAQ") is None
        assert bundle_instrument_type_for_leaf("tradfi", "FUTURE", None) is None
        assert grain_for_instrument_type("tradfi", "FUTURE", "NASDAQ") == GRAIN_LEAF

    def test_tradfi_combo_bundles_to_combo_not_options_chain(self) -> None:
        # CME spread/combo (databento class T) → writer keeps instrument_type=combo
        # (a distinct per-underlying partition), NOT options_chain. Venue-agnostic.
        assert bundle_instrument_type_for_leaf("tradfi", "COMBO", "CME") == "combo"
        assert bundle_instrument_type_for_leaf("tradfi", "combo", "ICE") == "combo"
        assert grain_for_instrument_type("tradfi", "COMBO", "CME") == GRAIN_BUNDLE_BY_UNDERLYING

    def test_tradfi_option_still_bundles_to_options_chain(self) -> None:
        # Regression guard: the option→options_chain roll-up is unchanged.
        assert bundle_instrument_type_for_leaf("tradfi", "OPTION", "CME") == "options_chain"

    def test_cefi_combo_unchanged_options_chain(self) -> None:
        # Regression guard: cefi COMBO (Deribit) still rolls into options_chain —
        # the combo re-grain is TradFi-only.
        assert bundle_instrument_type_for_leaf("cefi", "COMBO", "DERIBIT") == "options_chain"

    def test_cefi_future_venue_overlay_unchanged(self) -> None:
        # Regression guard: cefi FUTURE bundling is still DERIBIT/OKX-only, BYBIT leaf.
        assert bundle_instrument_type_for_leaf("cefi", "FUTURE", "DERIBIT") == "futures_chain"
        assert bundle_instrument_type_for_leaf("cefi", "FUTURE", "BYBIT") is None

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
# (GRAIN_BUNDLE_BY_UNDERLYING / GRAIN_LEAF / grain_for_instrument_type are imported
# at module top alongside bundle_instrument_type_for_leaf — 2026-06-22.)


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


# (bundle_instrument_type_for_leaf is imported at module top — 2026-06-22.)


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


class TestValidDataTypesForVenueInstrumentType:
    """DeFi protocol-grain narrowing (G1-ENUM venue/protocol refinement).

    The instrument_type-grain ``valid_data_types_for_instrument_type`` builds
    the DeFi set as the UNION across every protocol that declares an
    instrument_type, so a hybrid protocol (GMX = pool + perp_funding) leaks
    ``perp_funding`` into the valid set for ALL pools. The venue-aware accessor
    keys validity to the protocol named by the venue id.
    """

    def test_uniswap_pool_excludes_perp_funding(self) -> None:
        # UNISWAP_V3 declares POOL with DEX data only — NO perp_funding.
        valid = valid_data_types_for_venue_instrument_type("defi", "UNISWAP_V3-ETHEREUM", "pool")
        assert valid is not None
        assert "dex_pool_state" in valid
        assert "dex_pool_swaps" in valid
        assert "perp_funding" not in valid

    def test_gmx_pool_includes_perp_funding(self) -> None:
        # GMX is a hybrid protocol — its POOL legitimately carries perp_funding.
        valid = valid_data_types_for_venue_instrument_type("defi", "GMX-ARBITRUM", "pool")
        assert valid is not None
        assert "perp_funding" in valid
        assert "dex_pool_state" in valid

    def test_union_leaks_perp_funding_but_venue_grain_does_not(self) -> None:
        # Demonstrates the bug the refinement fixes: the instrument_type-grain
        # union DOES include perp_funding for ``pool`` (from GMX); the
        # venue-grain accessor removes it for a pure-DEX venue.
        union = valid_data_types_for_instrument_type("defi", "pool")
        assert union is not None and "perp_funding" in union
        uni = valid_data_types_for_venue_instrument_type("defi", "UNISWAP_V3-ETHEREUM", "pool")
        assert uni is not None and "perp_funding" not in uni

    def test_unmapped_protocol_falls_back_to_union(self) -> None:
        # An unknown protocol must NOT under-report — it delegates to the union.
        unknown = valid_data_types_for_venue_instrument_type("defi", "NOTAPROTOCOL-ETHEREUM", "pool")
        union = valid_data_types_for_instrument_type("defi", "pool")
        assert unknown == union

    def test_non_defi_delegates_unchanged(self) -> None:
        # For every non-DeFi asset_group the venue-aware accessor is identical
        # to the instrument_type-grain matrix (venue is ignored).
        for ag, venue, it in (
            ("cefi", "BINANCE-FUTURES", "perpetual"),
            ("tradfi", "CME", "future"),
        ):
            assert valid_data_types_for_venue_instrument_type(ag, venue, it) == valid_data_types_for_instrument_type(
                ag, it
            )

    def test_missing_venue_delegates_to_union(self) -> None:
        # A blank/None venue on a DeFi row cannot resolve a protocol → union.
        assert valid_data_types_for_venue_instrument_type("defi", None, "pool") == valid_data_types_for_instrument_type(
            "defi", "pool"
        )
