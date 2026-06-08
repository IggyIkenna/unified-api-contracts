"""Per-(asset_group, data_type) source priority registry.

SSOT for the ordered list of source keys that may serve a given
``(asset_group, data_type)``. The top entry is the primary — the source
whose emission time defines ``available_at`` for live and batch (per the
workspace ``Live = batch`` rule).

Per the workspace CLAUDE.md ``Live = batch — same data, same fields,
same timing semantics, different sources OK`` rule:

> Historical writes MUST be timestamped with the ``available_at`` we'd
> actually have in live mode (the ``SOURCE_PRIORITY`` top entry's
> emission time, NOT the canonical historical source's slower archive
> time).

Phase 2 (multi-source merge) is implemented in
``plans/active/tradfi_massive_dual_source_2026_05_28.md`` (archived once
complete). The helpers :func:`get_all_sources_with_priority`,
:func:`select_primary_available_source`, and
:func:`detect_dual_source_conflicts` land the merge-logic building blocks.
The ``multi_source_priority_merge_2026_*`` placeholder is resolved.

Tie-breaker rules (when multiple sources are listed):

1. **Timestamp-availability** — sources that emit at live-time win over
   archive-only sources.
2. **Coverage** — sources with broader date / instrument coverage win.
3. **Information richness** — sources with more fields per row win.
4. **Merge-different-fields** — when two sources cover non-overlapping
   field sets, both stay in the list and consumers union.

The :data:`SOURCE_PRIORITY` registry below records the *single
authoritative source* for each pair today. When a second source becomes
available for the same pair, the writer-side merge logic must land
before the dict gets a multi-entry list (otherwise live=batch breaks).

Phase 1C (2026-05-08) — ``pipeline_mode`` per-source mapping
============================================================

Per ``gcs_migration_bundle_pipeline_mode_2026_05_08`` Phase 1C, each row
selected via :func:`read_with_source_priority` returns ``(source,
pipeline_mode)`` so downstream consumers know which on-disk
``pipeline_mode=`` partition serves the row, enabling the batch-vs-live
reconciliation gate in
``live_pipeline_mtds_mdps_features_2026_05_08`` Phase 12.

**Design choice — Option B (chosen over Option A).** ``pipeline_mode``
is a property of the *source string itself*, not of the
``(asset_group, data_type, source)`` triple — every source has
exactly one batch ``PipelineMode`` value via the closed-set round-trip
already enforced in
:mod:`unified_api_contracts.canonical.crosscutting.pipeline_mode`. So
rather than restructuring :data:`SOURCE_PRIORITY`'s value type from
``list[str]`` to ``list[SourcePriorityEntry]`` (Option A), we keep the
existing shape and look up the ``PipelineMode`` for each source via the
existing :func:`pipeline_mode_for_source` helper. This:

* Avoids breaking every existing consumer of ``list[str]`` semantics.
* Composes with the existing closed-set test
  (``tests/unit/test_pipeline_mode.py``) which already asserts every
  source string in ``SOURCE_PRIORITY`` round-trips to a
  ``PipelineMode``.
* Keeps the SSOT surface narrow — adding new sources = one entry in
  ``SOURCE_PRIORITY`` + one ``PipelineMode`` member, not two coupled
  mutations of the same triple.

The :func:`read_with_source_priority` reader returned tuple is
``(source, pipeline_mode)`` and the live-priority-over-batch behaviour
is enforced by callers stratifying rows by ``pipeline_mode`` first
(live wins if a live row exists for the same
``(asset_group, venue, day)``); the SSOT lookup itself returns the
single primary batch source.
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Final

from unified_api_contracts.canonical.crosscutting.pipeline_mode import (
    Mode,
    PipelineMode,
    pipeline_mode_for_source,
)

logger = logging.getLogger(__name__)


class DivergenceKind(StrEnum):
    """Closed-set reasons a manifest row is flagged as a cross-source divergence.

    Written into the manifest ``divergence_kind`` column (nullable; ``None``
    means no divergence). Per Phase 2 of
    ``tradfi_massive_dual_source_2026_05_28.md``:

    * ``DUAL_SOURCE_DUPLICATE`` — the same ``(asset_group, venue, day, ticker,
      ts)`` row-key appears in two or more sources. The sources agree on the
      key but may differ on values (price, volume). Logged + counted; do NOT
      silently drop either source's row — downstream reconciliation decides
      the winner via :func:`select_primary_available_source`.

    Future values (extend this enum, do NOT add bare strings):
    * ``TEMPORAL_GAP`` — source A has the day; source B is absent.
    * ``FIELD_UNION`` — sources have non-overlapping field sets (rule 4 of
      the tie-breaker docstring); consumer unions both rows.
    """

    DUAL_SOURCE_DUPLICATE = "DUAL_SOURCE_DUPLICATE"


SOURCE_PRIORITY: Final[dict[tuple[str, str], list[str]]] = {
    # ---- Sports ---------------------------------------------------------
    # Fixture lifecycle data — api_football is primary, footystats is the
    # multi-source merge candidate (deferred). Soccer-football-info handles
    # the SFI_PROGRESSIVE_STATS slice.
    ("sports", "FIXTURES"): [
        "api_football",
        "footystats",
    ],  # footystats is the deferred multi-source merge candidate (see module docstring Phase 1B)
    ("sports", "FIXTURE_LINEUPS"): ["api_football"],
    ("sports", "FIXTURE_EVENTS"): ["api_football"],
    ("sports", "FIXTURE_STATS"): ["api_football"],
    ("sports", "FIXTURE_PLAYER_STATS"): ["api_football"],
    ("sports", "INJURIES"): ["api_football"],
    ("sports", "RESULTS"): ["api_football"],
    ("sports", "UNDERSTAT_XG"): ["understat"],
    ("sports", "SFI_PROGRESSIVE_STATS"): ["soccer_football_info"],
    ("sports", "ODDS_SNAPSHOT"): ["odds_api"],
    ("sports", "ODDS_MOVEMENT"): ["odds_api"],
    ("sports", "ARBITRAGE"): ["odds_api"],
    ("sports", "WEATHER_FORECAST"): ["open_meteo"],
    # Sports raw data types (instruments-service manifest data_type names).
    ("sports", "XG"): ["understat"],
    ("sports", "XG_SHOTS"): ["understat"],
    ("sports", "MATCHES"): ["footystats"],
    ("sports", "STANDINGS"): ["api_football"],
    ("sports", "WEATHER"): ["open_meteo"],
    ("sports", "PREDICTIONS"): ["footystats"],
    ("sports", "ODDS"): ["footystats"],
    ("sports", "ODDS_HORIZON_BUCKET"): ["mdps_odds_horizon_bucket"],
    ("sports", "TRANSFER_RECORDS"): ["transfermarkt"],
    # Sports reference tables.
    ("sports", "TEAMS"): ["api_football"],
    ("sports", "PLAYERS"): ["api_football"],
    ("sports", "VENUES"): ["api_football"],
    ("sports", "LEAGUES"): ["api_football"],
    ("sports", "PLAYER_VALUES"): ["transfermarkt"],
    # ---- CeFi -----------------------------------------------------------
    # Tardis is the canonical CeFi tick source (multi-venue archive).
    # Per-venue REST/WS adapters serve live-time updates; archive falls
    # back to Tardis.
    ("cefi", "trades"): ["tardis"],
    ("cefi", "ohlcv_1m"): ["tardis"],
    ("cefi", "ohlcv_15m"): ["tardis"],
    ("cefi", "book_snapshot"): ["tardis"],
    ("cefi", "liquidations"): ["tardis"],
    # ERA-B (operator 2026-06-07): options_chain / futures_chain are
    # INSTRUMENT_TYPES (per-underlying chain bundles), captured as data_type=trades
    # — so the Era-B writer resolves source via ``(cefi, "trades")`` above (same
    # primary, tardis). These data_type-keyed entries are RETAINED only for (a) the
    # legacy data_type=options_chain rows pending the per-AG v8→v9 relabel
    # (OUT OF SCOPE here) and (b) the bidirectional SOURCE_PRIORITY ↔
    # AVAILABILITY_AT_SEMANTICS closed-set round-trip; drop them once the per-AG
    # migrators relabel the legacy rows to trades.
    ("cefi", "options_chain"): ["tardis"],
    ("cefi", "futures_chain"): ["tardis"],
    ("cefi", "perpetual"): ["tardis"],
    ("cefi", "funding_rate"): ["tardis"],
    # ---- DeFi -----------------------------------------------------------
    # DeFi has per-protocol on-chain readers; no single canonical source.
    ("defi", "swap"): ["onchain_subgraph"],
    ("defi", "fx_rate"): ["onchain_subgraph"],
    ("defi", "liquidity"): ["onchain_subgraph"],
    ("defi", "market_state"): ["onchain_subgraph"],
    ("defi", "gas_fees"): ["onchain_rpc"],
    ("defi", "lst_yields"): ["onchain_subgraph"],
    ("defi", "vault_state"): ["onchain_subgraph"],
    # Phase 1A feature_dag seed gap closeout (2026-05-07): 5 on-chain DeFi
    # data_types declared in AVAILABILITY_AT_SEMANTICS but missing from
    # SOURCE_PRIORITY. Top-entry-only seeds per the Phase 1B convention
    # documented in this module's docstring; multi-source merge (e.g. The
    # Graph for AaveV3 + morpho_blue_api for Morpho on lending_indices)
    # is deferred to ``multi_source_priority_merge_2026_*<TBD>.md``.
    # `risk_params` reads protocol configurator state at the contract level
    # (Aave LendingPoolConfigurator, Morpho IRM params) → ``onchain_rpc``;
    # the other four are event-stream / index reads → ``onchain_subgraph``.
    ("defi", "lending_indices"): ["onchain_subgraph"],
    ("defi", "risk_params"): ["onchain_rpc"],
    ("defi", "rewards"): ["onchain_subgraph"],
    ("defi", "flash_loan_events"): ["onchain_subgraph"],
    ("defi", "eigenlayer_rewards"): ["onchain_subgraph"],
    # Phase 4.MTDS / Phase 5 availability-semantic gap closeout (2026-05-12):
    # 14 DeFi data_types present in AVAILABILITY_AT_SEMANTICS (Ikenna Phase 5
    # audit 2026-05-11) but missing from SOURCE_PRIORITY. Source assignments
    # derived from MTDS handler survey in
    # ``scratch_codefreeze_phase4_mtds_fanout_2026_05_12.md`` per-source
    # mapping table. Subgraph = EVM The Graph / Messari indexer; RPC = direct
    # node call or signed transaction event; hyperliquid = Hyperliquid (vendor;
    # REST transport for the Solana-based perp + DEX legs — transport is a column,
    # never glued to the source name, operator R4 2026-06-07).
    ("defi", "bridge_events"): ["onchain_rpc"],
    ("defi", "dex_pool_state"): ["onchain_subgraph"],
    # dex pool SWAPS — canonical data_type ``dex_pool_swaps`` (the bucket-spec
    # ``canonical_dt`` in migrate_defi_full_v9_canonical.py:112 + the on-disk
    # ``data_type=dex_pool_swaps`` in ``dex-swaps-*``; the legacy ``dex_swaps``
    # logical key is retired). Read from The Graph subgraph (the uniswap_v3 /
    # curve adapters fetch pools + SWAPS + liquidity from the SAME subgraph —
    # uniswap_v3_adapter.py "primary for pools, swaps, liquidity"), so the source
    # is ``onchain_subgraph``, matching ``dex_pool_state`` above. Was previously
    # UNREGISTERED → fell through to the defi asset_group fallback
    # (``BATCH_ONCHAIN_RPC``), which mis-stamped swaps as ``onchain_rpc``. (F2
    # registry tidy slot-7 2026-06-07 mis-keyed this as ``("defi", "n")`` — a dead
    # key matching no real shard, so ``dex_pool_swaps`` kept falling to the
    # onchain_rpc fallback; corrected to the real canonical data_type by the slot-2
    # pre-apply audit 2026-06-08 so the v9 migrator derives
    # ``batch_onchain_subgraph`` for dex-swaps.)
    ("defi", "dex_pool_swaps"): ["onchain_subgraph"],
    ("defi", "governance_events"): ["onchain_subgraph"],
    ("defi", "liquidation_events"): ["onchain_rpc"],
    ("defi", "liquidations"): ["onchain_subgraph"],
    ("defi", "lst_rates"): ["onchain_subgraph"],
    ("defi", "mev_events"): ["onchain_rpc"],
    # native_staking_rates: Solana RPC (getInflationRate/getEpochInfo) is primary;
    # helius_rpc for per-validator APY breakdown (requires Helius API key).
    ("defi", "native_staking_rates"): ["solana_rpc", "helius_rpc"],
    # oracle_prices dispatches Pyth Hermes (Solana feeds) as primary and
    # Chainlink (EVM aggregator rounds) as secondary; per-row pipeline_mode
    # is resolved at callsite by the MTDS oracle_prices_handler resolver.
    ("defi", "oracle_prices"): ["pyth_hermes", "chainlink"],
    # perp_funding + solana_defi are Hyperliquid REST legs; Hyperliquid (the vendor,
    # via its REST transport) is the primary (and currently only) source for both
    # data_types. source=hyperliquid, transport=rest (a column, not the name).
    # NOTE (F2 registry tidy, slot-7 2026-06-07): non-Hyperliquid perp venues
    # (e.g. LIGHTER, which reads its perp funding from the Tardis archive) are
    # deliberately NOT listed here — they are resolved PER-SHARD by the venue
    # override layer (``pipeline_mode_resolver._VENUE_OVERRIDES["LIGHTER"] →
    # BATCH_TARDIS``), which runs BEFORE the SOURCE_PRIORITY lookup. Adding tardis
    # to this list would flip ``source_required(defi, perp_funding)`` to True (a
    # 2-external-source cell) and break the single-source auto-stamp for the
    # Hyperliquid-native cells. The venue-override layer is the correct home for a
    # per-venue source that differs from the data_type default.
    ("defi", "perp_funding"): ["hyperliquid"],
    ("defi", "position_data"): ["onchain_rpc"],
    ("defi", "solana_defi"): ["hyperliquid"],
    ("defi", "staking_yields"): ["onchain_subgraph"],
    ("defi", "token_transfers"): ["onchain_rpc"],
    ("defi", "vault_share_price"): ["onchain_subgraph"],
    # execution_fills — emitted by execution-service (not an external
    # market-data vendor); source tag is ``execution_service``.
    # d3_manifest_v8_finish_2026_05_20 Phase 1 — closes
    # PipelineMode.BATCH_EXECUTION_SERVICE closed-set round-trip with
    # SOURCE_PRIORITY (both CeFi + DeFi execution legs write execution_fills).
    ("cefi", "execution_fills"): ["execution_service"],
    ("defi", "execution_fills"): ["execution_service"],
    # hedge_ratio_snapshot — emitted by strategy-service (not an external
    # market-data vendor); source tag is ``strategy_service``.
    # hedge_ratio_snapshot_persistence_2026_05_13 Phase 1.
    ("defi", "hedge_ratio_snapshot"): ["strategy_service"],
    # strategy_decision_context — emitted by strategy-service on every tick
    # (pre-decision inputs for audit trail); same source as hedge_ratio_snapshot.
    # hedge_ratio_snapshot_persistence_2026_05_13 Phase 5.
    ("defi", "strategy_decision_context"): ["strategy_service"],
    # feature_observation_snapshot — emitted by features-onchain-service on every
    # tick (per-tick APY inputs + MTDS provenance for audit chain).
    # features_tick_observation_audit_2026_05_18 Phase 1.
    ("defi", "feature_observation_snapshot"): ["features_onchain_service"],
    # cross_instrument_signal — emitted by features-service cross_instrument
    # family on every batch run (multi-asset / multi-venue derived features).
    # d5_features_missing_data_downgrade_2026_05_20 Phase 2 — closes
    # PipelineMode.BATCH_CROSS_INSTRUMENT closed-set round-trip with
    # SOURCE_PRIORITY (the family crosses asset_groups; registered under
    # "defi" as the primary live archetype consumer per CLAUDE.md
    # "DeFi + CeFi hybrid" rule — carry_staked_basis + perp_funding_vs_spot
    # are the cross_instrument family's live targets).
    ("defi", "cross_instrument_signal"): ["cross_instrument"],
    # ---- TradFi ---------------------------------------------------------
    # Databento for CME/NQ/options/futures; Yahoo for VIX 15m rolling
    # window; Barchart for VIX 15m historical preload (handled at the
    # MTDS routing layer, not here — both are listed for the same shard
    # but the orchestrator picks by date).
    # EIA (US Energy Information Administration) — commodity storage + series data.
    # BATCH_EIA manifest mode: features-commodity-service D5 Phase 1.
    ("tradfi", "energy_data"): ["eia"],
    ("tradfi", "trades"): ["databento", "massive"],
    ("tradfi", "tbbo"): ["databento", "massive"],
    ("tradfi", "ohlcv_1m"): ["databento", "massive"],
    # databento primary; massive secondary (REST batch, delayed tier); yahoo: VIX 15m rolling 60d fallback;
    # barchart: VIX 15m historical preload 2020-2025. Massive slotted AFTER databento, BEFORE yahoo/barchart
    # per tradfi_massive_dual_source_2026_05_28.md Phase 1 operator decision. CFE (VX/VIX futures) is NOT
    # covered by Massive — existing yahoo+barchart layering handles those via MTDS routing.
    ("tradfi", "ohlcv_15m"): ["databento", "massive", "yahoo", "barchart"],
    # ERA-B: options_chain / futures_chain are instrument_types captured as
    # data_type=trades → Era-B source resolves via ``(tradfi, "trades")`` above
    # (databento, massive). Legacy-data_type keys retained for the pre-migration
    # rows + the closed-set round-trip (see the cefi note above).
    ("tradfi", "options_chain"): ["databento", "massive"],
    ("tradfi", "futures_chain"): ["databento", "massive"],
    # commodity_signal — emitted by features-service commodity family from
    # EIA (crude oil + natural gas weekly storage) + CFTC + Baker Hughes +
    # Open-Meteo + Yahoo factor inputs. Top entry is EIA per the storage
    # factor's dominant role in the commodity feature set (per
    # features_service/commodity/README.md factor table).
    # d5_features_missing_data_downgrade_2026_05_20 Phase 1 — closes
    # PipelineMode.BATCH_EIA closed-set round-trip with SOURCE_PRIORITY.
    ("tradfi", "commodity_signal"): ["eia"],
    # ---- Prediction -----------------------------------------------------
    ("prediction", "trades"): ["polymarket_clob"],
    ("prediction", "book_snapshot"): ["polymarket_clob"],
    ("prediction", "prediction_canonical_question_group"): ["polymarket_clob"],
    # MARKET_LIFECYCLE source — instruments-service reads from Polymarket
    # gamma API ``/markets/{conditionId}`` for created/resolution/settlement
    # timestamps. Phase 1B writes top entry only; Kalshi metadata source is
    # a deferred follow-up plan slot. Predictions plan
    # ``predictions_canonical_question_group_polymarket_migration_2026_05_06.md``
    # Phase 1A.
    ("prediction", "MARKET_LIFECYCLE"): ["polymarket_gamma_api"],
    # cross_instrument — computed by features-service cross_instrument handler
    # (honest-absence manifest calls). BATCH_CROSS_INSTRUMENT mode: D5 Phase 2.
    ("cefi", "cross_instrument"): ["cross_instrument"],
    # ---- Reference (asset-group-agnostic) -------------------------------
    ("reference", "instruments"): ["instruments_service"],
    ("reference", "venue_trading_calendar"): ["instruments_service"],
    # ---- Features-service computed outputs ------------------------------
    # commodity_features — tradfi energy signals (storage, weather, COT, rig_count,
    # price_momentum) produced by features-service commodity sub-package from EIA + CFTC + BH feeds.
    # BATCH_EIA PipelineMode prerequisite (D5 Phase 1 / uac@fb3751e8).
    ("tradfi", "commodity_features"): ["eia"],
    # cross_instrument_features — cross-asset/cross-venue signals (paired_price_dispersion,
    # cross_venue_spreads, regime_detection, cross_asset_correlation, cross_instrument_dynamics)
    # produced by features-service cross_instrument sub-package from delta-one inputs.
    # BATCH_CROSS_INSTRUMENT PipelineMode prerequisite (D5 Phase 2 / uac@39733749).
    ("cefi", "cross_instrument_features"): ["cross_instrument"],
}


def get_source_priority(asset_group: str, data_type: str) -> list[str]:
    """Return the ordered source list for a ``(asset_group, data_type)`` pair.

    Returns a copy so callers cannot mutate the registry.

    Args:
        asset_group: One of ``cefi`` / ``defi`` / ``tradfi`` / ``prediction``
            / ``sports`` / ``reference``.
        data_type: Canonical data_type string.

    Returns:
        Ordered list of source keys. Top entry is primary (the
        live-time-winning source).

    Raises:
        KeyError: If the pair is not registered. Failing loud is intentional
            — silent fallback would mask schema-drift bugs.
    """
    key = (asset_group, data_type)
    if key not in SOURCE_PRIORITY:
        msg = (
            f"No source priority registered for "
            f"asset_group={asset_group!r}, data_type={data_type!r}. "
            "Register the pair in SOURCE_PRIORITY before use."
        )
        raise KeyError(msg)
    return list(SOURCE_PRIORITY[key])


def get_primary_source(asset_group: str, data_type: str) -> str:
    """Return the primary (top-of-list) source key for a pair.

    Convenience for callers that don't need the full list — most stamping
    helpers just need the live-time source name to compute available_at.
    """
    return get_source_priority(asset_group, data_type)[0]


def has_source_priority(asset_group: str, data_type: str) -> bool:
    """Check whether the pair is registered (non-raising membership test)."""
    return (asset_group, data_type) in SOURCE_PRIORITY


COMPUTED_SOURCES: Final[frozenset[str]] = frozenset(
    {
        # Internal service emitters — NOT external market-data vendors. Their
        # rows' lineage is the upstream cell they were computed from, not a
        # vendor, so the data-source provenance gate is N/A for them
        # (data_source_provenance_all_asset_groups_2026_06_01.md § Scope
        # boundary — "EXEMPT: computed, no external vendor"). These source
        # strings exist in SOURCE_PRIORITY only to satisfy the PipelineMode
        # closed-set round-trip; they are exempt from source stamping.
        "execution_service",  # execution-service fills
        "strategy_service",  # strategy-service hedge-ratio / decision-context
        "features_onchain_service",  # features-onchain per-tick snapshots
        "cross_instrument",  # features-service cross_instrument family outputs
    }
)
"""Source strings denoting internal computed/service emitters (provenance-exempt).

