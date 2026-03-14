"""Canonical sports schemas — cross-source normalised types."""

from unified_api_contracts.canonical.domain.bookmaker_registry import (
    BOOKMAKER_REGISTRY,
    BookmakerRegistry,
)
from unified_api_contracts.canonical.domain.sports import (
    BookmakerCategory,
    BookmakerInfo,
    CanonicalFixture,
    CanonicalLeague,
    CanonicalPlayer,
    CanonicalReferee,
    CanonicalTeam,
    CanonicalVenue,
    FixtureMapping,
    PlayerMapping,
    TeamMapping,
)
from unified_api_contracts.external.sports.canonical.arbitrage import (
    ArbitrageMarket,
    ArbitrageOpportunity,
    ArbitrageStatus,
    ExpectedValue,
)
from unified_api_contracts.external.sports.canonical.betting import (
    BetExecution,
    BetOrder,
    BetStatus,
    BettingSignal,
    SignalSource,
)
from unified_api_contracts.external.sports.canonical.events import (
    CanonicalFixtureEvent,
)
from unified_api_contracts.external.sports.canonical.features import (
    SportsFeatureVector,
)
from unified_api_contracts.external.sports.canonical.fixture_stats import (
    CanonicalFixtureStatsDetail,
)
from unified_api_contracts.external.sports.canonical.injury import (
    CanonicalInjury,
)
from unified_api_contracts.external.sports.canonical.lineup import (
    CanonicalLineup,
    LineupPlayer,
)
from unified_api_contracts.external.sports.canonical.live import (
    LiveMatchState,
    LiveOddsUpdate,
    MatchPeriod,
    ScraperVersionMeta,
)
from unified_api_contracts.external.sports.canonical.odds import (
    CanonicalBookmakerMarket,
    CanonicalOdds,
    MarketStatus,
    OddsType,
    OutcomeType,
)
from unified_api_contracts.external.sports.canonical.player_stats import (
    CanonicalPlayerMatchStats,
)
from unified_api_contracts.external.sports.canonical.processed_odds import (
    ProcessedOddsOutput,
)
from unified_api_contracts.external.sports.canonical.progressive import (
    CanonicalProgressiveOdds,
    CanonicalProgressiveStats,
)

__all__ = [
    "BOOKMAKER_REGISTRY",
    "ArbitrageMarket",
    "ArbitrageOpportunity",
    "ArbitrageStatus",
    "BetExecution",
    "BetOrder",
    "BetStatus",
    "BettingSignal",
    "BookmakerCategory",
    "BookmakerInfo",
    "BookmakerRegistry",
    "CanonicalBookmakerMarket",
    "CanonicalFixture",
    "CanonicalFixtureEvent",
    "CanonicalFixtureStatsDetail",
    "CanonicalInjury",
    "CanonicalLeague",
    "CanonicalLineup",
    "CanonicalOdds",
    "CanonicalPlayer",
    "CanonicalPlayerMatchStats",
    "CanonicalProgressiveOdds",
    "CanonicalProgressiveStats",
    "CanonicalReferee",
    "CanonicalTeam",
    "CanonicalVenue",
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
