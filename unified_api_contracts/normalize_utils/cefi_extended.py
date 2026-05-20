"""Extended CeFi venue normalizers — re-exports from per-venue modules.

Each venue provides:
  - normalize_{venue}_trade    -> CanonicalTrade
  - normalize_{venue}_orderbook -> CanonicalOrderBook
  - normalize_{venue}_order    -> CanonicalOrder
  - normalize_{venue}_fill     -> CanonicalFill  (where fill data available)

OKX fill normalizer also added here (uses OKXRealizedPnlResponse as fill proxy).
Deribit fill normalizer added (DeribitSettlementRecord / user trade via DeribitTrade).
Upbit fill normalizer added (UpbitWithdrawalResponse is not a fill; using UpbitOrder executed_volume as fill proxy).

All venue normalizers are now imported from their canonical external/{venue}/normalize.py
modules (single source of truth). This file re-exports them for unified access.
"""


from __future__ import annotations

# ---------------------------------------------------------------------------
# KuCoin — from external/kucoin/normalize.py
# ---------------------------------------------------------------------------
from ..external.kucoin.normalize import (
    normalize_kucoin_fill,
    normalize_kucoin_order,
    normalize_kucoin_orderbook,
    normalize_kucoin_trade,
)

# ---------------------------------------------------------------------------
# Re-exports from cefi_extended2.py (MEXC, Huobi, Bitget, OKX, Deribit, Upbit)
# ---------------------------------------------------------------------------
from .cefi_extended2 import (
    normalize_bitget_fill,
    normalize_bitget_order,
    normalize_bitget_orderbook,
    normalize_bitget_trade,
    normalize_deribit_fill,
    normalize_huobi_fill,
    normalize_huobi_order,
    normalize_huobi_orderbook,
    normalize_huobi_trade,
    normalize_mexc_fill,
    normalize_mexc_order,
    normalize_mexc_orderbook,
    normalize_mexc_trade,
    normalize_okx_fill,
    normalize_upbit_fill,
)

__all__ = [
    # Bitget
    "normalize_bitget_fill",
    "normalize_bitget_order",
    "normalize_bitget_orderbook",
    "normalize_bitget_trade",
    # Deribit fill
    "normalize_deribit_fill",
    # Huobi / HTX
    "normalize_huobi_fill",
    "normalize_huobi_order",
    "normalize_huobi_orderbook",
    "normalize_huobi_trade",
    # KuCoin
    "normalize_kucoin_fill",
    "normalize_kucoin_order",
    "normalize_kucoin_orderbook",
    "normalize_kucoin_trade",
    # MEXC
    "normalize_mexc_fill",
    "normalize_mexc_order",
    "normalize_mexc_orderbook",
    "normalize_mexc_trade",
    # OKX fill
    "normalize_okx_fill",
    # Upbit fill
    "normalize_upbit_fill",
]
