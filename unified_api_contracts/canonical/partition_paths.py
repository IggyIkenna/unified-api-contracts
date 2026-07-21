"""SSOT for non-sports per-asset-group GCS partition paths.

Sports already has its own domain-co-located SSOT at
:mod:`unified_api_contracts.canonical.domain.sports.gcs_paths` (tied to
fixture / league semantics, kept there for proximity). This module covers the
remaining 4 asset groups (CeFi, DeFi, TradFi, Prediction) — each writes to
its dedicated ``market-data-tick-{ag}-{pid}`` bucket but with different
partition keys per data shape.

Wire-format SSOT (matches deployed MTDS adapters as of 2026-05-02):

All 4 asset groups share the ``raw_tick_data/by_date/`` bucket-relative root
prefix. Concrete patterns:

DeFi (operator-locked 2026-06-01): ``pipeline_mode={mode}`` IS a CANONICAL
       segment of the DeFi path, inserted AFTER ``day={D}`` and BEFORE
       ``asset_group=defi`` (``mode`` ∈ ``batch``/``live``). Pass
       ``pipeline_mode=`` to :func:`build_defi_partition_path` to get it;
       ``None`` (the back-compat default) omits the segment.

       ``raw_tick_data/by_date/day={D}/pipeline_mode={mode}/asset_group=defi/
       venue={V}/chain={C}/instrument_type={IT}/data_type={DT}/{file}``

       (back-compat, ``pipeline_mode=None``):
       ``raw_tick_data/by_date/day={D}/asset_group=defi/venue={V}/chain={C}/
       instrument_type={IT}/data_type={DT}/{file}``
       SSOT: ``codex/02-data/defi-canonical-naming-ssot.md``.
CeFi: ``raw_tick_data/by_date/day={D}/asset_group=cefi/venue={V}/
       instrument_type={IT}/data_type={DT}/{file}``
TradFi: ``raw_tick_data/by_date/day={D}/pipeline_mode={mode}/asset_group=tradfi/venue={V}/
         instrument_type={IT}/data_type={DT}/{file}``
         (back-compat without segment: ``raw_tick_data/by_date/day={D}/asset_group=tradfi/...``)
Prediction: ``raw_tick_data/by_date/day={D}/asset_group=prediction/
             venue={V}/instrument_type={IT}/data_type={DT}/{condition_id}.parquet``

Pre-2026-05-02, the ``raw_tick_data/by_date/`` prefix was added by callers
(MTDS ``PartitionedTickWriter`` did the prepend; DeFi handlers via
``write_defi_rows`` did NOT — that gap put EigenLayer rewards / DEX swaps /
liquidations / etc. at bucket root ``day=*/...`` and produced 100% phantom
rates in the manifest audit). This module is now the single source of truth
for the FULL bucket-relative path including the prefix; callers must NOT
prepend further.

Use the unified dispatcher :func:`candidate_parquet_paths` for code that
spans asset_groups; use the per-asset-group ``build_*_partition_path``
functions for type-checked single-asset-group code.
"""

from __future__ import annotations

import datetime as _dt
import re
from enum import StrEnum
from typing import Final

from unified_api_contracts._instrument_enums import InstrumentType
from unified_api_contracts.canonical.gcs_paths import AssetGroup

# Hive partition key for the asset_group axis. Canonical wire-format value.
# Legacy on-disk objects use ``category=`` — readers that need both should try
# canonical first then fall back, but new writes use this key.
ASSET_GROUP_HIVE_KEY = "asset_group"

# Bucket-relative root prefix shared by all market-tick parquets across every
# asset_group. Includes the trailing ``/``. SSOT — never duplicate this string
# in writer code or readers; import it from here.
RAW_TICK_DATA_PREFIX = "raw_tick_data/by_date/"


# ---------------------------------------------------------------------------
# DeFi
# ---------------------------------------------------------------------------


def _normalize_venue_upper(venue: str) -> str:
    if not venue:
        msg = "venue must be a non-empty string"
        raise ValueError(msg)
    return venue.upper()


def _normalize_chain_upper(chain: str) -> str:
    if not chain:
        msg = "chain must be a non-empty string (DeFi rows require an explicit chain)"
        raise ValueError(msg)
    return chain.upper()


def build_defi_partition_path(
    *,
    venue: str,
    chain: str,
    instrument_type: InstrumentType,
    data_type: str,
    day: _dt.date,
    file_name: str,
    pipeline_mode: str | None = None,
) -> str:
    """Build the canonical DeFi partition path (full bucket-relative path).

    Wire format (returns the full path including the
    ``raw_tick_data/by_date/`` prefix — callers MUST NOT prepend further).

    With ``pipeline_mode`` (CANONICAL — operator-locked 2026-06-01), the
    ``pipeline_mode={mode}/`` segment is inserted AFTER ``day={D}/`` and BEFORE
    ``asset_group=defi/``:

    ``raw_tick_data/by_date/day={YYYY-MM-DD}/pipeline_mode={mode}/
    asset_group=defi/venue={V}/chain={C}/instrument_type={IT}/
    data_type={DT}/{file_name}``

    With ``pipeline_mode=None`` (back-compat default) the segment is omitted:

    ``raw_tick_data/by_date/day={YYYY-MM-DD}/asset_group=defi/venue={V}/
    chain={C}/instrument_type={IT}/data_type={DT}/{file_name}``

    Where ``venue`` is the protocol only (e.g. ``AAVE_V3``, ``UNISWAP_V3``,
    ``LIDO``) — never the legacy ``PROTOCOL-CHAIN`` overload — and
    ``chain`` is the uppercased chain identifier
    (``ETHEREUM`` / ``ARBITRUM`` / ``SOLANA`` / ``HYPERLIQUID`` / ...; see
    ``ChainKind`` + ``to_canonical_chain_wire`` for the Hyperliquid wire
    override). SSOT: ``codex/02-data/defi-canonical-naming-ssot.md``.

    Args:
        pipeline_mode: When provided, insert the canonical
            ``pipeline_mode={mode}/`` segment after ``day=`` (``mode`` ∈
            ``batch``/``live``). ``None`` (default) → no segment (back-compat).

    Example:
        >>> build_defi_partition_path(
        ...     venue="AAVE_V3",
        ...     chain="ETHEREUM",
        ...     instrument_type=InstrumentType.A_TOKEN,
        ...     data_type="lending_indices",
        ...     day=_dt.date(2026, 4, 17),
        ...     file_name="aUSDC.parquet",
        ... )
        'raw_tick_data/by_date/day=2026-04-17/asset_group=defi/venue=AAVE_V3/chain=ETHEREUM/instrument_type=a_token/data_type=lending_indices/aUSDC.parquet'
        >>> build_defi_partition_path(
        ...     venue="AAVE_V3",
        ...     chain="ETHEREUM",
        ...     instrument_type=InstrumentType.A_TOKEN,
        ...     data_type="lending_indices",
        ...     day=_dt.date(2026, 4, 17),
        ...     file_name="aUSDC.parquet",
        ...     pipeline_mode="batch",
        ... )
        'raw_tick_data/by_date/day=2026-04-17/pipeline_mode=batch/asset_group=defi/venue=AAVE_V3/chain=ETHEREUM/instrument_type=a_token/data_type=lending_indices/aUSDC.parquet'
    """
    if not data_type:
        msg = "data_type must be a non-empty string"
        raise ValueError(msg)
    if not file_name:
        msg = "file_name must be a non-empty string"
        raise ValueError(msg)

    v = _normalize_venue_upper(venue)
    c = _normalize_chain_upper(chain)
    # Hive partition values are lowercased for consistency with the rest of
    # the MTDS partition vocabulary (day=, asset_group=, data_type=). The
    # canonical ``instrument_id`` column preserves the enum's upper-case
    # value, so the two forms are deliberately distinct.
    it = instrument_type.value.lower()
    day_str = day.strftime("%Y-%m-%d")
    # ``pipeline_mode={mode}/`` is a CANONICAL DeFi segment (operator-locked
    # 2026-06-01) inserted after ``day=`` and before ``asset_group=``. This is
    # the SINGLE source for that segment — the cross-asset-group dispatcher
    # ``candidate_parquet_paths`` routes DeFi through here rather than
    # string-rewriting the bare path. ``None`` omits it (back-compat).
    pipeline_mode_segment = f"pipeline_mode={pipeline_mode}/" if pipeline_mode else ""
    return (
        f"{RAW_TICK_DATA_PREFIX}day={day_str}/{pipeline_mode_segment}{ASSET_GROUP_HIVE_KEY}=defi/"
        f"venue={v}/chain={c}/"
        f"instrument_type={it}/data_type={data_type}/"
        f"{file_name}"
    )


