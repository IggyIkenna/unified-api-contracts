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

from typing import Final

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
    # Sports snapshot-vs-candle discriminator (2026-08-08, sports_taxonomy_p1):
    # ``odds`` collapsed to ONE raw data_type, but MDPS derives TWO distinct
    # shapes from it — an OHLC candle (keyed via the ``odds`` entry above,
    # ``odds_ohlcv_{tf}``) and a LOCF point-in-time snapshot. Since this dict
    # is raw_dt -> ONE prefix, the snapshot form cannot reuse the ``odds`` key;
    # ``odds_snapshot`` here is an MDPS-INTERNAL lookup key only (NOT added to
    # ``DATA_TYPES_BY_ASSET_GROUP`` — it is not a new raw MTDS capture type).
    # SSOT: /codex/02-data/sports-data-types-catalog.md.
    "odds_snapshot": "odds_snap",
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

# Standard candle timeframe suffixes, used only to materialise
# ``PROCESSED_REQUIRES_RAW``'s legacy AGGREGATED keys (``{prefix}_{tf}``,
# e.g. ``ohlcv_15s`` / ``deriv_ohlcv_1d``) for pre-752eaff manifest rows that
# still carry that convention. ``24h`` is the legacy MDPS token for daily;
# ``1d`` is the UAC-canonical form — both are kept so manifest rows written
# under either token resolve consistently (intentional dual-key, not a bug:
# a historical-suffix compat set, not a going-forward vocabulary). ``15s``
# (2026-07-22) closes a real gap found during
# mdps_datatype_axis_switch_breaks_generic_classifier_2026_07_21's B2 review:
# MDPS_CANONICAL_TIMEFRAMES below includes ``15s`` as a genuine derived
# candle grain (``mdps_data_type_key`` can and does emit ``book5_ohlcv_15s``
# / ``ohlcv_15s`` etc.), so omitting it here left `is_processed_data_type`
# blind to any pre-cutover 15s-aggregate row — verified against the writer's
# real output (``canonical_writer_shaping.mdps_data_type_key``), not copied
# from an existing constant.
_TIMEFRAMES: tuple[str, ...] = ("15s", "1m", "5m", "15m", "1h", "4h", "1d", "24h")


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
            elif prefix == "odds_snap":
                # ``odds_snapshot`` (the dict key above) is an MDPS-internal
                # lookup token, NOT a genuine raw precondition — nothing ever
                # raw-captures it. The real raw precondition for the LOCF
                # snapshot form is ``odds`` itself (same source the OHLC
                # candle depends on), so it is substituted here rather than
                # falling through to the generic ``[raw_dt]`` branch, which
                # would wrongly declare a precondition that can never resolve.
                expanded[key] = ["odds"]
            else:
                expanded[key] = [raw_dt]
    for derived_dt, raw_sources in _DERIVED_ONLY.items():
        expanded[derived_dt] = list(raw_sources)
    return expanded


PROCESSED_REQUIRES_RAW: dict[str, list[str]] = _expand_processed_keys()

# ---------------------------------------------------------------------------
# MDPS timeframe-aware honest-coverage — SSOT for "what does MDPS derive
# candles from, and at which timeframes" (mtds_data_status_page_parity_2026_07_21).
# ---------------------------------------------------------------------------
#
# ``MDPS_DERIVABLE_DATA_TYPES`` is the set of SOURCE data_type tokens MDPS
# candle-derives FROM. Per the MDPS canonical_writer operator ruling
# (2026-07-21, "manifest data_type AXIS = SOURCE data_type; path==manifest on
# data_type"), an MDPS manifest row's ``data_type`` column carries the RAW
# source token (``trades``, ``book_snapshot_5``, ...) — the SAME vocabulary
# MTDS's raw-tick manifest rows use — with the candle timeframe living in a
# SEPARATE ``timeframe`` column. This is why ``get_expected_data_types_for_venue``
# must NARROW (not reuse) the venue's full raw-capability list for MDPS: most
# raw data_types a venue can produce (``gas_fees``, ``perp_funding``,
# ``eigenlayer_rewards``, event-typed handlers, ...) have no candle/aggregate
# form and MDPS never writes them — only the keys below do.
#
# Two sources compose the set:
#   1. ``_RAW_TO_PROCESSED_PREFIX`` keys — the raw dts with a direct MDPS
#      ``{prefix}_{tf}`` candle form (trades -> ohlcv_*, book_snapshot_5 ->
#      book5_ohlcv_*, liquidations -> liq_agg_*, the DEFI per-pool/index
#      types, ...).
#   2. ``_PASSTHROUGH_RAW_FOR_OHLCV`` (``["trades", "ohlcv_1m"]``) — TradFi
#      venues (CME/NASDAQ/NYSE/CBOE) declare their raw capability as
#      ``ohlcv_1m`` (Databento 1m passthrough), NOT ``trades``; MDPS derives
#      5m/15m/1h/4h/1d candles FROM that ``ohlcv_1m`` raw source exactly the
#      same way it derives them from CeFi ``trades``. Omitting ``ohlcv_1m``
#      here would make ``get_expected_data_types_for_venue(<tradfi venue>,
#      service="market-data-processing-service")`` return an empty set for
#      EVERY TradFi venue (they never declare raw ``trades``) — a silent
#      "MDPS produces nothing for TradFi" false negative.
MDPS_DERIVABLE_DATA_TYPES: frozenset[str] = frozenset(_RAW_TO_PROCESSED_PREFIX) | frozenset(_PASSTHROUGH_RAW_FOR_OHLCV)

