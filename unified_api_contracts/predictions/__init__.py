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
  canonical group. Unmatched markets route to :attr:`CanonicalQuestionGroup.OTHER`
  (the honest-absence catch-all) and emit ``OTHER_BUCKET_MEMBER_ADDED`` at INFO
  level for operator audit; never returns ``None``.
* :data:`KALSHI_TICKER_PREFIX_TO_GROUP` — rule table mapping ``KX*`` event-ticker
  prefixes to canonical groups; shared real-world questions (BTC daily, SPX,
  Fed rate, CPI …) resolve to the **same** :class:`CanonicalQuestionGroup`
  value as the equivalent Polymarket market, enabling cross-venue arbitrage.
* :data:`CLASSIFIER_STABILITY_HASH` — manifest writers stamp this on
  every captured prediction shard so re-runs skip re-classification when
  unchanged.
* :class:`MarketLifecycle` + :func:`is_market_active_at` /
  :func:`expected_market_ids_for_canonical_group` — per-market lifecycle
  helpers used by MTDS adapters (tick gating) and the cluster gate
  (per-day expected market_id derivation).

Reference plan:
``unified-trading-pm/plans/active/predictions_canonical_question_group_polymarket_migration_2026_05_06.plan``.
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
    KALSHI_TICKER_PREFIX_TO_GROUP,
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
from unified_api_contracts.canonical.domain.predictions.two_axis import (
    CANONICAL_GROUP_TO_BET_TYPE,
    CANONICAL_GROUP_TO_UNDERLYING,
    PredictionBetType,
    PredictionUnderlying,
    bet_type_for_group,
    cross_venue_underlying_overlap,
    underlying_for_group,
)

__all__ = [
    "CANONICAL_GROUP_METADATA",
    "CANONICAL_GROUP_TO_BET_TYPE",
    "CANONICAL_GROUP_TO_UNDERLYING",
    "CLASSIFIER_STABILITY_HASH",
    "CLASSIFIER_VERSION",
    "KALSHI_TICKER_PREFIX_TO_GROUP",
    "KALSHI_TICKER_TO_GROUP",
    "POLYMARKET_CONDITION_ID_TO_GROUP",
    "CanonicalGroupMetadata",
    "CanonicalQuestionGroup",
    "MarketLifecycle",
    "PredictionBetType",
    "PredictionUnderlying",
    "bet_type_for_group",
    "classify_kalshi_to_canonical_group",
    "classify_polymarket_to_canonical_group",
    "cross_venue_underlying_overlap",
    "expected_market_ids_for_canonical_group",
    "is_market_active_at",
    "underlying_for_group",
]
