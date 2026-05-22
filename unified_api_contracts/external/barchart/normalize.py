"""Barchart normalizers — all normalize_barchart_* functions.

Extracted from normalize_utils/ohlcv.py.

Covers 15-minute OHLCV bar normalization.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ...canonical.domain import CanonicalOhlcvBar
from ...normalize_utils import _helpers
from .schemas import BarchartOhlcv15m

# ---------------------------------------------------------------------------
# Barchart — OHLCV
# ---------------------------------------------------------------------------


def normalize_barchart_ohlcv(raw: BarchartOhlcv15m, venue: str = "barchart") -> CanonicalOhlcvBar:
    """Convert BarchartOhlcv15m to CanonicalOhlcvBar.

    Barchart Time field is a string in US Eastern Time (YYYY-MM-DD HH:MM).
    It is stored as-is (no timezone conversion) and treated as a naive
    local timestamp; callers requiring UTC should convert before calling.
    The field is parsed as UTC-naive then made UTC-aware by attaching UTC tz.
    """
    ts = datetime.strptime(raw.Time, "%Y-%m-%d %H:%M").replace(tzinfo=UTC)
    symbol = "BARCHART"
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=symbol,
        open=_helpers._d(raw.Open),
        high=_helpers._d(raw.High),
        low=_helpers._d(raw.Low),
        close=_helpers._d(raw.Last),
        volume=_helpers._d(raw.Volume),
        quote_volume=None,
        count=None,
        vwap=None,
    )


__all__ = [
    "normalize_barchart_ohlcv",
]
