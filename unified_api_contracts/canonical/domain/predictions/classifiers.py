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
# Kalshi ticker-prefix → CanonicalQuestionGroup (rule-based fallback).
#
# Kalshi event tickers follow a ``KXSERIES[-DATE][-STRIKESUFFIX]`` schema.
# The *series prefix* (the letters before the first digit or trailing dash
# that identifies a concrete contract) determines the market family.
#
# Key design notes:
# - Longer / more-specific prefixes take precedence.  The lookup in
#   ``classify_kalshi_to_canonical_group`` tries prefixes from longest to
#   shortest so ``KXBTCD`` (daily directional) wins over ``KXBTC`` (generic
#   range) when a ticker starts with the longer string.
# - Where a Kalshi market family represents the SAME real-world question as
#   a Polymarket group, both venues map to the IDENTICAL
#   ``CanonicalQuestionGroup`` value.  This enables the
#   ``arbitrage_price_dispersion`` strategy to compare fair-value across
#   venues without any venue-translation layer.
# - Prefixes are upper-cased; callers must ensure ``ticker.upper()`` is
#   passed (``classify_kalshi_to_canonical_group`` does this automatically).
#
# Derived from the full Kalshi series catalogue (v2/series, 2026-06-20)
# and cross-referenced against ``_CATEGORY_UNDERLYING_PERIOD_TO_GROUP`` so
# the same ``CanonicalQuestionGroup`` values are assigned on both sides.
# ---------------------------------------------------------------------------

_G = CanonicalQuestionGroup  # local shorthand, matches the Polymarket side

