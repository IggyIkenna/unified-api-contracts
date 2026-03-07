"""Liquidation cluster normalizers: raw provider → CanonicalLiquidationCluster.

Covers:
  - CoinGlass liquidation heatmap  (LiquidationHeatmapResponse per level)
  - Hyblock liquidation level API  (HyblockLiquidationLevelResponse per level)

CanonicalLiquidationCluster represents PREDICTED forced-flow concentration at a
price level — distinct from CanonicalLiquidation (an observed liquidation event).

Field mapping:
  - price_level: the price point the cluster is modelled at
  - long_liq_usd: estimated USD value of long liquidations at this level
  - short_liq_usd: estimated USD value of short liquidations at this level
  - leverage_assumption: leverage tier attributed to this level (if known)
  - cluster_strength: normalised intensity [0-1] relative to the session max (if provided)
  - source: "coinglass" | "hyblock"
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ...unified_api_contracts_external.coinglass.schemas import LiquidationHeatmapResponse
from ...unified_api_contracts_external.hyblock.schemas import (
    HyblockLiquidationLevelResponse,
)
from ..domain import CanonicalLiquidationCluster

__all__ = [
    "normalize_coinglass_liquidation_cluster",
    "normalize_hyblock_liquidation_level",
]


def normalize_coinglass_liquidation_cluster(
    raw: LiquidationHeatmapResponse,
    venue: str,
    level_index: int = 0,
) -> CanonicalLiquidationCluster:
    """Convert one CoinGlass heatmap level to CanonicalLiquidationCluster.

    CoinGlass heatmap levels represent MODEL-estimated liquidation concentrations
    (not observed events).  Use CanonicalLiquidation for observed fills.

    Args:
        raw: LiquidationHeatmapResponse from CoinGlass API.
        venue: Underlying exchange this heatmap is for (e.g. "binance").
        level_index: Index into raw.levels to normalise; defaults to 0.

    Returns:
        CanonicalLiquidationCluster for the requested level.
    """
    instrument_key = f"{venue.upper()}:PERPETUAL:{raw.symbol}"
    ts = datetime.fromtimestamp(raw.timestamp_ms / 1000.0, tz=UTC)

    levels = raw.levels
    if not levels or level_index >= len(levels):
        return CanonicalLiquidationCluster(
            instrument_key=instrument_key,
            venue=venue,
            timestamp=ts,
            price_level=Decimal(str(raw.current_price)),
            long_liq_usd=Decimal("0"),
            short_liq_usd=Decimal("0"),
            source="coinglass",
        )

    level = levels[level_index]
    return CanonicalLiquidationCluster(
        instrument_key=instrument_key,
        venue=venue,
        timestamp=ts,
        price_level=Decimal(str(level.price)),
        long_liq_usd=Decimal(str(level.long_liq_usd)),
        short_liq_usd=Decimal(str(level.short_liq_usd)),
        source="coinglass",
    )


def normalize_hyblock_liquidation_level(
    raw: HyblockLiquidationLevelResponse,
    venue: str,
    level_index: int = 0,
) -> CanonicalLiquidationCluster:
    """Convert one Hyblock liquidation level entry to CanonicalLiquidationCluster.

    Hyblock levels may carry per-leverage-tier attribution and a cluster_strength
    score.  Both are mapped through when present.

    Args:
        raw: HyblockLiquidationLevelResponse from Hyblock API.
        venue: Underlying exchange (e.g. "binance").
        level_index: Index into raw.levels to normalise; defaults to 0.

    Returns:
        CanonicalLiquidationCluster for the requested level.
    """
    instrument_key = f"{venue.upper()}:PERPETUAL:{raw.symbol}"
    ts = datetime.fromtimestamp(raw.timestamp_ms / 1000.0, tz=UTC)

    levels = raw.levels
    if not levels or level_index >= len(levels):
        return CanonicalLiquidationCluster(
            instrument_key=instrument_key,
            venue=venue,
            timestamp=ts,
            price_level=Decimal(str(raw.current_price)),
            long_liq_usd=Decimal("0"),
            short_liq_usd=Decimal("0"),
            source="hyblock",
        )

    level = levels[level_index]

    leverage_assumption: Decimal | None = None
    if level.leverage_tier is not None:
        # Parse "10x" → Decimal("10")
        try:
            leverage_assumption = Decimal(level.leverage_tier.lower().rstrip("x"))
        except (ValueError, ArithmeticError):
            leverage_assumption = None

    cluster_strength: Decimal | None = None
    if level.cluster_strength is not None:
        cluster_strength = Decimal(str(level.cluster_strength))

    return CanonicalLiquidationCluster(
        instrument_key=instrument_key,
        venue=venue,
        timestamp=ts,
        price_level=Decimal(str(level.price)),
        long_liq_usd=Decimal(str(level.long_liq_usd)),
        short_liq_usd=Decimal(str(level.short_liq_usd)),
        leverage_assumption=leverage_assumption,
        cluster_strength=cluster_strength,
        source="hyblock",
    )
