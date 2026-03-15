"""CeFi extended normalizers: Kraken, KuCoin, Gate.io, Bitfinex, Bitstamp, MEXC, Huobi/HTX, Bitget, dYdX.

Each venue provides:
  - normalize_{venue}_trade    -> CanonicalTrade
  - normalize_{venue}_orderbook -> CanonicalOrderBook
  - normalize_{venue}_order    -> CanonicalOrder
  - normalize_{venue}_fill     -> CanonicalFill  (where fill data available)

OKX fill normalizer also added here (uses OKXRealizedPnlResponse as fill proxy).
Deribit fill normalizer added (DeribitSettlementRecord / user trade via DeribitTrade).
Upbit fill normalizer added (UpbitWithdrawalResponse is not a fill; using UpbitOrder executed_volume as fill proxy).
"""

from __future__ import annotations

from ..external.bitfinex.normalize import (
    normalize_bitfinex_fill,
    normalize_bitfinex_order,
    normalize_bitfinex_orderbook,
    normalize_bitfinex_trade,
)
from ..external.bitstamp.normalize import (
    normalize_bitstamp_fill,
    normalize_bitstamp_order,
    normalize_bitstamp_orderbook,
    normalize_bitstamp_trade,
)
from ..external.gateio.normalize import (
    normalize_gateio_fill,
    normalize_gateio_order,
    normalize_gateio_orderbook,
    normalize_gateio_trade,
)
from ..external.kraken.normalize import (
    normalize_kraken_fill,
    normalize_kraken_order,
    normalize_kraken_orderbook,
    normalize_kraken_trade,
)
from ..external.kucoin.normalize import (
    normalize_kucoin_fill,
    normalize_kucoin_order,
    normalize_kucoin_orderbook,
    normalize_kucoin_trade,
)

__all__ = [
    "normalize_bitfinex_fill",
    "normalize_bitfinex_order",
    "normalize_bitfinex_orderbook",
    "normalize_bitfinex_trade",
    "normalize_bitstamp_fill",
    "normalize_bitstamp_order",
    "normalize_bitstamp_orderbook",
    "normalize_bitstamp_trade",
    "normalize_gateio_fill",
    "normalize_gateio_order",
    "normalize_gateio_orderbook",
    "normalize_gateio_trade",
    "normalize_kraken_fill",
    "normalize_kraken_order",
    "normalize_kraken_orderbook",
    "normalize_kraken_trade",
    "normalize_kucoin_fill",
    "normalize_kucoin_order",
    "normalize_kucoin_orderbook",
    "normalize_kucoin_trade",
]
