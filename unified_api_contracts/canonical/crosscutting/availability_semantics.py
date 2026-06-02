"""Per-(asset_group, data_type) write-time `available_at` stamping rules.

SSOT for the semantic that determines a row's ``available_at`` column at
write-time. Per the workspace CLAUDE.md ``available_at`` rule:

> ``available_at`` is per-row, write-time, equal to live-pipeline-arrival
> (workspace-wide) — every shard's parquet contains an ``available_at``
> column. Each row's value = when the live pipeline would have actually
> had that row's information. NEVER derived at read-time.

Each :class:`AvailabilitySemantic` corresponds to a stamping helper in
``unified_trading_library.availability_stamping``; this module is the
[UAC] half of the layer split — it declares WHAT semantic applies for
each ``(asset_group, data_type)``, and UTL's stamping helpers implement
HOW to derive the timestamp from the source row.

Reference: writegate-honest-coverage plan Phase 1B + the historical-source-vs-live-pipeline
section of the workspace CLAUDE.md.
"""

from __future__ import annotations

from typing import Final, Literal

AvailabilitySemantic = Literal[
    "fetch_completed_at",
    "kickoff_minus_60min",
    "match_end_time",
    "event_time",
    "report_time",
    "announced_at",
    "forecast_issue_time",
    "publication_time",
    "tick_timestamp",
    "market_created_at",
]
"""The closed set of stamping semantics.

* ``fetch_completed_at`` — reference tables, instrument metadata, league rosters.
* ``kickoff_minus_60min`` — sports lineups (conservative; clip earlier leaks).
* ``match_end_time`` — post-match fixture stats, player stats, results, xG.
* ``event_time`` — fixture_events (per-row event timestamp).
* ``report_time`` — injuries (per-row report / occurrence timestamp).
* ``announced_at`` — fixtures (when the fixture itself was announced).
* ``forecast_issue_time`` — weather forecasts (issue time, NOT target time).
* ``publication_time`` — pre-match odds snapshots (per snapshot publication).
* ``tick_timestamp`` — CeFi / DeFi / TradFi market data; tick-time +
  source-priority scrape latency.
* ``market_created_at`` — prediction markets cannot have ticks before
  their listing time (lifecycle bound).
"""


# ---------------------------------------------------------------------------
# Per-(asset_group, data_type) registry.
# ---------------------------------------------------------------------------


