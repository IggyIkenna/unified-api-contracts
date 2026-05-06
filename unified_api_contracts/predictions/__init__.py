"""Public facade for prediction-market canonical-question-group SSOT.

Consumers (instruments-service, MTDS, features-cross-instrument,
strategy-service prediction archetypes) import from this facade
exclusively. Deep paths (``unified_api_contracts.canonical.domain.predictions.*``)
are UAC-internal per the workspace Citadel import rule.

Re-exports:

* :class:`CanonicalQuestionGroup` — closed-set enum of canonical groups
  (cadenced range-bracket + event markets).
* :class:`CanonicalGroupMetadata` + :data:`CANONICAL_GROUP_METADATA` —
  per-group cadence / expected counts / settlement_lag.
* :func:`classify_polymarket_to_canonical_group` /
  :func:`classify_kalshi_to_canonical_group` — raw market metadata →
  canonical group. ``None`` for sub-threshold confidence (caller routes
  to ``attempted_failed[reason=ClassifierConfidenceLow]``).
* :data:`CLASSIFIER_STABILITY_HASH` — manifest writers stamp this on
  every captured prediction shard so re-runs skip re-classification when
  unchanged.
* :class:`MarketLifecycle` + :func:`is_market_active_at` /
  :func:`expected_market_ids_for_canonical_group` — per-market lifecycle
  helpers used by MTDS adapters (tick gating) and the cluster gate
  (per-day expected market_id derivation).

Reference plan:
``unified-trading-pm/plans/active/predictions_canonical_question_group_polymarket_migration_2026_05_06.plan.md``.
"""

from __future__ import annotations

from unified_api_contracts.canonical.domain.predictions.canonical_groups import (
    CANONICAL_GROUP_METADATA,
    CanonicalGroupMetadata,
    CanonicalQuestionGroup,
)
from unified_api_contracts.canonical.domain.predictions.classifiers import (
    CLASSIFIER_STABILITY_HASH,
    CLASSIFIER_VERSION,
    KALSHI_TICKER_TO_GROUP,
    POLYMARKET_CONDITION_ID_TO_GROUP,
    classify_kalshi_to_canonical_group,
    classify_polymarket_to_canonical_group,
)
from unified_api_contracts.canonical.domain.predictions.lifecycle import (
    MarketLifecycle,
    expected_market_ids_for_canonical_group,
    is_market_active_at,
)

__all__ = [
    "CANONICAL_GROUP_METADATA",
    "CLASSIFIER_STABILITY_HASH",
    "CLASSIFIER_VERSION",
    "KALSHI_TICKER_TO_GROUP",
    "POLYMARKET_CONDITION_ID_TO_GROUP",
    "CanonicalGroupMetadata",
    "CanonicalQuestionGroup",
    "MarketLifecycle",
    "classify_kalshi_to_canonical_group",
    "classify_polymarket_to_canonical_group",
    "expected_market_ids_for_canonical_group",
    "is_market_active_at",
]
