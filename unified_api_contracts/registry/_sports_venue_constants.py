"""Sports venue classification constants (split from venue_constants.py for file-size compliance)."""

from __future__ import annotations

from enum import StrEnum

from ..canonical.domain.sports.odds import OddsType
from .venue_constants import (
    API_FOOTBALL,
    BET365,
    BET888SPORT,
    BETDAQ,
    BETFAIR,
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
    ODDSJAM,
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

SPORTS_AUTH_MAP: dict[str, SportsAuthMethod] = {
    BETFAIR: SportsAuthMethod.SESSION_TOKEN,
    SMARKETS: SportsAuthMethod.API_KEY,
    MATCHBOOK: SportsAuthMethod.API_KEY,
    BETDAQ: SportsAuthMethod.API_KEY,
    POLYMARKET: SportsAuthMethod.WALLET_SIGNATURE,
    KALSHI: SportsAuthMethod.API_KEY,
    NOVIG: SportsAuthMethod.API_KEY,
    BETOPENLY: SportsAuthMethod.API_KEY,
    PROPHETX: SportsAuthMethod.API_KEY,
    PINNACLE: SportsAuthMethod.API_KEY,
    ONEXBET: SportsAuthMethod.API_KEY,
    ODDS_API: SportsAuthMethod.API_KEY,
    OPTICODDS: SportsAuthMethod.API_KEY,
    ODDSJAM: SportsAuthMethod.API_KEY,
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
    **dict.fromkeys(
        {ODDS_API, OPTICODDS, ODDSJAM, SHARPAPI, METABET, ODDS_ENGINE}, SportsAggregatorType.ODDS_AGGREGATOR
    ),
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
