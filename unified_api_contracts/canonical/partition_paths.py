"""SSOT for non-sports per-asset-group GCS partition paths.

Sports already has its own domain-co-located SSOT at
:mod:`unified_api_contracts.canonical.domain.sports.gcs_paths` (tied to
fixture / league semantics, kept there for proximity). This module covers the
remaining 4 asset groups (CeFi, DeFi, TradFi, Prediction) — each writes to
its dedicated ``market-data-tick-{ag}-{pid}`` bucket but with different
partition keys per data shape.

Wire-format SSOT (matches deployed MTDS adapters as of 2026-04-29):

DeFi: ``day={D}/asset_group=defi/venue={V}/chain={C}/instrument_type={IT}/data_type={DT}/{file}``
  Migrated 2026-04-29 from
  ``market-tick-data-service/.../adapters/defi/canonical_write.py::build_defi_partition_path``.

CeFi / TradFi / Prediction: see per-function docstrings.

Use the unified dispatcher :func:`candidate_parquet_paths` for code that
spans asset_groups; use the per-asset-group ``build_*_partition_path``
functions for type-checked single-asset-group code.
"""

from __future__ import annotations

import datetime as _dt

from unified_api_contracts._instrument_enums import InstrumentType
from unified_api_contracts.canonical.gcs_paths import AssetGroup

