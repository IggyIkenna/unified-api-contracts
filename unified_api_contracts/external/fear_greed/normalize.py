"""Crypto Fear & Greed Index normalizers.

alternative.me sentiment gauge -> CanonicalOnChainMetric.
Risk regime feature consumed by DeFi/CeFi strategies.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal

from ...canonical.domain import CanonicalOnChainMetric
from .schemas import FearGreedRawObservation, FearGreedReading


def _epoch_to_utc(epoch_seconds: str | int | None) -> datetime:
    """Parse a Unix-epoch-seconds value (int or string) to aware UTC datetime."""
    if epoch_seconds is None or str(epoch_seconds).strip() == "":
        return datetime.now(UTC)
    with contextlib.suppress(ValueError, TypeError, OverflowError, OSError):
        return datetime.fromtimestamp(int(str(epoch_seconds).strip()), tz=UTC)
    return datetime.now(UTC)


def parse_fear_greed_observation(
    raw: FearGreedRawObservation,
    retrieved_at: datetime | None = None,
) -> FearGreedReading | None:
    """Parse a raw ``/fng/`` observation into a typed FearGreedReading.

    Returns None when the value is missing or non-integer (honest absence —
    never fabricate a default index).
    """
    value_str = (raw.value or "").strip()
    if not value_str:
        return None
    try:
        value_int = int(float(value_str))
    except (ValueError, TypeError):
        return None
    return FearGreedReading(
        observed_at=_epoch_to_utc(raw.timestamp),
        value=value_int,
        classification=raw.value_classification or "",
        retrieved_at=retrieved_at if retrieved_at is not None else datetime.now(UTC),
    )


def normalize_fear_greed_reading(
    raw: FearGreedReading,
    venue: str = "fear_greed",
) -> CanonicalOnChainMetric:
    """Convert FearGreedReading to CanonicalOnChainMetric.

    metric_type = "crypto_fear_greed"
    value = index in [0, 100]
    asset = "CRYPTO" (market-wide composite, not a single token)
    """
    ts = raw.observed_at if raw.observed_at.tzinfo else raw.observed_at.replace(tzinfo=UTC)
    return CanonicalOnChainMetric(
        timestamp=ts,
        venue=venue,
        metric_type="crypto_fear_greed",
        asset="CRYPTO",
        value=Decimal(raw.value),
        secondary_value=None,
        entity=None,
        raw={
            "value": raw.value,
            "classification": raw.classification,
        },
    )


__all__ = [
    "normalize_fear_greed_reading",
    "parse_fear_greed_observation",
]
