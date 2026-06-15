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
# valid set.  Every exclusion carries a typed reason constant defined below.
#
# Reason taxonomy (closed set):
#
#   COMPUTED_SERVICE_OUTPUT — data_type is a pipeline/strategy/execution service
#       output (e.g. execution_fills, hedge_ratio_snapshot).  Not produced by any
#       market-data instrument_type in the catalogue.
#
#   REFERENCE_AG_NO_MATRIX — the "reference" asset_group has no instrument_type
#       matrix row; it is not a market-data category the enumerator seeds.
#
#   CEFI_LEGACY_KEY — "perpetual", "funding_rate", and "book_snapshot" are
#       instrument_type tokens or legacy aliases — NOT valid market-data
#       data_types in DATA_TYPES_BY_ASSET_GROUP["cefi"].  Retained in
#       SOURCE_PRIORITY for the closed-set pipeline_mode round-trip only.
#
#   ERA_B_LEGACY_RETAINED — data_type string matches an INSTRUMENT_TYPE name
#       (options_chain / futures_chain).  Era-B (operator 2026-06-07) clarified
#       these are instrument_types, not data_types.  The SOURCE_PRIORITY rows are
#       RETAINED BY DESIGN for pre-migration manifest rows and SOURCE_PRIORITY ↔
#       availability round-trips.  SSOT:
#       master_data_canonicalisation_migration_catalogue_2026_06_07.md.
#
#   BLOCKED_UPSTREAM_CAPABILITY — DeFi data_types that exist in
#       DATA_TYPES_BY_ASSET_GROUP["defi"] but no PROTOCOL_CAPABILITIES
#       instrument_type declares them as producible yet.  Gap is in the
#       protocol capability declaration, not in the validity matrix logic.
#       Re-classify to WIRED (remove from this list) once a protocol's
#       _ProtocolCapability.data_types list is extended.
#
#   REFERENCE_NOT_INSTRUMENT_GRAIN — sports data_types that represent entity
#       catalogues, competition-level metadata, or aggregated/derived outputs
#       (LEAGUES, PLAYERS, VENUES, ARBITRAGE, RESULTS, etc.).  Not enumerated
#       at per-instrument (league) grain via SPORTS_DATA_TYPE_TO_SOURCE;
#       tracked in SOURCE_PRIORITY for reference-layer provenance only.
#
#   CEFI_MATRIX_GAP — data_type exists in SOURCE_PRIORITY for a cefi source
#       but no cefi instrument_type in the validity matrix produces it.
#       Not a logic error; marks a gap between SOURCE_PRIORITY and the cefi
#       matrix that should be resolved by either adding the data_type to
#       an instrument_type frozenset (if genuinely producible) or demoting the
#       SOURCE_PRIORITY entry.
#
# If a pair is removed from this list without being present in the matrix, the
# test will fail loudly — that is the point.
#

# Typed reason constants — each exclusion entry cites exactly one.
_COMPUTED_SERVICE_OUTPUT = "COMPUTED_SERVICE_OUTPUT"
_REFERENCE_AG_NO_MATRIX = "REFERENCE_AG_NO_MATRIX"
_CEFI_LEGACY_KEY = "CEFI_LEGACY_KEY"
_ERA_B_LEGACY_RETAINED = "ERA_B_LEGACY_RETAINED"
_BLOCKED_UPSTREAM_CAPABILITY = "BLOCKED_UPSTREAM_CAPABILITY"
_REFERENCE_NOT_INSTRUMENT_GRAIN = "REFERENCE_NOT_INSTRUMENT_GRAIN"
_CEFI_MATRIX_GAP = "CEFI_MATRIX_GAP"
# PENDING_SNAPSHOT_SLICE — options_chain / futures_chain SOURCE_PRIORITY entries
#     retained for cefi/tradfi pending the per-AG instrument_type snapshot slice
#     widening (slot-3 widens cefi futures_chain to admit data_type=options_chain;
#     tradfi options_chain/futures_chain retain their legacy Era-A snapshot rows).
#     Supersedes ERA_B_LEGACY_RETAINED for these three pairs: the Era-B context
#     is accurate but the PENDING framing better conveys the actionable gap
#     (adding the snapshot data_type to the instrument_type frozenset unblocks them).
_PENDING_SNAPSHOT_SLICE = "PENDING_SNAPSHOT_SLICE"

