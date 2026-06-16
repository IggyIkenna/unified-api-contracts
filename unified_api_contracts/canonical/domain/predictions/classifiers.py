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

import logging
from typing import Final

from unified_api_contracts.canonical.domain.predictions.canonical_groups import (
    CanonicalQuestionGroup,
)

_log = logging.getLogger(__name__)
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
    # Specific intraday intervals (5m, 15m) → dedicated groups
    (_C.CRYPTO_PRICE, "BTC", _P.FIVE_MIN): _G.BTC_UP_DOWN_5MIN,
    (_C.CRYPTO_PRICE, "BTC", _P.FIFTEEN_MIN): _G.BTC_UP_DOWN_15MIN,
    (_C.CRYPTO_PRICE, "ETH", _P.FIVE_MIN): _G.ETH_UP_DOWN_5MIN,
    (_C.CRYPTO_PRICE, "ETH", _P.FIFTEEN_MIN): _G.ETH_UP_DOWN_15MIN,
    # 1m and unknown-interval intraday → INTRADAY fallback group
    (_C.CRYPTO_PRICE, "BTC", _P.ONE_MIN): _G.BTC_UP_DOWN_INTRADAY,
    (_C.CRYPTO_PRICE, "ETH", _P.ONE_MIN): _G.ETH_UP_DOWN_INTRADAY,
    (_C.CRYPTO_PRICE, "BTC", _P.INTRADAY): _G.BTC_UP_DOWN_INTRADAY,
    (_C.CRYPTO_PRICE, "ETH", _P.INTRADAY): _G.ETH_UP_DOWN_INTRADAY,
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
    # Alt-coin daily up-or-down — mirror BTC/ETH (decision 338, 2026-06-16).
    # Observed alt-coin price markets are range_bracket with a month token →
    # MONTHLY, which the DAILY-fallback below maps onto these DAILY keys.
    (_C.CRYPTO_PRICE, "SOL", _P.DAILY): _G.SOL_UP_DOWN_DAILY,
    (_C.CRYPTO_PRICE, "XRP", _P.DAILY): _G.XRP_UP_DOWN_DAILY,
    (_C.CRYPTO_PRICE, "DOGE", _P.DAILY): _G.DOGE_UP_DOWN_DAILY,
    (_C.CRYPTO_PRICE, "BNB", _P.DAILY): _G.BNB_UP_DOWN_DAILY,
    (_C.CRYPTO_PRICE, "ADA", _P.DAILY): _G.ADA_UP_DOWN_DAILY,
    (_C.CRYPTO_PRICE, "AVAX", _P.DAILY): _G.AVAX_UP_DOWN_DAILY,
    (_C.CRYPTO_PRICE, "LINK", _P.DAILY): _G.LINK_UP_DOWN_DAILY,
    (_C.CRYPTO_PRICE, "LTC", _P.DAILY): _G.LTC_UP_DOWN_DAILY,
    (_C.CRYPTO_PRICE, "SUI", _P.DAILY): _G.SUI_UP_DOWN_DAILY,
    (_C.CRYPTO_PRICE, "HYPE", _P.DAILY): _G.HYPE_UP_DOWN_DAILY,
    # Weather daily highest-temperature — range_bracket "between N-Nf"; the
    # taxonomy assigns EVENT resolution to WEATHER (decision 338).
    (_C.WEATHER, "TEMPERATURE", _P.EVENT): _G.WEATHER_TEMP_DAILY,
}
"""(category, underlying, resolution_period) → canonical group.

Closed set; sub-threshold / unknown combinations fall through to the
override path or ``None``.
"""


# Macro-event groups: keyed on (category, underlying) only because the
# resolution_period is event-driven, not clock-driven.
_CATEGORY_UNDERLYING_TO_EVENT_GROUP: Final[dict[tuple[_C, str], CanonicalQuestionGroup]] = {
    # NOTE: the key underlying MUST match what the taxonomy emits. The FED
    # slug prefixes (fed-/fed-rate-/fomc-) map to underlying "FED_FUNDS", NOT
    # "FED_RATE" — the prior "FED_RATE" key was DEAD (no market ever matched),
    # so every FED market fell to OTHER. Fixed 2026-06-16 (decision 338).
    (_C.MACRO, "FED_FUNDS"): _G.FED_RATE_DECISION_PER_FOMC,
    (_C.MACRO, "CPI"): _G.CPI_PRINT_PER_MONTH,
    # Macro economic-release groups — recurring prints (decision 338).
    (_C.MACRO, "UNEMPLOYMENT"): _G.UNEMPLOYMENT_RATE_PER_MONTH,
    (_C.MACRO, "NONFARM_PAYROLLS"): _G.NONFARM_PAYROLLS_PER_MONTH,
    (_C.MACRO, "GDP"): _G.GDP_PRINT_PER_QUARTER,
    (_C.MACRO, "PPI"): _G.PPI_PRINT_PER_MONTH,
    (_C.MACRO, "PCE"): _G.PCE_PRINT_PER_MONTH,
    (_C.MACRO, "TREASURY_YIELDS"): _G.TREASURY_YIELD_PER_PRINT,
    (_C.MACRO, "FEAR_GREED"): _G.CRYPTO_FEAR_GREED_INDEX,
    (_C.POLITICS_US, "PRESIDENT_2028"): _G.ELECTION_PRESIDENT_2028,
    (_C.CULTURE, "OSCARS_BEST_PICTURE"): _G.OSCARS_BEST_PICTURE,
    # Weather daily highest-temperature — binary "Nf or higher" variant
    # (range_bracket "between N-Nf" handled in the cadence map). Decision 338.
    (_C.WEATHER, "TEMPERATURE"): _G.WEATHER_TEMP_DAILY,
}


