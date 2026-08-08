"""SINK_MATRIX — per-shard persistence configuration for the central event-log spine.

Every live ``(asset_group, data_type)`` shard that publishes to the Pub/Sub
central log must have an entry here. The matrix drives:

* Which sinks are enabled (hot-path subscription, GCS warm sink, BQ external table).
* Retention class (REPRODUCIBLE → TTL; STREAM_ONLY → forever, no TTL).
* Warm GCS TTL (~7d) and cold GCS TTL (REPRODUCIBLE: enumerated below; STREAM_ONLY: None).

The wildcard sentinel ``"*"`` in the ``asset_group`` position matches any
asset_group for cross-cutting shards (execution data, model predictions).

Resolver helpers :func:`retention_class_for` and :func:`sinks_for` raise
:exc:`KeyError` on unknown shards — no silent default. New connectors that
add a shard MUST add a SINK_MATRIX entry before going live (enforced by the
completeness gate in ``tests/unit/test_sink_matrix_completeness.py``).

Plan: ``live_data_persistence_central_event_log_2026_06_25.md`` Plan 01.
Audit seed: ``plans/audit/results/live_persist_00_audit_2026_06_26.md`` §2.
"""

from __future__ import annotations

from dataclasses import dataclass

from unified_api_contracts.events.persist import RetentionClass

# Wildcard sentinel: matches any asset_group when an exact entry is absent.
_WILDCARD = "*"


@dataclass(frozen=True)
class SinkConfig:
    """Configuration for one ``(asset_group, data_type)`` shard.

    Fields:

    * ``retention_class`` — REPRODUCIBLE (TTL-eligible) or STREAM_ONLY (forever).
    * ``hot`` — hot-path service consumer subscription enabled.
    * ``gcs_warm`` — Cloud Storage subscription sink enabled (~5-min batching).
    * ``table`` — BigQuery external table view enabled (D3: false for raw firehose shards).
    * ``warm_ttl_days`` — GCS warm tier TTL in days (always ~7; here for explicit docs).
    * ``cold_ttl_days`` — cold GCS TTL in days; ``None`` = STREAM_ONLY (never expire).
    * ``keep_flag`` — preserve beyond TTL even if REPRODUCIBLE (e.g. costly to refetch).
    """

    retention_class: RetentionClass
    hot: bool = True
    gcs_warm: bool = True
    table: bool = True
    warm_ttl_days: int = 7
    cold_ttl_days: int | None = None
    keep_flag: bool = False


# ---------------------------------------------------------------------------
# SINK_MATRIX
#
# Key: (asset_group, data_type) — use "*" for cross-cutting shards.
# Seed from audit: plans/audit/results/live_persist_00_audit_2026_06_26.md §2.
# D3 resolution: no firehose shards (MTDS produces windowed ticks only);
# all shards default table=True.
# ---------------------------------------------------------------------------

_R = RetentionClass.REPRODUCIBLE
_SO = RetentionClass.STREAM_ONLY