KALSHI_TICKER_PREFIX_TO_GROUP: Final[dict[str, CanonicalQuestionGroup]] = {
    # ── Crypto: BTC ─────────────────────────────────────────────────────────
    # More-specific prefixes listed first; the classifier iterates
    # longest-to-shortest so these always beat the bare "KXBTC" fallback.
    "KXBTC15M": _G.BTC_UP_DOWN_15MIN,  # 15-minute up/down (KXBTC15M-*)
    "KXBTCD": _G.BTC_UP_DOWN_DAILY,  # daily directional above/below (KXBTCD-*)
    "KXBTCI": _G.BTC_UP_DOWN_HOURLY,  # hourly intraday (KXBTCI-*)
    "KXBTCMAXD": _G.BTC_UP_DOWN_DAILY,  # daily max/one-touch
    "KXBTC": _G.BTC_PRICE_RANGE_DAILY,  # generic BTC range (KXBTC-DDMMMYY*)
    # ── Crypto: ETH ─────────────────────────────────────────────────────────
    "KXETH15M": _G.ETH_UP_DOWN_15MIN,
    "KXETHD": _G.ETH_UP_DOWN_DAILY,
    "KXETHI": _G.ETH_UP_DOWN_HOURLY,
    "KXETH": _G.ETH_PRICE_RANGE_DAILY,
    # ── Crypto: SOL ─────────────────────────────────────────────────────────
    "KXSOL15M": _G.SOL_UP_DOWN_DAILY,
    "KXSOLD": _G.SOL_UP_DOWN_DAILY,
    "KXSOL": _G.SOL_PRICE_RANGE_DAILY,
    # ── Crypto: XRP ─────────────────────────────────────────────────────────
    "KXXRP15M": _G.XRP_UP_DOWN_DAILY,
    "KXXRPD": _G.XRP_UP_DOWN_DAILY,
    "KXXRP": _G.XRP_PRICE_RANGE_DAILY,
    # Kalshi also lists XRP under the legacy ticker stem "RIPPLE" (KXRIPPLED =
    # daily directional, KXRIPPLE / KXRIPPLEMAXY / KXRIPPLEMINY = range/min/max).
    # Verified against the live /series?category=Crypto catalogue 2026-06-23 — these
    # fell to OTHER before, splitting XRP off its Polymarket counterpart. Route them
    # to the SAME XRP groups so cross-venue XRP dispersion works. Longest-prefix-first
    # ensures KXRIPPLED (directional) beats KXRIPPLE (range).
    "KXRIPPLED": _G.XRP_UP_DOWN_DAILY,
    "KXRIPPLE": _G.XRP_PRICE_RANGE_DAILY,
    # ── Crypto: DOGE ────────────────────────────────────────────────────────
    "KXDOGE15M": _G.DOGE_UP_DOWN_DAILY,
    "KXDOGED": _G.DOGE_UP_DOWN_DAILY,
    "KXDOGE": _G.DOGE_PRICE_RANGE_DAILY,
    # ── Crypto: BNB ─────────────────────────────────────────────────────────
    "KXBNB15M": _G.BNB_UP_DOWN_DAILY,
    "KXBNBD": _G.BNB_UP_DOWN_DAILY,
    "KXBNB": _G.BNB_PRICE_RANGE_DAILY,
    # ── Crypto: ADA ─────────────────────────────────────────────────────────
    "KXADA15M": _G.ADA_UP_DOWN_DAILY,
    "KXADAD": _G.ADA_UP_DOWN_DAILY,
    "KXADA": _G.ADA_PRICE_RANGE_DAILY,
    # ── Crypto: AVAX ────────────────────────────────────────────────────────
    "KXAVAXD": _G.AVAX_UP_DOWN_DAILY,
    "KXAVAX": _G.AVAX_PRICE_RANGE_DAILY,
    # ── Crypto: LINK (Chainlink) ─────────────────────────────────────────────
    "KXLINKD": _G.LINK_UP_DOWN_DAILY,
    "KXLINK": _G.LINK_PRICE_RANGE_DAILY,
    # ── Crypto: LTC (Litecoin) ───────────────────────────────────────────────
    "KXLTCD": _G.LTC_UP_DOWN_DAILY,
    "KXLTC": _G.LTC_PRICE_RANGE_DAILY,
    # ── Crypto: HYPE ────────────────────────────────────────────────────────
    "KXHYPE15M": _G.HYPE_UP_DOWN_DAILY,
    "KXHYPED": _G.HYPE_UP_DOWN_DAILY,
    "KXHYPE": _G.HYPE_PRICE_RANGE_DAILY,
    # ── Equity indices ───────────────────────────────────────────────────────
    # INX = S&P 500; shared with Polymarket's SPX_UP_DOWN_DAILY group.
    # All KXINX* variants (daily, weekly, hourly, range-bracket) map to
    # SPX_UP_DOWN_DAILY — no SPX-specific range group exists in the enum yet.
    "KXINXI": _G.SPX_UP_DOWN_DAILY,  # hourly S&P range (KXINXI-*)
    "KXINXU": _G.SPX_UP_DOWN_DAILY,  # daily above/below (KXINXU-*)
    "KXINXAB": _G.SPX_UP_DOWN_DAILY,  # daily close above/below
    "KXINXB": _G.SPX_UP_DOWN_DAILY,  # bracketed range (KXINXB-*)
    "KXINXW": _G.SPX_UP_DOWN_DAILY,  # weekly range
    "KXINXM": _G.SPX_UP_DOWN_DAILY,  # monthly range
    "KXINX": _G.SPX_UP_DOWN_DAILY,  # generic S&P range (KXINX-*)
    # NASDAQ-100 → NDX_UP_DOWN_DAILY (shared with Polymarket)
    "KXNASDAQ100U": _G.NDX_UP_DOWN_DAILY,
    "KXNASDAQ100W": _G.NDX_UP_DOWN_DAILY,
    "KXNASDAQ100M": _G.NDX_UP_DOWN_DAILY,
    "KXNASDAQ100": _G.NDX_UP_DOWN_DAILY,
    # DJIA → DJIA_UP_DOWN_DAILY
    "KXDJIA": _G.DJIA_UP_DOWN_DAILY,
    # Russell 2000 → RUT_UP_DOWN_DAILY
    "KXRUT": _G.RUT_UP_DOWN_DAILY,
    # ── Commodities ──────────────────────────────────────────────────────────
    # Gold — daily directional gets GOLD_UP_DOWN_DAILY; level/range → GOLD_PRICE_LEVEL.
    "KXGOLDD": _G.GOLD_UP_DOWN_DAILY,
    "KXGOLDW": _G.GOLD_PRICE_LEVEL,
    "KXGOLDMON": _G.GOLD_PRICE_LEVEL,
    "KXGOLD": _G.GOLD_PRICE_LEVEL,
    # Silver — all Kalshi KXSILVER* series are price-level markets.
    "KXSILVERD": _G.SILVER_PRICE_LEVEL,
    "KXSILVERW": _G.SILVER_PRICE_LEVEL,
    "KXSILVERMON": _G.SILVER_PRICE_LEVEL,
    # Oil (WTI — weekly/monthly price range)
    "KXOILW": _G.CRUDE_OIL_PRICE_LEVEL,
    "KXOIL": _G.CRUDE_OIL_PRICE_LEVEL,
    # Copper — no dedicated group exists yet; route to OTHER (operator note:
    # add COPPER_PRICE_LEVEL to the enum when a Polymarket counterpart lands).
    # Keys deliberately omitted so the ticker falls through to OTHER.
    # ── FX ───────────────────────────────────────────────────────────────────
    # EUR/USD → EUR_UP_DOWN_DAILY (shared with Polymarket). Kalshi's EUR/USD series
    # are KXEURUSD* (daily/weekly/quarterly/yearly) + KXEUROIMF. The bare "KXEURO"
    # prefix was DROPPED 2026-06-23: it greedily caught sports/entertainment series
    # KXEUROLEAGUE* / KXEUROCUP* (basketball) + KXEUROVISION* → mis-classified them
    # as FX. "KXEURUSD" was previously MISSING so the real EUR/USD daily markets
    # (KXEURUSDD etc.) fell to OTHER — now captured.
    "KXEURUSD": _G.EUR_UP_DOWN_DAILY,
    "KXEUROIMF": _G.EUR_UP_DOWN_DAILY,
    # ── Macro releases ───────────────────────────────────────────────────────
    # Fed funds rate decision → FED_RATE_DECISION_PER_FOMC (shared Polymarket)
    "KXFEDDECISION": _G.FED_RATE_DECISION_PER_FOMC,
    "KXFED": _G.FED_RATE_DECISION_PER_FOMC,
    # CPI → CPI_PRINT_PER_MONTH (shared with Polymarket)
    "KXCPIYOY": _G.CPI_PRINT_PER_MONTH,
    "KXCPICORE": _G.CPI_PRINT_PER_MONTH,
    "KXCPICOREYOY": _G.CPI_PRINT_PER_MONTH,
    "KXCPICOMBO": _G.CPI_PRINT_PER_MONTH,
    "KXCPI": _G.CPI_PRINT_PER_MONTH,
    # Non-farm payrolls → NONFARM_PAYROLLS_PER_MONTH (shared with Polymarket)
    "KXPAYROLLS": _G.NONFARM_PAYROLLS_PER_MONTH,
    # GDP → GDP_PRINT_PER_QUARTER (shared with Polymarket)
    "KXGDP": _G.GDP_PRINT_PER_QUARTER,
    # PCE → PCE_PRINT_PER_MONTH (shared with Polymarket)
    "KXPCECORE": _G.PCE_PRINT_PER_MONTH,
    # Natural gas (EIA weekly/daily/monthly price) → NATGAS_UP_DOWN_DAILY
    "KXGASD": _G.NATGAS_UP_DOWN_DAILY,
    "KXGAS": _G.NATGAS_UP_DOWN_DAILY,
    # Treasury yields → TREASURY_YIELD_PER_PRINT (shared with Polymarket)
    "KX10YUSTSRY": _G.TREASURY_YIELD_PER_PRINT,  # 10Y UST yield
    "KX10Y2Y": _G.TREASURY_YIELD_PER_PRINT,  # 10Y-2Y spread
    "KX10Y3M": _G.TREASURY_YIELD_PER_PRINT,  # 10Y-3M spread
}
"""Kalshi event-ticker prefix → canonical group (rule-based fallback layer).

The classifier tries prefixes from **longest to shortest** so a
series-specific prefix (e.g. ``KXBTCD``) always wins over the generic
family prefix (``KXBTC``).  Shared real-world questions (BTC daily,
SPX, Fed rate, CPI, etc.) are deliberately assigned the **same**
:class:`CanonicalQuestionGroup` value as their Polymarket counterpart —
this enables cross-venue arbitrage detection in the
``arbitrage_price_dispersion`` strategy without any translation layer.
"""


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