# Mapping: (asset_group, data_type) → reason constant.
# Every exclusion MUST carry a reason; the test
# ``test_every_exclusion_has_typed_reason`` enforces this.
_SOURCE_PRIORITY_EXCLUSION_REASONS: dict[tuple[str, str], str] = {
    # ── Reference AG (no instrument matrix, not a market-data category) ──
    ("reference", "instruments"): _REFERENCE_AG_NO_MATRIX,
    ("reference", "venue_trading_calendar"): _REFERENCE_AG_NO_MATRIX,
    # ── CeFi legacy data_type keys (pre-migration / not catalogue data_types) ──
    # "perpetual" and "funding_rate" are INSTRUMENT_TYPE tokens, not data_types;
    # "book_snapshot" is a legacy alias for "book_snapshot_5" (not in
    # DATA_TYPES_BY_ASSET_GROUP["cefi"]). These exist in SOURCE_PRIORITY for
    # the closed-set pipeline_mode round-trip; they carry no valid matrix entry.
    ("cefi", "perpetual"): _CEFI_LEGACY_KEY,
    ("cefi", "funding_rate"): _CEFI_LEGACY_KEY,
    ("cefi", "book_snapshot"): _CEFI_LEGACY_KEY,
    # ── Pending snapshot slice — options_chain / futures_chain SOURCE_PRIORITY
    #    entries retained while the per-AG instrument_type snapshot slice widens.
    #    These are instrument_types in the matrix but the slot-3 scope adds the
    #    snapshot data_type to the frozenset (e.g. cefi futures_chain admits
    #    data_type=options_chain for the Deribit greeks snapshot; tradfi
    #    options_chain/futures_chain retain their Era-A snapshot rows pending
    #    the per-AG v8→v9 relabel). Remove each once the slice is widened.
    #    NOTE: (tradfi, options_chain) IS already reachable — the tradfi
    #    options_chain INSTRUMENT_TYPE's frozenset includes data_type=options_chain
    #    per the T-OLD-2b PRESERVE decision (291 Era-A mark_iv/greeks rows).
    ("cefi", "options_chain"): _PENDING_SNAPSHOT_SLICE,
    ("cefi", "futures_chain"): _PENDING_SNAPSHOT_SLICE,
    ("tradfi", "futures_chain"): _PENDING_SNAPSHOT_SLICE,
    # ── CeFi computed service outputs ──
    ("cefi", "execution_fills"): _COMPUTED_SERVICE_OUTPUT,
    ("cefi", "cross_instrument"): _COMPUTED_SERVICE_OUTPUT,
    ("cefi", "cross_instrument_features"): _COMPUTED_SERVICE_OUTPUT,
    # greeks-service computed outputs (in-house BS greeks + IV surface from the
    # canonical options_chain) — not produced by any market-data instrument_type.
    ("cefi", "greeks_snapshot"): _COMPUTED_SERVICE_OUTPUT,
    ("cefi", "implied_vol_surface"): _COMPUTED_SERVICE_OUTPUT,
    ("tradfi", "greeks_snapshot"): _COMPUTED_SERVICE_OUTPUT,
    ("tradfi", "implied_vol_surface"): _COMPUTED_SERVICE_OUTPUT,
    # ── DeFi computed/service outputs (no instrument produces these) ──
    ("defi", "execution_fills"): _COMPUTED_SERVICE_OUTPUT,
    ("defi", "hedge_ratio_snapshot"): _COMPUTED_SERVICE_OUTPUT,
    ("defi", "strategy_decision_context"): _COMPUTED_SERVICE_OUTPUT,
    ("defi", "feature_observation_snapshot"): _COMPUTED_SERVICE_OUTPUT,
    ("defi", "cross_instrument_signal"): _COMPUTED_SERVICE_OUTPUT,
    # ── DeFi data_types in DATA_TYPES_BY_ASSET_GROUP but not yet mapped
    #    to any PROTOCOL_CAPABILITIES instrument_type (BLOCKED-UPSTREAM gap).
    #    Valid DeFi event/state data types that exist in the AG catalogue but
    #    the instrument_type matrix has not been extended to cover them yet.
    #    Remove from this list once a _ProtocolCapability.data_types entry
    #    is added for the appropriate instrument_type.
    #
    #    Wired 2026-06-09 (operator-directed; venue-evidence in
    #    DEFI_VENUE_DATA_TYPE_CAPABILITIES for each):
    #      bridge_events, eigenlayer_rewards, flash_loan_events, governance_events,
    #      liquidation_events, mev_events, position_data, staking_yields, token_transfers
    #
    #    Remaining no-producer gaps (not in DEFI_VENUE_DATA_TYPE_CAPABILITIES):
    ("defi", "native_staking_rates"): _BLOCKED_UPSTREAM_CAPABILITY,  # Solana RPC not yet a protocol capability
    ("defi", "vault_share_price"): _BLOCKED_UPSTREAM_CAPABILITY,  # ERC-4626 share-price — no venue evidence
    # ── DeFi data_types in SOURCE_PRIORITY but NOT in DATA_TYPES_BY_ASSET_GROUP
    #    (internal protocol-specific outputs or feature-layer constructs that
    #    bypassed the AG catalogue).  These are COMPUTED_SERVICE_OUTPUT or
    #    protocol-internal aliases.
    ("defi", "swap"): _COMPUTED_SERVICE_OUTPUT,
    ("defi", "fx_rate"): _COMPUTED_SERVICE_OUTPUT,
    ("defi", "liquidity"): _COMPUTED_SERVICE_OUTPUT,
    ("defi", "market_state"): _COMPUTED_SERVICE_OUTPUT,
    ("defi", "lst_yields"): _COMPUTED_SERVICE_OUTPUT,  # canonical name is lst_rates
    ("defi", "vault_state"): _COMPUTED_SERVICE_OUTPUT,
    ("defi", "solana_defi"): _COMPUTED_SERVICE_OUTPUT,
    # ── TradFi computed / pipeline outputs (not instrument-grain market data) ──
    ("tradfi", "commodity_signal"): _COMPUTED_SERVICE_OUTPUT,
    ("tradfi", "commodity_features"): _COMPUTED_SERVICE_OUTPUT,
    ("tradfi", "energy_data"): _COMPUTED_SERVICE_OUTPUT,
    # ── Prediction ──
    # "book_snapshot" is a legacy/non-canonical key in SOURCE_PRIORITY
    # (prediction catalogue only carries "trades" and the prediction types).
    ("prediction", "book_snapshot"): _CEFI_LEGACY_KEY,
    # ── Sports reference/classification data_types in SOURCE_PRIORITY
    #    that are NOT in SPORTS_DATA_TYPE_TO_SOURCE (not reachable via the
    #    "league" instrument_type's derived valid set).
    #    These are competition-level metadata (LEAGUES), entity catalogues
    #    (PLAYERS, VENUES), results/transfer records, computed arbitrage
    #    outputs, temporal odds variants (ODDS_SNAPSHOT, ODDS_MOVEMENT),
    #    and weather forecast data — tracked in SOURCE_PRIORITY for
    #    reference-layer provenance but not enumerated at instrument grain.
    ("sports", "ARBITRAGE"): _REFERENCE_NOT_INSTRUMENT_GRAIN,
    ("sports", "FIXTURE_PLAYER_STATS"): _REFERENCE_NOT_INSTRUMENT_GRAIN,
    ("sports", "LEAGUES"): _REFERENCE_NOT_INSTRUMENT_GRAIN,
    ("sports", "ODDS_MOVEMENT"): _REFERENCE_NOT_INSTRUMENT_GRAIN,
    ("sports", "ODDS_SNAPSHOT"): _REFERENCE_NOT_INSTRUMENT_GRAIN,
    ("sports", "PLAYERS"): _REFERENCE_NOT_INSTRUMENT_GRAIN,
    ("sports", "RESULTS"): _REFERENCE_NOT_INSTRUMENT_GRAIN,
    ("sports", "TRANSFER_RECORDS"): _REFERENCE_NOT_INSTRUMENT_GRAIN,
    ("sports", "UNDERSTAT_XG"): _REFERENCE_NOT_INSTRUMENT_GRAIN,
    ("sports", "VENUES"): _REFERENCE_NOT_INSTRUMENT_GRAIN,
    ("sports", "WEATHER_FORECAST"): _REFERENCE_NOT_INSTRUMENT_GRAIN,
}