# ---------------------------------------------------------------------------
# CeFi
# ---------------------------------------------------------------------------
# Pattern derived from MTDS adapters
# (binance/, deribit/, okx/, bybit/, hyperliquid/, ...) which write through
# the shared raw-tick partitioning layer at
# ``market-data-tick-cefi-{pid}/raw_tick_data/by_date/``. CeFi has no chain
# axis (vs DeFi). instrument_type covers ``spot`` / ``perpetual`` / ``future``
# / ``option`` / ``index``.

# instrument_types that bundle an entire chain into a single file per
# underlying per day. Mirrors MTDS
# ``cefi/tardis_shared.py::CHAIN_INSTRUMENT_TYPES``.
CEFI_CHAIN_INSTRUMENT_TYPES: frozenset[str] = frozenset({"options_chain", "futures_chain"})


def build_cefi_partition_path(
    *,
    venue: str,
    instrument_type: InstrumentType | str,
    data_type: str,
    day: _dt.date,
    file_name: str,
    underlying: str = "",
    quote_asset: str = "",
    margin_type: str = "",
) -> str:
    """Build the canonical CeFi partition path (full bucket-relative path).

    Returns the full path including the ``raw_tick_data/by_date/`` prefix —
    callers MUST NOT prepend further.

    v5 (legacy) layout — single-symbol shards or callers leaving
    underlying / quote_asset / margin_type empty:

    ``raw_tick_data/by_date/day={YYYY-MM-DD}/asset_group=cefi/venue={V}/
    instrument_type={IT}/data_type={DT}/{file_name}``

    v6 layout (2026-04-23) — only when ``instrument_type`` is a CHAIN bundle
    (``options_chain`` / ``futures_chain``) AND all three of
    ``underlying`` / ``quote_asset`` / ``margin_type`` are populated:

    ``raw_tick_data/by_date/day=.../instrument_type={IT}/data_type={DT}/
    underlying={U}/quote={Q}/margin={M}/ticks.parquet``

    For per-symbol (non-chain) shards, v6 does NOT add extra path segments —
    the instrument_id itself already disambiguates
    (``BTC-PERPETUAL.parquet`` vs ``BTC_USDC-PERPETUAL.parquet``).

    Mirrors MTDS ``cefi/tardis_shared.py::build_partition_path``. Accepts
    either ``InstrumentType`` enum members or raw lowercase strings (the
    chain-bundle tokens ``options_chain`` / ``futures_chain`` aren't in the
    canonical enum so callers pass them as strings).
    """
    if not data_type:
        msg = "data_type must be a non-empty string"
        raise ValueError(msg)
    if not file_name:
        msg = "file_name must be a non-empty string"
        raise ValueError(msg)

    v = _normalize_venue_upper(venue)
    it = instrument_type.value.lower() if isinstance(instrument_type, InstrumentType) else instrument_type.lower()
    day_str = day.strftime("%Y-%m-%d")
    base = (
        f"{RAW_TICK_DATA_PREFIX}day={day_str}/{ASSET_GROUP_HIVE_KEY}=cefi/"
        f"venue={v}/instrument_type={it}/data_type={data_type}"
    )

    # v6 layout only for CHAIN bundles with all three axes populated.
    is_chain = it in CEFI_CHAIN_INSTRUMENT_TYPES
    if is_chain and underlying and quote_asset and margin_type:
        return (
            f"{base}/underlying={underlying.upper()}/quote={quote_asset.upper()}/"
            f"margin={margin_type.lower()}/ticks.parquet"
        )

    return f"{base}/{file_name}"


# ---------------------------------------------------------------------------
# TradFi
# ---------------------------------------------------------------------------
# Pattern derived from MTDS adapters (fred_adapter, databento_opra_converter,
# tardis_adapter). TradFi has venue-as-source (``FRED``, ``OPRA``, ``CME``,
# ``DATABENTO``, ``TARDIS``) and no chain axis. Some sources (FRED) emit
# series-keyed shards rather than instrument_type-keyed; for those,
# ``instrument_type`` carries the series-class token (e.g. ``rates``,
# ``options``, ``etf_flows``).

# instrument_types that bundle an entire chain into a single file per
# underlying per day. Mirrors MTDS
# ``tradfi/tradfi_shared.py::CHAIN_INSTRUMENT_TYPES`` and the CeFi v6 chain
# layout. ``combo`` is deliberately EXCLUDED (its leg-aware id format is
# unsettled — combo chains keep the bare ``underlying=.../ticks.parquet``
# fan-in without the quote/margin tail).
TRADFI_CHAIN_INSTRUMENT_TYPES: frozenset[str] = frozenset({"options_chain", "futures_chain"})

# Single-instrument tradfi types whose canonical shard filename is the FULL
# instrument_id (``NYSE:EQUITY:ABBV-USD.parquet``). Mirrors MTDS
# ``tradfi/tradfi_shared.py::SINGLE_INSTRUMENT_TYPES`` minus ``combo`` (excluded,
# bare-symbol). The write-time guard enforces the full-id filename for THESE
# itypes only — special bundle types (``event_contract`` / ``combo``) that do
# not yet carry a canonical id are left alone.
TRADFI_SINGLE_INSTRUMENT_TYPES: frozenset[str] = frozenset(
    {"equity", "etf", "index", "currency", "bond", "cds", "commodity", "future", "option", "spot_pair"}
)


