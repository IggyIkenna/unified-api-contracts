"""DataTypeCapability registry — per (asset_group, data_type, venue) live/batch.

The catalogue generator joins this registry with the manifest to compute
``live_ready`` / ``batch_ready`` per tuple and to surface retention /
TTM / liquidity cutoffs in the catalogue artefact.

This is a seed registry — populated against high-volume capture targets as
of 2026-04-29. Every entry carries a ``# source:`` reference (file or
ADR) so future maintainers can verify the row. Missing tuples in the
catalogue generator default to ``live_capable=False`` /
``batch_capable=True`` — the venue clearly writes data (it appears in the
manifest) but we don't have a streaming declaration for it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from unified_api_contracts.canonical.gcs_paths import AssetGroup


@dataclass(frozen=True)
class DataTypeCapability:
    """Per-tuple capability declaration.

    Identifying axes (``asset_group`` / ``data_type`` / ``venue`` /
    ``instrument_type``) match the manifest shard key columns. Coverage
    cutoffs (``ttm_cutoff_days`` / ``liquidity_cutoff_usd`` /
    ``retention_days``) carry through to the catalogue MD output so
    downstream readers can reason about expected denominator clipping.
    """

    asset_group: AssetGroup
    data_type: str
    venue: str
    instrument_type: str | None = None
    live_capable: bool = False  # WS / streaming feed exists
    batch_capable: bool = True  # REST / parquet snapshot exists
    streaming_protocol: str | None = None  # "ws" | "fix" | "sse" | None
    requires_credentials: bool = False
    ttm_cutoff_days: int | None = None  # options: ignore expiries beyond this
    liquidity_cutoff_usd: float | None = None  # ignore < this 24h volume
    retention_days: int | None = None  # rolling-window cutoff; None = unbounded
    notes: str | None = None
    sources: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Seed registry
# ---------------------------------------------------------------------------
# Ordering: by asset_group → data_type → venue. Each entry is a frozen
# dataclass — never mutate at import time.

DATA_TYPE_CAPABILITY_REGISTRY: Final[tuple[DataTypeCapability, ...]] = (
    # =====================================================================
    # CeFi
    # =====================================================================
    # Trades
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="BINANCE",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        retention_days=None,
        sources=("market_tick_data_service/market_interface/adapters/binance/",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="BINANCE",
        instrument_type="spot",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/binance/",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="DERIBIT",
        instrument_type="option",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        ttm_cutoff_days=180,
        liquidity_cutoff_usd=10_000.0,
        sources=("market_tick_data_service/market_interface/adapters/deribit.py",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="DERIBIT",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/deribit.py",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="HYPERLIQUID",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/hyperliquid/",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="OKX",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/okx/",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="BYBIT",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/bybit/",),
    ),
    # Funding rates
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="funding_rate",
        venue="BINANCE",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="funding_rate",
        venue="OKX",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="funding_rate",
        venue="BYBIT",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="funding_rate",
        venue="DERIBIT",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="funding_rate",
        venue="HYPERLIQUID",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    # Liquidations
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="liquidations",
        venue="BINANCE",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="liquidations",
        venue="HYPERLIQUID",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    # Open interest
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="open_interest",
        venue="BINANCE",
        instrument_type="perpetual",
        live_capable=False,
        batch_capable=True,
        notes="REST poll only — venue does not stream OI",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="open_interest",
        venue="DERIBIT",
        instrument_type="option",
        live_capable=False,
        batch_capable=True,
        ttm_cutoff_days=365,
    ),
    # Book snapshots
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="book_snapshot",
        venue="BINANCE",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="book_snapshot",
        venue="DERIBIT",
        instrument_type="option",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        liquidity_cutoff_usd=5_000.0,
    ),
    # =====================================================================
    # DeFi
    # =====================================================================
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="lending_indices",
        venue="AAVE_V3",
        instrument_type="a_token",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
        notes="On-chain block-by-block indexing; live = follow head",
        sources=("market_tick_data_service/market_interface/adapters/defi/aave/",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="dex_pool_swaps",
        venue="UNISWAP_V3",
        instrument_type="pool",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
        liquidity_cutoff_usd=1_000_000.0,
        notes="Pool TVL filter — sub-1M pools dropped from canonical capture",
        sources=("market_tick_data_service/market_interface/adapters/defi/uniswap_v3_adapter.py",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="dex_pool_state",
        venue="UNISWAP_V3",
        instrument_type="pool",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="lst_rates",
        venue="LIDO",
        instrument_type="lst",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="yield_snapshots",
        venue="ETHENA",
        instrument_type="yield_bearing",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    # =====================================================================
    # TradFi
    # =====================================================================
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="rates_curve",
        venue="FRED",
        instrument_type="bond",
        live_capable=False,
        batch_capable=True,
        notes="Daily series; FRED publishes after-hours",
        sources=("market_tick_data_service/market_interface/adapters/tradfi/fred_adapter.py",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="options_chain",
        venue="OPRA",
        instrument_type="option",
        live_capable=False,
        batch_capable=True,
        ttm_cutoff_days=365,
        liquidity_cutoff_usd=1_000.0,
        sources=("market_tick_data_service/market_interface/adapters/tradfi/databento_opra_converter.py",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="etf_flows",
        venue="TARDIS",
        instrument_type="etf",
        live_capable=False,
        batch_capable=True,
        sources=("market_tick_data_service/market_interface/adapters/tradfi/tardis_adapter.py",),
    ),
    # =====================================================================
    # Prediction
    # =====================================================================
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="trades",
        venue="POLYMARKET",
        instrument_type="prediction_market",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/prediction/polymarket_adapter.py",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="book_snapshot",
        venue="POLYMARKET",
        instrument_type="prediction_market",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="trades",
        venue="KALSHI",
        instrument_type="prediction_market",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="market_metadata",
        venue="POLYMARKET",
        instrument_type="prediction_market",
        live_capable=False,
        batch_capable=True,
        notes="Market list refreshed via REST poll",
    ),
    # =====================================================================
    # Sports
    # =====================================================================
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="FIXTURES",
        venue="API_FOOTBALL",
        instrument_type="fixture",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="ODDS",
        venue="ODDS_API",
        instrument_type="fixture",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
        retention_days=730,
        notes="Odds-API historical depth limited by tier",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="FIXTURE_EVENTS",
        venue="API_FOOTBALL",
        instrument_type="fixture",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
)


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------


def find_capability(
    asset_group: AssetGroup | str,
    data_type: str,
    venue: str,
    instrument_type: str | None = None,
) -> DataTypeCapability | None:
    """Return the matching capability or ``None``.

    ``instrument_type=None`` matches the first row with the same
    (asset_group, data_type, venue) regardless of instrument_type — useful
    when the caller doesn't have an instrument_type axis (e.g. the venue
    has only one).
    """
    ag = AssetGroup(asset_group) if not isinstance(asset_group, AssetGroup) else asset_group
    for cap in DATA_TYPE_CAPABILITY_REGISTRY:
        if cap.asset_group != ag:
            continue
        if cap.data_type != data_type:
            continue
        if cap.venue != venue:
            continue
        if instrument_type is not None and cap.instrument_type != instrument_type:
            continue
        return cap
    return None


def capabilities_for_asset_group(
    asset_group: AssetGroup | str,
) -> tuple[DataTypeCapability, ...]:
    """Return all capability rows for an asset group."""
    ag = AssetGroup(asset_group) if not isinstance(asset_group, AssetGroup) else asset_group
    return tuple(c for c in DATA_TYPE_CAPABILITY_REGISTRY if c.asset_group == ag)


__all__ = [
    "DATA_TYPE_CAPABILITY_REGISTRY",
    "DataTypeCapability",
    "capabilities_for_asset_group",
    "find_capability",
]
