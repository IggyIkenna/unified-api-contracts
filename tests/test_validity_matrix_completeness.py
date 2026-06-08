"""Validity-matrix completeness + SOURCE_PRIORITY reachability test.

Converts a recurring agentic audit into a pinned, deterministic gate.

audit_criteria_automation_2026_06_08.md — Tier-2 P2

Covers four invariants:
1. SOURCE_PRIORITY reachability — every (asset_group, data_type) key in
   SOURCE_PRIORITY is reachable as a VALID (instrument_type, data_type)
   for at least one instrument_type of that asset_group in the validity
   matrix, OR is on the documented exclusion list.
2. No impossible pair enumerable — representative impossible combos per AG
   (e.g. PERPETUAL x options_chain, SPOT x funding_rate) are rejected by
   valid_data_types_for_instrument_type.
3. Era-B — for cefi/tradfi options_chain/futures_chain instrument_types,
   the valid data_type set is {"trades"} (cefi) or
   {"trades", "ohlcv_1m", "options_chain"} / {"trades", "ohlcv_1m", "tbbo"}
   (tradfi — T-OLD-2b PRESERVE), never data_type=options_chain/futures_chain
   for cefi bundles.
4. No silent fallback — every (asset_group, instrument_type) that can be
   enumerated either has an explicit entry in the matrix or returns None
   (the documented fallback to all/warn path, which the enumerator must
   not silently treat as "all data_types allowed").
"""

from __future__ import annotations

from unified_api_contracts.canonical.crosscutting.source_priority import (
    SOURCE_PRIORITY,
)
from unified_api_contracts.registry.market_data_categories import (
    DATA_TYPES_BY_ASSET_GROUP,
    VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE,
    valid_data_types_for_instrument_type,
)

