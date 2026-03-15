"""Pyth Network normalizers — all normalize_pyth_* functions.

Extracted from normalize_utils/onchain.py.

Covers oracle price feeds with fixed-point conversion: price * 10^expo.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from ...canonical.domain import CanonicalOraclePriceFeed
from .schemas import PythPriceFeed

# ---------------------------------------------------------------------------
# Pyth Network — oracle price feeds
# ---------------------------------------------------------------------------


def normalize_pyth_price_feed(
    raw: PythPriceFeed,
    venue: str = "pyth",
) -> CanonicalOraclePriceFeed | None:
    """Normalize PythPriceFeed to CanonicalOraclePriceFeed.

    Pyth fixed-point: actual_price = price_mantissa * 10^expo.
    publish_time is microseconds since epoch.

    Args:
        raw:   PythPriceFeed from the WebSocket or REST response.
        venue: Provider tag, defaults to "pyth".
    """
    if raw.price is None or raw.expo is None:
        return None

    try:
        exponent = int(raw.expo)
        price_decimal = Decimal(str(raw.price)) * (Decimal(10) ** exponent)
    except (InvalidOperation, ValueError, TypeError, ArithmeticError):
        return None

    confidence: Decimal | None = None
    if raw.conf is not None:
        try:
            confidence = Decimal(str(raw.conf)) * (Decimal(10) ** exponent)
        except (InvalidOperation, ValueError, TypeError, ArithmeticError):
            confidence = None

    # publish_time is microseconds
    ts: datetime
    if raw.publish_time is not None:
        try:
            ts = datetime.fromtimestamp(raw.publish_time / 1_000_000, tz=UTC)
        except (ValueError, OSError, OverflowError):
            ts = datetime.now(UTC)
    else:
        ts = datetime.now(UTC)

    return CanonicalOraclePriceFeed(
        timestamp=ts,
        venue=venue,
        feed_id=raw.id or "",
        price=price_decimal,
        confidence=confidence,
    )


__all__ = [
    "normalize_pyth_price_feed",
]
