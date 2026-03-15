"""Liquidation normalizers: raw venue liquidation event -> CanonicalLiquidation.

Covers all major CeFi venues:
  - Binance  (!forceOrder@arr WebSocket stream — BinanceLiquidationOrder)
  - Bybit    (allLiquidation WS stream — BybitLiquidationOrder)
  - OKX      (liquidation-orders WS channel — OKXLiquidationOrder)
  - Deribit  (user fills WS channel, type=liquidation — DeribitLiquidationOrder)
  - Hyperliquid (clearinghouse liquidation event — HyperliquidLiquidation)
  - CoinGlass (liquidation heatmap aggregator — CoinGlassLiquidation stub)

Field mapping conventions:
  - side: "buy" (liquidated a short — exchange buys back) or "sell" (liquidated a long)
  - price: execution/fill price of the liquidation order (Decimal, > 0 when known)
  - size: contracts/coins liquidated (Decimal, > 0 when known)
  - liquidated_account_value: total account value at time of liquidation (USD)
  - liquidated_ntl_pos: total notional position liquidated (USD)
  - liquidated_user: wallet address / userId — marked PII in CanonicalLiquidation
  - is_market_feed: True when from a public WebSocket feed; False when own-account event
    NOTE: is_market_feed is not a field on CanonicalLiquidation; it informs the caller
    which normalizer to use (public vs. private feed).
"""

from __future__ import annotations

from ..external.aster.normalize import normalize_aster_liquidation
from ..external.binance.normalize import normalize_binance_liquidation
from ..external.bybit.normalize import normalize_bybit_liquidation
from ..external.ccxt.normalize import normalize_ccxt_liquidation
from ..external.coinglass.normalize import normalize_coinglass_liquidation
from ..external.deribit.normalize import normalize_deribit_liquidation
from ..external.hyperliquid.normalize import normalize_hyperliquid_liquidation
from ..external.okx.normalize import normalize_okx_liquidation
from ..external.tardis.normalize import normalize_tardis_liquidation

__all__ = [
    "normalize_aster_liquidation",
    "normalize_binance_liquidation",
    "normalize_bybit_liquidation",
    "normalize_ccxt_liquidation",
    "normalize_coinglass_liquidation",
    "normalize_deribit_liquidation",
    "normalize_hyperliquid_liquidation",
    "normalize_okx_liquidation",
    "normalize_tardis_liquidation",
]
