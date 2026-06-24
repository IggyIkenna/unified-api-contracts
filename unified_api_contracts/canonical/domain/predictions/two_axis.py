"""Two-axis canonical decomposition of :class:`CanonicalQuestionGroup`.

The :class:`CanonicalQuestionGroup` enum encodes UNDERLYING and BET-TYPE
*together* (e.g. ``BTC_UP_DOWN_DAILY``, ``CRUDE_OIL_PRICE_LEVEL``,
``SPORTS_MLB_SPREAD``). For cross-venue overlap measurement we want to score
overlap at the **underlying / category** level so a shared subject is counted
once regardless of bet structure — a Polymarket CRUDE_OIL up/down market and a
Kalshi CRUDE_OIL price-level market both live under the same Axis-1 category
(``CRUDE_OIL``) even though they don't *directly* arbitrage.

This module is **purely additive**: it does NOT mutate or replace the cqg enum.
It provides a comprehensive decomposition:

* :class:`PredictionUnderlying` (Axis-1) — the semantic SUBJECT of the market
  (BTC, CRUDE_OIL, CPI, TRUMP, SPORTS_MLB, …, plus ``OTHER``).
* :class:`PredictionBetType` (Axis-2) — the prediction STRUCTURE (UP_DOWN,
  PRICE_RANGE, PRICE_LEVEL, MATCH, SPREAD, …, plus ``OTHER``).
* :data:`CANONICAL_GROUP_TO_UNDERLYING` / :data:`CANONICAL_GROUP_TO_BET_TYPE` —
  total maps covering EVERY :class:`CanonicalQuestionGroup` value (completeness
  asserted by tests so a new cqg can never be silently uncategorised).
* :func:`underlying_for_group` / :func:`bet_type_for_group` — accessors
  (return ``OTHER`` for forward-compat with new cqg values not yet mapped; the
  completeness tests catch any current gap).
* :func:`cross_venue_underlying_overlap` — measures shared / venue-only
  underlyings between two iterables of cqgs at the Axis-1 level.

**Judgment (operator "no false pairs")**: Axis-1 is CATEGORISATION only. It
deliberately groups e.g. ``CRUDE_OIL_UP_DOWN_DAILY`` + ``CRUDE_OIL_PRICE_LEVEL``
under ``CRUDE_OIL`` — that is correct comprehensive overlap. Deciding which cqgs
actually arb (bet-type + settlement compatibility) is the downstream
arb-pairing layer's job, NOT this module.

Reference plan:
``unified-trading-pm/plans/active/prediction_venue_perps_and_live_clob_depth_2026_06_20.md``
(items #559 / #684 / #692).
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import Final

from unified_api_contracts.canonical.domain.predictions.canonical_groups import (
    CanonicalQuestionGroup,
)


class PredictionUnderlying(StrEnum):
    """Axis-1 — the semantic SUBJECT / category of a prediction market.

    Comprehensive: every :class:`CanonicalQuestionGroup` maps to exactly one
    member here. ``OTHER`` is the honest-absence catch-all (mirrors the cqg
    ``OTHER`` / ``MISC_NOVELTY`` bucket).
    """

    # Crypto
    BTC = "BTC"
    ETH = "ETH"
    SOL = "SOL"
    XRP = "XRP"
    DOGE = "DOGE"
    BNB = "BNB"
    ADA = "ADA"
    AVAX = "AVAX"
    LINK = "LINK"
    LTC = "LTC"
    SUI = "SUI"
    HYPE = "HYPE"
    CRYPTO_SENTIMENT = "CRYPTO_SENTIMENT"  # fear/greed index

    # Equity indices
    SPX = "SPX"
    NDX = "NDX"
    RUT = "RUT"
    DJIA = "DJIA"

    # Commodities / FX
    GOLD = "GOLD"
    SILVER = "SILVER"
    CRUDE_OIL = "CRUDE_OIL"
    NATGAS = "NATGAS"
    EUR = "EUR"

    # Macro economic releases
    CPI = "CPI"
    FED = "FED"
    GDP = "GDP"
    UNEMPLOYMENT_RATE = "UNEMPLOYMENT_RATE"
    NONFARM_PAYROLLS = "NONFARM_PAYROLLS"
    PPI = "PPI"
    PCE = "PCE"
    TREASURY = "TREASURY"

    # Weather
    WEATHER_TEMP = "WEATHER_TEMP"

    # Politics / public figures
    ELECTION = "ELECTION"
    TRUMP = "TRUMP"
    ELON = "ELON"

    # Geopolitics
    GEO_ISRAEL_IRAN = "GEO_ISRAEL_IRAN"
    GEO_RUSSIA_UKRAINE = "GEO_RUSSIA_UKRAINE"
    GEO_OTHER = "GEO_OTHER"

    # Culture / entertainment
    OSCARS = "OSCARS"
    BOX_OFFICE = "BOX_OFFICE"

    # Sports (league-level)
    SPORTS_MLB = "SPORTS_MLB"
    SPORTS_NFL = "SPORTS_NFL"
    SPORTS_NBA = "SPORTS_NBA"
    SPORTS_NHL = "SPORTS_NHL"
    SPORTS_EPL = "SPORTS_EPL"
    SPORTS_UEFA = "SPORTS_UEFA"
    SPORTS_CHAMPIONS_LEAGUE = "SPORTS_CHAMPIONS_LEAGUE"
    SPORTS_LA_LIGA = "SPORTS_LA_LIGA"
    SPORTS_SERIE_A = "SPORTS_SERIE_A"
    SPORTS_BUNDESLIGA = "SPORTS_BUNDESLIGA"
    SPORTS_WORLD_CUP = "SPORTS_WORLD_CUP"
    SPORTS_F1 = "SPORTS_F1"
    SPORTS_TENNIS = "SPORTS_TENNIS"
    SPORTS_GOLF = "SPORTS_GOLF"
    SPORTS_UFC = "SPORTS_UFC"
    SPORTS_BOXING = "SPORTS_BOXING"
    SPORTS_OLYMPICS = "SPORTS_OLYMPICS"

    # Honest-absence catch-all.
    OTHER = "OTHER"


class PredictionBetType(StrEnum):
    """Axis-2 — the prediction STRUCTURE of a market.

    Comprehensive: every :class:`CanonicalQuestionGroup` maps to exactly one
    member here. ``OTHER`` is the catch-all.
    """

    UP_DOWN = "UP_DOWN"  # direction-only (close higher/lower)
    PRICE_RANGE = "PRICE_RANGE"  # "between $X-$Y" / multistrike
    PRICE_LEVEL = "PRICE_LEVEL"  # "above $X by DATE" threshold
    MATCH = "MATCH"  # moneyline / winner-of-field / 3-way
    SPREAD = "SPREAD"  # cover the handicap
    TOTAL = "TOTAL"  # over/under
    NRFI = "NRFI"  # no-run-first-inning yes/no
    PER_MONTH = "PER_MONTH"  # recurring macro print (release-driven)
    APPROVAL_RATING = "APPROVAL_RATING"  # poll-driven rating threshold
    STATEMENTS = "STATEMENTS"  # will-say / will-tweet style
    EXEC_ORDER = "EXEC_ORDER"  # executive-order issuance
    EVENT = "EVENT"  # single-fire / conflict-by-date / generic event
    OTHER = "OTHER"


# === Axis-1 map — EVERY CanonicalQuestionGroup → PredictionUnderlying ===
_G = CanonicalQuestionGroup
_U = PredictionUnderlying

CANONICAL_GROUP_TO_UNDERLYING: Final[dict[CanonicalQuestionGroup, PredictionUnderlying]] = {
    # Crypto up/down (all cadences) + price-range share the coin underlying.
    _G.BTC_UP_DOWN_5MIN: _U.BTC,
    _G.BTC_UP_DOWN_15MIN: _U.BTC,
    _G.BTC_UP_DOWN_INTRADAY: _U.BTC,
    _G.BTC_UP_DOWN_HOURLY: _U.BTC,
    _G.BTC_UP_DOWN_DAILY: _U.BTC,
    _G.BTC_PRICE_RANGE_DAILY: _U.BTC,
    _G.ETH_UP_DOWN_5MIN: _U.ETH,
    _G.ETH_UP_DOWN_15MIN: _U.ETH,
    _G.ETH_UP_DOWN_INTRADAY: _U.ETH,
    _G.ETH_UP_DOWN_HOURLY: _U.ETH,
    _G.ETH_UP_DOWN_DAILY: _U.ETH,
    _G.ETH_PRICE_RANGE_DAILY: _U.ETH,
    _G.SOL_UP_DOWN_DAILY: _U.SOL,
    _G.SOL_PRICE_RANGE_DAILY: _U.SOL,
    _G.XRP_UP_DOWN_DAILY: _U.XRP,
    _G.XRP_PRICE_RANGE_DAILY: _U.XRP,
    _G.DOGE_UP_DOWN_DAILY: _U.DOGE,
    _G.DOGE_PRICE_RANGE_DAILY: _U.DOGE,
    _G.BNB_UP_DOWN_DAILY: _U.BNB,
    _G.BNB_PRICE_RANGE_DAILY: _U.BNB,
    _G.ADA_UP_DOWN_DAILY: _U.ADA,
    _G.ADA_PRICE_RANGE_DAILY: _U.ADA,
    _G.AVAX_UP_DOWN_DAILY: _U.AVAX,
    _G.AVAX_PRICE_RANGE_DAILY: _U.AVAX,
    _G.LINK_UP_DOWN_DAILY: _U.LINK,
    _G.LINK_PRICE_RANGE_DAILY: _U.LINK,
    _G.LTC_UP_DOWN_DAILY: _U.LTC,
    _G.LTC_PRICE_RANGE_DAILY: _U.LTC,
    _G.SUI_UP_DOWN_DAILY: _U.SUI,
    _G.SUI_PRICE_RANGE_DAILY: _U.SUI,
    _G.HYPE_UP_DOWN_DAILY: _U.HYPE,
    _G.HYPE_PRICE_RANGE_DAILY: _U.HYPE,
    _G.CRYPTO_FEAR_GREED_INDEX: _U.CRYPTO_SENTIMENT,
    # Equity indices.
    _G.SPX_UP_DOWN_DAILY: _U.SPX,
    _G.NDX_UP_DOWN_DAILY: _U.NDX,
    _G.RUT_UP_DOWN_DAILY: _U.RUT,
    _G.DJIA_UP_DOWN_DAILY: _U.DJIA,
    # Commodities / FX — up/down AND price-level share the commodity underlying.
    _G.GOLD_UP_DOWN_DAILY: _U.GOLD,
    _G.GOLD_PRICE_LEVEL: _U.GOLD,
    _G.SILVER_PRICE_LEVEL: _U.SILVER,
    _G.CRUDE_OIL_UP_DOWN_DAILY: _U.CRUDE_OIL,
    _G.CRUDE_OIL_PRICE_LEVEL: _U.CRUDE_OIL,
    _G.NATGAS_UP_DOWN_DAILY: _U.NATGAS,
    _G.EUR_UP_DOWN_DAILY: _U.EUR,
    # Macro economic releases.
    _G.FED_RATE_DECISION_PER_FOMC: _U.FED,
    _G.CPI_PRINT_PER_MONTH: _U.CPI,
    _G.UNEMPLOYMENT_RATE_PER_MONTH: _U.UNEMPLOYMENT_RATE,
    _G.NONFARM_PAYROLLS_PER_MONTH: _U.NONFARM_PAYROLLS,
    _G.GDP_PRINT_PER_QUARTER: _U.GDP,
    _G.PPI_PRINT_PER_MONTH: _U.PPI,
    _G.PCE_PRINT_PER_MONTH: _U.PCE,
    _G.TREASURY_YIELD_PER_PRINT: _U.TREASURY,
    # Weather.
    _G.WEATHER_TEMP_DAILY: _U.WEATHER_TEMP,
    # Politics / public figures.
    _G.ELECTION_PRESIDENT_2028: _U.ELECTION,
    _G.TRUMP_APPROVAL_RATING: _U.TRUMP,
    _G.TRUMP_STATEMENTS: _U.TRUMP,
    _G.TRUMP_EXEC_ORDER: _U.TRUMP,
    _G.ELON_TWEET_COUNT: _U.ELON,
    _G.ELON_STATEMENTS: _U.ELON,
    _G.ELON_NET_WORTH: _U.ELON,
    # Geopolitics.
    _G.GEO_ISRAEL_IRAN: _U.GEO_ISRAEL_IRAN,
    _G.GEO_RUSSIA_UKRAINE: _U.GEO_RUSSIA_UKRAINE,
    _G.GEO_OTHER_BY_DATE: _U.GEO_OTHER,
    # Culture / entertainment.
    _G.OSCARS_BEST_PICTURE: _U.OSCARS,
    _G.BOX_OFFICE_OPENING_WEEKEND: _U.BOX_OFFICE,
    # Sports — league underlying, bet-type carried on Axis-2.
    _G.SPORTS_MLB_MATCH: _U.SPORTS_MLB,
    _G.SPORTS_MLB_SPREAD: _U.SPORTS_MLB,
    _G.SPORTS_MLB_TOTAL: _U.SPORTS_MLB,
    _G.SPORTS_MLB_NRFI: _U.SPORTS_MLB,
    _G.SPORTS_NFL_MATCH: _U.SPORTS_NFL,
    _G.SPORTS_NFL_SPREAD: _U.SPORTS_NFL,
    _G.SPORTS_NFL_TOTAL: _U.SPORTS_NFL,
    _G.SPORTS_NBA_MATCH: _U.SPORTS_NBA,
    _G.SPORTS_NBA_SPREAD: _U.SPORTS_NBA,
    _G.SPORTS_NBA_TOTAL: _U.SPORTS_NBA,
    _G.SPORTS_NHL_MATCH: _U.SPORTS_NHL,
    _G.SPORTS_NHL_SPREAD: _U.SPORTS_NHL,
    _G.SPORTS_NHL_TOTAL: _U.SPORTS_NHL,
    _G.SPORTS_EPL_MATCH: _U.SPORTS_EPL,
    _G.SPORTS_EPL_TOTAL: _U.SPORTS_EPL,
    _G.SPORTS_UEFA_MATCH: _U.SPORTS_UEFA,
    _G.SPORTS_UEFA_TOTAL: _U.SPORTS_UEFA,
    _G.SPORTS_CHAMPIONS_LEAGUE_MATCH: _U.SPORTS_CHAMPIONS_LEAGUE,
    _G.SPORTS_LA_LIGA_MATCH: _U.SPORTS_LA_LIGA,
    _G.SPORTS_SERIE_A_MATCH: _U.SPORTS_SERIE_A,
    _G.SPORTS_BUNDESLIGA_MATCH: _U.SPORTS_BUNDESLIGA,
    _G.SPORTS_WORLD_CUP_MATCH: _U.SPORTS_WORLD_CUP,
    _G.SPORTS_F1_MATCH: _U.SPORTS_F1,
    _G.SPORTS_F1_GP_WINNER: _U.SPORTS_F1,
    _G.SPORTS_F1_CONSTRUCTOR: _U.SPORTS_F1,
    _G.SPORTS_TENNIS_MATCH: _U.SPORTS_TENNIS,
    _G.SPORTS_GOLF_MATCH: _U.SPORTS_GOLF,
    _G.SPORTS_UFC_MATCH: _U.SPORTS_UFC,
    _G.SPORTS_BOXING_MATCH: _U.SPORTS_BOXING,
    _G.SPORTS_OLYMPICS_MATCH: _U.SPORTS_OLYMPICS,
    # Catch-all.
    _G.MISC_NOVELTY: _U.OTHER,
    _G.OTHER: _U.OTHER,
}


# === Axis-2 map — EVERY CanonicalQuestionGroup → PredictionBetType ===
_B = PredictionBetType

CANONICAL_GROUP_TO_BET_TYPE: Final[dict[CanonicalQuestionGroup, PredictionBetType]] = {
    # Crypto direction-only (all cadences).
    _G.BTC_UP_DOWN_5MIN: _B.UP_DOWN,
    _G.BTC_UP_DOWN_15MIN: _B.UP_DOWN,
    _G.BTC_UP_DOWN_INTRADAY: _B.UP_DOWN,
    _G.BTC_UP_DOWN_HOURLY: _B.UP_DOWN,
    _G.BTC_UP_DOWN_DAILY: _B.UP_DOWN,
    _G.ETH_UP_DOWN_5MIN: _B.UP_DOWN,
    _G.ETH_UP_DOWN_15MIN: _B.UP_DOWN,
    _G.ETH_UP_DOWN_INTRADAY: _B.UP_DOWN,
    _G.ETH_UP_DOWN_HOURLY: _B.UP_DOWN,
    _G.ETH_UP_DOWN_DAILY: _B.UP_DOWN,
    _G.SOL_UP_DOWN_DAILY: _B.UP_DOWN,
    _G.XRP_UP_DOWN_DAILY: _B.UP_DOWN,
    _G.DOGE_UP_DOWN_DAILY: _B.UP_DOWN,
    _G.BNB_UP_DOWN_DAILY: _B.UP_DOWN,
    _G.ADA_UP_DOWN_DAILY: _B.UP_DOWN,
    _G.AVAX_UP_DOWN_DAILY: _B.UP_DOWN,
    _G.LINK_UP_DOWN_DAILY: _B.UP_DOWN,
    _G.LTC_UP_DOWN_DAILY: _B.UP_DOWN,
    _G.SUI_UP_DOWN_DAILY: _B.UP_DOWN,
    _G.HYPE_UP_DOWN_DAILY: _B.UP_DOWN,
    # Equity indices — direction-only daily.
    _G.SPX_UP_DOWN_DAILY: _B.UP_DOWN,
    _G.NDX_UP_DOWN_DAILY: _B.UP_DOWN,
    _G.RUT_UP_DOWN_DAILY: _B.UP_DOWN,
    _G.DJIA_UP_DOWN_DAILY: _B.UP_DOWN,
    # Commodity / FX direction-only daily.
    _G.GOLD_UP_DOWN_DAILY: _B.UP_DOWN,
    _G.CRUDE_OIL_UP_DOWN_DAILY: _B.UP_DOWN,
    _G.NATGAS_UP_DOWN_DAILY: _B.UP_DOWN,
    _G.EUR_UP_DOWN_DAILY: _B.UP_DOWN,
    # Price-range (multistrike / between-X-Y).
    _G.BTC_PRICE_RANGE_DAILY: _B.PRICE_RANGE,
    _G.ETH_PRICE_RANGE_DAILY: _B.PRICE_RANGE,
    _G.SOL_PRICE_RANGE_DAILY: _B.PRICE_RANGE,
    _G.XRP_PRICE_RANGE_DAILY: _B.PRICE_RANGE,
    _G.DOGE_PRICE_RANGE_DAILY: _B.PRICE_RANGE,
    _G.BNB_PRICE_RANGE_DAILY: _B.PRICE_RANGE,
    _G.ADA_PRICE_RANGE_DAILY: _B.PRICE_RANGE,
    _G.AVAX_PRICE_RANGE_DAILY: _B.PRICE_RANGE,
    _G.LINK_PRICE_RANGE_DAILY: _B.PRICE_RANGE,
    _G.LTC_PRICE_RANGE_DAILY: _B.PRICE_RANGE,
    _G.SUI_PRICE_RANGE_DAILY: _B.PRICE_RANGE,
    _G.HYPE_PRICE_RANGE_DAILY: _B.PRICE_RANGE,
    # Price-level (above-threshold-by-date).
    _G.GOLD_PRICE_LEVEL: _B.PRICE_LEVEL,
    _G.SILVER_PRICE_LEVEL: _B.PRICE_LEVEL,
    _G.CRUDE_OIL_PRICE_LEVEL: _B.PRICE_LEVEL,
    _G.TREASURY_YIELD_PER_PRINT: _B.PRICE_LEVEL,
    _G.CRYPTO_FEAR_GREED_INDEX: _B.PRICE_LEVEL,
    # Macro recurring prints (release-driven).
    _G.FED_RATE_DECISION_PER_FOMC: _B.PER_MONTH,
    _G.CPI_PRINT_PER_MONTH: _B.PER_MONTH,
    _G.UNEMPLOYMENT_RATE_PER_MONTH: _B.PER_MONTH,
    _G.NONFARM_PAYROLLS_PER_MONTH: _B.PER_MONTH,
    _G.GDP_PRINT_PER_QUARTER: _B.PER_MONTH,
    _G.PPI_PRINT_PER_MONTH: _B.PER_MONTH,
    _G.PCE_PRINT_PER_MONTH: _B.PER_MONTH,
    # Weather highest-temp (range/threshold) — PRICE_LEVEL structure.
    _G.WEATHER_TEMP_DAILY: _B.PRICE_LEVEL,
    # Politics / figures.
    _G.ELECTION_PRESIDENT_2028: _B.MATCH,  # winner-of-field
    _G.TRUMP_APPROVAL_RATING: _B.APPROVAL_RATING,
    _G.TRUMP_STATEMENTS: _B.STATEMENTS,
    _G.TRUMP_EXEC_ORDER: _B.EXEC_ORDER,
    _G.ELON_TWEET_COUNT: _B.STATEMENTS,
    _G.ELON_STATEMENTS: _B.STATEMENTS,
    _G.ELON_NET_WORTH: _B.PRICE_LEVEL,
    # Geopolitics / single-event.
    _G.GEO_ISRAEL_IRAN: _B.EVENT,
    _G.GEO_RUSSIA_UKRAINE: _B.EVENT,
    _G.GEO_OTHER_BY_DATE: _B.EVENT,
    # Culture.
    _G.OSCARS_BEST_PICTURE: _B.MATCH,  # winner-of-field
    _G.BOX_OFFICE_OPENING_WEEKEND: _B.PRICE_LEVEL,
    # Sports — bet-type is the Axis-2 split.
    _G.SPORTS_MLB_MATCH: _B.MATCH,
    _G.SPORTS_MLB_SPREAD: _B.SPREAD,
    _G.SPORTS_MLB_TOTAL: _B.TOTAL,
    _G.SPORTS_MLB_NRFI: _B.NRFI,
    _G.SPORTS_NFL_MATCH: _B.MATCH,
    _G.SPORTS_NFL_SPREAD: _B.SPREAD,
    _G.SPORTS_NFL_TOTAL: _B.TOTAL,
    _G.SPORTS_NBA_MATCH: _B.MATCH,
    _G.SPORTS_NBA_SPREAD: _B.SPREAD,
    _G.SPORTS_NBA_TOTAL: _B.TOTAL,
    _G.SPORTS_NHL_MATCH: _B.MATCH,
    _G.SPORTS_NHL_SPREAD: _B.SPREAD,
    _G.SPORTS_NHL_TOTAL: _B.TOTAL,
    _G.SPORTS_EPL_MATCH: _B.MATCH,
    _G.SPORTS_EPL_TOTAL: _B.TOTAL,
    _G.SPORTS_UEFA_MATCH: _B.MATCH,
    _G.SPORTS_UEFA_TOTAL: _B.TOTAL,
    _G.SPORTS_CHAMPIONS_LEAGUE_MATCH: _B.MATCH,
    _G.SPORTS_LA_LIGA_MATCH: _B.MATCH,
    _G.SPORTS_SERIE_A_MATCH: _B.MATCH,
    _G.SPORTS_BUNDESLIGA_MATCH: _B.MATCH,
    _G.SPORTS_WORLD_CUP_MATCH: _B.MATCH,
    _G.SPORTS_F1_MATCH: _B.MATCH,
    _G.SPORTS_F1_GP_WINNER: _B.MATCH,
    _G.SPORTS_F1_CONSTRUCTOR: _B.MATCH,
    _G.SPORTS_TENNIS_MATCH: _B.MATCH,
    _G.SPORTS_GOLF_MATCH: _B.MATCH,
    _G.SPORTS_UFC_MATCH: _B.MATCH,
    _G.SPORTS_BOXING_MATCH: _B.MATCH,
    _G.SPORTS_OLYMPICS_MATCH: _B.MATCH,
    # Catch-all.
    _G.MISC_NOVELTY: _B.OTHER,
    _G.OTHER: _B.OTHER,
}


def underlying_for_group(cqg: CanonicalQuestionGroup) -> PredictionUnderlying:
    """Return the Axis-1 underlying for ``cqg``.

    Returns :attr:`PredictionUnderlying.OTHER` for any cqg not yet present in
    :data:`CANONICAL_GROUP_TO_UNDERLYING` (forward-compat for a freshly-added
    enum value). The completeness test asserts every *current* cqg is mapped,
    so an ``OTHER`` here in practice only means "new enum value, not yet
    categorised".
    """
    return CANONICAL_GROUP_TO_UNDERLYING.get(cqg, PredictionUnderlying.OTHER)


def bet_type_for_group(cqg: CanonicalQuestionGroup) -> PredictionBetType:
    """Return the Axis-2 bet-type for ``cqg``.

    Returns :attr:`PredictionBetType.OTHER` for any cqg not yet present in
    :data:`CANONICAL_GROUP_TO_BET_TYPE` (forward-compat for a freshly-added
    enum value). The completeness test asserts every *current* cqg is mapped.
    """
    return CANONICAL_GROUP_TO_BET_TYPE.get(cqg, PredictionBetType.OTHER)


def cross_venue_underlying_overlap(
    kalshi_cqgs: Iterable[CanonicalQuestionGroup],
    polymarket_cqgs: Iterable[CanonicalQuestionGroup],
) -> dict[str, set[PredictionUnderlying]]:
    """Measure cross-venue overlap at the Axis-1 UNDERLYING level.

    Maps each venue's cqgs to their underlyings (collapsing bet-type) and
    returns the shared / venue-only underlying sets. ``OTHER`` is treated like
    any other underlying here — callers that want to ignore the catch-all
    should filter it out of the inputs first.

    :param kalshi_cqgs: cqgs Kalshi can produce.
    :param polymarket_cqgs: cqgs Polymarket can produce.
    :returns: ``{"shared_underlyings", "kalshi_only", "polymarket_only"}`` ->
        ``set[PredictionUnderlying]``.
    """
    kalshi_underlyings = {underlying_for_group(cqg) for cqg in kalshi_cqgs}
    polymarket_underlyings = {underlying_for_group(cqg) for cqg in polymarket_cqgs}
    return {
        "shared_underlyings": kalshi_underlyings & polymarket_underlyings,
        "kalshi_only": kalshi_underlyings - polymarket_underlyings,
        "polymarket_only": polymarket_underlyings - kalshi_underlyings,
    }


__all__ = [
    "CANONICAL_GROUP_TO_BET_TYPE",
    "CANONICAL_GROUP_TO_UNDERLYING",
    "PredictionBetType",
    "PredictionUnderlying",
    "bet_type_for_group",
    "cross_venue_underlying_overlap",
    "underlying_for_group",
]
