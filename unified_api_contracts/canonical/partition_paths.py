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
CeFi: ``raw_tick_data/by_date/day={D}/pipeline_mode={mode}/asset_group=cefi/venue={V}/
       instrument_type={IT}/data_type={DT}/{file}``
       (``pipeline_mode`` is a REQUIRED :func:`build_cefi_partition_path` parameter as
       of 2026-07-29 — see the "write-side footgun fix" note below.)
TradFi: ``raw_tick_data/by_date/day={D}/pipeline_mode={mode}/asset_group=tradfi/venue={V}/
         instrument_type={IT}/data_type={DT}/{file}``
         (``pipeline_mode`` is likewise REQUIRED as of 2026-07-29 — the old back-compat
         no-segment shape can no longer be produced by :func:`build_tradfi_partition_path`.)
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

Write-side footgun fix (2026-07-29): :func:`build_cefi_partition_path` and
:func:`build_tradfi_partition_path` now REQUIRE ``pipeline_mode`` as a
keyword argument (mirroring :func:`build_defi_partition_path`'s existing
contract) instead of leaving every caller to remember a post-hoc
``.replace(f"day={D}/", f"day={D}/pipeline_mode={pm}/", 1)`` insertion. That
manual-insertion convention caused the SAME bug — a writer forgetting the
insertion, silently producing a non-canonical object path — to recur 3
independent times (KALSHI_PERP/POLYMARKET_PERP, Deribit options_chain, and
the original MDPS ``_check_existing_outputs`` bug that triggered the audit).
This is a BREAKING signature change on purpose: a call missing
``pipeline_mode`` now fails loudly (``TypeError``) at the call site instead
of silently shipping a wrong path. SSOT:
``unified-trading-pm/plans/active/issues/gcs_path_resolution_centralization_audit_2026_07_28.md``
§ "Centralization design ... RULED 2026-07-29".
"""

from __future__ import annotations

import datetime as _dt

from unified_api_contracts._instrument_enums import InstrumentType
from unified_api_contracts.canonical._partition_path_canonicality import (
    ASSET_GROUP_HIVE_KEY,
    CEFI_CHAIN_INSTRUMENT_TYPES,
    PROCESSED_CANDLES_PREFIX,
    RAW_TICK_DATA_PREFIX,
    TRADFI_CHAIN_INSTRUMENT_TYPES,
    TRADFI_SINGLE_INSTRUMENT_TYPES,
    CanonicalViolationClass,
    canonical_path_violations,
    canonical_path_violations_classified,
    is_canonical,
    is_canonical_instrument_id,
)
from unified_api_contracts.canonical.gcs_paths import AssetGroup

# ASSET_GROUP_HIVE_KEY / RAW_TICK_DATA_PREFIX / PROCESSED_CANDLES_PREFIX /
# CEFI_CHAIN_INSTRUMENT_TYPES / TRADFI_CHAIN_INSTRUMENT_TYPES /
# TRADFI_SINGLE_INSTRUMENT_TYPES live in _partition_path_canonicality (shared
# by the builders below AND the validator) — imported above, re-exported
# unchanged via __all__ so the public import path is untouched.


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

# CEFI_CHAIN_INSTRUMENT_TYPES (instrument_types that bundle an entire chain
# into a single file per underlying per day; mirrors MTDS
# ``cefi/tardis_shared.py::CHAIN_INSTRUMENT_TYPES``) lives in
# _partition_path_canonicality (shared with the validator) — imported above.


def build_cefi_partition_path(
    *,
    venue: str,
    instrument_type: InstrumentType | str,
    data_type: str,
    day: _dt.date,
    file_name: str,
    pipeline_mode: str,
    underlying: str = "",
    quote_asset: str = "",
    margin_type: str = "",
) -> str:
    """Build the canonical CeFi partition path (full bucket-relative path).

    Returns the full path including the ``raw_tick_data/by_date/`` prefix —
    callers MUST NOT prepend further.

    v5 (legacy) layout — single-symbol shards or callers leaving
    underlying / quote_asset / margin_type empty:

    ``raw_tick_data/by_date/day={YYYY-MM-DD}/pipeline_mode={mode}/
    asset_group=cefi/venue={V}/instrument_type={IT}/data_type={DT}/{file_name}``

    v6 layout (2026-04-23) — only when ``instrument_type`` is a CHAIN bundle
    (``options_chain`` / ``futures_chain``) AND all three of
    ``underlying`` / ``quote_asset`` / ``margin_type`` are populated:

    ``raw_tick_data/by_date/day=.../pipeline_mode={mode}/asset_group=cefi/
    venue={V}/instrument_type={IT}/data_type={DT}/
    underlying={U}/quote={Q}/margin={M}/ticks.parquet``

    For per-symbol (non-chain) shards, v6 does NOT add extra path segments —
    the instrument_id itself already disambiguates
    (``BTC-PERPETUAL.parquet`` vs ``BTC_USDC-PERPETUAL.parquet``).

    Mirrors MTDS ``cefi/tardis_shared.py::build_partition_path``. Accepts
    either ``InstrumentType`` enum members or raw lowercase strings (the
    chain-bundle tokens ``options_chain`` / ``futures_chain`` aren't in the
    canonical enum so callers pass them as strings).

    Args:
        pipeline_mode: REQUIRED (2026-07-29 write-side footgun fix — see the
            module docstring). Inserted as the ``pipeline_mode={mode}/``
            segment immediately after ``day={D}/`` and before
            ``asset_group=cefi/`` — the SAME position every confirmed-correct
            CeFi writer already inserted it via a manual post-hoc
            ``.replace()`` before this fix (mirrors
            :func:`build_defi_partition_path`'s existing contract). A caller
            with no real ``pipeline_mode`` value is a bug at the call site,
            not something this builder should paper over with a default.

    Raises:
        TypeError: if ``pipeline_mode`` (or any other required keyword-only
            argument) is omitted — Python's own required-kwarg enforcement.
        ValueError: if ``pipeline_mode`` is an empty string, or any of
            ``data_type`` / ``file_name`` are empty.
    """
    if not data_type:
        msg = "data_type must be a non-empty string"
        raise ValueError(msg)
    if not file_name:
        msg = "file_name must be a non-empty string"
        raise ValueError(msg)
    if not pipeline_mode:
        msg = "pipeline_mode must be a non-empty string"
        raise ValueError(msg)

    v = _normalize_venue_upper(venue)
    it = instrument_type.value.lower() if isinstance(instrument_type, InstrumentType) else instrument_type.lower()
    day_str = day.strftime("%Y-%m-%d")
    base = (
        f"{RAW_TICK_DATA_PREFIX}day={day_str}/pipeline_mode={pipeline_mode}/{ASSET_GROUP_HIVE_KEY}=cefi/"
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

# TRADFI_CHAIN_INSTRUMENT_TYPES / TRADFI_SINGLE_INSTRUMENT_TYPES (mirrors MTDS
# ``tradfi/tradfi_shared.py``'s chain / single-instrument type sets) live in
# _partition_path_canonicality (shared with the validator) — imported above.


def build_tradfi_partition_path(
    *,
    venue: str,
    instrument_type: InstrumentType | str,
    data_type: str,
    day: _dt.date,
    file_name: str,
    pipeline_mode: str,
    underlying: str = "",
    quote_asset: str = "",
    margin_type: str = "",
) -> str:
    """Build the canonical TradFi partition path (full bucket-relative path).

    Returns the full path including the ``raw_tick_data/by_date/`` prefix —
    callers MUST NOT prepend further.

    ``pipeline_mode`` (canonical — operator-locked 2026-06-01; REQUIRED as of
    the 2026-07-29 write-side footgun fix, see the module docstring) is
    inserted as the ``pipeline_mode={mode}/`` segment AFTER ``day={D}/`` and
    BEFORE ``asset_group=tradfi/``:

    ``raw_tick_data/by_date/day={YYYY-MM-DD}/pipeline_mode={mode}/
    asset_group=tradfi/venue={V}/instrument_type={IT}/data_type={DT}/{file_name}``

    The old back-compat no-segment shape
    (``raw_tick_data/by_date/day={YYYY-MM-DD}/asset_group=tradfi/venue={V}/
    instrument_type={IT}/data_type={DT}/{file_name}``) can no longer be
    produced by this builder — it is still what legacy pre-migration objects
    on disk look like, and readers still probe for it via the fallback chain
    in :func:`candidate_parquet_paths`, but a NEW write must always carry the
    segment.

    v6 chain layout (2026-07-19) — only when ``instrument_type`` is a CHAIN
    bundle (``options_chain`` / ``futures_chain``) AND all three of
    ``underlying`` / ``quote_asset`` / ``margin_type`` are populated (mirrors
    :func:`build_cefi_partition_path` byte-for-byte + the shipped migration
    executor ``migrate_tradfi_canonical_2026_07._canonical_chain_path``):

    ``raw_tick_data/by_date/day=.../pipeline_mode={mode}/asset_group=tradfi/
    venue={V}/instrument_type={IT}/data_type={DT}/
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

    Raises:
        TypeError: if ``pipeline_mode`` (or any other required keyword-only
            argument) is omitted — Python's own required-kwarg enforcement.
        ValueError: if ``pipeline_mode`` is an empty string, or any of
            ``data_type`` / ``file_name`` are empty.
    """
    if not data_type:
        msg = "data_type must be a non-empty string"
        raise ValueError(msg)
    if not file_name:
        msg = "file_name must be a non-empty string"
        raise ValueError(msg)
    if not pipeline_mode:
        msg = "pipeline_mode must be a non-empty string"
        raise ValueError(msg)

    v = _normalize_venue_upper(venue)
    it = instrument_type.value.lower() if isinstance(instrument_type, InstrumentType) else instrument_type.lower()
    day_str = day.strftime("%Y-%m-%d")
    base = (
        f"{RAW_TICK_DATA_PREFIX}day={day_str}/pipeline_mode={pipeline_mode}/"
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

# Throwaway value used ONLY to obtain build_cefi_partition_path's /
# build_tradfi_partition_path's positional path SHAPE when a
# candidate_parquet_paths() caller doesn't know pipeline_mode yet (both
# builders now REQUIRE it — 2026-07-29 write-side footgun fix). Stripped back
# out by _strip_pipeline_mode_segment before any path is returned — this
# literal string never appears in a candidate path a caller sees.
_LEGACY_SHAPE_PROBE_PIPELINE_MODE = "_legacy_shape_probe_"


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
            - Sports: ``league_id`` (optional). See
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
        return sports_candidates(
            data_type=data_type,
            day=day.strftime("%Y-%m-%d"),
            league_id=league_id,
            pipeline_mode=pipeline_mode,
        )

    day_str = day.strftime("%Y-%m-%d")

    def _prepend_pipeline_mode(path: str) -> str:
        """Insert ``pipeline_mode={mode}/`` after ``day={D}/`` in a canonical path.

        Used by Prediction only (its builder has no ``pipeline_mode`` param).
        DeFi does NOT use this — its ``pipeline_mode={mode}/`` segment is
        canonical and produced directly by :func:`build_defi_partition_path`
        (the single source), so the DeFi branch passes ``pipeline_mode``
        through to the builder instead. CeFi / TradFi ALSO pass
        ``pipeline_mode`` straight to their builders now (2026-07-29
        write-side footgun fix made it a required builder param) — see
        ``_strip_pipeline_mode_segment`` below for how those two branches
        derive the bare/legacy fallback candidate instead.
        """
        marker = f"day={day_str}/{ASSET_GROUP_HIVE_KEY}="
        return path.replace(marker, f"day={day_str}/pipeline_mode={pipeline_mode}/{ASSET_GROUP_HIVE_KEY}=", 1)

    def _strip_pipeline_mode_segment(path_with_segment: str, pipeline_mode_value: str) -> str:
        """Inverse of the builders' own segment insertion: remove a
        ``pipeline_mode={value}/`` segment, recovering the pre-2026-06-01-lock
        bare (legacy) path shape used as the CeFi/TradFi read-side fallback
        candidate.

        ``build_cefi_partition_path`` / ``build_tradfi_partition_path`` can no
        longer produce the bare shape directly (``pipeline_mode`` is a
        REQUIRED param as of the 2026-07-29 write-side footgun fix), so the
        bare candidate is derived by building WITH a value, then stripping the
        segment back out. When the caller's own ``pipeline_mode`` is unknown
        (``None``), ``_LEGACY_SHAPE_PROBE_PIPELINE_MODE`` is used purely to
        obtain the builder's positional shape — that placeholder value never
        appears in a path this dispatcher returns (always stripped below).
        """
        return path_with_segment.replace(f"pipeline_mode={pipeline_mode_value}/", "", 1)

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
        # build_cefi_partition_path now REQUIRES pipeline_mode (2026-07-29
        # write-side footgun fix) — build WITH a value (the caller's real one,
        # or the shape-probe placeholder when unknown) then derive the bare
        # legacy fallback candidate by stripping the segment back out, rather
        # than asking the builder for a shape it can no longer produce.
        _cefi_probe_pm = pipeline_mode or _LEGACY_SHAPE_PROBE_PIPELINE_MODE
        _cefi_with_segment = build_cefi_partition_path(
            venue=str(kwargs["venue"]),
            instrument_type=_coerce_instrument_type(kwargs["instrument_type"]),
            data_type=data_type,
            day=day,
            file_name=str(kwargs["file_name"]),
            pipeline_mode=_cefi_probe_pm,
        )
        _cefi_bare = _strip_pipeline_mode_segment(_cefi_with_segment, _cefi_probe_pm)
        if pipeline_mode:
            return [_cefi_with_segment, _cefi_bare]
        return [_cefi_bare]

    if ag == AssetGroup.TRADFI:
        # TradFi: pipeline_mode= is a CANONICAL segment (operator-locked
        # 2026-06-01) and — like CeFi above — now a REQUIRED builder param
        # (2026-07-29 write-side footgun fix). Same build-with-a-value /
        # strip-for-the-bare-fallback approach as CeFi (one builder call
        # instead of the old two-call pattern). The canonical (with-segment)
        # path is the first probe; the bare path follows as a migration
        # fallback (Phase 5.3 / 8 window).
        _tradfi_probe_pm = pipeline_mode or _LEGACY_SHAPE_PROBE_PIPELINE_MODE
        _tradfi_with_segment = build_tradfi_partition_path(
            venue=str(kwargs["venue"]),
            instrument_type=_coerce_instrument_type(kwargs["instrument_type"]),
            data_type=data_type,
            day=day,
            file_name=str(kwargs["file_name"]),
            pipeline_mode=_tradfi_probe_pm,
        )
        _tradfi_bare = _strip_pipeline_mode_segment(_tradfi_with_segment, _tradfi_probe_pm)
        if pipeline_mode:
            return [_tradfi_with_segment, _tradfi_bare]
        return [_tradfi_bare]

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


__all__ = [
    "ASSET_GROUP_HIVE_KEY",
    "CEFI_CHAIN_INSTRUMENT_TYPES",
    "PROCESSED_CANDLES_PREFIX",
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
