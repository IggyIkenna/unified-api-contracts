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

# Target derive-at-read-time replacement for the stamped `exchange_odds`/
# `fixed_odds` instrument_type split (operator ruling 9,
# `plans/active/sports_taxonomy_p1_capture_and_contracts_2026_08_08.md` —
# "retire the exchange_odds/fixed_odds instrument_type split... exchange-
# vs-sportsbook is a property of the VENUE, so stamping it per-instrument is
# redundant. Derive at read time."). `SPORTS_VENUE_TYPE_MAP` above already
# encodes exactly this distinction (EXCHANGE_API vs BOOKMAKER_API/WEB_SCRAPER)
# — this table + resolver just name the target instrument_type token each
# venue type derives to, so P2's physical migration and every consumer have
# one SSOT instead of re-deriving the venue-type-to-token mapping ad hoc.
#
# This is the P1 CONTRACT only, same pattern as `SPORTS_IS_DATA_TYPE_
# LOWERCASE_FORM`/`SPORTS_ODDS_DATA_TYPE_CANONICAL_FORM` in `league_data.py`:
# the physical re-stamp (writers stop stamping `instrument_type=exchange_odds`/
# `fixed_odds`, the `CONTRACT_REGISTRY[("sports","exchange_odds"/"fixed_odds",
# "trades")]` entries retire, and `contracts.py::_SPORTS_ODDS_FORK_
# INSTRUMENT_TYPES`'s dual-read fallback is removed) is P2 scope. Deliberately
# NOT wired into `CONTRACT_REGISTRY` or any writer/reader this phase.
#
# `PREDICTION_MARKET_API`/`DFS_PLATFORM`/`DATA_ONLY` venue types (e.g.
# ODDS_API, which leaves the venue axis entirely per operator ruling 2 in the
# same plan) have no exchange/sportsbook classification and correctly resolve
# to `None` — this split only ever covered the two bet-placement venue types
# it was named for.
SPORTS_ODDS_FORK_INSTRUMENT_TYPE_BY_VENUE_TYPE: dict[SportsVenueType, str] = {
    SportsVenueType.EXCHANGE_API: "exchange_odds",
    SportsVenueType.BOOKMAKER_API: "fixed_odds",
    SportsVenueType.WEB_SCRAPER: "fixed_odds",
}


def derive_sports_odds_fork_instrument_type(venue: str) -> str | None:
    """Return the TARGET `exchange_odds`/`fixed_odds` instrument_type for a
    sports venue, derived from its `SportsVenueType` instead of a per-row
    stamp.

    Accepts either case; returns ``None`` for a venue with no registered
    `SportsVenueType` (unknown venue) or one whose venue type carries no
    exchange/sportsbook classification (prediction-market, DFS, or
    data-only venues, e.g. `ODDS_API`). P1 contract only — see the
    `SPORTS_ODDS_FORK_INSTRUMENT_TYPE_BY_VENUE_TYPE` docstring above for why
    the physical stamp + registry retirement are deferred to P2.
    """
    venue_type = SPORTS_VENUE_TYPE_MAP.get(venue.upper())
    if venue_type is None:
        return None
    return SPORTS_ODDS_FORK_INSTRUMENT_TYPE_BY_VENUE_TYPE.get(venue_type)


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
