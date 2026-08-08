"""Sports venue classification constants (split from venue_constants.py for file-size compliance)."""

from __future__ import annotations

from enum import StrEnum

from ..canonical.domain.sports.odds import OddsType
from .venue_constants import (
    API_FOOTBALL,
    BET365,
    BET888SPORT,
    BETFAIR,
    BETFAIR_EX_EU,
    BETFAIR_EX_UK,
    BETMGM,
    BETOPENLY,
    BOVADA,
    CORAL,
    DRAFTKINGS,
    FANDUEL,
    FOOTYSTATS,
    KALSHI,
    LADBROKES,
    MATCHBOOK,
    METABET,
    NOVIG,
    ODDS_API,
    ODDS_ENGINE,
    ONEXBET,
    OPEN_METEO,
    OPTICODDS,
    PADDYPOWER,
    PINNACLE,
    POLYMARKET,
    PROPHETX,
    SBOBET,
    SHARPAPI,
    SKYBET,
    SMARKETS,
    SOCCER_FOOTBALL_INFO,
    SPORTS_BOOKMAKER_API_VENUES,
    SPORTS_BOOKMAKER_WEB_VENUES,
    SPORTS_DATA_VENUES,
    SPORTS_DFS_VENUES,
    SPORTS_EXCHANGE_VENUES,
    SPORTS_PREDICTION_MARKET_VENUES,
    TRANSFERMARKT,
    UNDERSTAT,
    WILLIAMHILL,
)


class SportsVenueType(StrEnum):
    """How we connect to a sports venue for bet placement."""

    EXCHANGE_API = "exchange_api"
    BOOKMAKER_API = "bookmaker_api"
    PREDICTION_MARKET_API = "prediction_market_api"
    WEB_SCRAPER = "web_scraper"
    DFS_PLATFORM = "dfs_platform"
    DATA_ONLY = "data_only"


class SportsAuthMethod(StrEnum):
    """Authentication mechanism for placing bets at the venue."""

    API_KEY = "api_key"
    SESSION_TOKEN = "session_token"
    LOGIN_CREDENTIALS = "login_credentials"
    WALLET_SIGNATURE = "wallet_signature"
    OAUTH2 = "oauth2"
    NONE = "none"


SPORTS_VENUE_TYPE_MAP: dict[str, SportsVenueType] = {}
SPORTS_VENUE_TYPE_MAP.update(dict.fromkeys(SPORTS_EXCHANGE_VENUES, SportsVenueType.EXCHANGE_API))
SPORTS_VENUE_TYPE_MAP.update(dict.fromkeys(SPORTS_PREDICTION_MARKET_VENUES, SportsVenueType.PREDICTION_MARKET_API))
SPORTS_VENUE_TYPE_MAP.update(dict.fromkeys(SPORTS_BOOKMAKER_API_VENUES, SportsVenueType.BOOKMAKER_API))
SPORTS_VENUE_TYPE_MAP.update(dict.fromkeys(SPORTS_BOOKMAKER_WEB_VENUES, SportsVenueType.WEB_SCRAPER))
SPORTS_VENUE_TYPE_MAP.update(dict.fromkeys(SPORTS_DFS_VENUES, SportsVenueType.DFS_PLATFORM))
SPORTS_VENUE_TYPE_MAP.update(dict.fromkeys(SPORTS_DATA_VENUES, SportsVenueType.DATA_ONLY))