AVAILABILITY_AT_SEMANTICS: Final[dict[tuple[str, str], AvailabilitySemantic]] = {
    # ---- Sports ----------------------------------------------------------
    ("sports", "FIXTURES"): "announced_at",
    ("sports", "FIXTURE_LINEUPS"): "kickoff_minus_60min",
    ("sports", "FIXTURE_EVENTS"): "event_time",
    ("sports", "INJURIES"): "report_time",
    ("sports", "FIXTURE_STATS"): "match_end_time",
    ("sports", "FIXTURE_PLAYER_STATS"): "match_end_time",
    ("sports", "RESULTS"): "match_end_time",
    ("sports", "UNDERSTAT_XG"): "match_end_time",
    ("sports", "SFI_PROGRESSIVE_STATS"): "match_end_time",
    ("sports", "ODDS_SNAPSHOT"): "publication_time",
    ("sports", "ODDS_MOVEMENT"): "publication_time",
    ("sports", "ARBITRAGE"): "publication_time",
    ("sports", "WEATHER_FORECAST"): "forecast_issue_time",
    # Sports raw data types written by instruments-service (as recorded in
    # the manifest and used by features-sports-service as upstream inputs).
    # These differ from the processed output types above (UNDERSTAT_XG,
    # WEATHER_FORECAST, ODDS_SNAPSHOT) which represent features-service outputs.
    ("sports", "XG"): "match_end_time",  # understat raw XG; post-match
    ("sports", "XG_SHOTS"): "match_end_time",  # understat per-shot XG; post-match
    ("sports", "MATCHES"): "match_end_time",  # footystats match data; post-match
    ("sports", "STANDINGS"): "fetch_completed_at",  # api_football standings; polled
    ("sports", "WEATHER"): "match_end_time",  # open_meteo reanalysis; post-match
    ("sports", "PREDICTIONS"): "announced_at",  # footystats pre-match predictions
    ("sports", "ODDS"): "publication_time",  # footystats raw odds
    ("sports", "ODDS_HORIZON_BUCKET"): "publication_time",  # MDPS bucketed odds
    ("sports", "TRANSFER_RECORDS"): "fetch_completed_at",  # transfermarkt transfers
    # Sports reference tables.
    ("sports", "TEAMS"): "fetch_completed_at",
    ("sports", "PLAYERS"): "fetch_completed_at",
    ("sports", "VENUES"): "fetch_completed_at",
    ("sports", "LEAGUES"): "fetch_completed_at",
    ("sports", "PLAYER_VALUES"): "fetch_completed_at",
    # ---- CeFi -----------------------------------------------------------
    ("cefi", "trades"): "tick_timestamp",
    ("cefi", "ohlcv_1m"): "tick_timestamp",
    ("cefi", "ohlcv_15m"): "tick_timestamp",
    ("cefi", "book_snapshot"): "tick_timestamp",
    ("cefi", "liquidations"): "tick_timestamp",
    ("cefi", "options_chain"): "tick_timestamp",
    ("cefi", "futures_chain"): "tick_timestamp",
    ("cefi", "perpetual"): "tick_timestamp",
    ("cefi", "funding_rate"): "tick_timestamp",
    # ---- DeFi -----------------------------------------------------------
    ("defi", "swap"): "tick_timestamp",
    ("defi", "fx_rate"): "tick_timestamp",
    ("defi", "liquidity"): "tick_timestamp",
    ("defi", "market_state"): "tick_timestamp",
    ("defi", "gas_fees"): "tick_timestamp",
    ("defi", "lst_yields"): "tick_timestamp",
    ("defi", "vault_state"): "tick_timestamp",
    # Phase 1A feature_dag seed gap (closed 2026-05-07): 5 on-chain DeFi
    # data_types that features-onchain consumes but were missing
    # availability_at semantics — blocked 10 of 12 onchain feature_groups
    # from completing the DAG seed. All 5 are per-event on-chain reads
    # where the row's own timestamp IS the available_at, matching every
    # other DeFi entry's ``tick_timestamp`` semantic. Per
    # ``unified_api_contracts.registry.market_data_categories``
    # ``DEFI_DATA_TYPES`` registry these are the canonical data_type
    # strings; any drift between this registry and that one is a bug.
    ("defi", "lending_indices"): "tick_timestamp",
    ("defi", "risk_params"): "tick_timestamp",
    ("defi", "rewards"): "tick_timestamp",
    ("defi", "flash_loan_events"): "tick_timestamp",
    ("defi", "eigenlayer_rewards"): "tick_timestamp",
    # Phase 5 audit 2026-05-11 (`ikenna-available-at-tab`) — every defi
    # data_type that an MTDS handler calls ``record_captured(...)`` on must
    # have a semantic entry, else stamping at write-time raises KeyError.
    # All 14 below are per-row on-chain event reads where the row's own
    # timestamp IS the available_at — same semantic as every other defi
    # entry above. Coverage probe: MTDS handler grep across
    # ``market_tick_data_service/cli/handlers/*.py`` for literal
    # ``record_captured(`` callsites with ``data_type=<literal>``.
    ("defi", "dex_pool_state"): "tick_timestamp",
    ("defi", "vault_share_price"): "tick_timestamp",
    ("defi", "solana_defi"): "tick_timestamp",
    ("defi", "oracle_prices"): "tick_timestamp",
    ("defi", "governance_events"): "tick_timestamp",
    ("defi", "perp_funding"): "tick_timestamp",
    ("defi", "staking_yields"): "tick_timestamp",
    ("defi", "bridge_events"): "tick_timestamp",
    ("defi", "position_data"): "tick_timestamp",
    ("defi", "token_transfers"): "tick_timestamp",
    ("defi", "liquidation_events"): "tick_timestamp",
    ("defi", "liquidations"): "tick_timestamp",
    ("defi", "mev_events"): "tick_timestamp",
    ("defi", "lst_rates"): "tick_timestamp",
    ("defi", "native_staking_rates"): "tick_timestamp",
    # hedge_ratio_snapshot — emitted by strategy-service at each rebalance
    # event (not a market-data tick); available_at = write-time per
    # ``fetch_completed_at`` semantic.  Phase 0 decision from
    # ``hedge_ratio_snapshot_persistence_2026_05_13``.
    ("defi", "hedge_ratio_snapshot"): "fetch_completed_at",
    # strategy_decision_context — emitted by strategy-service on EVERY tick
    # (not just rebalances); available_at = write-time per ``fetch_completed_at``
    # semantic.  Phase 5 decision from ``hedge_ratio_snapshot_persistence_2026_05_13``.
    ("defi", "strategy_decision_context"): "fetch_completed_at",
    # feature_observation_snapshot — emitted by features-onchain-service on
    # EVERY tick (per-tick APY inputs + provenance for audit chain).
    # features_tick_observation_audit_2026_05_18 Phase 1.
    ("defi", "feature_observation_snapshot"): "fetch_completed_at",
    # cross_instrument_signal — emitted by features-service cross_instrument
    # family at each batch run (multi-asset derived features); available_at =
    # write-time per ``fetch_completed_at`` (same pattern as other service-emitted
    # snapshots above). d5_features_missing_data_downgrade_2026_05_20 Phase 2.
    ("defi", "cross_instrument_signal"): "fetch_completed_at",
    # execution_fills — emitted by execution-service at result write time
    # (orders/fills/positions/equity batch + live paths); available_at = write-time.
    # d3_manifest_v8_finish_2026_05_20 Phase 1 — closes PipelineMode.BATCH_EXECUTION_SERVICE.
    ("cefi", "execution_fills"): "fetch_completed_at",
    ("defi", "execution_fills"): "fetch_completed_at",
    # ---- TradFi ---------------------------------------------------------
    ("tradfi", "trades"): "tick_timestamp",
    ("tradfi", "tbbo"): "tick_timestamp",
    ("tradfi", "ohlcv_1m"): "tick_timestamp",
    ("tradfi", "ohlcv_15m"): "tick_timestamp",
    ("tradfi", "options_chain"): "tick_timestamp",
    ("tradfi", "futures_chain"): "tick_timestamp",
    # commodity_signal — emitted by features-service commodity family from
    # EIA + CFTC + Baker Hughes + Open-Meteo + Yahoo factor inputs;
    # available_at = write-time per ``fetch_completed_at`` (downstream of
    # weekly EIA publication cadence). d5_features_missing_data_downgrade_2026_05_20 Phase 1.
    ("tradfi", "commodity_signal"): "fetch_completed_at",
    # ---- Prediction -----------------------------------------------------
    # Prediction CLOB ticks: tick_timestamp at write, but the orchestrator
    # ALSO clips by market_created_at upstream (no ticks before market
    # listing). The semantic here is the per-row stamp; lifecycle clipping
    # lives in instruments-service + MTDS pre-flight.
    ("prediction", "trades"): "tick_timestamp",
    ("prediction", "book_snapshot"): "tick_timestamp",
    ("prediction", "prediction_canonical_question_group"): "tick_timestamp",
    # MARKET_LIFECYCLE rows are written by instruments-service per
    # market_id (Polymarket conditionId / Kalshi ticker) and stamp the
    # available_at as ``market_created_at`` — we couldn't have known
    # about the market before it was listed. Predictions plan
    # ``predictions_canonical_question_group_polymarket_migration_2026_05_06.md``
    # Phase 1A.
    ("prediction", "MARKET_LIFECYCLE"): "market_created_at",
    # EIA commodity storage/series — weekly publication; available_at = fetch
    # completion time (row written after the weekly report is fetched and parsed).
    # features-commodity-service D5 Phase 1.
    ("tradfi", "energy_data"): "fetch_completed_at",
    # cross_instrument — features-service derived enrichment; written inline
    # at calculation time; available_at = write-time. D5 Phase 2.
    ("cefi", "cross_instrument"): "fetch_completed_at",
    # ---- Reference data (asset-group-agnostic) --------------------------
    ("reference", "instruments"): "fetch_completed_at",
    ("reference", "venue_trading_calendar"): "fetch_completed_at",
    # ---- Features-service computed outputs ------------------------------
    # commodity_features: batch-computed at write-time; available_at = fetch_completed_at.
    # D5 Phase 1 prerequisite — BATCH_EIA PipelineMode / SOURCE_PRIORITY round-trip.
    ("tradfi", "commodity_features"): "fetch_completed_at",
    # cross_instrument_features: batch-computed at write-time; available_at = fetch_completed_at.
    # D5 Phase 2 prerequisite — BATCH_CROSS_INSTRUMENT PipelineMode / SOURCE_PRIORITY round-trip.
    ("cefi", "cross_instrument_features"): "fetch_completed_at",
}