def build_tradfi_partition_path(
    *,
    venue: str,
    instrument_type: InstrumentType | str,
    data_type: str,
    day: _dt.date,
    file_name: str,
    pipeline_mode: str | None = None,
    underlying: str = "",
    quote_asset: str = "",
    margin_type: str = "",
) -> str:
    """Build the canonical TradFi partition path (full bucket-relative path).

    Returns the full path including the ``raw_tick_data/by_date/`` prefix —
    callers MUST NOT prepend further.

    With ``pipeline_mode`` (canonical — operator-locked 2026-06-01), the
    ``pipeline_mode={mode}/`` segment is inserted AFTER ``day={D}/`` and
    BEFORE ``asset_group=tradfi/``:

    ``raw_tick_data/by_date/day={YYYY-MM-DD}/pipeline_mode={mode}/
    asset_group=tradfi/venue={V}/instrument_type={IT}/data_type={DT}/{file_name}``

    Without ``pipeline_mode`` (``None``, back-compat default) the segment is
    omitted — matching the legacy on-disk shape that readers still probe via
    the fallback chain in :func:`candidate_parquet_paths`.

    ``raw_tick_data/by_date/day={YYYY-MM-DD}/asset_group=tradfi/venue={V}/
    instrument_type={IT}/data_type={DT}/{file_name}``

    v6 chain layout (2026-07-19) — only when ``instrument_type`` is a CHAIN
    bundle (``options_chain`` / ``futures_chain``) AND all three of
    ``underlying`` / ``quote_asset`` / ``margin_type`` are populated (mirrors
    :func:`build_cefi_partition_path` byte-for-byte + the shipped migration
    executor ``migrate_tradfi_canonical_2026_07._canonical_chain_path``):

    ``raw_tick_data/by_date/day=.../instrument_type={IT}/data_type={DT}/
    underlying={U}/quote={Q}/margin={M}/ticks.parquet``

    For single-instrument (non-chain) shards, the v6 layout does NOT add extra
    path segments — the ``file_name`` already carries the full canonical
    instrument_id (``NYSE:EQUITY:ABBV-USD.parquet``).

    Accepts either an ``InstrumentType`` enum member or a raw lowercase string
    (the chain-bundle tokens ``options_chain`` / ``futures_chain`` are not in
    the canonical enum so callers pass them as strings — same as CeFi).

    Used by FRED (rates curve via DGS series), OPRA (options chains via
    Databento), Tardis (ETF flows / institutional feeds), CME (futures
    chains).
    """
    if not data_type:
        msg = "data_type must be a non-empty string"
        raise ValueError(msg)
    if not file_name:
        msg = "file_name must be a non-empty string"
        raise ValueError(msg)

    v = _normalize_venue_upper(venue)
    it = instrument_type.value.lower() if isinstance(instrument_type, InstrumentType) else instrument_type.lower()
    day_str = day.strftime("%Y-%m-%d")
    pipeline_mode_segment = f"pipeline_mode={pipeline_mode}/" if pipeline_mode else ""
    base = (
        f"{RAW_TICK_DATA_PREFIX}day={day_str}/{pipeline_mode_segment}"
        f"{ASSET_GROUP_HIVE_KEY}=tradfi/"
        f"venue={v}/instrument_type={it}/data_type={data_type}"
    )

    # v6 layout only for CHAIN bundles with all three axes populated.
    is_chain = it in TRADFI_CHAIN_INSTRUMENT_TYPES
    if is_chain and underlying and quote_asset and margin_type:
        return (
            f"{base}/underlying={underlying.upper()}/quote={quote_asset.upper()}/"
            f"margin={margin_type.lower()}/ticks.parquet"
        )

    return f"{base}/{file_name}"


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------
# Pattern derived from MTDS prediction adapters (polymarket, kalshi).
# Prediction venues key by ``condition_id`` (the on-chain market
# resolution identifier) — a market lifetime spans many days, but each
# day's tick shard partitions by condition. instrument_type carries the
# market category (``binary`` / ``categorical`` / ``scalar``).


def _sanitize_symbol(symbol: str) -> str:
    """Match MTDS ``orchestrator._sanitize_symbol``: replace ``/`` with ``_``
    so condition_ids with slashes (rare) don't escape into directory names."""
    return symbol.replace("/", "_") if symbol else "_unknown_"


def build_prediction_partition_path(
    *,
    venue: str,
    condition_id: str,
    instrument_type: InstrumentType | str = "prediction_market",
    data_type: str,
    day: _dt.date,
) -> str:
    """Build the canonical Prediction partition path (full bucket-relative path).

    Returns the full path including the ``raw_tick_data/by_date/`` prefix —
    callers MUST NOT prepend further.

    Wire format (verified 2026-04-29 against MTDS orchestrator
    ``PartitionedTickWriter`` lines 640-650 and adapters
    ``prediction/polymarket_adapter.py`` line 532-541 +
    ``prediction/kalshi_adapter.py`` line 256-261):

    ``raw_tick_data/by_date/day={YYYY-MM-DD}/asset_group=prediction/
    venue={V}/instrument_type={IT}/data_type={DT}/{condition_id}.parquet``

    The ``condition_id`` is used as the per-instrument FILENAME (matching
    the per-instrument-symbol writer pattern), NOT a partition segment.
    All Polymarket/Kalshi markets share
    ``instrument_type=prediction_market``; per-market disambiguation
    happens via the ``condition_id`` filename.

    Args:
        venue: ``POLYMARKET`` / ``KALSHI``.
        condition_id: Per-market identifier (Polymarket
            ``conditionId`` / Kalshi event_ticker).
            Used as the parquet file stem.
        instrument_type: Defaults to ``"prediction_market"`` matching
            production. Override only if a future variant emerges.
        data_type: ``trades`` / ``book_snapshot`` / ``market_metadata``.
        day: Partition day.
    """
    if not condition_id:
        msg = "condition_id must be a non-empty string"
        raise ValueError(msg)
    if not data_type:
        msg = "data_type must be a non-empty string"
        raise ValueError(msg)

    v = _normalize_venue_upper(venue)
    it = instrument_type.value.lower() if isinstance(instrument_type, InstrumentType) else instrument_type.lower()
    day_str = day.strftime("%Y-%m-%d")
    sanitized = _sanitize_symbol(condition_id)
    return (
        f"{RAW_TICK_DATA_PREFIX}day={day_str}/{ASSET_GROUP_HIVE_KEY}=prediction/"
        f"venue={v}/instrument_type={it}/data_type={data_type}/{sanitized}.parquet"
    )


# ---------------------------------------------------------------------------
# Cross-asset-group dispatcher
# ---------------------------------------------------------------------------


