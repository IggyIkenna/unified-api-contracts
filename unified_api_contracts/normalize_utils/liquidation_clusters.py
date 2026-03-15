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

from ..external.coinglass.normalize import normalize_coinglass_liquidation_cluster
from ..external.hyblock.normalize import normalize_hyblock_liquidation_level

__all__ = [
    "normalize_coinglass_liquidation_cluster",
    "normalize_hyblock_liquidation_level",
]
