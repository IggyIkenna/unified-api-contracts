"""Canonical sports schemas — cross-source normalised types."""

from unified_api_contracts.unified_api_contracts_external.sports.canonical.arbitrage import (
    ArbitrageMarket,
    ArbitrageOpportunity,
    ArbitrageStatus,
    ExpectedValue,
)
from unified_api_contracts.unified_api_contracts_external.sports.canonical.betting import (
    BetExecution,
    BetOrder,
    BetStatus,
    BettingSignal,
    SignalSource,
)
from unified_api_contracts.unified_api_contracts_external.sports.canonical.bookmaker import (
    BookmakerInfo,
)
from unified_api_contracts.unified_api_contracts_external.sports.canonical.events import (
    CanonicalFixtureEvent,
)
from unified_api_contracts.unified_api_contracts_external.sports.canonical.features import (
    SportsFeatureVector,
)
from unified_api_contracts.unified_api_contracts_external.sports.canonical.fixture_stats import (
    CanonicalFixtureStatsDetail,
)
from unified_api_contracts.unified_api_contracts_external.sports.canonical.injury import (
    CanonicalInjury,
)
from unified_api_contracts.unified_api_contracts_external.sports.canonical.lineup import (
    CanonicalLineup,
    LineupPlayer,
)
from unified_api_contracts.unified_api_contracts_external.sports.canonical.live import (
    LiveMatchState,
    LiveOddsUpdate,
    MatchPeriod,
    ScraperVersionMeta,
)
from unified_api_contracts.unified_api_contracts_external.sports.canonical.mappings import (
    FixtureMapping,
    PlayerMapping,
    TeamMapping,
)
from unified_api_contracts.unified_api_contracts_external.sports.canonical.odds import (
    CanonicalBookmakerMarket,
    CanonicalOdds,
    MarketStatus,
    OddsType,
    OutcomeType,
)
from unified_api_contracts.unified_api_contracts_external.sports.canonical.player_stats import (
    CanonicalPlayerMatchStats,
)
from unified_api_contracts.unified_api_contracts_external.sports.canonical.processed_odds import (
    ProcessedOddsOutput,
)
from unified_api_contracts.unified_api_contracts_external.sports.canonical.progressive import (
    CanonicalProgressiveOdds,
    CanonicalProgressiveStats,
)

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
    "CanonicalFixtureEvent",
    "CanonicalFixtureStatsDetail",
    "CanonicalInjury",
    "CanonicalLineup",
    "CanonicalOdds",
    "CanonicalPlayerMatchStats",
    "CanonicalProgressiveOdds",
    "CanonicalProgressiveStats",
    "ExpectedValue",
    "FixtureMapping",
    "LineupPlayer",
    "LiveMatchState",
    "LiveOddsUpdate",
    "MarketStatus",
    "MatchPeriod",
    "OddsType",
    "OutcomeType",
    "PlayerMapping",
    "ProcessedOddsOutput",
    "ScraperVersionMeta",
    "SignalSource",
    "SportsFeatureVector",
    "TeamMapping",
]
