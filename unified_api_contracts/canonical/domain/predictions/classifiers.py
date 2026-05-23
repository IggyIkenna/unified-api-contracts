"""Polymarket / Kalshi market → :class:`CanonicalQuestionGroup` classifier.

Predictions plan
``predictions_canonical_question_group_polymarket_migration_2026_05_06.md``
Phase 1A.

Wraps the existing rule-first classifier in
:mod:`unified_api_contracts.internal.schemas._prediction_market_taxonomy`
(which returns a 4-tuple of category / underlying / market_type /
resolution_period) and maps that tuple onto a
:class:`CanonicalQuestionGroup` enum value.

Design:

1. **Override-first** — :data:`POLYMARKET_CONDITION_ID_TO_GROUP` and
   :data:`KALSHI_TICKER_TO_GROUP` are hand-curated dicts for headline
   markets where the rule classifier could plausibly disagree. Override
   wins.
2. **Rule-based fallback** — call
   ``classify_polymarket_market`` and project the 4-tuple onto a canonical
   group via :data:`_CATEGORY_UNDERLYING_PERIOD_TO_GROUP`.
3. **Sub-threshold** — when neither path produces a group, return ``None``;
   caller marks the shard as
   ``attempted_failed[reason=ClassifierConfidenceLow]``.

The internal classifier already exposes ``CLASSIFIER_STABILITY_HASH``
(commit ``5f76bd4`` 2026-05-06). This module re-exports it as
:data:`CLASSIFIER_STABILITY_HASH` so MTDS / instruments-service writers
stamp it on every prediction manifest row; re-runs skip re-classification
when the hash is unchanged.
"""

from __future__ import annotations

from typing import Final

from unified_api_contracts.canonical.domain.predictions.canonical_groups import (
    CanonicalQuestionGroup,
)
from unified_api_contracts.internal.schemas._prediction_market_taxonomy import (
    CLASSIFIER_STABILITY_HASH,
    CLASSIFIER_VERSION,
    PredictionShardCategory,
    PredictionShardMarketType,
    PredictionShardResolutionPeriod,
    classify_polymarket_market,
)

# ---------------------------------------------------------------------------
# Override dicts — headline markets where the rule classifier could
# plausibly disagree. Lookup-first, rule-fallback.
# ---------------------------------------------------------------------------


POLYMARKET_CONDITION_ID_TO_GROUP: Final[dict[str, CanonicalQuestionGroup]] = {
    # Seed empty; populated as headline markets surface that need explicit
    # routing (typically when the slug heuristics don't hit clean enough).
}
"""Polymarket conditionId → canonical group override dict."""


KALSHI_TICKER_TO_GROUP: Final[dict[str, CanonicalQuestionGroup]] = {
    # Seed empty; populated when a Kalshi ticker disagrees with the
    # rule-classifier output and we want to pin the routing.
}
"""Kalshi ticker → canonical group override dict."""


# ---------------------------------------------------------------------------
# (category, underlying, resolution_period) → CanonicalQuestionGroup
#
# Mapping table for the rule-based fallback path. Only RANGE_BRACKET +
# CATEGORICAL market types use the (cat, und, period) keying because
# those are the ones that recur cyclically.
# ---------------------------------------------------------------------------


_C = PredictionShardCategory
_P = PredictionShardResolutionPeriod
_G = CanonicalQuestionGroup


_CATEGORY_UNDERLYING_PERIOD_TO_GROUP: Final[dict[tuple[_C, str, _P], CanonicalQuestionGroup]] = {
    (_C.CRYPTO_PRICE, "BTC", _P.HOURLY): _G.BTC_UP_DOWN_HOURLY,
    (_C.CRYPTO_PRICE, "BTC", _P.DAILY): _G.BTC_UP_DOWN_DAILY,
    (_C.CRYPTO_PRICE, "ETH", _P.HOURLY): _G.ETH_UP_DOWN_HOURLY,
    (_C.CRYPTO_PRICE, "ETH", _P.DAILY): _G.ETH_UP_DOWN_DAILY,
    # Equity indices — CME event-contract linked (predictions_master Phase 5, 2026-05-22)
    (_C.EQUITY_INDEX, "SPX", _P.DAILY): _G.SPX_UP_DOWN_DAILY,
    (_C.EQUITY_INDEX, "NDX", _P.DAILY): _G.NDX_UP_DOWN_DAILY,
    (_C.EQUITY_INDEX, "DJIA", _P.DAILY): _G.DJIA_UP_DOWN_DAILY,
    (_C.EQUITY_INDEX, "RUT", _P.DAILY): _G.RUT_UP_DOWN_DAILY,
    # Commodities — CME event-contract linked
    (_C.COMMODITY, "GOLD", _P.DAILY): _G.GOLD_UP_DOWN_DAILY,
    (_C.COMMODITY, "CRUDE_OIL", _P.DAILY): _G.CRUDE_OIL_UP_DOWN_DAILY,
    # NAT_GAS: taxonomy underlying uses "NAT_GAS" (from nat-gas-/natural-gas- prefixes)
    (_C.COMMODITY, "NAT_GAS", _P.DAILY): _G.NATGAS_UP_DOWN_DAILY,
    # FX — EURUSD: taxonomy underlying uses "EURUSD" (from eur-usd-/usd-eur- prefixes)
    (_C.FX, "EURUSD", _P.DAILY): _G.EUR_UP_DOWN_DAILY,
}
"""(category, underlying, resolution_period) → canonical group.

Closed set; sub-threshold / unknown combinations fall through to the
override path or ``None``.
"""