# ---------------------------------------------------------------------------
# decision 338 pass 2 (2026-06-16) — granular sub-type routing.
#
# The 4-tuple taxonomy tags (category, underlying) but not the *sub-type*
# (price-range vs direction, sports bet-type, political approval vs statement,
# conflict pair). These read the slug in the projection layer (NOT the
# taxonomy — keeps the stability-hash inputs unchanged; the cqg version bump
# is the reclassification lever).
# ---------------------------------------------------------------------------


_CRYPTO_PRICE_RANGE_GROUP: Final[dict[str, CanonicalQuestionGroup]] = {
    "BTC": _G.BTC_PRICE_RANGE_DAILY,
    "ETH": _G.ETH_PRICE_RANGE_DAILY,
    "SOL": _G.SOL_PRICE_RANGE_DAILY,
    "XRP": _G.XRP_PRICE_RANGE_DAILY,
    "DOGE": _G.DOGE_PRICE_RANGE_DAILY,
    "BNB": _G.BNB_PRICE_RANGE_DAILY,
    "ADA": _G.ADA_PRICE_RANGE_DAILY,
    "AVAX": _G.AVAX_PRICE_RANGE_DAILY,
    "LINK": _G.LINK_PRICE_RANGE_DAILY,
    "LTC": _G.LTC_PRICE_RANGE_DAILY,
    "SUI": _G.SUI_PRICE_RANGE_DAILY,
    "HYPE": _G.HYPE_PRICE_RANGE_DAILY,
}

_COMMODITY_PRICE_LEVEL_GROUP: Final[dict[str, CanonicalQuestionGroup]] = {
    "GOLD": _G.GOLD_PRICE_LEVEL,
    "SILVER": _G.SILVER_PRICE_LEVEL,
    "CRUDE_OIL": _G.CRUDE_OIL_PRICE_LEVEL,
}

# Conflict event-type tokens — gate GEO_OTHER_BY_DATE so it catches
# strike/ceasefire/capture markets, NOT intl ELECTION markets.
_CONFLICT_SLUG_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "war",
        "strike",
        "airstrike",
        "ceasefire",
        "invade",
        "invasion",
        "capture",
        "military",
        "nuclear",
        "attack",
        "missile",
        "troops",
        "annex",
        "occupy",
    }
)


def _route_pass2_subtype(
    category: PredictionShardCategory,
    underlying: str,
    slug: str,
    market_type: PredictionShardMarketType,
) -> CanonicalQuestionGroup | None:
    """Category-specific sub-type routing (decision 338 pass 2).

    Returns a :class:`CanonicalQuestionGroup`, or ``None`` to fall through to
    the generic cadence-map / event-map routing. ``slug`` MUST be lowercased.
    """
    und = underlying.upper()
    s = slug

    # Box-office markets carry a movie title the taxonomy can't tag → category
    # MISC. Detect category-agnostically by slug token.
    if "box-office" in s or "opening-weekend" in s:
        return CanonicalQuestionGroup.BOX_OFFICE_OPENING_WEEKEND

    if category is PredictionShardCategory.CRYPTO_PRICE:
        # PRICE-RANGE = a price-level market that is NOT a direction bet
        # ("between $X-$Y" / multistrike / above-below). UP_DOWN falls through
        # to the cadence map (which carries the {COIN}_UP_DOWN_* groups).
        if "up-or-down" not in s and (market_type is PredictionShardMarketType.RANGE_BRACKET or "multistrike" in s):
            return _CRYPTO_PRICE_RANGE_GROUP.get(und)
        return None

    if category is PredictionShardCategory.COMMODITY:
        # PRICE-LEVEL = non-direction commodity price market ("gold above $X").
        if "up-or-down" not in s and (
            market_type is PredictionShardMarketType.RANGE_BRACKET
            or any(t in s for t in ("above", "below", "reach", "hit"))
        ):
            return _COMMODITY_PRICE_LEVEL_GROUP.get(und)
        return None

    if category is PredictionShardCategory.POLITICS_US and und == "TRUMP":
        if "approval" in s:
            return CanonicalQuestionGroup.TRUMP_APPROVAL_RATING
        if "executive-order" in s or "exec-order" in s or ("sign" in s and "order" in s):
            return CanonicalQuestionGroup.TRUMP_EXEC_ORDER
        if any(t in s for t in ("say", "said", "tweet", "post", "mention")):
            return CanonicalQuestionGroup.TRUMP_STATEMENTS
        return None

    if category is PredictionShardCategory.TECH and und == "ELON_MUSK":
        if "tweet" in s or ("post" in s and "time" in s):
            return CanonicalQuestionGroup.ELON_TWEET_COUNT
        if "net-worth" in s or "networth" in s or "wealth" in s:
            return CanonicalQuestionGroup.ELON_NET_WORTH
        if any(t in s for t in ("say", "said", "mention")):
            return CanonicalQuestionGroup.ELON_STATEMENTS
        return None

    if category is PredictionShardCategory.POLITICS_INTL:
        if und in ("ISRAEL", "IRAN"):
            return CanonicalQuestionGroup.GEO_ISRAEL_IRAN
        if und in ("RUSSIA", "UKRAINE"):
            return CanonicalQuestionGroup.GEO_RUSSIA_UKRAINE
        if any(t in s for t in _CONFLICT_SLUG_TOKENS):
            return CanonicalQuestionGroup.GEO_OTHER_BY_DATE
        return None  # intl elections etc. → generic fall-through

    return None