# Sports (league, bet_type) → group. league = taxonomy underlying; bet_type
# from the slug. Every league has a MATCH entry so the fallback in
# _route_pass2_subtype guarantees per-league grouping (never silent OTHER).
_SPORTS_GROUP: Final[dict[tuple[str, str], CanonicalQuestionGroup]] = {
    ("MLB", "MATCH"): _G.SPORTS_MLB_MATCH,
    ("MLB", "SPREAD"): _G.SPORTS_MLB_SPREAD,
    ("MLB", "TOTAL"): _G.SPORTS_MLB_TOTAL,
    ("MLB", "NRFI"): _G.SPORTS_MLB_NRFI,
    ("NFL", "MATCH"): _G.SPORTS_NFL_MATCH,
    ("NFL", "SPREAD"): _G.SPORTS_NFL_SPREAD,
    ("NFL", "TOTAL"): _G.SPORTS_NFL_TOTAL,
    ("NBA", "MATCH"): _G.SPORTS_NBA_MATCH,
    ("NBA", "SPREAD"): _G.SPORTS_NBA_SPREAD,
    ("NBA", "TOTAL"): _G.SPORTS_NBA_TOTAL,
    ("NHL", "MATCH"): _G.SPORTS_NHL_MATCH,
    ("NHL", "SPREAD"): _G.SPORTS_NHL_SPREAD,
    ("NHL", "TOTAL"): _G.SPORTS_NHL_TOTAL,
    ("EPL", "MATCH"): _G.SPORTS_EPL_MATCH,
    ("EPL", "TOTAL"): _G.SPORTS_EPL_TOTAL,
    ("UEFA", "MATCH"): _G.SPORTS_UEFA_MATCH,
    ("UEFA", "TOTAL"): _G.SPORTS_UEFA_TOTAL,
    ("CHAMPIONS_LEAGUE", "MATCH"): _G.SPORTS_CHAMPIONS_LEAGUE_MATCH,
    ("LA_LIGA", "MATCH"): _G.SPORTS_LA_LIGA_MATCH,
    ("SERIE_A", "MATCH"): _G.SPORTS_SERIE_A_MATCH,
    ("BUNDESLIGA", "MATCH"): _G.SPORTS_BUNDESLIGA_MATCH,
    ("WORLD_CUP", "MATCH"): _G.SPORTS_WORLD_CUP_MATCH,
    ("F1", "MATCH"): _G.SPORTS_F1_MATCH,
    ("F1", "GP_WINNER"): _G.SPORTS_F1_GP_WINNER,
    ("F1", "CONSTRUCTOR"): _G.SPORTS_F1_CONSTRUCTOR,
    ("TENNIS", "MATCH"): _G.SPORTS_TENNIS_MATCH,
    ("GOLF", "MATCH"): _G.SPORTS_GOLF_MATCH,
    ("UFC", "MATCH"): _G.SPORTS_UFC_MATCH,
    ("BOXING", "MATCH"): _G.SPORTS_BOXING_MATCH,
    ("OLYMPICS", "MATCH"): _G.SPORTS_OLYMPICS_MATCH,
}