# Hive partition key for the asset_group axis. Canonical wire-format value.
# Legacy on-disk objects use ``category=`` — readers that need both should try
# canonical first then fall back, but new writes use this key.
ASSET_GROUP_HIVE_KEY = "asset_group"


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
) -> str:
    """Build the canonical DeFi partition path (without bucket prefix).

    Wire format (mirrors hive-partitioning conventions used by MTDS reader +
    PartitionedTickWriter):

    ``day={YYYY-MM-DD}/asset_group=defi/venue={V}/chain={C}/
    instrument_type={IT}/data_type={DT}/{file_name}``

    Where ``venue`` is the protocol only (e.g. ``AAVE_V3``, ``UNISWAP_V3``,
    ``LIDO``) — never the legacy ``PROTOCOL-CHAIN`` overload — and
    ``chain`` is the uppercased chain identifier
    (``ETHEREUM`` / ``ARBITRUM`` / ``SOLANA`` / ...).

    Example:
        >>> build_defi_partition_path(
        ...     venue="AAVE_V3",
        ...     chain="ETHEREUM",
        ...     instrument_type=InstrumentType.A_TOKEN,
        ...     data_type="lending_indices",
        ...     day=_dt.date(2026, 4, 17),
        ...     file_name="aUSDC.parquet",
        ... )
        'day=2026-04-17/asset_group=defi/venue=AAVE_V3/chain=ETHEREUM/instrument_type=a_token/data_type=lending_indices/aUSDC.parquet'
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
    return (
        f"day={day_str}/{ASSET_GROUP_HIVE_KEY}=defi/"
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
    """Build the canonical CeFi partition path (without bucket or
    ``raw_tick_data/by_date/`` prefix — the writer prepends those).

    v5 (legacy) layout — single-symbol shards or callers leaving
    underlying / quote_asset / margin_type empty:

    ``day={YYYY-MM-DD}/asset_group=cefi/venue={V}/
    instrument_type={IT}/data_type={DT}/{file_name}``

    v6 layout (2026-04-23) — only when ``instrument_type`` is a CHAIN bundle
    (``options_chain`` / ``futures_chain``) AND all three of
    ``underlying`` / ``quote_asset`` / ``margin_type`` are populated:

    ``day=.../instrument_type={IT}/data_type={DT}/
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
    base = f"day={day_str}/{ASSET_GROUP_HIVE_KEY}=cefi/venue={v}/instrument_type={it}/data_type={data_type}"

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
) -> str:
    """Build the canonical TradFi partition path (without bucket or
    ``raw_tick_data/by_date/`` prefix — the writer prepends those).

    Wire format (matches MTDS
    ``tradfi/tradfi_shared.py::build_partition_path``):

    ``day={YYYY-MM-DD}/asset_group=tradfi/venue={V}/
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
    return (
        f"day={day_str}/{ASSET_GROUP_HIVE_KEY}=tradfi/venue={v}/instrument_type={it}/data_type={data_type}/{file_name}"
    )


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------
# Pattern derived from MTDS prediction adapters (polymarket, kalshi,
# manifold). Prediction venues key by ``condition_id`` (the on-chain market
# resolution identifier) — a market lifetime spans many days, but each
# day's tick shard partitions by condition. instrument_type carries the
# market category (``binary`` / ``categorical`` / ``scalar``).


def build_prediction_partition_path(
    *,
    venue: str,
    condition_id: str,
    instrument_type: InstrumentType,
    data_type: str,
    day: _dt.date,
    file_name: str,
) -> str:
    """Build the canonical Prediction partition path (without bucket or
    ``raw_tick_data/by_date/`` prefix — the writer prepends those).

    Wire format:

    ``day={YYYY-MM-DD}/asset_group=prediction/venue={V}/
    instrument_type={IT}/condition_id={CID}/data_type={DT}/{file_name}``

    Used by Polymarket / Kalshi / Manifold prediction-market adapters.

    VERIFY: As of 2026-04-29 the prediction adapters in MTDS construct
    paths inline rather than via a shared helper. This canonical shape is
    derived from the cross-asset pattern (CeFi/TradFi) plus the
    ``condition_id`` axis that polymarket/kalshi pivot on. Audit the
    actual wire format before using as a phantom-detection oracle.
    """
    if not condition_id:
        msg = "condition_id must be a non-empty string"
        raise ValueError(msg)
    if not data_type:
        msg = "data_type must be a non-empty string"
        raise ValueError(msg)
    if not file_name:
        msg = "file_name must be a non-empty string"
        raise ValueError(msg)

    v = _normalize_venue_upper(venue)
    it = instrument_type.value.lower()
    day_str = day.strftime("%Y-%m-%d")
    return (
        f"day={day_str}/{ASSET_GROUP_HIVE_KEY}=prediction/venue={v}/"
        f"instrument_type={it}/condition_id={condition_id}/"
        f"data_type={data_type}/{file_name}"
    )


# ---------------------------------------------------------------------------
# Cross-asset-group dispatcher
# ---------------------------------------------------------------------------


def candidate_parquet_paths(
    asset_group: AssetGroup | str,
    data_type: str,
    day: _dt.date,
    **kwargs: object,
) -> list[str]:
    """Return ordered list of candidate partition paths for any asset_group.

    Args:
        asset_group: Asset group enum or lowercase string token.
        data_type: Data type token (asset-group-specific vocabulary).
        day: Partition day.
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

        league_id = str(kwargs.get("league_id", "") or "")
        include_legacy_archive = bool(kwargs.get("include_legacy_archive", False))
        return sports_candidates(
            data_type=data_type,
            day=day.strftime("%Y-%m-%d") if isinstance(day, _dt.date) else str(day),
            league_id=league_id,
            include_legacy_archive=include_legacy_archive,
        )

    if ag == AssetGroup.DEFI:
        return [
            build_defi_partition_path(
                venue=str(kwargs["venue"]),
                chain=str(kwargs["chain"]),
                instrument_type=_coerce_instrument_type(kwargs["instrument_type"]),
                data_type=data_type,
                day=day,
                file_name=str(kwargs["file_name"]),
            )
        ]

    if ag == AssetGroup.CEFI:
        return [
            build_cefi_partition_path(
                venue=str(kwargs["venue"]),
                instrument_type=_coerce_instrument_type(kwargs["instrument_type"]),
                data_type=data_type,
                day=day,
                file_name=str(kwargs["file_name"]),
            )
        ]

    if ag == AssetGroup.TRADFI:
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
        return [
            build_prediction_partition_path(
                venue=str(kwargs["venue"]),
                condition_id=str(kwargs["condition_id"]),
                instrument_type=_coerce_instrument_type(kwargs["instrument_type"]),
                data_type=data_type,
                day=day,
                file_name=str(kwargs["file_name"]),
            )
        ]

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
    "build_cefi_partition_path",
    "build_defi_partition_path",
    "build_prediction_partition_path",
    "build_tradfi_partition_path",
    "candidate_parquet_paths",
]