The data-source provenance gate
(``data_source_provenance_all_asset_groups_2026_06_01.md``) stamps ``source``
on every *external-vendor* market-data cell. Cells whose only source(s) are
internal service emitters carry no external provenance — their lineage is the
upstream cell, not a vendor — so they are exempt from the gate. Membership here
is the principled exemption (vs a hardcoded data_type list)."""


# ---------------------------------------------------------------------------
# M2 — source-mode capability registry + M9 mock source
# (pipeline_mode_source_batch_live_replay_standardisation_2026_06_05.md)
# ---------------------------------------------------------------------------

MOCK_SOURCE: Final[str] = "mock"
"""M9 — simulated/fake data source. Routes to the DEV cloud-storage path via the
env-tier bucket split (``-dev-``/`-stg-` vs `-prd-`) so it NEVER touches prod;
makes test fixtures first-class. Mock implies dev-tier only."""

# RATIFIED source-mode capability (operator 2026-06-07) — encodes
# ``plans/audit/results/source_mode_capability_matrix_2026_06_07.md`` row-for-row,
# including its "CORRECTED MODEL" section. These flags are LOAD-BEARING (M2/M3/M4/M6
# read them), not a draft seed.
#
# Every EXTERNAL source is batch-capable (the ``batch_<source>`` closed-set floor).
# LIVE = a real-time stream (or a short-interval poll for push-less sources like
# onchain_subgraph). REPLAY (format-agnostic) = the ability to re-fetch
# "today-since-start" ON DEMAND to fill an intraday / startup / live-downtime gap;
# a source that cannot re-fetch intraday simply means its live-downtime gap waits
# for batch (honest absence) — NOT a decision.
#
# Notes on the ratified rows:
# * tardis = {batch} ONLY — the academic licence blocks replay AND CeFi live/replay
#   come from the EXCHANGES (the per-venue ``live_<venue>``/``replay_<venue>`` sources),
#   not Tardis. Tardis is the CeFi BATCH (T+1 archive) source. (Matrix R1 + CORRECTED
#   MODEL.) The SAME shard therefore carries source=tardis in batch and source=<venue>
#   in live/replay — the row-level ``source`` column already models this.
# * massive (= Polygon.io) = {batch, live, replay}; final live testing is gated on the
#   paid real-time tier upgrade (a deploy-time gate, not a code gate). Starter-tier
#   live is 15-min delayed (see EMISSION_LATENCY_MS_BY_SOURCE).
# * Internal service sources (instruments_service/execution_service/strategy_service/
#   features_onchain_service/cross_instrument/mdps_odds_horizon_bucket) = service mode:
#   batch=live symmetry, re-run = replay.
SOURCE_MODE_CAPABILITY: Final[dict[str, frozenset[Mode]]] = {
    # ---- CeFi ----
    "tardis": frozenset({Mode.BATCH}),  # batch (archive) ONLY; live/replay = exchanges
    # ---- TradFi ----
    "databento": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "massive": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "yahoo": frozenset({Mode.BATCH}),
    "barchart": frozenset({Mode.BATCH}),
    "eia": frozenset({Mode.BATCH, Mode.REPLAY}),  # weekly series re-fetchable by date
    # ---- DeFi ----
    # hyperliquid (unified vendor) lives in the CeFi-venue block below — it is the
    # ONE venue that is ALSO batch-capable (DeFi perp_funding/solana_defi via REST
    # candleSnapshot), so it carries {BATCH, LIVE, REPLAY}. The former
    # ``hyperliquid_rest`` key (transport glued into the source) is retired (R4).
    "onchain_rpc": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "solana_rpc": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "helius_rpc": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "onchain_subgraph": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),  # live = poll
    "chainlink": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "pyth_hermes": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    # ---- Prediction ----
    "polymarket_clob": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "polymarket_gamma_api": frozenset({Mode.BATCH}),  # market metadata; not a tick series
    # ---- Sports ---- (no in-play live source until a sports live archetype exists;
    # historical odds + Secret-Manager keys already held → replay-capable now)
    "api_football": frozenset({Mode.BATCH, Mode.REPLAY}),
    "footystats": frozenset({Mode.BATCH, Mode.REPLAY}),
    "odds_api": frozenset({Mode.BATCH, Mode.REPLAY}),
    "understat": frozenset({Mode.BATCH, Mode.REPLAY}),
    "transfermarkt": frozenset({Mode.BATCH, Mode.REPLAY}),
    "soccer_football_info": frozenset({Mode.BATCH, Mode.REPLAY}),
    "open_meteo": frozenset({Mode.BATCH, Mode.REPLAY}),
    # ---- Internal service sources (service mode = batch=live symmetry, re-run=replay)
    "instruments_service": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "mdps_odds_horizon_bucket": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "execution_service": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "strategy_service": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "features_onchain_service": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "cross_instrument": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    # ---- CeFi per-venue live/replay sources ----
    # CeFi `live`/`replay` `source` = the EXCHANGE (CeFi `batch` source = tardis).
    # The SAME shard carries source=tardis in batch and source=<venue> in live/replay.
    # These venue sources are NOT batch-capable (Tardis is the CeFi archive) — they
    # have NO batch_<venue> PipelineMode. Replay-fact table (matrix 2026-06-07):
    # binance/okx/deribit/kraken/hyperliquid re-fetch a same-day window via REST
    # (replay ✓); Bybit (public REST recent-only) + Aster (newer venue, unverified)
    # are LIVE-only — a live-downtime gap waits for batch (T+1), replay ABSENT.
    # hyperliquid is the SOLE batch-capable venue: it is ALSO the DeFi
    # perp_funding/solana_defi batch source (REST candleSnapshot), so it carries
    # {BATCH, LIVE, REPLAY} (operator R4 2026-06-07 — the unified ``hyperliquid``
    # vendor). The other venues stay live/replay-only (CeFi batch = tardis).
    "binance": frozenset({Mode.LIVE, Mode.REPLAY}),
    "okx": frozenset({Mode.LIVE, Mode.REPLAY}),
    "deribit": frozenset({Mode.LIVE, Mode.REPLAY}),
    "kraken": frozenset({Mode.LIVE, Mode.REPLAY}),
    "hyperliquid": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "bybit": frozenset({Mode.LIVE}),
    "aster": frozenset({Mode.LIVE}),
}

CEFI_LIVE_VENUES: Final[frozenset[str]] = frozenset(
    {"binance", "okx", "deribit", "kraken", "hyperliquid", "bybit", "aster"}
)

BATCH_CAPABLE_CEFI_VENUES: Final[frozenset[str]] = frozenset({"hyperliquid"})
"""CeFi live venues that are ALSO a batch source (operator R4 2026-06-07).