# ---------------------------------------------------------------------------
# INVARIANT 1: SOURCE_PRIORITY reachability
# ---------------------------------------------------------------------------
#
# For each (ag, dt) key in SOURCE_PRIORITY, we need at least one instrument_type
# of that asset_group to have dt in its valid data_type set.
#
# EXCLUSION LIST: (asset_group, data_type) pairs that are registered in
# SOURCE_PRIORITY but whose data_type is NOT a member of ANY instrument_type's
# valid set because:
#
#   (a) COMPUTED / SERVICE emitters — their "data_type" is not a market-data
#       type enumerated by the catalogue (no instrument yields them).
#
#   (b) REFERENCE-group entries (asset_group="reference") — the reference AG
#       has no instrument_type matrix row (it is not a market-data category
#       that the enumerator seeds).
#
#   (c) CeFi LEGACY data_type keys retained only for the pre-migration rows —
#       perpetual / funding_rate / book_snapshot are instrument_type tokens or
#       aliases, not valid market-data data_types enumerated by the cefi catalogue.
#
#   (d) ERA-B DATA_TYPE ORPHANS — data_type keys in SOURCE_PRIORITY whose string
#       matches an INSTRUMENT_TYPE name (options_chain / futures_chain), not a
#       market-data row type. The Era-B invariant ensures the chain names are
#       instrument_types; data_type=options_chain / data_type=futures_chain are
#       pre-Era-B keys that have no instrument_type mapping in the current matrix.
#
#   (e) DeFi DATA_TYPES IN DATA_TYPES_BY_ASSET_GROUP but not yet mapped to any
#       instrument_type in PROTOCOL_CAPABILITIES — these are DeFi event/state
#       data types (bridge_events, staking_yields, etc.) that are in the AG
#       catalogue but have no PROTOCOL_CAPABILITIES instrument_type that
#       produces them yet (BLOCKED-UPSTREAM gap, not a logic error here).
#
#   (f) Sports reference/classification data_types in SOURCE_PRIORITY that are
#       NOT in SPORTS_DATA_TYPE_TO_SOURCE (the "league" instrument_type's valid
#       set). These are coarser catalogue types (LEAGUES, PLAYERS, VENUES, etc.)
#       that are tracked in SOURCE_PRIORITY but not enumerated via the
#       league-instrument grain.
#
#   (g) TradFi / DeFi computed pipeline outputs (commodity_signal,
#       commodity_features, energy_data) that are service/pipeline outputs
#       rather than instrument-day-grain market data types.
#
# If a pair is removed from this list without being present in the matrix, the
# test will fail loudly — that is the point.
#
_SOURCE_PRIORITY_INSTRUMENT_EXCLUSIONS: frozenset[tuple[str, str]] = frozenset(
    {
        # ── (b) Reference AG (no instrument matrix, not a market-data category) ──
        ("reference", "instruments"),
        ("reference", "venue_trading_calendar"),
        # ── (c) CeFi legacy data_type keys (pre-migration / not catalogue data_types) ──
        # "perpetual" and "funding_rate" are INSTRUMENT_TYPE tokens, not data_types;
        # "book_snapshot" is a legacy alias for "book_snapshot_5" (not in
        # DATA_TYPES_BY_ASSET_GROUP["cefi"]). These exist in SOURCE_PRIORITY for
        # the closed-set pipeline_mode round-trip; they carry no valid matrix entry.
        ("cefi", "perpetual"),
        ("cefi", "funding_rate"),
        ("cefi", "book_snapshot"),
        # ── (d) Era-B data_type orphans — instrument_type names masquerading as
        #    data_type keys in SOURCE_PRIORITY. The matrix only maps these as
        #    instrument_types, never as data_types:
        #       (cefi, options_chain): instrument_type -> data_type=trades; no cefi
        #           instrument has data_type=options_chain in its valid set.
        #       (cefi, futures_chain): same — instrument_type -> data_type=trades.
        #       (tradfi, futures_chain): instrument_type -> {trades, ohlcv_1m, tbbo};
        #           no tradfi instrument has data_type=futures_chain in its valid set.
        #    NOTE: (tradfi, options_chain) IS reachable — the tradfi options_chain
        #    INSTRUMENT_TYPE's frozenset includes data_type=options_chain per the
        #    T-OLD-2b PRESERVE decision (291 Era-A mark_iv/greeks snapshot rows).
        ("cefi", "options_chain"),
        ("cefi", "futures_chain"),
        ("tradfi", "futures_chain"),
        # ── (c) CeFi ohlcv_15m — in SOURCE_PRIORITY (tardis source) but no cefi
        #    instrument_type in the validity matrix admits ohlcv_15m. This is a
        #    gap between SOURCE_PRIORITY and the cefi matrix (tradfi has ohlcv_15m
        #    but cefi does not). Tracked as an exclusion until the cefi matrix
        #    adds ohlcv_15m to the appropriate instrument_type's valid set.
        ("cefi", "ohlcv_15m"),
        # ── (a) CeFi computed service outputs ──
        ("cefi", "execution_fills"),
        ("cefi", "cross_instrument"),
        ("cefi", "cross_instrument_features"),
        # ── (a) DeFi computed/service outputs (no instrument produces these) ──
        ("defi", "execution_fills"),
        ("defi", "hedge_ratio_snapshot"),
        ("defi", "strategy_decision_context"),
        ("defi", "feature_observation_snapshot"),
        ("defi", "cross_instrument_signal"),
        # ── (e) DeFi data_types in DATA_TYPES_BY_ASSET_GROUP but not yet mapped
        #    to any PROTOCOL_CAPABILITIES instrument_type (BLOCKED-UPSTREAM gap).
        #    These are valid DeFi event/state data types that exist in the AG
        #    catalogue but the instrument_type matrix has not been extended to
        #    cover them yet. They should be added to the appropriate
        #    PROTOCOL_CAPABILITIES instrument_type once the mapping is decided.
        ("defi", "bridge_events"),
        ("defi", "eigenlayer_rewards"),
        ("defi", "flash_loan_events"),
        ("defi", "governance_events"),
        ("defi", "liquidation_events"),
        ("defi", "mev_events"),
        ("defi", "native_staking_rates"),
        ("defi", "position_data"),
        ("defi", "staking_yields"),
        ("defi", "token_transfers"),
        ("defi", "vault_share_price"),
        # ── (a) DeFi data_types in SOURCE_PRIORITY but NOT in DATA_TYPES_BY_ASSET_GROUP
        #    (internal protocol-specific outputs or feature-layer constructs):
        ("defi", "swap"),
        ("defi", "fx_rate"),
        ("defi", "liquidity"),
        ("defi", "market_state"),
        ("defi", "lst_yields"),  # canonical name is lst_rates, not lst_yields
        ("defi", "vault_state"),
        ("defi", "solana_defi"),
        # ── (g) TradFi computed / pipeline outputs (not instrument-grain) ──
        ("tradfi", "commodity_signal"),
        ("tradfi", "commodity_features"),
        ("tradfi", "energy_data"),
        # ── (a) Prediction ──
        # "book_snapshot" is a legacy/non-canonical key in SOURCE_PRIORITY
        # (prediction catalogue only carries "trades" and the prediction types).
        ("prediction", "book_snapshot"),
        # ── (f) Sports reference/classification data_types in SOURCE_PRIORITY
        #    that are NOT in SPORTS_DATA_TYPE_TO_SOURCE (not reachable via the
        #    "league" instrument_type's derived valid set). These are coarser
        #    catalogue data_types tracked in SOURCE_PRIORITY but not enumerated
        #    at instrument grain (e.g. competition-level metadata like LEAGUES,
        #    entity catalogues like PLAYERS/VENUES, computed outputs like ARBITRAGE,
        #    and temporal variants like ODDS_SNAPSHOT/ODDS_MOVEMENT/WEATHER_FORECAST).
        ("sports", "ARBITRAGE"),
        ("sports", "FIXTURE_PLAYER_STATS"),
        ("sports", "LEAGUES"),
        ("sports", "ODDS_MOVEMENT"),
        ("sports", "ODDS_SNAPSHOT"),
        ("sports", "PLAYERS"),
        ("sports", "RESULTS"),
        ("sports", "TRANSFER_RECORDS"),
        ("sports", "UNDERSTAT_XG"),
        ("sports", "VENUES"),
        ("sports", "WEATHER_FORECAST"),
    }
)