def candidate_parquet_paths(
    asset_group: AssetGroup | str,
    data_type: str,
    day: _dt.date,
    *,
    pipeline_mode: str | None = None,
    **kwargs: object,
) -> list[str]:
    """Return ordered list of candidate partition paths for any asset_group.

    When ``pipeline_mode`` is provided, the pipeline_mode-aware canonical path
    ``raw_tick_data/by_date/day={D}/pipeline_mode={mode}/asset_group={ag}/...``
    is prepended as the first probe; the existing path without the segment
    follows as a fallback (Phase 5.3 migration fallback chain). Default
    ``None`` returns only the existing paths (back-compat).

    Args:
        asset_group: Asset group enum or lowercase string token.
        data_type: Data type token (asset-group-specific vocabulary).
        day: Partition day.
        pipeline_mode: When provided, prepend the pipeline_mode-aware
            canonical path as the first probe. See
            :mod:`unified_api_contracts.canonical.domain.sports.gcs_paths`
            for the Sports flavour.
        **kwargs: Asset-group-specific path components.
            - DeFi: ``venue``, ``chain``, ``instrument_type``, ``file_name``.
            - CeFi / TradFi: ``venue``, ``instrument_type``, ``file_name``.
            - Prediction: ``venue``, ``condition_id``, ``instrument_type``,
              ``file_name``.
            - Sports: ``league_id`` (optional). Sports has its own
              ``include_legacy_archive`` knob — see
              :mod:`unified_api_contracts.canonical.domain.sports.gcs_paths`.

    Returns:
        Ordered list of candidate paths (most-likely first) without bucket
        prefix. Caller probes each in turn; first hit wins.
    """
    ag = AssetGroup(asset_group) if not isinstance(asset_group, AssetGroup) else asset_group

    if ag == AssetGroup.SPORTS:
        # Sports lives in its domain-co-located module — delegate.
        from unified_api_contracts.canonical.domain.sports.gcs_paths import (
            candidate_parquet_paths as sports_candidates,
        )

        _league_id_raw = kwargs.get("league_id")
        league_id = str(_league_id_raw) if _league_id_raw is not None else ""
        include_legacy_archive = bool(kwargs.get("include_legacy_archive", False))
        return sports_candidates(
            data_type=data_type,
            day=day.strftime("%Y-%m-%d"),
            league_id=league_id,
            include_legacy_archive=include_legacy_archive,
            pipeline_mode=pipeline_mode,
        )

    day_str = day.strftime("%Y-%m-%d")

    def _prepend_pipeline_mode(path: str) -> str:
        """Insert ``pipeline_mode={mode}/`` after ``day={D}/`` in a canonical path.

        Used by CeFi / TradFi / Prediction. DeFi does NOT use this — its
        ``pipeline_mode={mode}/`` segment is canonical and produced directly by
        :func:`build_defi_partition_path` (the single source), so the DeFi
        branch passes ``pipeline_mode`` through to the builder instead.
        """
        marker = f"day={day_str}/{ASSET_GROUP_HIVE_KEY}="
        return path.replace(marker, f"day={day_str}/pipeline_mode={pipeline_mode}/{ASSET_GROUP_HIVE_KEY}=", 1)

    if ag == AssetGroup.DEFI:
        # DeFi: pipeline_mode= is a CANONICAL segment owned by the builder
        # (operator-locked 2026-06-01) — pass it through so the builder is the
        # single source, rather than string-rewriting the bare path. The
        # canonical (with-segment) path is the first probe; the bare path
        # follows as a migration fallback.
        bare = build_defi_partition_path(
            venue=str(kwargs["venue"]),
            chain=str(kwargs["chain"]),
            instrument_type=_coerce_instrument_type(kwargs["instrument_type"]),
            data_type=data_type,
            day=day,
            file_name=str(kwargs["file_name"]),
        )
        if pipeline_mode:
            canonical = build_defi_partition_path(
                venue=str(kwargs["venue"]),
                chain=str(kwargs["chain"]),
                instrument_type=_coerce_instrument_type(kwargs["instrument_type"]),
                data_type=data_type,
                day=day,
                file_name=str(kwargs["file_name"]),
                pipeline_mode=pipeline_mode,
            )
            return [canonical, bare]
        return [bare]

    if ag == AssetGroup.CEFI:
        base = build_cefi_partition_path(
            venue=str(kwargs["venue"]),
            instrument_type=_coerce_instrument_type(kwargs["instrument_type"]),
            data_type=data_type,
            day=day,
            file_name=str(kwargs["file_name"]),
        )
        if pipeline_mode:
            return [_prepend_pipeline_mode(base), base]
        return [base]

    if ag == AssetGroup.TRADFI:
        # TradFi: pipeline_mode= is a CANONICAL segment (operator-locked
        # 2026-06-01) — pass it through to the builder (single code path)
        # so the UAC builder is the sole source of path-construction logic.
        # The canonical (with-segment) path is the first probe; the bare
        # path follows as a migration fallback (Phase 5.3 / 8 window).
        if pipeline_mode:
            canonical = build_tradfi_partition_path(
                venue=str(kwargs["venue"]),
                instrument_type=_coerce_instrument_type(kwargs["instrument_type"]),
                data_type=data_type,
                day=day,
                file_name=str(kwargs["file_name"]),
                pipeline_mode=pipeline_mode,
            )
            base = build_tradfi_partition_path(
                venue=str(kwargs["venue"]),
                instrument_type=_coerce_instrument_type(kwargs["instrument_type"]),
                data_type=data_type,
                day=day,
                file_name=str(kwargs["file_name"]),
            )
            return [canonical, base]
        return [
            build_tradfi_partition_path(
                venue=str(kwargs["venue"]),
                instrument_type=_coerce_instrument_type(kwargs["instrument_type"]),
                data_type=data_type,
                day=day,
                file_name=str(kwargs["file_name"]),
            )
        ]

    if ag == AssetGroup.PREDICTION:
        instrument_type_raw = kwargs.get("instrument_type", "prediction_market")
        if isinstance(instrument_type_raw, InstrumentType):
            instrument_type_arg: InstrumentType | str = instrument_type_raw
        else:
            instrument_type_arg = str(instrument_type_raw)
        base = build_prediction_partition_path(
            venue=str(kwargs["venue"]),
            condition_id=str(kwargs["condition_id"]),
            instrument_type=instrument_type_arg,
            data_type=data_type,
            day=day,
        )
        if pipeline_mode:
            return [_prepend_pipeline_mode(base), base]
        return [base]

    msg = f"unsupported asset_group: {ag!r}"
    raise ValueError(msg)


def _coerce_instrument_type(value: object) -> InstrumentType:
    """Accept either an InstrumentType or its string token (case-insensitive).

    The enum values are uppercase (``PERPETUAL`` / ``A_TOKEN`` / ``POOL``),
    but partition-path callers often hold the lowercase wire-format token
    (``perpetual`` / ``a_token`` / ``pool``). Both are accepted.
    """
    if isinstance(value, InstrumentType):
        return value
    if isinstance(value, str):
        return InstrumentType(value.upper())
    msg = f"instrument_type must be InstrumentType or str, got {type(value).__name__}"
    raise TypeError(msg)


