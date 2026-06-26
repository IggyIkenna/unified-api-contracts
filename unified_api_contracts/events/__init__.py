"""External streaming-event SSOT for the live-pipeline event bus.

This package houses Pydantic models for events that traverse the live-pipeline
event bus (currently Redis Streams; migrating to GCP Pub/Sub via
``live_data_persistence_central_event_log_2026_06_25.md``).

Two sub-modules:

* :mod:`~unified_api_contracts.events.streaming` — legacy Redis-stream event
  shapes (``CandleBoundaryCrossedEvent`` / ``CandleComputedEvent`` / ...).
  These are **in-flight migration** to the canonical envelope below; they
  remain exported for backward compat during the Plans 04-06 cutover.
* :mod:`~unified_api_contracts.events.persist` — canonical
  :class:`CanonicalPersistEnvelope` + :class:`RetentionClass` for the
  Pub/Sub central log. New producers use this shape.
* :mod:`~unified_api_contracts.events.sink_matrix` — :data:`SINK_MATRIX`
  lookup + :func:`retention_class_for` / :func:`sinks_for` resolvers.
"""

from __future__ import annotations

from unified_api_contracts.events.persist import (
    CanonicalPersistEnvelope,
    RetentionClass,
)
from unified_api_contracts.events.sink_matrix import (
    SINK_MATRIX,
    SinkConfig,
    retention_class_for,
    sinks_for,
)
from unified_api_contracts.events.streaming import (
    CandleBoundaryCrossedEvent,
    CandleComputedEvent,
    EmissionOutcome,
    FeaturesComputedEvent,
    InstrumentCacheRefreshTriggerEvent,
    parse_timeframe,
)

__all__ = [
    "SINK_MATRIX",
    "CandleBoundaryCrossedEvent",
    "CandleComputedEvent",
    "CanonicalPersistEnvelope",
    "EmissionOutcome",
    "FeaturesComputedEvent",
    "InstrumentCacheRefreshTriggerEvent",
    "RetentionClass",
    "SinkConfig",
    "parse_timeframe",
    "retention_class_for",
    "sinks_for",
]
