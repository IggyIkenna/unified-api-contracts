"""alternative.me Fear and Greed Index normalizers.

Fear & Greed index -> CanonicalOnChainMetric (metric_type="fear_greed").
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ...canonical.domain import CanonicalOnChainMetric
from .schemas import FearGreedReading


def _unix_to_utc(ts: int | str | None) -> datetime:
    """Convert Unix timestamp (seconds) to UTC datetime."""
    if ts is None:
        return datetime.now(UTC)
    try:
        return datetime.fromtimestamp(int(str(ts)), tz=UTC)
    except (ValueError, OSError, OverflowError):
        return datetime.now(UTC)


def normalize_fear_greed_reading(
    raw: FearGreedReading,
    venue: str = "alternative_me",
) -> CanonicalOnChainMetric | None:
    """Normalize FearGreedReading to CanonicalOnChainMetric.

    metric_type="fear_greed", value=0-100 index.
    """
    if raw.value is None:
        return None
    ts = _unix_to_utc(raw.timestamp)
    return CanonicalOnChainMetric(
        timestamp=ts,
        venue=venue,
        metric_type="fear_greed",
        asset="CRYPTO",
        value=Decimal(str(raw.value)),
        raw={
            "value": raw.value,
            "value_classification": str(raw.value_classification) if raw.value_classification else None,
            "timestamp": raw.timestamp,
        },
    )


__all__ = [
    "normalize_fear_greed_reading",
]
