"""Streaming event payloads for the live-pipeline Redis Stream cascade.

Three events traverse Redis Streams between co-located services in the live
pipeline:

* :class:`CandleBoundaryCrossedEvent` — published by MTDS when a window
  (``period_start`` … ``period_end``) closes for a given
  ``(asset_group, venue, data_type, instrument_id, timeframe)`` shard.
  Consumers (MDPS) read this and trigger candle aggregation for the closed
  window.
* :class:`CandleComputedEvent` — published by MDPS when an aggregated candle
  is finalised. Consumers (features-service, strategy-service) read this and
  fire downstream feature compute / signal evaluation.
* :class:`InstrumentCacheRefreshTriggerEvent` — published by instruments-service
  after every successful catalog refresh. Consumers (MTDS / MDPS / features
  -service) diff their in-process instrument cache and hot-reload deltas
  without bouncing the process.

Schema invariants (enforced by tests in
``tests/unit/test_streaming_events.py``):

* Every payload carries ``correlation_id``, ``vm_name``, ``pipeline_mode``
  (defaulting to :attr:`PipelineMode.LIVE_WEBSOCKET` for live-pipeline
  streaming), and ``asset_group``.
* :class:`CandleBoundaryCrossedEvent.period_end` minus ``period_start``
  exactly equals the duration encoded by ``timeframe`` (``"15s"``,
  ``"1m"``, ``"5m"``, ``"15m"``, ``"1h"``, ``"1d"``).
* ``data_freshness`` is closed-set per event (see each class docstring).
* :class:`CandleComputedEvent.emission_policy` records the POLICY in effect
  for the publishing service per
  :class:`unified_api_contracts.canonical.crosscutting.service_emission_policy.ServiceEmissionPolicy`.
  The orthogonal ``emission_outcome`` field records the OUTCOME of the
  decision per :class:`EmissionOutcome` (publishing OK, publishing degraded,
  stale heartbeat, blocked).

Plan: ``live_pipeline_mtds_mdps_features_2026_05_08`` Phase 1.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Final, Literal

from pydantic import BaseModel, Field

from unified_api_contracts.canonical.crosscutting.pipeline_mode import PipelineMode
from unified_api_contracts.canonical.crosscutting.service_emission_policy import (
    ServiceEmissionPolicy,
)
from unified_api_contracts.canonical.gcs_paths import AssetGroup
from unified_api_contracts.internal.domain.market_data_processing.candle_schema import (
    DataType,
)

# ---------------------------------------------------------------------------
# Timeframe parsing helper
#
# ``timeframe`` is a closed-set string token (no calendar-based timeframes —
# weeks/months are NOT supported because their duration is non-constant).
# ---------------------------------------------------------------------------


_TIMEFRAME_TO_TIMEDELTA: Final[dict[str, timedelta]] = {
    "15s": timedelta(seconds=15),
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
    "1d": timedelta(days=1),
}


def parse_timeframe(timeframe: str) -> timedelta:
    """Return the :class:`~datetime.timedelta` corresponding to a timeframe token.

    Raises :class:`ValueError` for unknown tokens. The closed set covers
    every timeframe used by the live-pipeline OHLCV cascade; longer
    timeframes (1w, 1mo) are intentionally absent because their duration
    varies (week-on-week DST drift, calendar-month length differences) and
    cannot be encoded as a single ``timedelta``.
    """

    try:
        return _TIMEFRAME_TO_TIMEDELTA[timeframe]
    except KeyError as exc:
        raise ValueError(
            f"Unknown timeframe token {timeframe!r}; expected one of {sorted(_TIMEFRAME_TO_TIMEDELTA)}."
        ) from exc


# ---------------------------------------------------------------------------
# Emission outcome — orthogonal to ServiceEmissionPolicy
#
# ServiceEmissionPolicy values describe the POLICY (the rule). EmissionOutcome
# values describe the OUTCOME (the result of applying the rule on this row).
# A row published under PARTIAL_OK can still be PUBLISHED_OK if the upstream
# window happened to be complete; the policy is the floor, the outcome is the
# observed event.
# ---------------------------------------------------------------------------


EmissionOutcome = Literal[
    "PUBLISHED_OK",
    "PUBLISHED_DEGRADED",
    "STALE_DATA",
    "BLOCKED",
]
"""Closed-set outcome of an emission cycle.