# ---------------------------------------------------------------------------
# Path-canonicality validator (failure class C3 —
# data_pipeline_hardening_self_monitoring_2026_06_22.md Phase 3 / Phase 4).
#
# The ``build_*_partition_path`` builders above CONSTRUCT canonical paths;
# :func:`is_canonical` is the inverse — it parses an arbitrary GCS path and
# asserts it matches the canonical shape, catching the documented drift
# classes that have silently corrupted the manifest:
#   - ``day-YYYY-MM-DD`` hyphen dir instead of ``day=YYYY-MM-DD``
#   - a glued ``VENUE-CHAIN`` venue token instead of separate
#     ``venue=.../chain=...`` segments (the legacy PROTOCOL-CHAIN overload)
#   - a glued ``V{N}`` version inside the venue token (e.g. ``AAVEV3`` vs
#     ``AAVE_V3``)
#   - an ``asset_group=`` value outside the closed set
#   - a missing ``pipeline_mode={mode}_{source}/`` segment (only when
#     ``require_pipeline_mode=True`` — bare back-compat paths the builders
#     still emit are accepted by default)
#
# Pragmatic, not a full grammar: it catches the documented drift shapes, and
# round-trips against every ``build_*_partition_path`` output (see the unit
# tests). Used by the Phase 3 hygiene orchestrator and the Phase 4 writer-side
# assert. Registry SSOT: DP-PATH-001..004.
# ---------------------------------------------------------------------------

_CANONICAL_ASSET_GROUPS: Final[frozenset[str]] = frozenset(member.value for member in AssetGroup)
"""Closed set of ``asset_group=`` hive values: {cefi, defi, tradfi, sports, prediction}."""

# A canonical ``day=`` partition value is an ISO date ``YYYY-MM-DD``.
_DAY_VALUE_RE: Final[re.Pattern[str]] = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Canonical pipeline_mode value is ``{mode}_{source}`` (mode ∈ batch/live/replay),
# optionally ``{mode}_{source}_{transport}``. The vendor source token may itself
# carry underscores, so we only assert the leading mode + at least one source
# segment separated by ``_``.
_PIPELINE_MODE_VALUE_RE: Final[re.Pattern[str]] = re.compile(r"^(batch|live|replay)_[a-z0-9]+(?:_[a-z0-9]+)*$")

# A glued ``V{N}`` version suffix directly fused onto an alphanumeric token
# (e.g. ``AAVEV3`` / ``UNISWAPV3``) — the canonical form separates it with an
# underscore (``AAVE_V3`` / ``UNISWAP_V3``).
_GLUED_VERSION_RE: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9]V\d")


class CanonicalViolationClass(StrEnum):
    """Which QUESTION a canonical-path violation answers.

    Path-STRUCTURE canonicality and instrument-id FORM canonicality are
    ORTHOGONAL — neither alone proves a path is canonical:

    ``STRUCTURAL``
        The hive skeleton: canonical prefix, ``day=YYYY-MM-DD``, ``key=value``
        partition segments, ``pipeline_mode={mode}_{source}``, the closed
        ``asset_group=`` set, the glued ``VENUE-CHAIN`` / ``V{N}`` guards and
        the tradfi chain quote/margin tail.
    ``ID_FORM``
        The FILENAME STEM: whether the per-instrument shard is named for a
        canonical ``instrument_id`` (``VENUE:ITYPE:BASE-QUOTE[@LIN|@INV]…``)
        rather than a raw venue wire symbol (``ADAF0:USTF0``) or a
        double-wrapped ``VENUE:ITYPE:<raw wire>`` catalogue-miss id.

    Until 2026-07-20 this module validated the stem for ``asset_group=tradfi``
    single-instrument shards ONLY, so a CeFi corpus carrying ~811,200
    wire-named objects came back CANONICAL (zero violations) from the machine
    oracle — a FALSE-CLEAN verdict for the exact defect the four-surface
    reconciliation procedure exists to catch. Both classes are now reported by
    DEFAULT; ``violation_classes=`` narrows the answer for callers that must
    enforce one class at a time. SSOT:
    ``plans/active/issues/canonical_path_oracle_blind_to_filename_stem_2026_07_20.md``.
    """

    STRUCTURAL = "structural"
    ID_FORM = "id_form"


# Canonical instrument_id shape (the ID-FORM oracle). Mirrors the resolver SSOT
# ``VENUE:ITYPE:BASE-QUOTE[@LIN|@INV][-YYYYMMDD][-STRIKE-C|P]`` plus the COMBO
# arm (COMBO ids are canonical but carry a free-form tail). Also covers the
# chain-less DeFi ``PERPETUAL`` lane (GMX) — ``VENUE:PERPETUAL:BASE-QUOTE`` —
# which deliberately has NO ``-CHAIN`` suffix (routes the cefi-simple builder
# branch, see ``canonical_id_builder.py``'s dispatch table).
_CANONICAL_INSTRUMENT_ID_RE: Final[re.Pattern[str]] = re.compile(
    r"^[A-Z0-9._-]+:(PERPETUAL|FUTURE|OPTION|SPOT_PAIR):[A-Z0-9]+-[A-Z0-9]+"
    r"(@(LIN|INV))?(-\d{8})?(-\d+(\.\d+)?-[CP])?$"
)
_COMBO_INSTRUMENT_ID_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Z0-9._-]+:COMBO:.+$")

# Canonical DeFi instrument_id shape (ID-FORM oracle widening, 2026-07-21) — the
# ratified grammar per DeFi type (``defi_consolidated_closeout_2026_07_18.md``
# "Instrument-uid grammar per DeFi type"): base = ``VENUE-CHAIN:TYPE:SYMBOL``,
# DeFi being the only asset group whose venue segment carries a ``-CHAIN``
# suffix (the venue itself may be compound, e.g. ``ETHERFI-GOV-ETHEREUM``, so
# the venue-chain segment requires only >=1 hyphen, not exactly one). The
# per-type SYMBOL variants (POOL glues its fee tier INTO the symbol with a
# hyphen — ``TOKEN0-TOKEN1[-FEE_BPS]``, operator ruling 2026-07-18; A_TOKEN /
# DEBT_TOKEN append an isolated-market id the same way; a Curve/Balancer
# multi-token pool symbol is an arbitrary-length hyphen chain; a bare
# LST/YIELD_BEARING/STAKING/SPOT_ASSET/RESTAKING token has zero extra
# segments) all reduce to the SAME hyphen-joined-segment shape, so one
# permissive symbol class covers every DeFi type without per-type
# sub-patterns. Symbol case is PRESERVED (not upper-cased, unlike CeFi/TradFi)
# because on-chain token symbols are case-sensitive (``aUSDC``, ``stETH``,
# ``variableDebtUSDC``). GMX's chain-less ``PERPETUAL`` DeFi lane is
# deliberately ABSENT from the type alternation here — it already matches
# :data:`_CANONICAL_INSTRUMENT_ID_RE` above. ``LENDING`` (the legacy flat
# lending type) stays in the alternation for the migration interim — see
# ``defi_consolidated_closeout_2026_07_18.md`` "Lending — ONE SSOT".
_DEFI_INSTRUMENT_ID_RE: Final[re.Pattern[str]] = re.compile(
    r"^[A-Z0-9_]+(?:-[A-Z0-9_]+)+:"
    r"(?:SPOT_ASSET|POOL|DEX_POOL|A_TOKEN|DEBT_TOKEN|LST|YIELD_BEARING|STAKING|RESTAKING|"
    r"SOLANA_AMM_POOL|SOLANA_LENDING|SOLANA_VAULT|LENDING):"
    r"[A-Za-z0-9_.]+(?:-[A-Za-z0-9_.]+)*$"
)