SINK_MATRIX: dict[tuple[str, str], SinkConfig] = {
    # -----------------------------------------------------------------------
    # MTDS shards (raw windowed ticks — 1-min UTCAlignedScheduler windows)
    # No true L2/L3/MBO firehose; table=True for all.
    # -----------------------------------------------------------------------
    ("cefi", "trades"): SinkConfig(_R, cold_ttl_days=90),
    ("cefi", "book_snapshot_5"): SinkConfig(_R, cold_ttl_days=30),
    ("cefi", "derivative_ticker"): SinkConfig(_R, cold_ttl_days=90),
    ("cefi", "liquidations"): SinkConfig(_R, cold_ttl_days=180),
    ("defi", "trades"): SinkConfig(_R, cold_ttl_days=90),
    ("defi", "book_snapshot_5"): SinkConfig(_R, cold_ttl_days=30),
    ("defi", "liquidations"): SinkConfig(_R, cold_ttl_days=180),
    ("defi", "lst_rates"): SinkConfig(_R, cold_ttl_days=365),
    ("defi", "lending_indices"): SinkConfig(_R, cold_ttl_days=365),
    ("defi", "dex_pool_state"): SinkConfig(_R, cold_ttl_days=365),
    ("defi", "dex_pool_swaps"): SinkConfig(_R, cold_ttl_days=90),
    ("defi", "arbitrage_price_dispersion"): SinkConfig(_R, cold_ttl_days=30),
    ("tradfi", "trades"): SinkConfig(_R, cold_ttl_days=90),
    ("sports", "odds"): SinkConfig(_R, cold_ttl_days=30),
    ("prediction", "trades"): SinkConfig(_R, cold_ttl_days=30),
    ("prediction", "book_snapshot"): SinkConfig(_R, cold_ttl_days=14),
    ("prediction", "book_snapshot_5"): SinkConfig(_R, cold_ttl_days=14),
    # -----------------------------------------------------------------------
    # MDPS shards — computed OHLCV candles (re-derivable from MTDS + formula)
    # Cross-cutting: one config covers all asset_groups via wildcard.
    # -----------------------------------------------------------------------
    (_WILDCARD, "candle"): SinkConfig(_R, cold_ttl_days=365),
    # -----------------------------------------------------------------------
    # features-service shards — all REPRODUCIBLE (pinned formula_version)
    # -----------------------------------------------------------------------
    # multi_timeframe family
    (_WILDCARD, "tf_momentum_alignment"): SinkConfig(_R, cold_ttl_days=180),
    (_WILDCARD, "tf_structure_context"): SinkConfig(_R, cold_ttl_days=180),
    (_WILDCARD, "tf_vol_compression"): SinkConfig(_R, cold_ttl_days=180),
    # cross_instrument family
    (_WILDCARD, "regime_detection"): SinkConfig(_R, cold_ttl_days=180),
    (_WILDCARD, "cross_venue_spreads"): SinkConfig(_R, cold_ttl_days=180),
    (_WILDCARD, "realized_implied_vol"): SinkConfig(_R, cold_ttl_days=180),
    (_WILDCARD, "cross_asset_correlation"): SinkConfig(_R, cold_ttl_days=180),
    (_WILDCARD, "cme_gap"): SinkConfig(_R, cold_ttl_days=180),
    (_WILDCARD, "book_depth_bands"): SinkConfig(_R, cold_ttl_days=90),
    (_WILDCARD, "liquidity_walls"): SinkConfig(_R, cold_ttl_days=90),
    (_WILDCARD, "liquidation_clusters"): SinkConfig(_R, cold_ttl_days=90),
    (_WILDCARD, "flow_interaction"): SinkConfig(_R, cold_ttl_days=90),
    (_WILDCARD, "composite_sr"): SinkConfig(_R, cold_ttl_days=180),
    # delta_one family
    (_WILDCARD, "technical_indicators"): SinkConfig(_R, cold_ttl_days=180),
    (_WILDCARD, "moving_averages"): SinkConfig(_R, cold_ttl_days=180),
    (_WILDCARD, "microstructure"): SinkConfig(_R, cold_ttl_days=90),
    # volatility family
    (_WILDCARD, "options_iv"): SinkConfig(_R, cold_ttl_days=180),
    (_WILDCARD, "options_term_structure"): SinkConfig(_R, cold_ttl_days=180),
    (_WILDCARD, "futures_basis"): SinkConfig(_R, cold_ttl_days=180),
    (_WILDCARD, "futures_term_structure"): SinkConfig(_R, cold_ttl_days=180),
    # calendar family
    (_WILDCARD, "time_features"): SinkConfig(_R, cold_ttl_days=365),
    (_WILDCARD, "economic_events"): SinkConfig(_R, cold_ttl_days=365),
    # sports family
    ("sports", "fixture_features"): SinkConfig(_R, cold_ttl_days=90),
    ("sports", "odds_features"): SinkConfig(_R, cold_ttl_days=30),
    ("sports", "derived_features"): SinkConfig(_R, cold_ttl_days=90),
    # commodity family
    ("commodity", "storage_alpha"): SinkConfig(_R, cold_ttl_days=180),
    ("commodity", "weather_delta"): SinkConfig(_R, cold_ttl_days=180),
    # onchain family
    ("defi", "lst_yields"): SinkConfig(_R, cold_ttl_days=365),
    ("defi", "lst_native_rates"): SinkConfig(_R, cold_ttl_days=365),
    # -----------------------------------------------------------------------
    # ml-service shards — REPRODUCIBLE with pinned model_id + model_version
    # keep_flag=True because model retraining is expensive; keep cold copy
    # even beyond TTL until operator explicitly rotates.
    # -----------------------------------------------------------------------
    (_WILDCARD, "per_strategy_signal"): SinkConfig(_R, cold_ttl_days=180, keep_flag=True),
    # -----------------------------------------------------------------------
    # execution-service shards — STREAM_ONLY / IRREPRODUCIBLE
    # System of record for fills/positions/PnL. cold_ttl_days=None = forever.
    # -----------------------------------------------------------------------
    (_WILDCARD, "execution_fills"): SinkConfig(_SO, cold_ttl_days=None),
    (_WILDCARD, "execution_positions"): SinkConfig(_SO, cold_ttl_days=None),
    (_WILDCARD, "execution_pnl"): SinkConfig(_SO, cold_ttl_days=None),
    (_WILDCARD, "paper_ledger"): SinkConfig(_SO, cold_ttl_days=None),
    # -----------------------------------------------------------------------
    # strategy-service shard — paper-LIVE routing seam (source="strategy").
    # AtomicInstructions published for execution-service's atomic_instruction_router
    # to route to AtomicLegExecutor.execute. STREAM_ONLY: this is the emitted
    # instruction itself (the system-of-record trigger for what execution acted
    # on), not a re-derivable market-data aggregate.
    # -----------------------------------------------------------------------
    (_WILDCARD, "atomic_instruction"): SinkConfig(_SO, cold_ttl_days=None),
}


def _resolve(asset_group: str, data_type: str) -> SinkConfig:
    exact = SINK_MATRIX.get((asset_group, data_type))
    if exact is not None:
        return exact
    wildcard = SINK_MATRIX.get((_WILDCARD, data_type))
    if wildcard is not None:
        return wildcard
    raise KeyError(
        f"No SINK_MATRIX entry for ({asset_group!r}, {data_type!r}). "
        "Add an entry before the shard goes live — no silent default."
    )


def retention_class_for(asset_group: str, data_type: str) -> RetentionClass:
    """Return the :class:`RetentionClass` for a shard.

    Raises :exc:`KeyError` if the shard is not in :data:`SINK_MATRIX`.
    Exact ``(asset_group, data_type)`` match first; wildcard ``"*"`` fallback.
    """
    return _resolve(asset_group, data_type).retention_class


def sinks_for(asset_group: str, data_type: str) -> SinkConfig:
    """Return the full :class:`SinkConfig` for a shard.

    Raises :exc:`KeyError` if the shard is not in :data:`SINK_MATRIX`.
    Exact ``(asset_group, data_type)`` match first; wildcard ``"*"`` fallback.
    """
    return _resolve(asset_group, data_type)


__all__ = [
    "SINK_MATRIX",
    "SinkConfig",
    "retention_class_for",
    "sinks_for",
]