# Derive-at-read-time resolver for the exchange_odds/fixed_odds instrument_type
# split (operator ruling 9, sports_taxonomy_p1_capture_and_contracts_2026_08_08.md
# -- "exchange-vs-sportsbook is a property of the VENUE, not something to stamp
# per-instrument; UAC SportsVenueType already encodes it"). Resolves
# `/plans/archive/issues/sports_odds_venue_enumeration_undercount_predrain_2026_07_27.md`'s
# "classify the unmapped bookmakers as EXCHANGE_ODDS or FIXED_ODDS" ask
# MECHANICALLY: every venue self-classifies via SPORTS_VENUE_TYPE_MAP above, so
# no per-venue operator judgment is needed and the doc's 19-vs-21 count
# discrepancy (a live-manifest re-measurement, not a classification gap) is
# moot under this model -- the resolver covers every venue in the map,
# regardless of count, not a hand-enumerated subset.
#
# This is the P1 CONTRACT only, same pattern as SPORTS_IS_DATA_TYPE_LOWERCASE_FORM
# / SPORTS_ODDS_DATA_TYPE_CANONICAL_FORM (canonical/domain/sports/league_data.py):
# additive, NOT wired into CONTRACT_REGISTRY's ("sports", "exchange_odds"/
# "fixed_odds", "trades") keys, the MTDS writer that still stamps the column, or
# any existing manifest row this phase -- switching the writer/readers to derive
# via this function instead of a stamped column, and retiring the stamped
# column + CONTRACT_REGISTRY entries, is P2 [REVIEW] P0 scope (full consumer
# enumeration there).
def derive_sports_odds_instrument_type(venue: str) -> str | None:
    """Return the exchange_odds/fixed_odds instrument_type for a sports VENUE.

    Exchange-style venues (:attr:`SportsVenueType.EXCHANGE_API`) resolve to
    ``"exchange_odds"``; bookmaker-style venues (``BOOKMAKER_API`` /
    ``WEB_SCRAPER``) resolve to ``"fixed_odds"``. Prediction-market, DFS,
    data-only, and unrecognised venues return ``None`` -- callers fall back to
    the legacy generic ``"odds"`` CONTRACT_REGISTRY entry for those, the same
    fallback :func:`unified_api_contracts.internal.schemas.contracts.lookup_contract`
    already performs during the fork's migration window.
    """
    venue_type = SPORTS_VENUE_TYPE_MAP.get(venue.upper())
    if venue_type is SportsVenueType.EXCHANGE_API:
        return "exchange_odds"
    if venue_type in (SportsVenueType.BOOKMAKER_API, SportsVenueType.WEB_SCRAPER):
        return "fixed_odds"
    return None


SPORTS_AUTH_MAP: dict[str, SportsAuthMethod] = {
    BETFAIR: SportsAuthMethod.SESSION_TOKEN,
    # BETFAIR_EX_UK/EX_EU are the same session-token-based Betfair Exchange API
    # family as bare BETFAIR (regional market variants, not separate accounts) —
    # closed 2026-08-08 alongside the SMARKETS gap below, same "every venue in
    # the set must resolve an auth method" principle (sports taxonomy P1).
    BETFAIR_EX_UK: SportsAuthMethod.SESSION_TOKEN,
    BETFAIR_EX_EU: SportsAuthMethod.SESSION_TOKEN,
    MATCHBOOK: SportsAuthMethod.API_KEY,
    # Best-available default pending a real integration (no adapter exists yet,
    # same as every other 2026-08-08 re-promoted bookmaker) — API_KEY mirrors
    # MATCHBOOK, its closest classified peer (both SPORTS_EXCHANGE_VENUES).
    SMARKETS: SportsAuthMethod.API_KEY,
    POLYMARKET: SportsAuthMethod.WALLET_SIGNATURE,
    KALSHI: SportsAuthMethod.API_KEY,
    NOVIG: SportsAuthMethod.API_KEY,
    BETOPENLY: SportsAuthMethod.API_KEY,
    PROPHETX: SportsAuthMethod.API_KEY,
    PINNACLE: SportsAuthMethod.API_KEY,
    ONEXBET: SportsAuthMethod.API_KEY,
    OPTICODDS: SportsAuthMethod.API_KEY,
    API_FOOTBALL: SportsAuthMethod.API_KEY,
}
SPORTS_AUTH_MAP.update(dict.fromkeys(SPORTS_BOOKMAKER_WEB_VENUES, SportsAuthMethod.LOGIN_CREDENTIALS))
SPORTS_AUTH_MAP.update(dict.fromkeys(SPORTS_DFS_VENUES, SportsAuthMethod.LOGIN_CREDENTIALS))
SPORTS_AUTH_MAP.update(
    dict.fromkeys(
        (FOOTYSTATS, SOCCER_FOOTBALL_INFO, OPEN_METEO, UNDERSTAT, TRANSFERMARKT, SHARPAPI, ODDS_ENGINE, METABET),
        SportsAuthMethod.NONE,
    )
)