# The canonical, forward-write timeframe set MDPS emits as its manifest
# ``timeframe`` column value (distinct from ``_TIMEFRAMES`` above, which
# additionally carries the legacy ``"24h"`` token so historical, already
# -written manifest data_type suffixes still resolve — this constant
# is the going-forward canonical form only, ``"1d"`` not ``"24h"``, per the
# ``_normalise_timeframe`` writer-side normalisation in MDPS
# ``canonical_writer_shaping.py``). Single-sourced by deployment-api's
# ``path_combinatorics.PROCESSING_TIMEFRAMES`` (2026-07-21 fix: that constant
# previously hardcoded ``"24h"``, which no real manifest row ever carries).
MDPS_CANONICAL_TIMEFRAMES: Final[tuple[str, ...]] = ("15s", "1m", "5m", "15m", "1h", "4h", "1d")


def get_expected_timeframes_for_venue_dt(venue: str, data_type: str) -> list[str]:
    """Return the expected MDPS candle timeframes for a ``(venue, data_type)`` pair.

    Today this ALWAYS returns the flat :data:`MDPS_CANONICAL_TIMEFRAMES` list,
    uniformly for every venue/data_type (open design question, DEFAULT
    resolution per mtds_data_status_page_parity_2026_07_21: no known
    (venue, data_type) pair has per-timeframe start-date divergence yet). The
    ``venue``/``data_type`` parameters are intentionally accepted-but-ignored
    so a future per-venue/per-dt override (e.g. a venue onboarded only at
    coarser timeframes) is a body-only change — no call-site signature churn.
    """
    _ = (venue, data_type)  # reserved for a future per-(venue, dt) override
    return list(MDPS_CANONICAL_TIMEFRAMES)


# Services whose manifest ``data_type`` axis is the SOURCE token, not the
# legacy AGGREGATED token (operator ruling 2026-07-21, MDPS
# ``canonical_writer.py`` "Manifest data_type AXIS = SOURCE data_type").
# ``is_processed_data_type``/``get_raw_source_data_types`` need this to
# disambiguate a bare SOURCE token like ``"trades"``/``"derivative_ticker"``,
# which is genuinely RAW under any other service (e.g. MTDS's own
# ``market-tick-data-service`` manifest rows) but is a PROCESSED candle row
# when observed under one of these services' own manifest scope — the token
# alone is ambiguous post-cutover; only the caller's ``service`` context
# resolves it. See
# mdps_datatype_axis_switch_breaks_generic_classifier_2026_07_21.md.
_SOURCE_AXIS_SERVICES: frozenset[str] = frozenset({"market-data-processing-service"})


def is_processed_data_type(data_type: str, *, service: str = "") -> bool:
    """Return ``True`` iff ``data_type`` is an MDPS-derived processed type.

    Used by deployment-api to decide whether to apply precondition logic
    (split missing-shards into ``missing`` vs ``blocked_on_raw``).

    ``service`` (optional, default ``""`` — BYTE-FOR-BYTE the pre-2026-07-22
    behaviour for every caller that doesn't pass it): when ``service`` is one
    of :data:`_SOURCE_AXIS_SERVICES`, a bare SOURCE token in
    :data:`MDPS_DERIVABLE_DATA_TYPES` (``"trades"``, ``"derivative_ticker"``,
    ...) is ALSO recognised as processed — this is what a post-752eaff MDPS
    manifest row's ``data_type`` actually carries. Without ``service``, the
    SOURCE token stays correctly classified as raw (it IS raw under e.g.
    MTDS's own manifest scope) — this is why the check is service-gated, not
    a global re-key: re-keying ``PROCESSED_REQUIRES_RAW`` itself to SOURCE
    tokens would make a genuine raw MTDS ``"trades"`` row misreport as
    processed too, since the same token means different things under
    different services post-cutover.
    """
    if data_type in PROCESSED_REQUIRES_RAW:
        return True
    return service in _SOURCE_AXIS_SERVICES and data_type in MDPS_DERIVABLE_DATA_TYPES


def get_raw_source_data_types(processed_data_type: str, *, service: str = "") -> list[str]:
    """Return the list of acceptable raw source dts for a processed dt.

    Returns an empty list when the data_type is not declared as processed
    — callers should branch on :func:`is_processed_data_type` first (pass the
    SAME ``service`` to both calls). A processed shard is "blocked on raw"
    only when *none* of the listed raw sources have a captured shard at the
    same coordinates.

    ``service``: see :func:`is_processed_data_type`. For a SOURCE-axis token
    resolved via the ``service`` branch, the raw source is the OHLCV
    passthrough set (:data:`_PASSTHROUGH_RAW_FOR_OHLCV`) when
    ``processed_data_type`` is itself one of those passthrough tokens, else
    the token IS its own raw source (mirrors the pre-cutover
    ``_RAW_TO_PROCESSED_PREFIX`` mapping, where e.g. ``deriv_ohlcv_*``'s only
    raw source was ``derivative_ticker`` itself).
    """
    if processed_data_type in PROCESSED_REQUIRES_RAW:
        return list(PROCESSED_REQUIRES_RAW[processed_data_type])
    if service in _SOURCE_AXIS_SERVICES and processed_data_type in MDPS_DERIVABLE_DATA_TYPES:
        if processed_data_type in _PASSTHROUGH_RAW_FOR_OHLCV:
            return list(_PASSTHROUGH_RAW_FOR_OHLCV)
        return [processed_data_type]
    return []


__all__ = [
    "MDPS_CANONICAL_TIMEFRAMES",
    "MDPS_DERIVABLE_DATA_TYPES",
    "PROCESSED_REQUIRES_RAW",
    "get_expected_timeframes_for_venue_dt",
    "get_raw_source_data_types",
    "is_processed_data_type",
]