def _build_reachable_set_for_ag(asset_group: str) -> set[str]:
    """Return the union of all valid data_types across every instrument_type
    that has a non-None, non-empty entry in the validity matrix for this AG.

    For DeFi the matrix is derived lazily from PROTOCOL_CAPABILITIES; for
    Sports the "league" type is derived from SPORTS_DATA_TYPE_TO_SOURCE.
    We call the public accessor (valid_data_types_for_instrument_type) for
    the known instrument_types of that AG, then for DeFi we also iterate
    the PROTOCOL_CAPABILITIES instrument_types.
    """
    reachable: set[str] = set()

    # Static matrix keys for this AG
    for ag_key, it_key in VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE:
        if ag_key == asset_group:
            valid = valid_data_types_for_instrument_type(asset_group, it_key)
            if valid:
                reachable.update(valid)

    # DeFi: derived from PROTOCOL_CAPABILITIES (not in the static dict)
    if asset_group == "defi":
        from unified_api_contracts.registry.capability_declarations._defi import (
            PROTOCOL_CAPABILITIES,
        )

        for cap in PROTOCOL_CAPABILITIES.values():
            for it in cap.instrument_types:
                valid = valid_data_types_for_instrument_type("defi", it)
                if valid:
                    reachable.update(valid)

    # Sports: "league" instrument_type is derived at accessor level
    if asset_group == "sports":
        league_valid = valid_data_types_for_instrument_type("sports", "league")
        if league_valid:
            reachable.update(league_valid)

    # Prediction: the static dict has "prediction_market" row
    if asset_group == "prediction":
        pm_valid = valid_data_types_for_instrument_type("prediction", "prediction_market")
        if pm_valid:
            reachable.update(pm_valid)

    return reachable