def _sports_bet_type(slug: str, league: str) -> str:
    """Detect the sports bet-type from the slug (decision 338 pass 2).

    Returns one of MATCH / SPREAD / TOTAL / NRFI / GP_WINNER / CONSTRUCTOR.
    Defaults to MATCH (moneyline / 3-way outcome / tournament winner).
    """
    if league == "F1":
        if "constructor" in slug:
            return "CONSTRUCTOR"
        if "grand-prix" in slug or "-gp-" in slug or slug.endswith("-gp") or "sprint" in slug:
            return "GP_WINNER"
        return "MATCH"
    if "nrfi" in slug:
        return "NRFI"
    if "spread" in slug or "run-line" in slug or "runline" in slug or "puck-line" in slug or "handicap" in slug:
        return "SPREAD"
    if "total" in slug or "over-under" in slug or "overunder" in slug or "over-or-under" in slug:
        return "TOTAL"
    return "MATCH"


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
        # PRICE-RANGE = a price-level market that is NOT a direction bet:
        # "between $X-$Y" / multistrike / above-X / below-X / reach-X / hit-X.
        # "bitcoin-above-95000", "will-bitcoin-reach-100k" etc. carry "above" /
        # "reach" / "hit" as plain substring tokens so we mirror the commodity
        # branch's any(t in s …) guard. UP_DOWN falls through to the cadence map.
        if "up-or-down" not in s and (
            market_type is PredictionShardMarketType.RANGE_BRACKET
            or "multistrike" in s
            or any(t in s for t in ("above", "below", "reach", "hit"))
        ):
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

    if category in (PredictionShardCategory.SPORTS_FOOTBALL, PredictionShardCategory.SPORTS_OTHER):
        # league x bet-type; per-league MATCH fallback guarantees grouping.
        bet_type = _sports_bet_type(s, und)
        return _SPORTS_GROUP.get((und, bet_type)) or _SPORTS_GROUP.get((und, "MATCH"))

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


