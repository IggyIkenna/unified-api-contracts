"""Ticker normalizers -- re-exports from per-source modules.

Each venue's normalize_*_ticker function lives in external/{venue}/normalize.py
alongside other normalizers for that venue. This module re-exports them all so
existing callers (normalize_utils.__init__, etc.) continue to work unchanged.
"""

from __future__ import annotations

# Re-exports from per-source normalize.py  (noqa: F401 keeps ruff happy)
from ..external.aster.normalize import normalize_aster_ticker
from ..external.binance.normalize import normalize_binance_ticker
from ..external.bitget.normalize import normalize_bitget_ticker
from ..external.bybit.normalize import normalize_bybit_ticker
from ..external.ccxt.normalize import normalize_ccxt_ticker
from ..external.coinbase.normalize import normalize_coinbase_ticker
from ..external.deribit.normalize import normalize_deribit_ticker
from ..external.huobi.normalize import normalize_huobi_ticker
from ..external.hyperliquid.normalize import normalize_hyperliquid_ticker
from ..external.ibkr.normalize import normalize_ibkr_ticker
from ..external.kalshi.normalize import normalize_kalshi_ticker
from ..external.kucoin.normalize import normalize_kucoin_ticker
from ..external.mexc.normalize import normalize_mexc_ticker
from ..external.okx.normalize import normalize_okx_ticker
from ..external.upbit.normalize import normalize_upbit_ticker

__all__ = [
    "normalize_aster_ticker",
    "normalize_binance_ticker",
    "normalize_bitget_ticker",
    "normalize_bybit_ticker",
    "normalize_ccxt_ticker",
    "normalize_coinbase_ticker",
    "normalize_deribit_ticker",
    "normalize_huobi_ticker",
    "normalize_hyperliquid_ticker",
    "normalize_ibkr_ticker",
    "normalize_kalshi_ticker",
    "normalize_kucoin_ticker",
    "normalize_mexc_ticker",
    "normalize_okx_ticker",
    "normalize_upbit_ticker",
]
