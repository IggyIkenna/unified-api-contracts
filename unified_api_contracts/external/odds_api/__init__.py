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

__all__ = [
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
]
