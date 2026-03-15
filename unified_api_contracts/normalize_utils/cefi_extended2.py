"""CeFi extended normalizers (part 2): MEXC, Huobi/HTX, Bitget, dYdX v4, OKX fill, Deribit fill, Upbit fill.

Split from cefi_extended.py to keep each file under the 900-line limit.
"""

from __future__ import annotations

from ..external.bitget.normalize import (
    normalize_bitget_fill,
    normalize_bitget_order,
    normalize_bitget_orderbook,
    normalize_bitget_trade,
)
from ..external.deribit.normalize import normalize_deribit_fill
from ..external.dydx.normalize import (
    normalize_dydx_fill,
    normalize_dydx_order,
    normalize_dydx_orderbook,
    normalize_dydx_trade,
)
from ..external.huobi.normalize import (
    normalize_huobi_fill,
    normalize_huobi_order,
    normalize_huobi_orderbook,
    normalize_huobi_trade,
)
from ..external.mexc.normalize import (
    normalize_mexc_fill,
    normalize_mexc_order,
    normalize_mexc_orderbook,
    normalize_mexc_trade,
)
from ..external.okx.normalize import normalize_okx_fill
from ..external.upbit.normalize import normalize_upbit_fill

__all__ = [
    "normalize_bitget_fill",
    "normalize_bitget_order",
    "normalize_bitget_orderbook",
    "normalize_bitget_trade",
    "normalize_deribit_fill",
    "normalize_dydx_fill",
    "normalize_dydx_order",
    "normalize_dydx_orderbook",
    "normalize_dydx_trade",
    "normalize_huobi_fill",
    "normalize_huobi_order",
    "normalize_huobi_orderbook",
    "normalize_huobi_trade",
    "normalize_mexc_fill",
    "normalize_mexc_order",
    "normalize_mexc_orderbook",
    "normalize_mexc_trade",
    "normalize_okx_fill",
    "normalize_upbit_fill",
]
