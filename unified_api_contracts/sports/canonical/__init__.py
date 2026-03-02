"""Canonical sports schemas — cross-source normalised types."""

from unified_api_contracts.sports.canonical.arbitrage import (
    ArbitrageMarket,
    ArbitrageOpportunity,
    ArbitrageStatus,
    ExpectedValue,
)
from unified_api_contracts.sports.canonical.betting import (
    BetExecution,
    BetOrder,
    BetStatus,
    BettingSignal,
    SignalSource,
)
from unified_api_contracts.sports.canonical.bookmaker import BookmakerInfo
from unified_api_contracts.sports.canonical.features import SportsFeatureVector
from unified_api_contracts.sports.canonical.mappings import (
    FixtureMapping,
    PlayerMapping,
    TeamMapping,
)
from unified_api_contracts.sports.canonical.odds import (
    CanonicalBookmakerMarket,
    CanonicalOdds,
    MarketStatus,
    OddsType,
    OutcomeType,
)
from unified_api_contracts.sports.canonical.processed_odds import ProcessedOddsOutput

__all__ = [
    "ArbitrageMarket",
    "ArbitrageOpportunity",
    "ArbitrageStatus",
    "BetExecution",
    "BetOrder",
    "BetStatus",
    "BettingSignal",
    "BookmakerInfo",
    "CanonicalBookmakerMarket",
    "CanonicalOdds",
    "ExpectedValue",
    "FixtureMapping",
    "MarketStatus",
    "OddsType",
    "OutcomeType",
    "PlayerMapping",
    "ProcessedOddsOutput",
    "SignalSource",
    "SportsFeatureVector",
    "TeamMapping",
]