# Fan-in shard filenames that legitimately carry NO per-instrument stem: chain
# bundles (``underlying=…/ticks.parquet``) and the symbol-less prediction
# ``book_snapshot_5`` fallback. These must NEVER be flagged by the ID-FORM
# oracle — they are canonical BY SHAPE, not by stem.
_STEMLESS_FAN_IN_FILE_NAMES: Final[frozenset[str]] = frozenset({"ticks.parquet"})

# Asset groups whose per-instrument shard filename is contractually the FULL
# canonical instrument_id. ``sports`` / ``prediction`` are DELIBERATELY absent:
# their ids route through domain-specific builders (fixture ids, condition
# ids) whose grammar is not the ``VENUE:ITYPE:BASE-QUOTE``/``VENUE-CHAIN:TYPE:
# SYMBOL`` shape, so applying this regex there would manufacture false
# violations. ``prediction``'s id grammar is explicitly OUT OF SCOPE here — it
# is its own future closeout (``defi_consolidated_closeout_2026_07_18.md``
# Track 1). ``defi`` widened 2026-07-21 — the grammar is ratified (see
# :data:`_DEFI_INSTRUMENT_ID_RE`); this is expected to surface a large
# NON_CANONICAL population on the current corpus (today's DeFi single-instrument
# filenames are the bare ``symbol`` column, not yet the wrapped id — see
# ``market-tick-data-service/.../partitioned_writer.py::_resolve_file_symbol``,
# "defi/sports are untouched"), the same honest-disclosure outcome the CeFi
# widening produced (20.82% canonical, not 100%) — NOT a bug in this checker.
# Widening ``prediction`` requires an id grammar for that asset group first.
_ID_FORM_CHECKED_ASSET_GROUPS: Final[frozenset[str]] = frozenset({"cefi", "defi"})


def is_canonical_instrument_id(candidate: str) -> bool:
    """True iff ``candidate`` is a canonical instrument_id (incl. the COMBO arm).

    The ID-FORM half of canonicality — deliberately independent of
    :func:`canonical_path_violations`'s path-STRUCTURE checks. A raw venue wire
    symbol (``ADAF0:USTF0``), a double-wrapped catalogue-miss id
    (``BITFINEX-FUTURES:PERPETUAL:ADAF0:USTF0``) and a bare symbol (``BTCUSD``)
    all return False. Recognises the CeFi/TradFi ``VENUE:ITYPE:BASE-QUOTE``
    shape, the COMBO arm, and the DeFi ``VENUE-CHAIN:TYPE:SYMBOL`` shape
    (:data:`_DEFI_INSTRUMENT_ID_RE`) — the three alternatives never overlap
    (disjoint TYPE-token alternations), so widening acceptance here is
    additive and cannot turn a previously-rejected CeFi/TradFi stem into a
    false positive.
    """
    return bool(
        _CANONICAL_INSTRUMENT_ID_RE.match(candidate)
        or _COMBO_INSTRUMENT_ID_RE.match(candidate)
        or _DEFI_INSTRUMENT_ID_RE.match(candidate)
    )


def _cefi_chain_tail_violations(
    asset_group: str | None, kv: dict[str, str], partition_segments: list[str], file_name: str
) -> list[str]:
    """STRUCTURAL violations for a cefi ``options_chain``/``futures_chain`` shard's tail.

    Operator ruling 2026-07-21: the cefi chain-tail v6 shape
    (``underlying=<BASE>/quote=<Q>/margin=<M>/ticks.parquet``) is canonical
    EVERYWHERE — the bare v5 tail (no quote/margin) is LOSSY (USD-vs-USDT /
    linear-vs-inverse chains on the same underlying collide and overwrite) and
    must not remain anywhere. Enforced write-time by the MTDS
    ``PartitionedTickWriter`` (asset_group=cefi) so a regressing backfill fails
    loud instead of silently reintroducing the collision. SSOT:
    cefi_chain_tail_v6_canonicalisation_2026_07_21.md.
    """
    if asset_group != "cefi":
        return []
    it_value = kv.get("instrument_type")
    if it_value not in CEFI_CHAIN_INSTRUMENT_TYPES:
        return []
    tail_keys = [seg.partition("=")[0] for seg in partition_segments[-3:]]
    if tail_keys == ["underlying", "quote", "margin"] and file_name == "ticks.parquet":
        return []
    return [
        f"cefi {it_value} shard must end "
        "'.../underlying=<BASE>/quote=<Q>/margin=<M>/ticks.parquet' "
        f"(got tail {[*partition_segments[-3:], file_name]!r}) — v5 bare chain "
        "tail is a lossy USD-vs-USDT / linear-vs-inverse collision, RULED v6-only "
        "everywhere (operator 2026-07-21)"
    ]


def _stem_id_form_violations(*, asset_group: str, instrument_type: str | None, file_name: str) -> list[str]:
    """ID-FORM violations for a single-instrument shard's filename stem.

    Returns ``[]`` for every legitimately stem-less shape (chain itypes and the
    ``ticks.parquet`` fan-in) and for asset groups outside
    :data:`_ID_FORM_CHECKED_ASSET_GROUPS`.
    """
    if asset_group not in _ID_FORM_CHECKED_ASSET_GROUPS:
        return []
    if file_name in _STEMLESS_FAN_IN_FILE_NAMES:
        return []
    if instrument_type in CEFI_CHAIN_INSTRUMENT_TYPES:
        return []
    stem = file_name.removesuffix(".parquet")
    if is_canonical_instrument_id(stem):
        return []
    expected_grammar = (
        "'VENUE-CHAIN:TYPE:SYMBOL'"
        if asset_group == "defi"
        else "'VENUE:ITYPE:BASE-QUOTE[@LIN|@INV][-YYYYMMDD][-STRIKE-C|P]'"
    )
    return [
        f"{asset_group} single-instrument shard filename {file_name!r} is not a canonical "
        f"instrument_id ({expected_grammar}) — raw venue wire symbol / bare symbol or a "
        "double-wrapped catalogue-miss id"
    ]