def get_availability_semantic(asset_group: str, data_type: str) -> AvailabilitySemantic:
    """Return the ``available_at`` stamping semantic for a shard.

    Args:
        asset_group: One of ``cefi`` / ``defi`` / ``tradfi`` / ``prediction``
            / ``sports`` / ``reference``.
        data_type: Canonical data_type string.

    Returns:
        The ``AvailabilitySemantic`` literal for the pair.

    Raises:
        KeyError: If the pair is not registered. Failing loud is intentional
            — silent fallback to a default like ``fetch_completed_at`` would
            mask schema-drift bugs (a new data_type that callers forgot to
            register here gets wrong stamping). Adding a new data_type
            requires registering it here in the same change.
    """
    key = (asset_group, data_type)
    if key not in AVAILABILITY_AT_SEMANTICS:
        msg = (
            f"No availability_at semantic registered for "
            f"asset_group={asset_group!r}, data_type={data_type!r}. "
            "Register the pair in AVAILABILITY_AT_SEMANTICS before use."
        )
        raise KeyError(msg)
    return AVAILABILITY_AT_SEMANTICS[key]


def has_availability_semantic(asset_group: str, data_type: str) -> bool:
    """Check whether the pair is registered (non-raising membership test)."""
    return (asset_group, data_type) in AVAILABILITY_AT_SEMANTICS


__all__ = [
    "AVAILABILITY_AT_SEMANTICS",
    "AvailabilitySemantic",
    "get_availability_semantic",
    "has_availability_semantic",
]
