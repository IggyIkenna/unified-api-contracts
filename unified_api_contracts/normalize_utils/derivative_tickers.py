"""Normalize raw venue derivative ticker responses to CanonicalDerivativeTicker.

Covers perp/futures venues: Binance (BinancePremiumIndex / BinanceTicker),
Bybit (BybitTicker + BybitFundingRateHistory), OKX (OKXTicker + OKXFundingRate +
OKXOpenInterest), Deribit (DeribitTickerFull), Hyperliquid (HyperliquidTicker),
and Aster (AsterMarkPrice + AsterOpenInterest + AsterFundingRate).

Tardis is a data-replay vendor with no live derivative ticker schema; a stub is
provided that accepts a plain dict and maps whichever keys are present.
"""

from __future__ import annotations

from ..external.aster.normalize import normalize_aster_derivative_ticker
from ..external.binance.normalize import normalize_binance_derivative_ticker
from ..external.bybit.normalize import normalize_bybit_derivative_ticker
from ..external.ccxt.normalize import normalize_ccxt_funding_rate
from ..external.deribit.normalize import normalize_deribit_derivative_ticker
from ..external.hyperliquid.normalize import normalize_hyperliquid_derivative_ticker
from ..external.okx.normalize import normalize_okx_derivative_ticker
from ..external.tardis.normalize import (
    _ms_to_utc,
    _now_utc,
    _to_decimal,
    normalize_tardis_derivative_ticker,
)

__all__ = [
    "_ms_to_utc",
    "_now_utc",
    "_to_decimal",
    "normalize_aster_derivative_ticker",
    "normalize_binance_derivative_ticker",
    "normalize_bybit_derivative_ticker",
    "normalize_ccxt_funding_rate",
    "normalize_deribit_derivative_ticker",
    "normalize_hyperliquid_derivative_ticker",
    "normalize_okx_derivative_ticker",
    "normalize_tardis_derivative_ticker",
]
