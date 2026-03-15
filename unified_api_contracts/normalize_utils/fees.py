"""Fee normalizers: raw venue fee schemas → CanonicalFee.

Pure field-mapping functions — no business logic.
One function per venue / fee kind.
"""

from __future__ import annotations

from ..external.binance.normalize import normalize_binance_fee_rate
from ..external.bitget.normalize import normalize_bitget_fee
from ..external.bybit.normalize import normalize_bybit_fee_rate
from ..external.ccxt.normalize import normalize_ccxt_fee
from ..external.coinbase.normalize import normalize_coinbase_fee
from ..external.deribit.normalize import normalize_deribit_fee
from ..external.hyperliquid.normalize import normalize_hyperliquid_fee
from ..external.okx.normalize import normalize_okx_fee_rate
from ..external.upbit.normalize import normalize_upbit_fee_rate

__all__ = [
    "normalize_binance_fee_rate",
    "normalize_bitget_fee",
    "normalize_bybit_fee_rate",
    "normalize_ccxt_fee",
    "normalize_coinbase_fee",
    "normalize_deribit_fee",
    "normalize_hyperliquid_fee",
    "normalize_okx_fee_rate",
    "normalize_upbit_fee_rate",
]
