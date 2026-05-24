"""Raw → processed data type dependency map (SSOT).

Phase 1 of the unified-data-status work — pairs MTDS raw tick coverage
with MDPS processed/downsampled coverage by declaring which raw sources
each processed data type depends on. ``deployment-api`` uses this map
to classify processed-data manifest gaps as either:

    - missing (raw exists, processed doesn't — actionable MDPS gap)
    - blocked_on_raw (raw doesn't exist — fix upstream first)

SSOT contract: any data_type emitted by MDPS as a candle / aggregate
must declare its raw source(s) here. The mapping mirrors
``mdps_data_type_key()`` in market-data-processing-service
``app/core/canonical_writer.py`` — keep both in sync. Sister registry
``expected_coverage.py`` declares the operator-intent subset of
(venue, data_type) pairs we plan to keep filled.
"""

from __future__ import annotations

# Source data_type → MDPS-key prefix.
# Mirrors ``_DATA_TYPE_TO_MDPS_PREFIX`` in MDPS ``canonical_writer.py``;
# both must move together.
_RAW_TO_PROCESSED_PREFIX: dict[str, str] = {
    "trades": "ohlcv",
    "book_snapshot_5": "book5_ohlcv",
    "derivative_ticker": "deriv_ohlcv",
    "liquidations": "liq_agg",
    "dex_pool_swaps": "swaps_ohlcv",
    "dex_pool_state": "state_ohlcv",
    "lending_indices": "lending_ohlcv",
    "oracle_prices": "oracle_ohlcv",
    "lst_rates": "lst_ohlcv",
    "odds": "odds_ohlcv",
    "prediction_market": "pred_ohlcv",
}

# Pure-derivation processed types — not candles / aggregations of a single
# raw stream. ``arbitrage_opportunity`` is computed by MDPS across multiple
# bookmakers' raw odds, so the raw precondition is just ``odds`` (any
# bookmaker shard captured).
_DERIVED_ONLY: dict[str, list[str]] = {
    "arbitrage_opportunity": ["odds"],
}

# TradFi pre-aggregated 1m candles can serve as the "raw" source for higher
# timeframe ohlcv (5m / 15m / 1h / 1d aggregation from 1m). Any of `trades`
# (CeFi tick-level) or `ohlcv_1m` (Databento passthrough) satisfies the raw
# precondition for an `ohlcv_*` processed shard.
_PASSTHROUGH_RAW_FOR_OHLCV: list[str] = ["trades", "ohlcv_1m"]

# Standard candle timeframe suffixes. ``24h`` is the legacy MDPS token for
# daily; ``1d`` is the UAC-canonical form. Both are kept so manifest rows
# written under either token resolve consistently.
_TIMEFRAMES: tuple[str, ...] = ("1m", "5m", "15m", "1h", "4h", "1d", "24h")


def _expand_processed_keys() -> dict[str, list[str]]:
    """Materialise the full ``{processed_dt: [raw_dt, ...]}`` map.

    For each ``(raw_dt, prefix)`` pair, generate the ``{prefix}_{tf}``
    processed key and assign the appropriate raw source list. The
    ``ohlcv`` prefix is special-cased to accept both raw ``trades`` and
    pre-aggregated ``ohlcv_1m`` (TradFi Databento passthrough).

    ``ohlcv_1m`` is intentionally NOT classified as processed: in TradFi
    Databento emits it natively (raw); in CeFi MDPS derives it from
    trades. Both paths can fill an ``ohlcv_1m`` gap, so the precondition
    resolver should treat a missing ``ohlcv_1m`` shard as a plain
    missing (not blocked-on-raw) — backfill or derive, either works.
    Other ``{prefix}_1m`` keys (``book5_ohlcv_1m``, ``deriv_ohlcv_1m``,
    …) remain processed because their only source is raw 15s ticks.
    """
    expanded: dict[str, list[str]] = {}
    for raw_dt, prefix in _RAW_TO_PROCESSED_PREFIX.items():
        for tf in _TIMEFRAMES:
            if prefix == "ohlcv" and tf == "1m":
                continue
            key = f"{prefix}_{tf}"
            if prefix == "ohlcv":
                expanded[key] = list(_PASSTHROUGH_RAW_FOR_OHLCV)
            else:
                expanded[key] = [raw_dt]
    for derived_dt, raw_sources in _DERIVED_ONLY.items():
        expanded[derived_dt] = list(raw_sources)
    return expanded


PROCESSED_REQUIRES_RAW: dict[str, list[str]] = _expand_processed_keys()


def is_processed_data_type(data_type: str) -> bool:
    """Return ``True`` iff ``data_type`` is an MDPS-derived processed type.

    Used by deployment-api to decide whether to apply precondition logic
    (split missing-shards into ``missing`` vs ``blocked_on_raw``).
    """
    return data_type in PROCESSED_REQUIRES_RAW


def get_raw_source_data_types(processed_data_type: str) -> list[str]:
    """Return the list of acceptable raw source dts for a processed dt.

    Returns an empty list when the data_type is not declared as processed
    — callers should branch on :func:`is_processed_data_type` first.
    A processed shard is "blocked on raw" only when *none* of the listed
    raw sources have a captured shard at the same coordinates.
    """
    return list(PROCESSED_REQUIRES_RAW.get(processed_data_type, []))


__all__ = [
    "PROCESSED_REQUIRES_RAW",
    "get_raw_source_data_types",
    "is_processed_data_type",
]