# Derived frozenset for O(1) membership checks in the reachability test.
_SOURCE_PRIORITY_INSTRUMENT_EXCLUSIONS: frozenset[tuple[str, str]] = frozenset(_SOURCE_PRIORITY_EXCLUSION_REASONS)


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

    def test_every_exclusion_has_typed_reason(self) -> None:
        """Every entry in _SOURCE_PRIORITY_INSTRUMENT_EXCLUSIONS must have
        a typed reason in _SOURCE_PRIORITY_EXCLUSION_REASONS.

        Prevents anonymous exclusions (bare frozenset entries with only a
        comment) from accumulating.  Every (ag, dt) pair that cannot be
        wired into the validity matrix must carry one of the closed-set
        reason constants, making the rationale machine-readable and
        auditable.
        """
        _VALID_REASONS = {
            _COMPUTED_SERVICE_OUTPUT,
            _REFERENCE_AG_NO_MATRIX,
            _CEFI_LEGACY_KEY,
            _ERA_B_LEGACY_RETAINED,
            _BLOCKED_UPSTREAM_CAPABILITY,
            _REFERENCE_NOT_INSTRUMENT_GRAIN,
            _CEFI_MATRIX_GAP,
            _PENDING_SNAPSHOT_SLICE,
        }

        # Every exclusion key must appear in the reasons dict.
        missing_reason = [
            key
            for key in sorted(_SOURCE_PRIORITY_INSTRUMENT_EXCLUSIONS)
            if key not in _SOURCE_PRIORITY_EXCLUSION_REASONS
        ]
        assert not missing_reason, (
            f"Exclusion entries without a typed reason in "
            f"_SOURCE_PRIORITY_EXCLUSION_REASONS: {missing_reason}. "
            "Add an entry to _SOURCE_PRIORITY_EXCLUSION_REASONS for each."
        )

        # Every reason value must be a recognised constant.
        unknown_reasons = [
            (key, reason) for key, reason in _SOURCE_PRIORITY_EXCLUSION_REASONS.items() if reason not in _VALID_REASONS
        ]
        assert not unknown_reasons, (
            f"Unrecognised reason values in _SOURCE_PRIORITY_EXCLUSION_REASONS: "
            f"{unknown_reasons}. "
            f"Use one of the defined constants: {sorted(_VALID_REASONS)}."
        )

        # The reasons dict must not have entries missing from the exclusion set
        # (would indicate a reason entry was added without its matching exclusion).
        extra_reason_keys = [
            key for key in _SOURCE_PRIORITY_EXCLUSION_REASONS if key not in _SOURCE_PRIORITY_INSTRUMENT_EXCLUSIONS
        ]
        assert not extra_reason_keys, (
            f"Keys in _SOURCE_PRIORITY_EXCLUSION_REASONS not present in "
            f"_SOURCE_PRIORITY_INSTRUMENT_EXCLUSIONS: {sorted(extra_reason_keys)}. "
            "Sync both dicts."
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
