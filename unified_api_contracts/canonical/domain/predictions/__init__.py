"""Canonical-question-group SSOT for prediction markets.

See ``unified_api_contracts.predictions`` for the public facade. Submodules:

* :mod:`canonical_groups` — :class:`CanonicalQuestionGroup` enum +
  :class:`CanonicalGroupMetadata` per-group metadata table.
* :mod:`classifiers` — wraps the existing internal classifier in
  :mod:`unified_api_contracts.internal.schemas._prediction_market_taxonomy`
  to map raw Polymarket / Kalshi market metadata onto a canonical group.
* :mod:`lifecycle` — :class:`MarketLifecycle` dataclass + helpers for
  per-market activity windows and per-day cluster expectations.

Reference plan:
``unified-trading-pm/plans/active/predictions_canonical_question_group_polymarket_migration_2026_05_06.plan.md``.
"""
