"""Ticker normalizers -- re-exports from per-source modules.

Each venue's normalize_*_ticker function lives in external/{venue}/normalize.py
alongside other normalizers for that venue. This module re-exports them all so
existing callers (normalize_utils.__init__, etc.) continue to work unchanged.
"""

from __future__ import annotations

# Re-exports from per-source normalize.py  (noqa: F401 keeps ruff happy)
from unified_api_contracts.external.aster.normalize import normalize_aster_ticker  # noqa: F401
from unified_api_contracts.external.binance.normalize import normalize_binance_ticker  # noqa: F401
from unified_api_contracts.external.bitget.normalize import normalize_bitget_ticker  # noqa: F401
from unified_api_contracts.external.bitstamp.normalize import normalize_bitstamp_ticker  # noqa: F401
from unified_api_contracts.external.bybit.normalize import normalize_bybit_ticker  # noqa: F401
from unified_api_contracts.external.ccxt.normalize import normalize_ccxt_ticker  # noqa: F401
from unified_api_contracts.external.coinbase.normalize import normalize_coinbase_ticker  # noqa: F401
from unified_api_contracts.external.deribit.normalize import normalize_deribit_ticker  # noqa: F401
from unified_api_contracts.external.huobi.normalize import normalize_huobi_ticker  # noqa: F401
from unified_api_contracts.external.hyperliquid.normalize import normalize_hyperliquid_ticker  # noqa: F401
from unified_api_contracts.external.ibkr.normalize import normalize_ibkr_ticker  # noqa: F401
from unified_api_contracts.external.kalshi.normalize import normalize_kalshi_ticker  # noqa: F401
from unified_api_contracts.external.kraken.normalize import normalize_kraken_ticker  # noqa: F401
from unified_api_contracts.external.kucoin.normalize import normalize_kucoin_ticker  # noqa: F401
from unified_api_contracts.external.mexc.normalize import normalize_mexc_ticker  # noqa: F401
from unified_api_contracts.external.okx.normalize import normalize_okx_ticker  # noqa: F401
from unified_api_contracts.external.upbit.normalize import normalize_upbit_ticker  # noqa: F401
