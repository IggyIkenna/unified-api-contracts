"""Per-market lifecycle SSOT for prediction markets.

Predictions plan
``predictions_canonical_question_group_polymarket_migration_2026_05_06.plan.md``
Phase 1A.

CLAUDE.md "Prediction market lifecycle timing" rule:
prediction markets (Polymarket / Kalshi / others) are NOT static
instruments. Each market has a lifecycle:

* ``market_created_at`` — when the market was listed.
* ``resolution_time`` — when the outcome was determined.
* ``settlement_time`` — when payouts cleared (typical UMA undisputed
  +2h, disputed +48-72h; see
  :data:`unified_api_contracts.canonical.domain.predictions.canonical_groups.CANONICAL_GROUP_METADATA`
  for per-group ``settlement_lag``).

MTDS CLOB capture must respect lifecycle bounds (NO ticks before
``market_created_at``; NO new ticks after ``settlement_time``). Cluster
validation per ``(canonical_question_group, day)`` checks that all
expected market_ids with active windows in that day are represented
(HOURLY → 24, DAILY → 1, etc.). LookaheadBiasError respects per-market
lifecycle: a feature compute at time T can only consume ticks where
``tick.timestamp <= T`` AND ``tick.market_id``'s
``market_created_at <= T``.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, time, timezone
from datetime import date as _date_t
from typing import Final, Literal

from unified_api_contracts.canonical.domain.predictions.canonical_groups import (
    CanonicalQuestionGroup,
)

_LifecycleStatus = Literal["created", "active", "resolved", "settled"]


@dataclass(frozen=True)
class MarketLifecycle:
    """Per-market lifecycle record.

    Persisted in instruments-service's ``MARKET_LIFECYCLE`` data_type
    parquet (one row per market_id). Read by MTDS adapters at write-time
    to gate ticks within ``[market_created_at, settlement_time)`` and by
    features-cross-instrument at compute-time to enforce per-market
    LookaheadBiasError.

    Args:
        market_id: Raw venue identifier — Polymarket conditionId or
            Kalshi ticker.
        venue: ``"POLYMARKET"`` or ``"KALSHI"``.
        canonical_group: Canonical group this market belongs to (output
            of ``classify_polymarket_to_canonical_group`` /
            ``classify_kalshi_to_canonical_group`` from the predictions facade).
        market_created_at: When the market was listed by the venue.
        resolution_time: When the outcome was determined.
        settlement_time: When payouts cleared. Falls back to
            ``resolution_time + canonical_group.settlement_lag`` when the
            source doesn't expose it directly (caller flags
            ``settlement_time_confidence="low_lifecycle_default"``).
        current_status: Where the market is in its lifecycle right now.
            ``"created"`` = market exists but trading hasn't started;
            ``"active"`` = trading; ``"resolved"`` = outcome known but
            payouts pending; ``"settled"`` = closed.
    """

    market_id: str
    venue: str
    canonical_group: CanonicalQuestionGroup
    market_created_at: datetime
    resolution_time: datetime
    settlement_time: datetime
    current_status: _LifecycleStatus


def is_market_active_at(lifecycle: MarketLifecycle, ts: datetime) -> bool:
    """Return True iff ``ts`` falls in ``[market_created_at, settlement_time)``.

    Tick-gating helper for MTDS adapters: ticks outside this window are
    rejected (pre-creation = market wasn't trading yet, post-settlement
    = market closed; either way the tick is not informative for prediction
    feature engineering).
    """
    return lifecycle.market_created_at <= ts < lifecycle.settlement_time


_UTC: Final[timezone] = UTC


def _day_window_utc(day: _date_t) -> tuple[datetime, datetime]:
    """Return ``(day_start, day_end)`` in UTC for the given calendar day."""
    return (
        datetime.combine(day, time.min, tzinfo=_UTC),
        datetime.combine(day, time.max, tzinfo=_UTC),
    )


def expected_market_ids_for_canonical_group(
    group: CanonicalQuestionGroup,
    day: _date_t,
    lifecycles: Iterable[MarketLifecycle],
) -> set[str]:
    """Return market_ids whose ``[created, settled)`` window overlaps ``day``.

    Used by the cluster gate to derive the registry-side expected set
    per ``(canonical_question_group, day)`` cell. The shard's actual
    captured market_id set must be a superset of this output (the cluster
    gate flips a partial bundle to ``attempted_failed[ClusterCoverageError]``).

    Args:
        group: Canonical question group to filter on.
        day: UTC calendar day.
        lifecycles: Iterable of ``MarketLifecycle`` records (typically
            the rows of instruments-service's ``MARKET_LIFECYCLE`` table
            for the relevant venue).

    Returns:
        Set of ``market_id`` strings whose lifecycle window overlaps the
        24-hour UTC window of ``day``.
    """
    day_start, day_end = _day_window_utc(day)
    return {
        lifecycle.market_id
        for lifecycle in lifecycles
        if lifecycle.canonical_group == group
        and lifecycle.market_created_at <= day_end
        and lifecycle.settlement_time > day_start
    }


__all__ = [
    "MarketLifecycle",
    "expected_market_ids_for_canonical_group",
    "is_market_active_at",
]
