"""Crypto Fear & Greed Index (alternative.me) response schemas.

Source: https://alternative.me/crypto/fear-and-greed-index/
API: https://api.alternative.me/fng/?limit={N}&format=json
Format: JSON, updated once per day (~00:00 UTC).
Authentication: None required (free, public, no key).

The index is a 0-100 composite crypto risk-sentiment gauge:
  0   = "Extreme Fear"   (historically a buy signal — capitulation)
  100 = "Extreme Greed"  (historically a sell signal — euphoria)
Buckets: 0-24 Extreme Fear, 25-49 Fear, 50-74 Greed, 75-100 Extreme Greed.

DeFi/CeFi strategies use the index (and its day-over-day change) as a
risk-on/risk-off regime feature.
"""

from __future__ import annotations

__api_version__ = "v1"

from dataclasses import dataclass
from datetime import datetime


@dataclass
class FearGreedRawObservation:
    """Single raw observation from the alternative.me ``/fng/`` endpoint.

    All fields arrive as strings in the JSON payload (the API stringifies
    everything). ``timestamp`` is a Unix-epoch-seconds string; ``value`` is
    an integer-valued string in [0, 100].
    """

    value: str
    value_classification: str
    timestamp: str  # Unix epoch seconds, as a string
    time_until_update: str | None = None


@dataclass
class FearGreedResponse:
    """Top-level ``/fng/`` response envelope.

    ``data`` holds one observation per day (most-recent-first), length set by
    the ``limit`` query parameter. ``metadata.error`` is non-null only on an
    upstream error.
    """

    name: str
    data: list[FearGreedRawObservation]
    metadata_error: str | None = None


@dataclass
class FearGreedReading:
    """Typed, parsed Fear & Greed observation for a single day.

    observed_at: UTC timestamp the index applies to (from the API ``timestamp``)
    value: composite index in [0, 100]
    classification: human bucket label (e.g. "Fear", "Extreme Greed")
    retrieved_at: capture time (write-time; immutable per batch==live discipline)
    """

    observed_at: datetime
    value: int  # 0-100
    classification: str
    retrieved_at: datetime
