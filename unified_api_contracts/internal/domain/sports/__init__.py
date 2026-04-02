"""UIC domain/sports — canonical sports execution extension types.

Extends UAC CanonicalOrder with sports-specific fields (persistence type,
market ID, selection ID, handicap, odds format).  Base CanonicalOrder fields
are unchanged so generic execution-service code works without modification.
"""

from unified_api_contracts.internal.domain.sports.arb_config import (
    EXCHANGE_COMMISSION_RATES,
    EXCHANGE_VENUES,
    ArbitrageStrategyConfig,
    VenueAllocationWeights,
    VenueBalance,
)
from unified_api_contracts.internal.domain.sports.execution import (
    BetCancelledEvent,
    BetFilledEvent,
    BetPlacedEvent,
    BetSettledEvent,
    CanonicalSportsFill,
    CanonicalSportsOrder,
    SportsBetEvent,
)
from unified_api_contracts.internal.domain.sports.risk import (
    BetSide,
    SportsBetPnL,
    SportsBetPosition,
    SportsExposure,
)

__all__ = [
    "EXCHANGE_COMMISSION_RATES",
    "EXCHANGE_VENUES",
    "ArbitrageStrategyConfig",
    "BetCancelledEvent",
    "BetFilledEvent",
    "BetPlacedEvent",
    "BetSettledEvent",
    "BetSide",
    "CanonicalSportsFill",
    "CanonicalSportsOrder",
    "SportsBetEvent",
    "SportsBetPnL",
    "SportsBetPosition",
    "SportsExposure",
    "VenueAllocationWeights",
    "VenueBalance",
]
