"""Service emission policy enums — policy types and lifecycle events."""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class ServiceEmissionPolicy(StrEnum):
    """Closed-set policy for what a service publishes when upstream input is incomplete.

    Every (service, output_data_type) pair MUST resolve to exactly one of these. The default
    for unknown pairs is :attr:`STRICT_FAIL` — fail-loud — to force explicit declaration as
    services migrate. See :data:`SERVICE_OUTPUT_POLICIES` for the seeded pairs.
    """

    STRICT_FAIL = "strict_fail"
    """Current-window upstream gap → DON'T publish the output row. Emit ``STALE_DATA``
    lifecycle event (heartbeat-only, no metric). Downstream sees: service is UP but data
    is stale.

    Use for: real-time current-bar metrics (``ohlcv_1m`` current, derivative_ticker
    snapshots), per-archetype signals, per-strategy orders, fills — anywhere partial
    truth is wrong (would mislead a trading decision)."""

    PARTIAL_OK = "partial_ok"
    """Inner-window upstream gaps → publish output row WITH ``completeness_fraction``
    column. Downstream branches its own policy on that fraction.

    Use for: rolling-window aggregates whose denominator is the WINDOW not the inner-bar
    count (``ohlcv_24h`` high/low, daily volume, weekly correlation matrices).
    Catalog-snapshot-style outputs where partial-best-effort is normal."""

    NAN_FILL = "nan_fill"
    """Inner-window upstream gaps → publish output row with NaN where affected.
    Downstream (typically ML) NaN-fills per its own training-time rule.

    Use for: features tree-based models can NaN-fill natively (per CLAUDE.md
    "Honest absence vs fake placeholders" — 1-10% missing tolerance is fine for
    rank-based allocators and tree learners). Rolling vols, autocorrelation matrices,
    feature_groups whose downstream consumer is ML."""

    BLOCK_CRITICAL = "block_critical"
    """Any upstream gap → don't publish + fire P0 alert. No heartbeat-only fallback.

    Use for: position-balance-monitor portfolio_state, execution fill confirmation,
    risk-and-exposure risk_state, ml-training model_version — anywhere "partial truth"
    is worse than "no truth + alert"."""


class EmissionLifecycleEvent(StrEnum):
    """Lifecycle event names emitted by the publish boundary on every emission cycle.

    Downstream branching:

    * **Service-down** (no heartbeat at all over N intervals) → service alarm.
    * **Data-stale** (heartbeat + ``STALE_DATA``) → upstream-data alarm, service is fine.
    * **Degraded-but-running** (``PUBLISHED_DEGRADED``) → operator watch-list, service
      decisions tolerated.
    * **Broken** (``BLOCKED``) → P0, manual intervention required.
    """

    PUBLISHED_OK = "PUBLISHED_OK"
    """``completeness_fraction == 1.0`` — full upstream window represented. Default-happy path."""

    PUBLISHED_DEGRADED = "PUBLISHED_DEGRADED"
    """Gaps present but published per ``PARTIAL_OK`` / ``NAN_FILL`` policy. Event metadata
    carries ``completeness_fraction`` + ``incomplete_window`` (list of upstream
    ``(venue, data_type, instrument_id, iso_window_start, iso_window_end)`` tuples)."""

    STALE_DATA = "STALE_DATA"
    """``STRICT_FAIL`` policy fired — heartbeat-only, no metric row written. Distinguishes
    upstream-data outage from service-process outage (no heartbeat at all)."""

    BLOCKED = "BLOCKED"
    """``BLOCK_CRITICAL`` policy fired — no metric row, P0 alert dispatched.
    Manual operator intervention required."""


EMISSION_LIFECYCLE_EVENTS: Final[frozenset[str]] = frozenset(member.value for member in EmissionLifecycleEvent)
"""String-membership view of :class:`EmissionLifecycleEvent`. UTL event-emission
hot path validates names against this set — unknown event names raise the same
fail-loud pattern as :data:`unified_api_contracts.canonical.crosscutting.honest_coverage.EMPTY_CONFIRMED_REASONS`."""


__all__ = [
    "EMISSION_LIFECYCLE_EVENTS",
    "EmissionLifecycleEvent",
    "ServiceEmissionPolicy",
]