class TestSourcePriorityReachability:
    """Every SOURCE_PRIORITY (ag, dt) key is reachable from the validity matrix.

    Catches orphan SOURCE_PRIORITY entries whose data_type no instrument_type
    can ever produce — an impossible cell that would silently inflate completion%.
    """

    def test_all_source_priority_pairs_reachable_or_excluded(self) -> None:
        """Every SOURCE_PRIORITY key is reachable from the validity matrix
        (i.e. at least one instrument_type of that AG has it in its valid set),
        OR it is on the documented exclusion list.

        Any entry that is NOT in the reachability union AND NOT in the exclusion
        list represents an orphan SOURCE_PRIORITY entry that no instrument can
        produce — a potential data-correctness gap.
        """
        orphans: list[tuple[str, str]] = []

        # Group SP keys by asset_group for efficient reachability queries
        sp_by_ag: dict[str, set[str]] = {}
        for ag, dt in SOURCE_PRIORITY:
            sp_by_ag.setdefault(ag, set()).add(dt)

        for ag, data_types in sp_by_ag.items():
            reachable = _build_reachable_set_for_ag(ag)
            for dt in sorted(data_types):
                key = (ag, dt)
                if key in _SOURCE_PRIORITY_INSTRUMENT_EXCLUSIONS:
                    continue  # explicitly excluded — skip
                if dt not in reachable:
                    orphans.append(key)

        assert not orphans, (
            f"SOURCE_PRIORITY pairs unreachable from the validity matrix "
            f"(not in any instrument_type's valid data_type set AND not in "
            f"_SOURCE_PRIORITY_INSTRUMENT_EXCLUSIONS): {sorted(orphans)}. "
            "Either (a) add the data_type to the appropriate instrument_type's "
            "frozenset in VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE, "
            "(b) add the pair to _SOURCE_PRIORITY_INSTRUMENT_EXCLUSIONS if it is "
            "a computed/service/reference output, or (c) investigate whether the "
            "SOURCE_PRIORITY entry itself is stale."
        )

    def test_exclusion_list_entries_are_all_in_source_priority(self) -> None:
        """Every entry in _SOURCE_PRIORITY_INSTRUMENT_EXCLUSIONS must actually
        exist in SOURCE_PRIORITY — prevents the exclusion list itself from going
        stale when SOURCE_PRIORITY entries are removed.
        """
        stale_exclusions = [key for key in _SOURCE_PRIORITY_INSTRUMENT_EXCLUSIONS if key not in SOURCE_PRIORITY]
        assert not stale_exclusions, (
            f"Entries in _SOURCE_PRIORITY_INSTRUMENT_EXCLUSIONS that are no "
            f"longer in SOURCE_PRIORITY (stale exclusions): {sorted(stale_exclusions)}. "
            "Remove them from the exclusion list."
        )


# ---------------------------------------------------------------------------
# INVARIANT 2: No impossible pair enumerable (representative combos per AG)
# ---------------------------------------------------------------------------