class SportsAggregatorType(StrEnum):
    """Classification of sports venue role in the execution chain."""

    DIRECT_EXECUTION = "direct_execution"
    ODDS_AGGREGATOR = "odds_aggregator"
    EXECUTION_AGGREGATOR = "execution_aggregator"
    POSITION_AGGREGATOR = "position_aggregator"


VENUE_AGGREGATOR_TYPE: dict[str, SportsAggregatorType] = {
    **dict.fromkeys({ODDS_API, OPTICODDS, SHARPAPI, METABET, ODDS_ENGINE}, SportsAggregatorType.ODDS_AGGREGATOR),
    **dict.fromkeys(
        SPORTS_EXCHANGE_VENUES | SPORTS_BOOKMAKER_API_VENUES | SPORTS_PREDICTION_MARKET_VENUES,
        SportsAggregatorType.DIRECT_EXECUTION,
    ),
}

SPORTS_CAPTCHA_RISK: set[str] = {
    BET365,
    WILLIAMHILL,
    LADBROKES,
    CORAL,
    PADDYPOWER,
    SKYBET,
    BOVADA,
    DRAFTKINGS,
    FANDUEL,
    BETMGM,
    SBOBET,
    BET888SPORT,
}

# Supported market types per sports venue category.
# Maps each venue to the frozenset of OddsType markets it supports.
_EXCHANGE_MARKET_TYPES: frozenset[OddsType] = frozenset(
    {
        OddsType.H2H,
        OddsType.OVER_UNDER,
        OddsType.ASIAN_HANDICAP,
        OddsType.BOTH_TEAMS_SCORE,
        OddsType.CORRECT_SCORE,
        OddsType.DRAW_NO_BET,
        OddsType.DOUBLE_CHANCE,
        OddsType.GOAL_SCORER,
        OddsType.PLAYER_PROPS,
        OddsType.HALF_TIME_RESULT,
        OddsType.FIRST_HALF_OVER_UNDER,
        OddsType.CORNERS,
        OddsType.CARDS,
    }
)

_PREDICTION_MARKET_TYPES: frozenset[OddsType] = frozenset(
    {
        OddsType.H2H,
        OddsType.OVER_UNDER,
        OddsType.OUTRIGHT,
    }
)

_BOOKMAKER_API_MARKET_TYPES: frozenset[OddsType] = frozenset(
    {
        OddsType.H2H,
        OddsType.OVER_UNDER,
        OddsType.ASIAN_HANDICAP,
        OddsType.BOTH_TEAMS_SCORE,
        OddsType.DRAW_NO_BET,
        OddsType.DOUBLE_CHANCE,
        OddsType.PLAYER_PROPS,
        OddsType.OUTRIGHT,
        OddsType.CORRECT_SCORE,
    }
)

_BOOKMAKER_WEB_MARKET_TYPES: frozenset[OddsType] = frozenset(
    {
        OddsType.H2H,
        OddsType.OVER_UNDER,
        OddsType.ASIAN_HANDICAP,
        OddsType.BOTH_TEAMS_SCORE,
    }
)

_DFS_MARKET_TYPES: frozenset[OddsType] = frozenset(
    {
        OddsType.PLAYER_PROPS,
    }
)

SUPPORTED_MARKET_TYPES: dict[str, frozenset[OddsType]] = {}
SUPPORTED_MARKET_TYPES.update(dict.fromkeys(SPORTS_EXCHANGE_VENUES, _EXCHANGE_MARKET_TYPES))
SUPPORTED_MARKET_TYPES.update(dict.fromkeys(SPORTS_PREDICTION_MARKET_VENUES, _PREDICTION_MARKET_TYPES))
SUPPORTED_MARKET_TYPES.update(dict.fromkeys(SPORTS_BOOKMAKER_API_VENUES, _BOOKMAKER_API_MARKET_TYPES))
SUPPORTED_MARKET_TYPES.update(dict.fromkeys(SPORTS_BOOKMAKER_WEB_VENUES, _BOOKMAKER_WEB_MARKET_TYPES))
SUPPORTED_MARKET_TYPES.update(dict.fromkeys(SPORTS_DFS_VENUES, _DFS_MARKET_TYPES))
