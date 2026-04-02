"""The Odds API contracts."""

from .schemas import (
    ODBookmakerRaw,
    OddsApiBookmaker,
    OddsApiError,
    OddsApiEvent,
    OddsApiFixture,
    OddsApiHistoricalOdds,
    OddsApiMarket,
    OddsApiOutcome,
    ODEventRaw,
    ODMarketRaw,
    ODOddsRaw,
    ODOutcomeRaw,
    ODTeamsRaw,
)
from .team_names import (
    CANONICAL_TO_ODDS_API_BUNDESLIGA,
    CANONICAL_TO_ODDS_API_EPL,
    CANONICAL_TO_UNDERSTAT_BUNDESLIGA,
    CANONICAL_TO_UNDERSTAT_EPL,
    get_odds_api_team_name,
    get_understat_team_name,
)

__all__ = [
    "CANONICAL_TO_ODDS_API_BUNDESLIGA",
    "CANONICAL_TO_ODDS_API_EPL",
    "CANONICAL_TO_UNDERSTAT_BUNDESLIGA",
    "CANONICAL_TO_UNDERSTAT_EPL",
    "ODBookmakerRaw",
    "ODEventRaw",
    "ODMarketRaw",
    "ODOddsRaw",
    "ODOutcomeRaw",
    "ODTeamsRaw",
    "OddsApiBookmaker",
    "OddsApiError",
    "OddsApiEvent",
    "OddsApiFixture",
    "OddsApiHistoricalOdds",
    "OddsApiMarket",
    "OddsApiOutcome",
    "get_odds_api_team_name",
    "get_understat_team_name",
]
