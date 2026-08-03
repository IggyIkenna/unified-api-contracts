"""Venue-agnostic classifications for internal write-guard rejections.

These are NOT vendor/venue API errors — they're raised by our OWN write-time
guards (e.g. MTDS partition-alignment validation) before any data reaches
storage, and can occur for ANY venue. They live under the pseudo-venue key
"internal" rather than being duplicated per real venue; classify_venue_error()
falls back to this bucket when a venue-specific lookup misses.
"""

from __future__ import annotations

from ._types import ErrorAction, VenueErrorClassification, ve

INTERNAL_VENUE_KEY = "internal"

VENUE_ERRORS_INTERNAL: dict[str, list[VenueErrorClassification]] = {
    INTERNAL_VENUE_KEY: [
        ve(
            INTERNAL_VENUE_KEY,
            "UpstreamTimestampBiasError",
            retry=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            desc=(
                "MTDS write-time guard: adapter received ticks but ALL fell outside the "
                "requested day partition after interval filtering (upstream partition "
                "mislabeled, replay window wrong, or clock skew) — not a vendor API error."
            ),
        ),
    ],
}