def _select_violation_classes(
    structural: list[str],
    id_form: list[str],
    violation_classes: frozenset[CanonicalViolationClass] | None,
) -> list[str]:
    """Flatten the two violation classes down to the caller's requested selection."""
    if violation_classes is None:
        return [*structural, *id_form]
    selected: list[str] = []
    if CanonicalViolationClass.STRUCTURAL in violation_classes:
        selected.extend(structural)
    if CanonicalViolationClass.ID_FORM in violation_classes:
        selected.extend(id_form)
    return selected


def canonical_path_violations(
    path: str,
    *,
    require_pipeline_mode: bool = False,
    violation_classes: frozenset[CanonicalViolationClass] | None = None,
) -> list[str]:
    """Return the list of canonical-form violations for ``path`` (empty == canonical).

    Parses a bucket-relative GCS partition path (the full
    ``raw_tick_data/by_date/...`` shape the ``build_*_partition_path`` builders
    emit) and returns one human-readable violation string per documented
    drift class found. An empty list means the path is canonical.

    Args:
        path: Bucket-relative path (no ``gs://bucket/`` prefix). A leading
            slash is tolerated and stripped.
        require_pipeline_mode: When True, a path lacking the
            ``pipeline_mode={mode}_{source}/`` segment left of ``asset_group=``
            is a violation. Default False accepts the back-compat bare paths
            the builders still emit (the segment is canonical-but-optional for
            CeFi/Prediction and back-compat for DeFi/TradFi).
        violation_classes: Restrict the answer to these
            :class:`CanonicalViolationClass` members. Default ``None`` reports
            BOTH classes — path STRUCTURE *and* filename instrument-id FORM.
            Pass ``frozenset({CanonicalViolationClass.STRUCTURAL})`` for the
            skeleton-only question (the pre-2026-07-20 behaviour).

    Note:
        Structure and id-form are ORTHOGONAL questions — an empty list means
        canonical only with respect to the classes actually requested.
    """
    structural: list[str] = []
    id_form: list[str] = []
    cleaned = path.lstrip("/")

    if not cleaned.startswith(RAW_TICK_DATA_PREFIX):
        structural.append(f"path does not start with the canonical prefix {RAW_TICK_DATA_PREFIX!r}")
        return _select_violation_classes(structural, id_form, violation_classes)

    remainder = cleaned[len(RAW_TICK_DATA_PREFIX) :]
    segments = remainder.split("/")
    # Last segment is the file name; the rest are hive ``key=value`` partitions.
    partition_segments = segments[:-1]

    # ── day= segment (must be the first partition, value YYYY-MM-DD) ──────────
    if not partition_segments:
        structural.append("no partition segments after the prefix")
        return _select_violation_classes(structural, id_form, violation_classes)

    day_seg = partition_segments[0]
    if day_seg.startswith("day-"):
        structural.append(f"legacy hyphen day segment {day_seg!r} — must be 'day=YYYY-MM-DD'")
    elif not day_seg.startswith("day="):
        structural.append(f"first partition is {day_seg!r}, expected 'day=YYYY-MM-DD'")
    elif not _DAY_VALUE_RE.match(day_seg[len("day=") :]):
        structural.append(f"day value {day_seg[len('day=') :]!r} is not ISO YYYY-MM-DD")

    # ── locate the keyed partition map (key=value segments) ──────────────────
    kv: dict[str, str] = {}
    has_pipeline_mode = False
    for seg in partition_segments[1:]:
        if "=" not in seg:
            structural.append(f"non-canonical partition segment {seg!r} (expected 'key=value')")
            continue
        key, _, value = seg.partition("=")
        if key == "pipeline_mode":
            has_pipeline_mode = True
            if not _PIPELINE_MODE_VALUE_RE.match(value):
                structural.append(
                    f"pipeline_mode value {value!r} is not canonical '{{mode}}_{{source}}' "
                    "(mode ∈ batch/live/replay, source = vendor token)"
                )
        kv[key] = value

    # ── asset_group= (must be present + in the closed set) ───────────────────
    asset_group_value = kv.get(ASSET_GROUP_HIVE_KEY)
    if asset_group_value is None:
        structural.append(f"missing '{ASSET_GROUP_HIVE_KEY}=' partition segment")
    elif asset_group_value not in _CANONICAL_ASSET_GROUPS:
        structural.append(
            f"{ASSET_GROUP_HIVE_KEY}={asset_group_value!r} is outside the canonical set "
            f"{sorted(_CANONICAL_ASSET_GROUPS)}"
        )

    # ── pipeline_mode required-but-missing (opt-in) ──────────────────────────
    if require_pipeline_mode and not has_pipeline_mode:
        structural.append(
            "missing 'pipeline_mode={mode}_{source}/' segment left of "
            f"'{ASSET_GROUP_HIVE_KEY}=' (required for this check)"
        )

    # ── venue= (glued VENUE-CHAIN overload / glued V{N} version) ─────────────
    venue_value = kv.get("venue")
    if venue_value is not None:
        # A hyphen in the venue token is the legacy PROTOCOL-CHAIN glue
        # (e.g. ``AAVE_V3-ETHEREUM``); chain MUST be its own ``chain=`` segment.
        # This is a DEFI-ONLY concern — ``chain`` is a defi axis. CeFi venue names
        # legitimately CONTAIN a hyphen (``BINANCE-FUTURES`` / ``OKX-FUTURES`` /
        # ``BYBIT-FUTURES`` / ``KRAKEN-FUTURES`` — the canonical cefi venue tokens in
        # registry/data_type_capability.py), so flagging every hyphen crashed the cefi
        # LIVE producers at the writer boundary (``venue='BINANCE-FUTURES' carries a
        # glued 'VENUE-CHAIN' token``), silently freezing the deribit/hyperliquid/binance
        # live VMs for hours (2026-06-23). Gate on defi so the legacy-glue guard still
        # protects the on-chain paths without false-flagging cefi/tradfi venue names.
        if asset_group_value == "defi" and "-" in venue_value:
            structural.append(
                f"venue={venue_value!r} carries a glued 'VENUE-CHAIN' token — chain must be a separate 'chain=' segment"
            )
        if _GLUED_VERSION_RE.search(venue_value):
            structural.append(
                f"venue={venue_value!r} carries a glued 'V{{N}}' version — canonical form separates "
                "it with an underscore (e.g. 'AAVE_V3', 'UNISWAP_V3')"
            )

    # ── tradfi canonical shape (chain quote/margin tail + single full-id filename) ──
    # Enforced write-time by the MTDS PartitionedTickWriter (asset_group=tradfi)
    # so a regressing backfill fails loud instead of silently re-diverging the
    # migrated corpus (chain object at underlying=/quote=/margin= vs a manifest
    # atom / new write that dropped the tail). SSOT:
    # plans/active/issues/tradfi_canonical_path_migration_design_2026_07_19.md.
    if asset_group_value == "tradfi":
        file_name = segments[-1]
        it_value = kv.get("instrument_type")
        if kv.get("pipeline_mode") == "batch_massive":
            structural.append(
                "tradfi pipeline_mode=batch_massive is forbidden — Massive is purged; "
                "Databento is the batch source of truth"
            )
        # ── garbage-underlying guard (chain + combo bundles) ─────────────────
        # A tradfi CHAIN/COMBO bundle carries ``underlying=<ROOT>``. The forensic
        # sweep found 189,830 objects whose ``underlying=`` was a numeric CBOE
        # globex GROUP code (``12``/``13``) or an opaque CBOE user-defined leg
        # code (``GN``/``VT``/``3W``) — the product root is UNRECOVERABLE from the
        # path, so a fresh write MUST fail loud (shard-level isolation → honest
        # ``attempted_failed``) rather than fake-canonicalise a garbage bundle.
        # Real roots (``SP500``/``MES``/``XAB``) and resolved named-spread combos
        # (``WTI-BZ``/``NAT-GAS-HH``) PASS. Covers combo too (not in
        # TRADFI_CHAIN_INSTRUMENT_TYPES): the opaque ``UD:1V: GN`` combos land
        # here. SSOT: tradfi_canonical_path_migration_design_2026_07_19.md.
        underlying_value = kv.get("underlying")
        if underlying_value is not None:
            # Call-time import (canonical→registry) — avoids the load-time cycle
            # (registry/__init__ imports canonical); at call time both are loaded.
            from unified_api_contracts.registry.tradfi_symbology import (
                is_recognized_tradfi_underlying,
            )

            if not is_recognized_tradfi_underlying(underlying_value):
                structural.append(
                    f"tradfi underlying={underlying_value!r} is not a real product root / "
                    "named-spread combo (numeric globex group code or opaque CBOE "
                    "user-defined leg code) — quarantine, never fake-canonicalize"
                )
        if it_value in TRADFI_CHAIN_INSTRUMENT_TYPES:
            # chain shard tail MUST be underlying=.../quote=.../margin=.../ticks.parquet
            tail_keys = [seg.partition("=")[0] for seg in partition_segments[-3:]]
            if tail_keys != ["underlying", "quote", "margin"] or file_name != "ticks.parquet":
                structural.append(
                    f"tradfi {it_value} shard must end "
                    "'.../underlying=<BASE>/quote=<Q>/margin=<M>/ticks.parquet' "
                    f"(got tail {[*partition_segments[-3:], file_name]!r})"
                )
        elif it_value in TRADFI_SINGLE_INSTRUMENT_TYPES:
            # single-instrument shard: filename MUST be the full canonical
            # instrument_id (VENUE:TYPE:SYMBOL...), never a bare symbol or a
            # symbol-less ticks.parquet fan-in. Scoped to the canonical single
            # itypes only — ``combo`` (bare-symbol, leg-id unsettled) and special
            # bundle types like ``event_contract`` are deliberately NOT enforced.
            if file_name == "ticks.parquet":
                id_form.append(
                    "tradfi single-instrument shard filename must be the full canonical "
                    "instrument_id, got a symbol-less 'ticks.parquet' fan-in"
                )
            elif ":" not in file_name:
                id_form.append(
                    f"tradfi single-instrument shard filename {file_name!r} must be the full "
                    "canonical instrument_id ('VENUE:TYPE:SYMBOL...'), got a bare symbol"
                )

    structural.extend(_cefi_chain_tail_violations(asset_group_value, kv, partition_segments, segments[-1]))

    # ── ID-FORM: the filename stem must BE a canonical instrument_id ─────────
    # The gap this closes: before 2026-07-20 the stem was dropped
    # (``partition_segments = segments[:-1]``) before validation for every
    # asset_group except tradfi, so a CeFi corpus of raw wire stems
    # (``ADAF0:USTF0.parquet``) and double-wrapped catalogue-miss ids
    # (``BITFINEX-FUTURES:PERPETUAL:ADAF0:USTF0.parquet``) measured CANONICAL.
    if asset_group_value is not None:
        id_form.extend(
            _stem_id_form_violations(
                asset_group=asset_group_value,
                instrument_type=kv.get("instrument_type"),
                file_name=segments[-1],
            )
        )

    return _select_violation_classes(structural, id_form, violation_classes)


