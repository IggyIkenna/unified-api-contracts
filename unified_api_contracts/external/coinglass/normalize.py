"""CoinGlass normalizers — all normalize_coinglass_* functions.

Extracted from normalize_utils/liquidation_clusters.py and normalize_utils/liquidations.py.

Covers liquidation heatmap clusters and liquidation events.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ...canonical.domain import CanonicalLiquidation, CanonicalLiquidationCluster
from .schemas import LiquidationHeatmapResponse

# ---------------------------------------------------------------------------
# CoinGlass — liquidation cluster (heatmap level)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# CoinGlass — liquidation event (heatmap aggregator)
# ---------------------------------------------------------------------------


def normalize_coinglass_liquidation(
    raw: LiquidationHeatmapResponse,
    venue: str,
    level_index: int = 0,
) -> CanonicalLiquidation:
    """Convert a single CoinGlass heatmap level to CanonicalLiquidation.

    CoinGlass is a data aggregator, not a trading venue. Each LiquidationLevel
    represents estimated liquidation USD volume at a price point across an exchange.
    This function maps one level (by `level_index`) to a canonical event.

    For batch processing of all levels, callers should iterate:
        for i, _ in enumerate(response.levels):
            canonical = normalize_coinglass_liquidation(response, venue="binance", level_index=i)

    Args:
        raw: LiquidationHeatmapResponse from CoinGlass API.
        venue: The underlying exchange this heatmap is for (e.g. "binance").
        level_index: Index into raw.levels to normalize; defaults to 0.

    Returns:
        CanonicalLiquidation representing the dominant liquidation direction at this level.
    """
    instrument_key = f"{venue}:PERPETUAL:{raw.symbol}"

    ts = datetime.fromtimestamp(raw.timestamp_ms / 1000.0, tz=UTC)

    levels = raw.levels
    if not levels or level_index >= len(levels):
        # Return zero-sized sentinel if level is missing
        return CanonicalLiquidation(
            instrument_key=instrument_key,
            venue=venue,
            timestamp=ts,
            side="sell",
            price=Decimal(str(raw.current_price)),
            size=Decimal("0"),
        )

    level = levels[level_index]
    level_price = Decimal(str(level.price))
    long_liq = Decimal(str(level.long_liq_usd))
    short_liq = Decimal(str(level.short_liq_usd))
    total_liq = long_liq + short_liq

    # Dominant side: long liq -> sell side (longs are force-sold); short liq -> buy
    side: str = "sell" if long_liq >= short_liq else "buy"
    dominant_liq = max(long_liq, short_liq)

    # Approximate contracts as dominant_usd / price (avoid division by zero)
    size: Decimal = dominant_liq / level_price if level_price > Decimal("0") else Decimal("0")

    account_value: Decimal | None = total_liq if total_liq > Decimal("0") else None

    return CanonicalLiquidation(
        instrument_key=instrument_key,
        venue=venue,
        timestamp=ts,
        side=side,
        price=level_price,
        size=size,
        order_id=None,
        liquidated_account_value=account_value,
        liquidated_ntl_pos=dominant_liq if dominant_liq > Decimal("0") else None,
        liquidated_user=None,
    )


__all__ = [
    "normalize_coinglass_liquidation",
    "normalize_coinglass_liquidation_cluster",
]
