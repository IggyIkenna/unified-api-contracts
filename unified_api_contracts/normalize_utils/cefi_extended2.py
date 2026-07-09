"""CeFi extended normalizers (part 2): MEXC, Bitget, OKX fill, Deribit fill, Upbit fill.

Split from cefi_extended.py to keep each file under the 900-line limit.

All venue normalizers are now imported from their canonical external/{venue}/normalize.py
modules (single source of truth). This file re-exports them for unified access.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Bitget — from external/bitget/normalize.py
# ---------------------------------------------------------------------------
from ..external.bitget.normalize import (
    normalize_bitget_fill,
    normalize_bitget_order,
    normalize_bitget_orderbook,
    normalize_bitget_trade,
)

# ---------------------------------------------------------------------------
# Deribit fill — from external/deribit/normalize.py
# ---------------------------------------------------------------------------
from ..external.deribit.normalize import normalize_deribit_fill

# ---------------------------------------------------------------------------
# MEXC — from external/mexc/normalize.py
# ---------------------------------------------------------------------------
from ..external.mexc.normalize import (
    normalize_mexc_fill,
    normalize_mexc_order,
    normalize_mexc_orderbook,
    normalize_mexc_trade,
)

# ---------------------------------------------------------------------------
# OKX fill — from external/okx/normalize.py
# ---------------------------------------------------------------------------
from ..external.okx.normalize import normalize_okx_fill

# ---------------------------------------------------------------------------
# Upbit fill — from external/upbit/normalize.py
# ---------------------------------------------------------------------------
from ..external.upbit.normalize import normalize_upbit_fill

__all__ = [
    # Bitget
    "normalize_bitget_fill",
    "normalize_bitget_order",
    "normalize_bitget_orderbook",
    "normalize_bitget_trade",
    # Deribit fill (supplement)
    "normalize_deribit_fill",
    # MEXC
    "normalize_mexc_fill",
    "normalize_mexc_order",
    "normalize_mexc_orderbook",
    "normalize_mexc_trade",
    # OKX fill (supplement)
    "normalize_okx_fill",
    # Upbit fill (supplement)
    "normalize_upbit_fill",
]