# ---------------------------------------------------------------------------
# Kalshi SPORTS ticker → shared SPORTS_{LEAGUE}_{BETTYPE} group (cross-venue).
#
# Cross-venue arb premise: a Kalshi per-GAME market (KX{LEAGUE}…GAME / *SPREAD /
# *TOTAL / *NRFI) is the SAME real-world event (a single game, same settlement +
# timing) as the Polymarket market for that game, so both must resolve to the
# IDENTICAL SPORTS_{LEAGUE}_{BETTYPE} group — then the arb engine pairs the exact
# same-game instruments WITHIN the group. Season-futures / draft / award /
# within-match props (NO game/spread/total/nrfi token) are NOT cleanly arbable and
# Polymarket rarely lists an identical contract → they stay OTHER (no false pairs).
# Only the ~17 leagues that have a canonical group are mapped; the hundreds of
# minor world leagues (Liiga / KHL / NPB / J-League / Serie B / …) have no
# Polymarket counterpart → OTHER. Verified vs the live /series?category=Sports
# catalogue 2026-06-23. Longest prefix first so a longer league name wins.
# ---------------------------------------------------------------------------

_KALSHI_SPORTS_PREFIX_TO_LEAGUE: Final[tuple[tuple[str, str], ...]] = (
    ("KXBUNDESLIGA", "BUNDESLIGA"),
    ("KXLALIGA", "LA_LIGA"),
    ("KXSERIEA", "SERIE_A"),
    ("KXNFL", "NFL"),
    ("KXNBA", "NBA"),
    ("KXMLB", "MLB"),
    ("KXNHL", "NHL"),
    ("KXEPL", "EPL"),
    ("KXUCL", "CHAMPIONS_LEAGUE"),
    ("KXWC", "WORLD_CUP"),
    ("KXATP", "TENNIS"),
    ("KXWTA", "TENNIS"),
    ("KXUFC", "UFC"),
    ("KXWBC", "BOXING"),
    ("KXLPGA", "GOLF"),
    ("KXPGA", "GOLF"),
    ("KXF1", "F1"),
)


def kalshi_sports_league_for_ticker(ticker: str) -> str | None:
    """Public accessor — the canonical league for a Kalshi sports ticker, or None.

    Longest-prefix match over the cross-venue league map (so ``KXLALIGA`` wins
    over a hypothetical ``KXLA``). Used by the per-fixture parser
    (``fixture_parsing``) which needs the league without re-importing the private
    prefix table. Returns ``None`` for a non-sports / unmapped-league ticker.
    """
    upper = ticker.upper()
    for prefix, lg in sorted(_KALSHI_SPORTS_PREFIX_TO_LEAGUE, key=lambda kv: len(kv[0]), reverse=True):
        if upper.startswith(prefix):
            return lg
    return None