class TestImpossiblePairsNotEnumerable:
    """Representative impossible (instrument_type x data_type) combos are
    rejected by valid_data_types_for_instrument_type.

    These are verified against the actual matrix — not assumed. If any of
    these start returning a non-empty set, the test catches the over-fan.
    """

    def test_cefi_spot_does_not_include_derivative_ticker(self) -> None:
        """SPOT has no funding / derivative ticker — that is a PERPETUAL type."""
        result = valid_data_types_for_instrument_type("cefi", "spot_pair")
        assert result is not None
        assert "derivative_ticker" not in result, "spot_pair should NOT have derivative_ticker (a perpetual-only type)"

    def test_cefi_spot_does_not_include_liquidations(self) -> None:
        """SPOT positions cannot be liquidated in the same sense as perps."""
        result = valid_data_types_for_instrument_type("cefi", "spot_pair")
        assert result is not None
        assert "liquidations" not in result

    def test_cefi_perpetual_does_not_include_options_chain(self) -> None:
        """PERPETUAL instrument is NOT an options chain bundle."""
        result = valid_data_types_for_instrument_type("cefi", "perpetual")
        assert result is not None
        assert "options_chain" not in result, "(cefi, perpetual) should NOT include options_chain as a data_type"

    def test_cefi_perpetual_does_not_include_futures_chain(self) -> None:
        """PERPETUAL instrument is NOT a futures chain bundle."""
        result = valid_data_types_for_instrument_type("cefi", "perpetual")
        assert result is not None
        assert "futures_chain" not in result

    def test_cefi_option_leaf_yields_no_rows(self) -> None:
        """A leaf OPTION contract rolls up to the options_chain bundle —
        the enumerator must emit ZERO per-contract rows for it.
        """
        result = valid_data_types_for_instrument_type("cefi", "option")
        assert result == frozenset(), (
            "(cefi, option) must be frozenset() — leaf options roll up to "
            "the per-underlying options_chain bundle (Era-B)"
        )

    def test_cefi_combo_leaf_yields_no_rows(self) -> None:
        """Same as option leaf — combo rolls up to the options_chain bundle."""
        result = valid_data_types_for_instrument_type("cefi", "combo")
        assert result == frozenset()

    def test_tradfi_option_leaf_yields_no_rows(self) -> None:
        """TradFi leaf OPTION — frozenset() (generalised Era-B)."""
        result = valid_data_types_for_instrument_type("tradfi", "option")
        assert result == frozenset(), (
            "(tradfi, option) must be frozenset() — leaf options roll up to the per-underlying options_chain bundle"
        )

    def test_tradfi_combo_leaf_yields_no_rows(self) -> None:
        """TradFi leaf COMBO — frozenset()."""
        result = valid_data_types_for_instrument_type("tradfi", "combo")
        assert result == frozenset()

    def test_tradfi_index_has_no_trades(self) -> None:
        """TradFi INDEX instruments (e.g. VIX) are OHLCV-only — no trade data."""
        result = valid_data_types_for_instrument_type("tradfi", "index")
        assert result is not None
        assert "trades" not in result, (
            "(tradfi, index) must not include trades — index instruments have no per-trade tick data"
        )

    def test_tradfi_equity_has_no_macro_result(self) -> None:
        """macro_result is a macro-economic data_type, not an equity data_type."""
        result = valid_data_types_for_instrument_type("tradfi", "equity")
        assert result is not None
        # macro_result belongs to no instrument_type in the tradfi matrix
        assert "macro_result" not in result, (
            "(tradfi, equity) must not include macro_result — macroeconomic data is not an instrument-level data_type"
        )

    def test_cefi_spot_does_not_include_dex_data(self) -> None:
        """CeFi SPOT instrument does NOT produce DeFi-specific data types."""
        result = valid_data_types_for_instrument_type("cefi", "spot_pair")
        assert result is not None
        defi_types = {"dex_pool_state", "dex_pool_swaps", "lending_indices", "lst_rates"}
        overlap = defi_types & result
        assert not overlap, f"(cefi, spot_pair) must not include DeFi types: {overlap}"


# ---------------------------------------------------------------------------
# INVARIANT 3: Era-B — chain bundle instrument_types carry trades, not chain names
# ---------------------------------------------------------------------------


