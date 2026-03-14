"""The Odds API v4 source schemas — public re-exports."""

from unified_api_contracts.external.sports.sources.odds_api.schemas import (
    ODBookmakerRaw,
    OddsApiBookmaker,
    OddsApiEvent,
    OddsApiMarket,
    OddsApiOutcome,
    ODEventRaw,
    ODMarketRaw,
    ODOddsRaw,
    ODOutcomeRaw,
    ODTeamsRaw,
)

__all__ = [
    # New Decimal-based raw source models
    "ODBookmakerRaw",
    "ODEventRaw",
    "ODMarketRaw",
    "ODOddsRaw",
    "ODOutcomeRaw",
    "ODTeamsRaw",
    # Original convenience schemas
    "OddsApiBookmaker",
    "OddsApiEvent",
    "OddsApiMarket",
    "OddsApiOutcome",
]