def _kalshi_sports_group(upper_ticker: str) -> CanonicalQuestionGroup | None:
    """Map a Kalshi sports ticker to a shared ``SPORTS_{LEAGUE}_{BETTYPE}`` group.

    Returns a group ONLY for cleanly-arbable per-game markets — a ``GAME`` /
    ``SPREAD`` / ``TOTAL`` / ``NRFI`` token on a league that has a canonical
    group. Season-futures, draft, awards and within-match props (no such token)
    return ``None`` (caller → OTHER) so we never create a false cross-venue pair;
    a non-MATCH bet-type with no dedicated group also returns ``None`` rather than
    collapsing to MATCH.
    """
    league: str | None = None
    for prefix, lg in sorted(_KALSHI_SPORTS_PREFIX_TO_LEAGUE, key=lambda kv: len(kv[0]), reverse=True):
        if upper_ticker.startswith(prefix):
            league = lg
            break
    if league is None:
        return None
    if "NRFI" in upper_ticker:
        bet_type = "NRFI"
    elif "SPREAD" in upper_ticker:
        bet_type = "SPREAD"
    elif "TOTAL" in upper_ticker:
        bet_type = "TOTAL"
    elif "GAME" in upper_ticker:
        bet_type = "MATCH"
    else:
        return None  # season / futures / award / within-match prop → not cleanly arbable
    group = _SPORTS_GROUP.get((league, bet_type))
    if group is not None:
        return group
    return _SPORTS_GROUP.get((league, "MATCH")) if bet_type == "MATCH" else None


def classify_kalshi_to_canonical_group(
    *,
    ticker: str,
) -> CanonicalQuestionGroup:
    """Map a Kalshi ticker (event_ticker or market ticker) onto a canonical group.

    Three-tier lookup — first match wins:

    1. **Override dict** (:data:`KALSHI_TICKER_TO_GROUP`) — exact-match on the
       full ticker string.  Use this to pin a specific contract when the
       prefix rule would disagree.
    2. **Prefix rules** (:data:`KALSHI_TICKER_PREFIX_TO_GROUP`) — iterate
       candidate prefixes from *longest to shortest* so a more-specific
       series (e.g. ``KXBTCD`` — daily directional) always beats the generic
       family prefix (``KXBTC`` — plain range).
    3. **OTHER catch-all** — emits ``OTHER_BUCKET_MEMBER_ADDED`` at INFO so
       operators can audit the residual bucket and promote recurring patterns
       to first-class groups.

    Where a Kalshi series represents the **same real-world question** as a
    Polymarket group (BTC daily up/down, SPX daily range, Fed rate, CPI …),
    both venues resolve to the *identical* :class:`CanonicalQuestionGroup`
    value — enabling the ``arbitrage_price_dispersion`` strategy to compare
    fair-value across venues without any translation layer.
    """
    upper_ticker = ticker.upper()

    # 1 — exact override wins
    result = KALSHI_TICKER_TO_GROUP.get(upper_ticker)
    if result is not None:
        return result

    # 1.5 — sports per-game markets → shared SPORTS_{LEAGUE}_{BETTYPE} group
    # (same game, same settlement as the Polymarket market → cross-venue pairable).
    sports = _kalshi_sports_group(upper_ticker)
    if sports is not None:
        return sports

    # 2 — prefix rules, longest-prefix first
    for prefix in sorted(KALSHI_TICKER_PREFIX_TO_GROUP, key=len, reverse=True):
        if upper_ticker.startswith(prefix):
            return KALSHI_TICKER_PREFIX_TO_GROUP[prefix]

    # 3 — fallback
    _log.info("OTHER_BUCKET_MEMBER_ADDED ticker=%s", ticker)
    return CanonicalQuestionGroup.OTHER


__all__ = [
    "CLASSIFIER_STABILITY_HASH",
    "CLASSIFIER_VERSION",
    "KALSHI_TICKER_PREFIX_TO_GROUP",
    "KALSHI_TICKER_TO_GROUP",
    "POLYMARKET_CONDITION_ID_TO_GROUP",
    "classify_kalshi_to_canonical_group",
    "classify_polymarket_to_canonical_group",
]