class TestEraBChainBundles:
    """Era-B (operator 2026-06-07): options_chain / futures_chain are
    INSTRUMENT_TYPES (per-underlying bundles), not data_types.

    For cefi: their market data_type is EXACTLY {"trades"}.
    For tradfi: T-OLD-2b PRESERVE (operator 2026-06-08) — the bundles admit
    the actually-captured data_types (wider than just "trades" for tradfi).
    """

    def test_cefi_options_chain_instrument_type_is_trades_only(self) -> None:
        """cefi options_chain INSTRUMENT_TYPE maps to data_type=trades only (Era-B)."""
        result = valid_data_types_for_instrument_type("cefi", "options_chain")
        assert result == frozenset({"trades"}), (
            "(cefi, options_chain) instrument_type must map to data_type=trades ONLY "
            "(Era-B: the chain name is the instrument_type; market data_type is trades)"
        )

    def test_cefi_futures_chain_instrument_type_is_trades_only(self) -> None:
        """cefi futures_chain INSTRUMENT_TYPE maps to data_type=trades only (Era-B)."""
        result = valid_data_types_for_instrument_type("cefi", "futures_chain")
        assert result == frozenset({"trades"}), (
            "(cefi, futures_chain) instrument_type must map to data_type=trades ONLY"
        )

    def test_cefi_options_chain_data_type_not_in_bundle_set(self) -> None:
        """The string 'options_chain' must NOT appear as a data_type in the
        cefi options_chain bundle's valid set — that would be the old Era-A overload.
        """
        result = valid_data_types_for_instrument_type("cefi", "options_chain")
        assert result is not None
        assert "options_chain" not in result, (
            "'options_chain' must not appear as a data_type inside the "
            "(cefi, options_chain) INSTRUMENT_TYPE's valid set (Era-B)"
        )

    def test_cefi_futures_chain_data_type_not_in_bundle_set(self) -> None:
        """The string 'futures_chain' must NOT appear as a data_type in the
        cefi futures_chain bundle's valid set.
        """
        result = valid_data_types_for_instrument_type("cefi", "futures_chain")
        assert result is not None
        assert "futures_chain" not in result

    def test_tradfi_options_chain_instrument_type_includes_trades(self) -> None:
        """tradfi options_chain INSTRUMENT_TYPE includes trades (T-OLD-2b PRESERVE)."""
        result = valid_data_types_for_instrument_type("tradfi", "options_chain")
        assert result is not None
        assert "trades" in result

    def test_tradfi_options_chain_includes_snapshot_data_type(self) -> None:
        """tradfi options_chain INSTRUMENT_TYPE includes data_type=options_chain
        (the mark_iv/greeks chain snapshot — 291 Era-A rows preserved per T-OLD-2b).
        """
        result = valid_data_types_for_instrument_type("tradfi", "options_chain")
        assert result is not None
        assert "options_chain" in result, (
            "(tradfi, options_chain) INSTRUMENT_TYPE must include data_type=options_chain "
            "to preserve the 291 Era-A mark_iv/greeks snapshot rows (T-OLD-2b PRESERVE)"
        )

    def test_tradfi_futures_chain_includes_trades_ohlcv_tbbo(self) -> None:
        """tradfi futures_chain INSTRUMENT_TYPE: trades / ohlcv_1m / tbbo present."""
        result = valid_data_types_for_instrument_type("tradfi", "futures_chain")
        assert result is not None
        assert "trades" in result
        assert "ohlcv_1m" in result
        assert "tbbo" in result

    def test_tradfi_futures_chain_does_not_include_futures_chain_data_type(self) -> None:
        """tradfi futures_chain INSTRUMENT_TYPE must NOT include data_type=futures_chain
        (no snapshot data_type observed for the futures_chain bundle on tradfi disk).
        """
        result = valid_data_types_for_instrument_type("tradfi", "futures_chain")
        assert result is not None
        assert "futures_chain" not in result, (
            "(tradfi, futures_chain) INSTRUMENT_TYPE must not include data_type=futures_chain "
            "(no snapshot captured on tradfi disk; would over-fan)"
        )


# ---------------------------------------------------------------------------
# INVARIANT 4: No silent fallback — unmapped (ag, it) must return None,
#              never silently fall back to "all data_types"
# ---------------------------------------------------------------------------