``hyperliquid`` is the unified vendor: a CeFi/DeFi live+replay venue AND the DeFi
``perp_funding``/``solana_defi`` BATCH source (REST candleSnapshot). It is the ONE
:data:`CEFI_LIVE_VENUES` member that carries a ``batch_<venue>`` PipelineMode +
``Mode.BATCH`` capability — every other CeFi venue is live/replay-only (CeFi batch
= tardis). Exempts hyperliquid from the "CeFi venues are not batch-capable"
invariant without weakening it for the rest."""
"""CeFi exchange venues that serve the `live`/`replay` capture modes (M2/M3).

CeFi `batch` data comes from ``tardis`` (the T+1 multi-venue archive); CeFi
`live`/`replay` data comes from the exchange itself, so the ``source`` for a CeFi
shard is mode-dependent: ``tardis`` in batch, the venue here in live/replay. These
venues are NOT in :data:`SOURCE_PRIORITY` (the batch-priority registry) and are NOT
batch-capable — they carry only ``live_<venue>`` / ``replay_<venue>`` PipelineMode
members. The mode-contextual reader that picks the venue source per (shard, mode)
is the M3/M4 next tranche."""


def modes_for_source(source: str) -> frozenset[Mode]:
    """Return the set of :class:`Mode`s ``source`` can run. ``mock`` ⇒ all modes
    (a fixture can stand in for any). Unregistered external source ⇒ ``{BATCH}``
    (the safe default — everything is at least batch-archivable).

    The per-source mode sets are RATIFIED + load-bearing (the
    ``source_mode_capability_matrix_2026_06_07.md`` rows). The REMAINING
    refinement (next tranche) is the per-``(source, data_type)`` KEYING — e.g.
    hyperliquid is LIVE for ``trades``/``l2_book`` (``ws_*`` ops) but REST/BATCH
    for ``funding_rates`` — to be added as ``modes_for(source, data_type)``
    derived from ``registry/capability_declarations`` ``SourceCapability``
    (per-operation REST/WS). SSOT:
    ``pipeline_mode_source_batch_live_replay_standardisation_2026_06_05.md``
    § M2 REFINEMENT."""
    if source == MOCK_SOURCE:
        return frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY})
    return SOURCE_MODE_CAPABILITY.get(source, frozenset({Mode.BATCH}))


def source_supports(source: str, mode: Mode) -> bool:
    """True if ``source`` can run in reconciliation ``mode`` (M2 guardrail)."""
    return mode in modes_for_source(source)


def sources_supporting(mode: Mode) -> set[str]:
    """All registered sources capable of ``mode`` (e.g. the replay-capable set)."""
    return {src for src, modes in SOURCE_MODE_CAPABILITY.items() if mode in modes}


def external_sources_for(asset_group: str, data_type: str) -> list[str]:
    """Return the external-vendor sources for a cell (computed sources removed).

    A cell's :data:`SOURCE_PRIORITY` list may mix external vendors with
    internal computed emitters (see :data:`COMPUTED_SOURCES`). This returns
    only the external entries, preserving priority order. Empty list when the
    pair is unregistered OR every source is a computed/service emitter.
    """
    return [s for s in SOURCE_PRIORITY.get((asset_group, data_type), ()) if s not in COMPUTED_SOURCES]


def source_required(asset_group: str, data_type: str) -> bool:
    """Return True when the writer MUST be *passed* an explicit ``source``.

    SSOT for the multi-source disambiguation half of the writer-side gate in
    ``unified_trading_library.manifest_writer`` (record_captured / add). A cell
    requires an explicit source ONLY when it has **more than one external
    source** — because the writer cannot otherwise know which provider served
    the row.

    Single-source external cells do NOT require an explicit source: the writer
    auto-stamps the sole registered external source via :func:`default_source`
    (universal stamping — every external cell carries ``source`` for
    swap-resilience, per the 2026-06-01 operator decision). Computed/service
    cells (:data:`COMPUTED_SOURCES`) and unregistered pairs are exempt.

    * TradFi ``trades`` (databento + massive)        → True (explicit needed)
    * DeFi ``oracle_prices`` (pyth_hermes+chainlink) → True
    * DeFi ``native_staking_rates`` (solana+helius)  → True
    * Sports ``FIXTURES`` (api_football+footystats)  → True
    * CeFi ``trades`` (tardis)                        → False (auto-stamped)
    * Prediction ``trades`` (polymarket_clob)         → False (auto-stamped)
    * DeFi ``execution_fills`` (execution_service)    → False (computed-exempt)
    * Unregistered pair                               → False

    Args:
        asset_group: ``cefi`` / ``defi`` / ``tradfi`` / ``prediction`` /
            ``sports`` / ``reference``. (The writer passes its ``category``.)
        data_type: Canonical data_type string.

    Returns:
        ``True`` iff the pair has >1 external source.
    """
    return len(external_sources_for(asset_group, data_type)) > 1


def default_source(asset_group: str, data_type: str) -> str | None:
    """Return the auto-stampable source for a single-source external cell.

    Universal-stamping helper (``data_source_provenance_all_asset_groups_2026_06_01.md``):
    when a cell has exactly **one** external source, the writer auto-stamps it
    so the row carries provenance even though only one vendor exists today
    (swap-resilience — when a 2nd vendor or a replacement lands, pre-existing
    rows stay distinguishable from the new source).

    Returns:
        The sole external source string when the cell has exactly one external
        source; ``None`` when the cell is multi-source (caller must pass an
        explicit source), computed/service-only, or unregistered (nothing to
        auto-stamp).
    """
    external = external_sources_for(asset_group, data_type)
    return external[0] if len(external) == 1 else None


EMISSION_LATENCY_MS_BY_SOURCE: Final[dict[str, int]] = {
    # Tick-level live sources — sub-second tick-to-pipeline arrival.
    "tardis": 50,  # multi-venue WS aggregator
    "databento": 10,  # CME direct feed, microsecond-grade infra
    "polymarket_clob": 200,  # HTTPS CLOB polling
    "onchain_rpc": 200,  # direct RPC, block-time bounded
    # Subgraph / indexer — block-confirmation latency dominates.
    "onchain_subgraph": 60_000,  # 1 min: block confirmation + Graph indexing
    # Sports REST APIs — emission cadence ≈ 1-5s.
    "api_football": 1_000,
    "odds_api": 5_000,
    # Equity / index intraday — free-tier delayed feeds (VIX 15m fallback route).
    "massive": 900_000,  # 15 min: Massive (formerly Polygon.io) Starter tier delayed feed
    "yahoo": 900_000,  # 15 min: Yahoo Finance free-tier intraday delay for CBOE-sourced indices like ^VIX
    # Post-match / batch-only — cadence is hours-to-day.
    "understat": 7_200_000,  # 2h post-match xG
    "soccer_football_info": 3_600_000,  # 1h SFI freeze cadence
    "open_meteo": 3_600_000,  # 1h forecast issue
    "transfermarkt": 86_400_000,  # 24h market values
    # Metadata / lifecycle reads — minute-cadence.
    "polymarket_gamma_api": 60_000,
    "instruments_service": 60_000,
    # strategy-service hedge-ratio snapshots — emitted inline at rebalance time;
    # latency = 0ms relative to the event that triggered it (the rebalance
    # decision is the event; available_at = captured_at = write time).
    "strategy_service": 0,
    # execution-service result writes — emitted inline at write time;
    # latency = 0ms (available_at = captured_at = write time).
    "execution_service": 0,
    # features-onchain-service — feature snapshots emitted inline at calculation
    # time; latency = 0ms relative to the observation trigger.
    "features_onchain_service": 0,
    # cross_instrument feature family — features emitted inline at batch-tick
    # calculation time; latency = 0ms relative to the upstream multi-asset
    # delta_one/MTDS read-event that triggered it.
    "cross_instrument": 0,
    # EIA weekly storage publication — Wednesdays 10:30 AM ET covering the
    # prior Friday → ~5 day publication lag. Conservative 86_400_000 (24h)
    # matches barchart-tier daily-archive sources; tightenable later via
    # source_emission_latency_calibration_2026_*<TBD>.md.
    "eia": 86_400_000,
    # DeFi REST APIs — Hyperliquid + oracle aggregators.
    "hyperliquid": 1_000,  # 1s: HL REST API polling cadence (source=hyperliquid, transport=rest)
    "pyth_hermes": 1_000,  # 1s: Pyth Hermes batch endpoint
    "chainlink": 200,  # 200ms: on-chain EVM oracle aggregator round (RPC-style)
    # Solana native-staking sources — epoch-granularity (~2.5 day cadence).
    "solana_rpc": 60_000,  # 1 min: Solana RPC getInflationRate/getEpochInfo polling
    "helius_rpc": 60_000,  # 1 min: Helius APY aggregation endpoint polling
    # Sports odds-horizon bucket — GCS batch writes by mdps-sports VM.
    "mdps_odds_horizon_bucket": 3_600_000,  # 1h: conservative batch-write cadence (VM-driven)
    # Sports batch-data provider (deferred multi-source merge candidate).
    "footystats": 3_600_000,  # 1h: Footystats batch publication cadence
    # Historical preload archive — daily publication delay.
    "barchart": 86_400_000,  # 24h: Barchart VIX 15m historical preload (2020-2025)
}
"""Per-source emission latency (ms) — live-pipeline tick-to-pipeline arrival.

