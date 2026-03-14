"""Temporary facade -- re-exports from canonical/domain/sports/ during migration.
Deleted in Phase 3 (p3-delete-emptied-dirs)."""

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
from unified_api_contracts.canonical.domain.sports.arbitrage import (
    ArbitrageMarket,
    ArbitrageOpportunity,
    ArbitrageStatus,
    ExpectedValue,
)
from unified_api_contracts.canonical.domain.sports.betting import (
    BetExecution,
    BetOrder,
    BetStatus,
    BettingSignal,
    SignalSource,
)
from unified_api_contracts.canonical.domain.sports.features import (
    SportsFeatureVector,
)
from unified_api_contracts.canonical.domain.sports.live import (
    LiveMatchState,
    LiveOddsUpdate,
    MatchPeriod,
    ScraperVersionMeta,
)
from unified_api_contracts.canonical.domain.sports.odds import (
    CanonicalBookmakerMarket,
    CanonicalOdds,
    MarketStatus,
    OddsType,
    OutcomeType,
)
from unified_api_contracts.external.sports.errors import (
    BetRejectedError,
    BookmakerUnavailableError,
    FixtureNotFoundError,
    MarketClosedError,
    OddsChangedError,
    ScraperError,
    SportsError,
)

__all__ = [
    "BOOKMAKER_REGISTRY",
    "ArbitrageMarket",
    "ArbitrageOpportunity",
    "ArbitrageStatus",
    "BetExecution",
    "BetOrder",
    "BetRejectedError",
    "BetStatus",
    "BettingSignal",
    "BookmakerCategory",
    "BookmakerInfo",
    "BookmakerRegistry",
    "BookmakerUnavailableError",
    "CanonicalBookmakerMarket",
    "CanonicalFixture",
    "CanonicalLeague",
    "CanonicalOdds",
    "CanonicalPlayer",
    "CanonicalReferee",
    "CanonicalTeam",
    "CanonicalVenue",
    "ExpectedValue",
    "FixtureMapping",
    "FixtureNotFoundError",
    "LiveMatchState",
    "LiveOddsUpdate",
    "MarketClosedError",
    "MarketStatus",
    "MatchPeriod",
    "OddsChangedError",
    "OddsType",
    "OutcomeType",
    "PlayerMapping",
    "ScraperError",
    "ScraperVersionMeta",
    "SignalSource",
    "SportsError",
    "SportsFeatureVector",
    "TeamMapping",
]