class TestNoSilentFallback:
    """The accessor returns None for unmapped (ag, instrument_type) entries.

    This is the critical guard against the ~563K-false-candidate bug class:
    a pre-G1-ENUM enumerator that treated None as "all data_types allowed"
    would fan out every instrument across ALL data_types (the wrong default).

    None = "caller must warn + not enumerate" — the enumerator must handle
    this explicitly, never silently treat None as "all".
    """

    def test_unknown_cefi_instrument_type_returns_none(self) -> None:
        result = valid_data_types_for_instrument_type("cefi", "NONEXISTENT_XYZ")
        assert result is None, (
            "An unknown instrument_type must return None (not a frozenset of "
            "all data_types) so the enumerator can warn + skip it."
        )

    def test_unknown_tradfi_instrument_type_returns_none(self) -> None:
        result = valid_data_types_for_instrument_type("tradfi", "NONEXISTENT_XYZ")
        assert result is None

    def test_unknown_asset_group_returns_none_for_known_instrument_type(self) -> None:
        result = valid_data_types_for_instrument_type("unknown_ag", "spot_pair")
        assert result is None

    def test_known_ags_with_explicitly_mapped_instrument_types_return_frozensets(self) -> None:
        """Spot-check that known (ag, it) pairs return frozenset (not None)."""
        checks: list[tuple[str, str]] = [
            ("cefi", "spot_pair"),
            ("cefi", "perpetual"),
            ("cefi", "options_chain"),
            ("cefi", "futures_chain"),
            ("tradfi", "equity"),
            ("tradfi", "etf"),
            ("tradfi", "future"),
            ("tradfi", "options_chain"),
            ("tradfi", "futures_chain"),
            ("tradfi", "index"),
        ]
        for ag, it in checks:
            result = valid_data_types_for_instrument_type(ag, it)
            assert isinstance(result, frozenset), (
                f"({ag!r}, {it!r}) is a known mapped pair but returned {result!r}; expected a frozenset"
            )

    def test_leaf_bundle_types_return_empty_frozenset_not_none(self) -> None:
        """Leaf option/combo types return frozenset() (explicitly empty — zero rows),
        NOT None (which would trigger the all-data_types fallback).

        frozenset() = "enumerator must skip all rows" (intentional zero fan-out).
        None = "unmapped — warn and fall back to all".
        These are semantically different.
        """
        leaf_types = [
            ("cefi", "option"),
            ("cefi", "combo"),
            ("tradfi", "option"),
            ("tradfi", "combo"),
        ]
        for ag, it in leaf_types:
            result = valid_data_types_for_instrument_type(ag, it)
            assert result == frozenset(), (
                f"({ag!r}, {it!r}) must return frozenset() (zero per-leaf rows, Era-B bundle roll-up), not None"
            )

    def test_matrix_all_values_are_frozensets_of_valid_ag_data_types(self) -> None:
        """Every value in VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE is a frozenset
        containing only data_types that appear in DATA_TYPES_BY_ASSET_GROUP for
        the given asset_group, OR is the empty frozenset (bundle-grain skip).

        Catches typos in the matrix where a data_type string is misspelled and
        would silently produce zero manifest rows without an error.

        Documented exceptions (not violations):
          - (tradfi, options_chain) includes data_type='options_chain' which is
            NOT in DATA_TYPES_BY_ASSET_GROUP["tradfi"] — T-OLD-2b PRESERVE decision
            (291 Era-A mark_iv/greeks chain snapshot rows; the data_type name matches
            the instrument_type name by design for the snapshot-level tradfi data).
        """
        # Documented exceptions: (ag, it, dt) triples that are intentional
        # schema decisions, not typos:
        _EXCEPTIONS: frozenset[tuple[str, str, str]] = frozenset(
            {
                # T-OLD-2b PRESERVE: tradfi options_chain instrument_type includes
                # data_type=options_chain (mark_iv/greeks chain snapshot — 291 rows).
                ("tradfi", "options_chain", "options_chain"),
            }
        )

        violations: list[tuple[str, str, str]] = []
        for (ag, it), valid_set in VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE.items():
            if not valid_set:
                continue  # empty frozenset = bundle-grain skip, valid by design
            ag_data_types = set(DATA_TYPES_BY_ASSET_GROUP.get(ag, []))
            for dt in valid_set:
                triple = (ag, it, dt)
                if triple in _EXCEPTIONS:
                    continue
                if dt not in ag_data_types:
                    violations.append(triple)

        assert not violations, (
            f"data_types in VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE that are NOT "
            f"in DATA_TYPES_BY_ASSET_GROUP for their asset_group (likely typos): "
            f"{violations}. "
            "Either add the data_type to DATA_TYPES_BY_ASSET_GROUP, fix the typo, or "
            "add a documented exception triple to _EXCEPTIONS above."
        )