Used by the live=batch ``available_at`` formula:
``available_at = tick_event_time + emission_latency_ms_for_source(primary_source)``.

The values represent the wall-clock delta between when an event happens at the
source and when our live pipeline would actually have the row in-process. Per
the workspace ``Live = batch — same data, same fields, same timing semantics``
rule, batch writes MUST stamp ``available_at`` with this delta added so historical
features see the same arrival horizon they would in live mode.

**Phase 1B seed values are CONSERVATIVE estimates** — empirical calibration via
per-source tick-arrival sampling is deferred to follow-up plan
``source_emission_latency_calibration_2026_*<TBD>.md`` (named-successor per the
workspace ``Temporary state must have a named successor plan`` rule). Sources
whose primary is in batch-archive shape (e.g. ``tardis`` for CeFi ticks) carry
the LIVE-equivalent latency, NOT the archive-fetch latency — the archive read
happens at backfill time, but the stamped ``available_at`` reflects when a live
pipeline would have the row.

**Closed-set round-trip rule (mirrors :data:`PipelineMode`):** every source
string appearing in :data:`SOURCE_PRIORITY` MUST have an entry here. The
:func:`assert_emission_latency_round_trip` helper enforces this and is wired
into the UAC unit-test suite.

Plans:

* ``cefi_master`` Q1 — F2-v2 prerequisite for CeFi adapter
  ``available_at`` stamping.