Mirrors the names of
:class:`~unified_api_contracts.canonical.crosscutting.service_emission_policy.EmissionLifecycleEvent`
so the streaming event's ``emission_outcome`` value matches what a downstream
event-stream subscriber would observe in the lifecycle stream.

* ``PUBLISHED_OK`` — full upstream window represented; no completeness
  fraction needed.
* ``PUBLISHED_DEGRADED`` — gaps present but published per ``PARTIAL_OK`` /
  ``NAN_FILL`` policy.
* ``STALE_DATA`` — ``STRICT_FAIL`` policy fired; heartbeat-only, no metric
  row written. The :class:`CandleComputedEvent` still publishes for
  visibility but downstream consumers should treat the row as
  non-actionable.
* ``BLOCKED`` — ``BLOCK_CRITICAL`` policy fired; P0 alert dispatched.
"""


# ---------------------------------------------------------------------------
# Event payloads
# ---------------------------------------------------------------------------


class CandleBoundaryCrossedEvent(BaseModel):
    """Published by MTDS when a candle window closes for a streaming shard.

    Stream-name convention: ``streaming.{asset_group}.candle_boundary_crossed``.

    Consumers (MDPS) use ``period_start`` / ``period_end`` to scope the
    aggregation read and ``tick_count`` to short-circuit zero-activity
    windows per the Phase 2.A zero-activity-bar rule.

    Invariants:

    * ``period_end - period_start == parse_timeframe(timeframe)`` — exact.
    * ``period_end <= available_at`` — finalisation never precedes window
      close.
    * ``data_freshness`` is one of ``"FRESH"`` (no WS reconnect mid-window)
      or ``"STALE"`` (one or more WS reconnects during the window; tick
      sequence may have gaps).
    * ``pipeline_mode`` defaults to :attr:`PipelineMode.LIVE_WEBSOCKET`;
      batch replays of the live cascade override with the matching
      ``BATCH_<SOURCE>`` value.
    """

    event_type: Literal["CANDLE_BOUNDARY_CROSSED"] = "CANDLE_BOUNDARY_CROSSED"
    asset_group: AssetGroup
    venue: str
    chain: str | None = None
    instrument_id: str | None = None
    data_type: DataType
    instrument_type: str | None = None
    league_id: str | None = None
    timeframe: str = Field(
        ...,
        description=("Closed-set timeframe token: one of '15s' / '1m' / '5m' / '15m' / '1h' / '1d'."),
    )
    period_start: datetime = Field(
        ...,
        description="UTC, aligned to the timeframe boundary.",
    )
    period_end: datetime = Field(
        ...,
        description="UTC, aligned (period_start + timeframe).",
    )
    tick_count: int = Field(
        ...,
        ge=0,
        description="Number of source ticks captured for the window.",
    )
    available_at: datetime = Field(
        ...,
        description="When MTDS finalised the window (= period_end + grace).",
    )
    data_freshness: Literal["FRESH", "STALE"] = "FRESH"
    pipeline_mode: PipelineMode = PipelineMode.LIVE_WEBSOCKET
    correlation_id: str
    vm_name: str


class CandleComputedEvent(BaseModel):
    """Published by MDPS when an aggregated candle finalises for a shard.

    Stream-name convention: ``streaming.{asset_group}.candle_computed``.

    Consumers (features-service, strategy-service) use ``available_at`` to
    pin the upstream-row availability column on derived features, and
    ``emission_policy`` + ``emission_outcome`` to decide whether the
    downstream compute should fire or skip.

    The ``emission_policy`` field carries the POLICY governing this output
    per
    :class:`~unified_api_contracts.canonical.crosscutting.service_emission_policy.ServiceEmissionPolicy`
    (``STRICT_FAIL`` / ``PARTIAL_OK`` / ``NAN_FILL`` / ``BLOCK_CRITICAL``).
    The orthogonal ``emission_outcome`` field carries the OUTCOME of
    applying the policy to this row per :data:`EmissionOutcome`
    (``PUBLISHED_OK`` / ``PUBLISHED_DEGRADED`` / ``STALE_DATA`` /
    ``BLOCKED``). Per CLAUDE.md "service emission policy" SSOT, an unseeded
    pair defaults to ``STRICT_FAIL`` (policy) — the row's actual outcome is
    set explicitly by the publisher each emission.

    Invariants:

    * ``data_freshness`` is one of ``"FRESH"``, ``"STALE"``, or
      ``"ZERO_ACTIVITY_BAR"`` (Phase 2.A zero-activity-bar rule:
      catalog-alive + market-hours + zero source ticks → carry-forward
      LTP / odds bar).
    * ``emission_outcome`` defaults to ``"PUBLISHED_OK"``.
    * ``policy_decision_reason`` is required when ``emission_outcome`` is
      ``"STALE_DATA"`` or ``"BLOCKED"``; optional for the publish-row
      outcomes (the publisher may still record one).
    """

    event_type: Literal["CANDLE_COMPUTED"] = "CANDLE_COMPUTED"
    asset_group: AssetGroup
    venue: str
    chain: str | None = None
    instrument_id: str | None = None
    data_type: DataType
    instrument_type: str | None = None
    league_id: str | None = None
    timeframe: str = Field(
        ...,
        description=("Closed-set timeframe token: one of '15s' / '1m' / '5m' / '15m' / '1h' / '1d'."),
    )
    period_start: datetime = Field(
        ...,
        description="UTC, aligned to the timeframe boundary.",
    )
    period_end: datetime = Field(
        ...,
        description="UTC, aligned (period_start + timeframe).",
    )
    row_count: int = Field(
        ...,
        ge=0,
        description="Rows in the emitted candle parquet (1 per window for OHLCV).",
    )
    available_at: datetime = Field(
        ...,
        description=("When MDPS finalised the candle (= window_close + aggregation latency)."),
    )
    data_freshness: Literal["FRESH", "STALE", "ZERO_ACTIVITY_BAR"] = "FRESH"
    emission_policy: ServiceEmissionPolicy = ServiceEmissionPolicy.STRICT_FAIL
    emission_outcome: EmissionOutcome = "PUBLISHED_OK"
    policy_decision_reason: str | None = None
    pipeline_mode: PipelineMode = PipelineMode.LIVE_WEBSOCKET
    correlation_id: str
    vm_name: str


class InstrumentCacheRefreshTriggerEvent(BaseModel):
    """Published by instruments-service after every successful catalog refresh.

    Stream-name convention: ``streaming.{asset_group}.instrument_cache_refresh_trigger``.

    Consumers (MTDS / MDPS / features-service) read this + diff their
    in-process instrument cache. ``row_count_added_since_last`` /
    ``row_count_removed_since_last`` of zero means consumers can skip the
    cache-refresh round-trip (no delta).

    The shape mirrors
    :class:`~unified_api_contracts.canonical.crosscutting.service_emission_policy.EmissionLifecycleEvent`-style
    payloads so existing event subscribers don't need a new code path —
    they receive structured fields and dispatch on ``event_type``.

    Invariants:

    * ``catalog_refresh_at`` is when the catalog parquet was finalised.
    * ``row_count_total`` is the canonical full-catalog row count
      post-refresh (snapshot view, not delta).
    * ``pipeline_mode`` defaults to :attr:`PipelineMode.LIVE_WEBSOCKET`;
      catalog snapshots refreshed during a batch replay override.
    """

    event_type: Literal["INSTRUMENT_CACHE_REFRESH_TRIGGER"] = "INSTRUMENT_CACHE_REFRESH_TRIGGER"
    asset_group: AssetGroup
    catalog_refresh_at: datetime = Field(
        ...,
        description="When the catalog parquet was finalised.",
    )
    row_count_total: int = Field(
        ...,
        ge=0,
        description="Canonical full-catalog row count post-refresh.",
    )
    row_count_added_since_last: int = Field(
        ...,
        ge=0,
        description="0 → consumers skip cache refresh.",
    )
    row_count_removed_since_last: int = Field(
        ...,
        ge=0,
    )
    pipeline_mode: PipelineMode = PipelineMode.LIVE_WEBSOCKET
    correlation_id: str
    vm_name: str


__all__ = [
    "CandleBoundaryCrossedEvent",
    "CandleComputedEvent",
    "EmissionOutcome",
    "InstrumentCacheRefreshTriggerEvent",
    "parse_timeframe",
]
