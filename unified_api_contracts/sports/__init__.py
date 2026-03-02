"""Sports betting schemas — canonical types and source-specific schemas."""

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
from unified_api_contracts.sports.canonical.bookmaker import (
    BOOKMAKER_REGISTRY,
    BookmakerCategory,
    BookmakerInfo,
    BookmakerRegistry,
)
from unified_api_contracts.sports.canonical.features import SportsFeatureVector
from unified_api_contracts.sports.canonical.fixture import (
    CanonicalFixture,
    CanonicalLeague,
    CanonicalPlayer,
    CanonicalReferee,
    CanonicalTeam,
    CanonicalVenue,
)
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
from unified_api_contracts.sports.errors import (
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
    "MarketClosedError",
    "MarketStatus",
    "OddsChangedError",
    "OddsType",
    "OutcomeType",
    "PlayerMapping",
    "ScraperError",
    "SignalSource",
    "SportsError",
    "SportsFeatureVector",
    "TeamMapping",
]