# Macro-event groups: keyed on (category, underlying) only because the
# resolution_period is event-driven, not clock-driven.
_CATEGORY_UNDERLYING_TO_EVENT_GROUP: Final[dict[tuple[_C, str], CanonicalQuestionGroup]] = {
    (_C.MACRO, "FED_RATE"): _G.FED_RATE_DECISION_PER_FOMC,
    (_C.MACRO, "CPI"): _G.CPI_PRINT_PER_MONTH,
    (_C.POLITICS_US, "PRESIDENT_2028"): _G.ELECTION_PRESIDENT_2028,
    (_C.CULTURE, "OSCARS_BEST_PICTURE"): _G.OSCARS_BEST_PICTURE,
}


def classify_polymarket_to_canonical_group(
    *,
    title: str,
    slug: str,
    event_slug: str,
    outcome: str,
    condition_id: str | None = None,
) -> CanonicalQuestionGroup | None:
    """Map a Polymarket market onto a canonical question group.

    Override-first: if ``condition_id`` is in
    :data:`POLYMARKET_CONDITION_ID_TO_GROUP`, that wins.
    Otherwise calls
    :func:`unified_api_contracts.internal.schemas._prediction_market_taxonomy.classify_polymarket_market`
    and projects the 4-tuple onto a :class:`CanonicalQuestionGroup` via
    :data:`_CATEGORY_UNDERLYING_PERIOD_TO_GROUP` (cadenced markets) or
    :data:`_CATEGORY_UNDERLYING_TO_EVENT_GROUP` (event markets).

    Returns ``None`` for sub-threshold combinations — caller routes to
    ``attempted_failed[reason=ClassifierConfidenceLow]``.

    The classifier output is stable per ``CLASSIFIER_STABILITY_HASH``;
    re-runs of the same input under the same hash always return the
    same group.
    """
    if condition_id and condition_id in POLYMARKET_CONDITION_ID_TO_GROUP:
        return POLYMARKET_CONDITION_ID_TO_GROUP[condition_id]

    category, underlying, market_type, resolution_period = classify_polymarket_market(
        title=title,
        slug=slug,
        event_slug=event_slug,
        outcome=outcome,
    )

    if market_type == PredictionShardMarketType.RANGE_BRACKET:
        cadence_key = (category, underlying.upper(), resolution_period)
        result = _CATEGORY_UNDERLYING_PERIOD_TO_GROUP.get(cadence_key)
        if result is not None:
            return result
        # Polymarket daily price markets encode their date as month+day in the
        # slug (e.g. "btc-up-or-down-may-22"), causing the taxonomy to assign
        # MONTHLY resolution.  Fall back to DAILY so those markets route to
        # BTC_UP_DOWN_DAILY / SPX_UP_DOWN_DAILY / CRUDE_OIL_UP_DOWN_DAILY etc.
        if resolution_period == PredictionShardResolutionPeriod.MONTHLY:
            daily_key = (category, underlying.upper(), PredictionShardResolutionPeriod.DAILY)
            return _CATEGORY_UNDERLYING_PERIOD_TO_GROUP.get(daily_key)
        return None

    event_key = (category, underlying.upper())
    return _CATEGORY_UNDERLYING_TO_EVENT_GROUP.get(event_key)


def classify_kalshi_to_canonical_group(
    *,
    ticker: str,
) -> CanonicalQuestionGroup | None:
    """Map a Kalshi ticker onto a canonical question group.

    Currently override-only (the Kalshi rule classifier is a deferred
    follow-up plan slot — the override dict is the single SSOT for
    headline tickers until the rule classifier lands). Returns ``None``
    when the ticker is unknown, signalling the caller to route to
    ``attempted_failed[reason=ClassifierConfidenceLow]``.
    """
    return KALSHI_TICKER_TO_GROUP.get(ticker)


__all__ = [
    "CLASSIFIER_STABILITY_HASH",
    "CLASSIFIER_VERSION",
    "KALSHI_TICKER_TO_GROUP",
    "POLYMARKET_CONDITION_ID_TO_GROUP",
    "classify_kalshi_to_canonical_group",
    "classify_polymarket_to_canonical_group",
]
