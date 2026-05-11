"""External streaming-event SSOT for cross-service Redis Stream payloads.

This package houses Pydantic models for events that traverse Redis Streams between
co-located services (MTDS → MDPS → features-service → strategy-service). They are
distinct from :mod:`unified_api_contracts.internal.events`, which describes the
GCS-archived structured-logging lifecycle envelope.

Streaming events are part of the live-pipeline cascade landed by
``live_pipeline_mtds_mdps_features_2026_05_08`` Phase 1.
"""

from __future__ import annotations

from unified_api_contracts.events.streaming import (
    CandleBoundaryCrossedEvent,
    CandleComputedEvent,
    EmissionOutcome,
    FeaturesComputedEvent,
    InstrumentCacheRefreshTriggerEvent,
)

__all__ = [
    "CandleBoundaryCrossedEvent",
    "CandleComputedEvent",
    "EmissionOutcome",
    "FeaturesComputedEvent",
    "InstrumentCacheRefreshTriggerEvent",
]