* ``predictions_master`` Q2 — Polymarket / Kalshi bundled-row
  ``available_at`` stamping.
"""


def emission_latency_ms_for_source(source: str) -> int:
    """Return the live-emission latency (ms) for ``source``.

    Args:
        source: A source string from :data:`SOURCE_PRIORITY` (e.g. ``"tardis"``,
            ``"databento"``, ``"api_football"``).

    Returns:
        Latency in milliseconds — wall-clock delta from event-at-source to
        row-in-pipeline.

    Raises:
        KeyError: If the source is not registered in
            :data:`EMISSION_LATENCY_MS_BY_SOURCE`. Failing loud is intentional —
            silent fallback would mask schema-drift bugs in the closed-set
            round-trip with :data:`SOURCE_PRIORITY`.
    """
    if source not in EMISSION_LATENCY_MS_BY_SOURCE:
        msg = (
            f"No emission latency registered for source={source!r}. "
            f"Add an entry to EMISSION_LATENCY_MS_BY_SOURCE before use. "
            f"Every source in SOURCE_PRIORITY must have a latency entry "
            f"(closed-set round-trip rule)."
        )
        raise KeyError(msg)
    return EMISSION_LATENCY_MS_BY_SOURCE[source]


def get_primary_source_with_latency(
    asset_group: str,
    data_type: str,
) -> tuple[str, int]:
    """Return ``(primary_source, emission_latency_ms)`` for an ``(asset_group, data_type)``.

    The latency-aware companion to :func:`get_primary_source`. Stamping helpers
    use this to compute ``available_at = tick_event_time + latency_ms`` per the
    live=batch invariant.

    Args:
        asset_group: One of ``cefi`` / ``defi`` / ``tradfi`` / ``prediction``
            / ``sports`` / ``reference``.
        data_type: Canonical data_type string.

    Returns:
        Tuple of ``(primary_source_string, emission_latency_ms)``.

    Raises:
        KeyError: If the ``(asset_group, data_type)`` pair is not registered
            (delegated from :func:`get_primary_source`) OR if the primary source
            has no latency entry (delegated from
            :func:`emission_latency_ms_for_source`). Both raise paths are
            prevented in CI by :func:`assert_emission_latency_round_trip`.
    """
    primary_source = get_primary_source(asset_group, data_type)
    latency_ms = emission_latency_ms_for_source(primary_source)
    return primary_source, latency_ms


def assert_emission_latency_round_trip() -> None:
    """Closed-set round-trip: every SOURCE_PRIORITY source has a latency entry.

    Mirrors :func:`pipeline_mode.assert_pipeline_mode_source_priority_round_trip`.
    Wired into the UAC unit-test suite via
    ``tests/unit/test_source_priority.py::test_emission_latency_round_trip``.

    Raises:
        AssertionError: If any source in :data:`SOURCE_PRIORITY` is missing from
            :data:`EMISSION_LATENCY_MS_BY_SOURCE`, or if any latency entry refers
            to a source not used in :data:`SOURCE_PRIORITY`.
    """
    sources_in_priority: set[str] = set()
    for source_list in SOURCE_PRIORITY.values():
        sources_in_priority.update(source_list)
    sources_in_latency: set[str] = set(EMISSION_LATENCY_MS_BY_SOURCE.keys())

    missing_latency = sources_in_priority - sources_in_latency
    if missing_latency:
        msg = (
            f"Sources in SOURCE_PRIORITY without emission latency entries: "
            f"{sorted(missing_latency)}. Add to EMISSION_LATENCY_MS_BY_SOURCE."
        )
        raise AssertionError(msg)

    orphan_latency = sources_in_latency - sources_in_priority
    if orphan_latency:
        msg = (
            f"Sources in EMISSION_LATENCY_MS_BY_SOURCE not used in SOURCE_PRIORITY: "
            f"{sorted(orphan_latency)}. Remove orphan latency entries or wire the "
            f"source into SOURCE_PRIORITY."
        )
        raise AssertionError(msg)


def read_with_source_priority(
    asset_group: str,
    data_type: str,
) -> tuple[str, PipelineMode]:
    """Return ``(primary_source, pipeline_mode)`` for an ``(asset_group, data_type)``.

    The pipeline-mode-aware companion to :func:`get_primary_source`. Per Phase 1C
    of ``gcs_migration_bundle_pipeline_mode_2026_05_08``, every read of the
    primary source is paired with the source's batch :class:`PipelineMode` so
    callers can:

    * Tag rows with the on-disk ``pipeline_mode=`` hive partition value
      (matches the partition the migration bundle writes).
    * Stratify batch-vs-live reconciliation in
      ``live_pipeline_mtds_mdps_features_2026_05_08`` Phase 12 — live rows
      (``pipeline_mode=PipelineMode.LIVE_WEBSOCKET``) win over batch rows
      with the same row-key.

    Args:
        asset_group: One of ``cefi`` / ``defi`` / ``tradfi`` / ``prediction``
            / ``sports`` / ``reference``.
        data_type: Canonical data_type string.

    Returns:
        Tuple of ``(primary_source_string, pipeline_mode)``. ``pipeline_mode``
        is always a batch value (e.g. :attr:`PipelineMode.BATCH_TARDIS`); the
        live mode :attr:`PipelineMode.LIVE_WEBSOCKET` is set by the streaming
        writer at write-time, not derived from this registry.

    Raises:
        KeyError: If the ``(asset_group, data_type)`` pair is not registered
            in :data:`SOURCE_PRIORITY` (delegated from
            :func:`get_primary_source`).
        ValueError: If the primary source string has no corresponding
            :class:`PipelineMode` value — closed-set round-trip violation.
            Existing test
            ``tests/unit/test_pipeline_mode.py::test_every_source_priority_source_has_pipeline_mode``
            prevents this from firing in CI.
    """
    primary_source = get_primary_source(asset_group, data_type)
    pipeline_mode = pipeline_mode_for_source(primary_source)
    return primary_source, pipeline_mode


def detect_dual_source_conflicts(
    source_a: str,
    keys_a: set[tuple],
    source_b: str,
    keys_b: set[tuple],
    *,
    asset_group: str,
    data_type: str,
) -> list[tuple]:
    """Return row keys present in both source_a and source_b.

    Per Phase 2 of ``tradfi_massive_dual_source_2026_05_28.md`` conflict
    detection: when the same ``(asset_group, venue, day, ticker, ts)``
    row-key appears in two sources, this function detects the overlap, logs
    the count at WARNING level, and returns the duplicate keys so callers can
    emit ``divergence_kind=DUAL_SOURCE_DUPLICATE`` into the manifest.

    DO NOT silently drop either source's row — downstream reconciliation
    (e.g. :func:`select_primary_available_source`) decides which source wins.

    Args:
        source_a: First source string (e.g. ``"databento"``).
        keys_a: Set of row-key tuples for source_a (e.g.
            ``{(venue, day, ticker, ts), ...}``). Any hashable tuple shape is
            accepted — the caller owns the row-key definition.
        source_b: Second source string (e.g. ``"massive"``).
        keys_b: Set of row-key tuples for source_b.
        asset_group: Used in log messages only.
        data_type: Used in log messages only.

    Returns:
        Sorted list of row-key tuples present in both ``keys_a`` and
        ``keys_b``. Empty list when there are no conflicts.
    """
    duplicates = keys_a & keys_b
    if duplicates:
        logger.warning(
            "DUAL_SOURCE_DUPLICATE: %d row-key(s) in (%s, %s) appear in both "
            "source=%r and source=%r. Mark manifest rows with "
            "divergence_kind=DUAL_SOURCE_DUPLICATE. Sample (up to 3): %s",
            len(duplicates),
            asset_group,
            data_type,
            source_a,
            source_b,
            sorted(duplicates)[:3],
        )
    return sorted(duplicates)


def select_primary_available_source(
    asset_group: str,
    data_type: str,
    available_sources: set[str],
) -> tuple[str, PipelineMode]:
    """Return the highest-priority available source for ``(asset_group, data_type)``.

    Applies the Phase 2 tie-breaker rules from the module docstring in priority
    order. The :data:`SOURCE_PRIORITY` list encodes the tie-breaker: index 0 is
    the winner when all sources are present. When only a subset is available
    (e.g. Databento has a gap but Massive has the day), this function falls
    through to the next registered source.

    Tie-breaker rules (in order):

    1. **Timestamp-availability** — sources that emit at live-time win
       (encoded as lower emission latency in :data:`EMISSION_LATENCY_MS_BY_SOURCE`).
    2. **Coverage** — broader date / instrument coverage wins.
    3. **Information richness** — more fields per row wins.
    4. **Merge-different-fields** — non-overlapping field sets: callers
       *union* rather than pick, so both sources remain in
       :data:`SOURCE_PRIORITY` (handled at the consumer / writer layer,
       not here).

    Rules 1-3 are resolved at registry-design time by the ordering in
    :data:`SOURCE_PRIORITY`; this helper enforces that ordering at runtime
    when not all sources have data.

    Args:
        asset_group: One of ``cefi`` / ``defi`` / ``tradfi`` / etc.
        data_type: Canonical data_type string.
        available_sources: Set of source strings that have data for the
            requested ``(asset_group, data_type, day)`` cell (e.g. from
            a manifest query or filesystem scan).

    Returns:
        ``(source_string, pipeline_mode)`` for the highest-priority source
        found in ``available_sources``.

    Raises:
        KeyError: If ``(asset_group, data_type)`` is not registered, OR if
            none of the registered sources appear in ``available_sources``.
    """
    priority_list = get_source_priority(asset_group, data_type)
    for source in priority_list:
        if source in available_sources:
            return source, pipeline_mode_for_source(source)
    raise KeyError(
        f"No registered source for ({asset_group!r}, {data_type!r}) is available. "
        f"Registered (priority order): {priority_list}. "
        f"Available: {sorted(available_sources)}."
    )


def get_all_sources_with_priority(
    asset_group: str,
    data_type: str,
) -> list[tuple[str, PipelineMode]]:
    """Return all registered sources for ``(asset_group, data_type)`` in priority order.

    Phase 2 of ``tradfi_massive_dual_source_2026_05_28.md`` — multi-source
    merge building block. Unlike :func:`read_with_source_priority` (which
    returns only the primary source), this function returns the full ordered
    list so callers can:

    * Iterate over all available sources for a cell (e.g. ``databento`` +
      ``massive`` for TradFi trades).
    * Apply tie-breaker logic at the consumer layer (timestamp-availability
      → coverage → information richness → field-union per module docstring).
    * Detect conflicts when the same ``(ticker, ts)`` appears in multiple
      source parquets.

    The returned list is ordered by priority (index 0 = highest priority,
    the same as ``read_with_source_priority`` returns). Each element pairs
    the source string with its batch :class:`PipelineMode`.

    Args:
        asset_group: One of ``cefi`` / ``defi`` / ``tradfi`` / ``prediction``
            / ``sports`` / ``reference``.
        data_type: Canonical data_type string.

    Returns:
        Ordered list of ``(source_string, pipeline_mode)`` tuples, highest
        priority first. Always non-empty (enforced by
        ``test_every_source_priority_entry_has_at_least_one_source``).

    Raises:
        KeyError: If the ``(asset_group, data_type)`` pair is not registered
            in :data:`SOURCE_PRIORITY`.
        ValueError: If any source string in the list has no corresponding
            :class:`PipelineMode` — closed-set round-trip violation prevented
            in CI by ``test_every_source_priority_source_round_trips_to_pipeline_mode``.
    """
    sources = get_source_priority(asset_group, data_type)
    return [(source, pipeline_mode_for_source(source)) for source in sources]


__all__ = [
    "BATCH_CAPABLE_CEFI_VENUES",
    "CEFI_LIVE_VENUES",
    "COMPUTED_SOURCES",
    "EMISSION_LATENCY_MS_BY_SOURCE",
    "SOURCE_PRIORITY",
    "DivergenceKind",
    "assert_emission_latency_round_trip",
    "default_source",
    "detect_dual_source_conflicts",
    "emission_latency_ms_for_source",
    "external_sources_for",
    "get_all_sources_with_priority",
    "get_primary_source",
    "get_primary_source_with_latency",
    "get_source_priority",
    "has_source_priority",
    "read_with_source_priority",
    "select_primary_available_source",
    "source_required",
]