def canonical_path_violations_classified(
    path: str,
    *,
    require_pipeline_mode: bool = False,
) -> dict[CanonicalViolationClass, list[str]]:
    """Canonical-form violations for ``path`` split by :class:`CanonicalViolationClass`.

    The audit-facing view: reconciliation reports need to say *which* surface
    is non-canonical (a wire-named file under a perfectly-shaped hive skeleton
    is a very different finding from a ``day-2026-05-01`` legacy prefix), and
    an enforcement boundary needs to act on one class at a time. Every class is
    always present as a key; a canonical path maps every class to ``[]``.
    """
    return {
        member: canonical_path_violations(
            path,
            require_pipeline_mode=require_pipeline_mode,
            violation_classes=frozenset({member}),
        )
        for member in CanonicalViolationClass
    }


def is_canonical(
    path: str,
    *,
    require_pipeline_mode: bool = False,
    violation_classes: frozenset[CanonicalViolationClass] | None = None,
) -> bool:
    """True iff ``path`` is a canonical GCS partition path (no drift violations).

    Thin boolean wrapper over :func:`canonical_path_violations` — accepts the
    output of every ``build_*_partition_path`` builder and rejects the
    documented non-canonical drift shapes (hyphen ``day-``, glued
    ``VENUE-CHAIN`` / ``V{N}``, out-of-set ``asset_group=``, a non-canonical
    filename instrument-id stem, and — when ``require_pipeline_mode=True`` — a
    missing ``pipeline_mode=`` segment).

    Like :func:`canonical_path_violations` this answers BOTH the STRUCTURAL and
    the ID_FORM question by default; narrow with ``violation_classes``.
    """
    return not canonical_path_violations(
        path,
        require_pipeline_mode=require_pipeline_mode,
        violation_classes=violation_classes,
    )


__all__ = [
    "ASSET_GROUP_HIVE_KEY",
    "CEFI_CHAIN_INSTRUMENT_TYPES",
    "RAW_TICK_DATA_PREFIX",
    "TRADFI_CHAIN_INSTRUMENT_TYPES",
    "TRADFI_SINGLE_INSTRUMENT_TYPES",
    "CanonicalViolationClass",
    "build_cefi_partition_path",
    "build_defi_partition_path",
    "build_prediction_partition_path",
    "build_tradfi_partition_path",
    "candidate_parquet_paths",
    "canonical_path_violations",
    "canonical_path_violations_classified",
    "is_canonical",
    "is_canonical_instrument_id",
]