def classify_polymarket_to_canonical_group(
    *,
    title: str,
    slug: str,
    event_slug: str,
    outcome: str,
    condition_id: str | None = None,
) -> CanonicalQuestionGroup:
    """Map a Polymarket market onto a canonical question group.

    Override-first: if ``condition_id`` is in
    :data:`POLYMARKET_CONDITION_ID_TO_GROUP`, that wins.
    Otherwise calls
    :func:`unified_api_contracts.internal.schemas._prediction_market_taxonomy.classify_polymarket_market`
    and projects the 4-tuple onto a :class:`CanonicalQuestionGroup` via
    :data:`_CATEGORY_UNDERLYING_PERIOD_TO_GROUP` (cadenced markets) or
    :data:`_CATEGORY_UNDERLYING_TO_EVENT_GROUP` (event markets).

    Returns :attr:`~CanonicalQuestionGroup.OTHER` for unmatched combinations
    and emits ``OTHER_BUCKET_MEMBER_ADDED`` at INFO level so operators can
    audit the catch-all bucket and promote recurring patterns to first-class
    groups. Previously returned ``None`` (caller routed to
    ``attempted_failed[reason=ClassifierConfidenceLow]``) — changed to
    ``OTHER`` so honest-absence capture replaces silent failure.

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

    # decision 338 pass 2 — granular sub-type routing (price-range vs direction,
    # political approval/statements/exec-order, conflict pair, box-office,
    # commodity price-level). Returns None to fall through to the generic maps.
    subtype_group = _route_pass2_subtype(category, underlying, (slug or "").lower(), market_type)
    if subtype_group is not None:
        return subtype_group

    # Genuinely-uncategorised (taxonomy returned MISC/UNKNOWN) → MISC_NOVELTY,
    # the explicit novelty residual; categorised-but-ungrouped → OTHER.
    residual = (
        CanonicalQuestionGroup.MISC_NOVELTY
        if category is PredictionShardCategory.MISC
        else CanonicalQuestionGroup.OTHER
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
            result = _CATEGORY_UNDERLYING_PERIOD_TO_GROUP.get(daily_key)
            if result is not None:
                return result
        _log.info("OTHER_BUCKET_MEMBER_ADDED condition_id=%s slug=%s", condition_id, slug)
        return residual

    event_key = (category, underlying.upper())
    result = _CATEGORY_UNDERLYING_TO_EVENT_GROUP.get(event_key)
    if result is not None:
        return result
    _log.info("OTHER_BUCKET_MEMBER_ADDED condition_id=%s slug=%s", condition_id, slug)
    return residual


def classify_kalshi_to_canonical_group(
    *,
    ticker: str,
) -> CanonicalQuestionGroup:
    """Map a Kalshi ticker onto a canonical question group.

    Currently override-only (the Kalshi rule classifier is a deferred
    follow-up plan slot — the override dict is the single SSOT for
    headline tickers until the rule classifier lands). Returns
    :attr:`~CanonicalQuestionGroup.OTHER` when the ticker is unknown and
    emits ``OTHER_BUCKET_MEMBER_ADDED`` at INFO level. Previously returned
    ``None`` (caller routed to ``attempted_failed``).
    """
    result = KALSHI_TICKER_TO_GROUP.get(ticker)
    if result is not None:
        return result
    _log.info("OTHER_BUCKET_MEMBER_ADDED ticker=%s", ticker)
    return CanonicalQuestionGroup.OTHER


__all__ = [
    "CLASSIFIER_STABILITY_HASH",
    "CLASSIFIER_VERSION",
    "KALSHI_TICKER_TO_GROUP",
    "POLYMARKET_CONDITION_ID_TO_GROUP",
    "classify_kalshi_to_canonical_group",
    "classify_polymarket_to_canonical_group",
]
