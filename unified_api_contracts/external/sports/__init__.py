"""Sports betting schemas — canonical types and source-specific schemas."""

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
from unified_api_contracts.external.sports.canonical.features import (
    SportsFeatureVector,
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
