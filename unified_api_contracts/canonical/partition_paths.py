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


def build_tradfi_partition_path(
    *,
    venue: str,
    instrument_type: InstrumentType,
    data_type: str,
    day: _dt.date,
    file_name: str,
    pipeline_mode: str | None = None,
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
    it = instrument_type.value.lower()
    day_str = day.strftime("%Y-%m-%d")
    pipeline_mode_segment = f"pipeline_mode={pipeline_mode}/" if pipeline_mode else ""
    return (
        f"{RAW_TICK_DATA_PREFIX}day={day_str}/{pipeline_mode_segment}"
        f"{ASSET_GROUP_HIVE_KEY}=tradfi/"
        f"venue={v}/instrument_type={it}/data_type={data_type}/{file_name}"
    )


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


def canonical_path_violations(path: str, *, require_pipeline_mode: bool = False) -> list[str]:
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
    """
    violations: list[str] = []
    cleaned = path.lstrip("/")

    if not cleaned.startswith(RAW_TICK_DATA_PREFIX):
        violations.append(f"path does not start with the canonical prefix {RAW_TICK_DATA_PREFIX!r}")
        return violations

    remainder = cleaned[len(RAW_TICK_DATA_PREFIX) :]
    segments = remainder.split("/")
    # Last segment is the file name; the rest are hive ``key=value`` partitions.
    partition_segments = segments[:-1]

    # ── day= segment (must be the first partition, value YYYY-MM-DD) ──────────
    if not partition_segments:
        violations.append("no partition segments after the prefix")
        return violations

    day_seg = partition_segments[0]
    if day_seg.startswith("day-"):
        violations.append(f"legacy hyphen day segment {day_seg!r} — must be 'day=YYYY-MM-DD'")
    elif not day_seg.startswith("day="):
        violations.append(f"first partition is {day_seg!r}, expected 'day=YYYY-MM-DD'")
    elif not _DAY_VALUE_RE.match(day_seg[len("day=") :]):
        violations.append(f"day value {day_seg[len('day=') :]!r} is not ISO YYYY-MM-DD")

    # ── locate the keyed partition map (key=value segments) ──────────────────
    kv: dict[str, str] = {}
    has_pipeline_mode = False
    for seg in partition_segments[1:]:
        if "=" not in seg:
            violations.append(f"non-canonical partition segment {seg!r} (expected 'key=value')")
            continue
        key, _, value = seg.partition("=")
        if key == "pipeline_mode":
            has_pipeline_mode = True
            if not _PIPELINE_MODE_VALUE_RE.match(value):
                violations.append(
                    f"pipeline_mode value {value!r} is not canonical '{{mode}}_{{source}}' "
                    "(mode ∈ batch/live/replay, source = vendor token)"
                )
        kv[key] = value

    # ── asset_group= (must be present + in the closed set) ───────────────────
    asset_group_value = kv.get(ASSET_GROUP_HIVE_KEY)
    if asset_group_value is None:
        violations.append(f"missing '{ASSET_GROUP_HIVE_KEY}=' partition segment")
    elif asset_group_value not in _CANONICAL_ASSET_GROUPS:
        violations.append(
            f"{ASSET_GROUP_HIVE_KEY}={asset_group_value!r} is outside the canonical set "
            f"{sorted(_CANONICAL_ASSET_GROUPS)}"
        )

    # ── pipeline_mode required-but-missing (opt-in) ──────────────────────────
    if require_pipeline_mode and not has_pipeline_mode:
        violations.append(
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
            violations.append(
                f"venue={venue_value!r} carries a glued 'VENUE-CHAIN' token — chain must be a separate 'chain=' segment"
            )
        if _GLUED_VERSION_RE.search(venue_value):
            violations.append(
                f"venue={venue_value!r} carries a glued 'V{{N}}' version — canonical form separates "
                "it with an underscore (e.g. 'AAVE_V3', 'UNISWAP_V3')"
            )

    return violations


def is_canonical(path: str, *, require_pipeline_mode: bool = False) -> bool:
    """True iff ``path`` is a canonical GCS partition path (no drift violations).

    Thin boolean wrapper over :func:`canonical_path_violations` — accepts the
    output of every ``build_*_partition_path`` builder and rejects the
    documented non-canonical drift shapes (hyphen ``day-``, glued
    ``VENUE-CHAIN`` / ``V{N}``, out-of-set ``asset_group=``, and — when
    ``require_pipeline_mode=True`` — a missing ``pipeline_mode=`` segment).
    """
    return not canonical_path_violations(path, require_pipeline_mode=require_pipeline_mode)


__all__ = [
    "ASSET_GROUP_HIVE_KEY",
    "CEFI_CHAIN_INSTRUMENT_TYPES",
    "RAW_TICK_DATA_PREFIX",
    "build_cefi_partition_path",
    "build_defi_partition_path",
    "build_prediction_partition_path",
    "build_tradfi_partition_path",
    "candidate_parquet_paths",
    "canonical_path_violations",
    "is_canonical",
]
