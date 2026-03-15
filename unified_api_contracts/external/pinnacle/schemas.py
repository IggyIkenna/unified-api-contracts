"""Pinnacle REST API: leagues, events, periods, odds (moneyline, totals, spread), settlements, errors.

Ref: https://github.com/pinnacleapi/openapi-specification
"""

from __future__ import annotations

__api_version__ = "v3"  # matches provider_api_versions.yaml


from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from unified_api_contracts.canonical.crosscutting.errors import ErrorAction

# ---------------------------------------------------------------------------
# Reference data — league/event listings
# ---------------------------------------------------------------------------


class PinnacleLeague(BaseModel):
    """League from Pinnacle reference data API."""

    id: int | None = None
    name: str | None = None
    home_country: str | None = Field(None, alias="homeCountry")
    sport_id: int | None = Field(None, alias="sportId")


class PinnacleEvent(BaseModel):
    """Event (match) from Pinnacle reference data API."""

    id: int | None = None
    league_id: int | None = Field(None, alias="leagueId")
    home: str | None = None
    away: str | None = None
    starts: str | None = None
    status: str | None = None
    rotation_number_home: str | None = Field(None, alias="rotationNumberHome")
    rotation_number_away: str | None = Field(None, alias="rotationNumberAway")


# ---------------------------------------------------------------------------
# Odds response — strongly-typed nested execution shapes (frozen, non-optional)
# ---------------------------------------------------------------------------


class PinnacleMoneyline(BaseModel, frozen=True):
    """Moneyline odds (execution shape — frozen, non-optional)."""

    home: float = 0.0
    draw: float = 0.0
    away: float = 0.0


class PinnacleTotalEntry(BaseModel, frozen=True):
    """Totals (over/under) entry (execution shape — frozen, non-optional)."""

    points: float = 0.0
    over: float = 0.0
    under: float = 0.0


class PinnacleSpreadEntry(BaseModel, frozen=True):
    """Spread (handicap) entry (execution shape — frozen, non-optional)."""

    hdp: float = 0.0
    home: float = 0.0
    away: float = 0.0


class PinnaclePeriod(BaseModel, frozen=True):
    """Period within an odds event (execution shape — frozen, non-optional)."""

    number: int = 0
    moneyline: PinnacleMoneyline | None = None
    totals: list[PinnacleTotalEntry] = []
    spreads: list[PinnacleSpreadEntry] = []


class PinnacleOddsEvent(BaseModel, frozen=True):
    """Event in an odds response (execution shape — nested periods)."""

    id: int = 0
    periods: list[PinnaclePeriod] = []


class PinnacleOddsLeague(BaseModel, frozen=True):
    """League in an odds response (execution shape — nested events)."""

    events: list[PinnacleOddsEvent] = []


class PinnacleOddsResponse(BaseModel, frozen=True):
    """Odds response (execution shape — strongly typed nested leagues)."""

    leagues: list[PinnacleOddsLeague] = []


# ---------------------------------------------------------------------------
# Fixture response
# ---------------------------------------------------------------------------


class PinnacleFixtureEvent(BaseModel, frozen=True):
    """Event entry in a fixtures response."""

    id: int = 0


class PinnacleFixtureLeague(BaseModel, frozen=True):
    """League entry in a fixtures response."""

    events: list[PinnacleFixtureEvent] = []


class PinnacleFixturesResponse(BaseModel, frozen=True):
    """Fixtures response."""

    league: list[PinnacleFixtureLeague] = []


# ---------------------------------------------------------------------------
# Settlement and error
# ---------------------------------------------------------------------------


class PinnacleSettlementResponse(BaseModel):
    """Settlement response from Pinnacle API."""

    settled_fixtures: list[dict[str, object]] | None = Field(None, alias="settledFixtures")
    settled_specials: list[dict[str, object]] | None = Field(None, alias="settledSpecials")


# Alias for adapter imports
PinnacleTotals = PinnacleTotalEntry


class PinnacleError(BaseModel):
    """Pinnacle API error response."""

    error: str | None = None
    message: str | None = None
    code: int | None = None

    @classmethod
    def classify(cls, code: int | None = None, error: str | None = None) -> ErrorAction:
        """Map Pinnacle error to retry action."""
        if code == 429 or (error and "rate" in (error or "").lower()):
            return ErrorAction.RETRY
        if code is not None and code >= 500:
            return ErrorAction.RETRY
        if code == 401 or (error and "unauthorized" in (error or "").lower()):
            return ErrorAction.FAIL
        return ErrorAction.FAIL


# ---------------------------------------------------------------------------
# Execution / bet placement (POST /v1/bets/straight)
# Ref: https://pinnacleapi.github.io/betsapi#operation/Bets_StraightBet_V3
# ---------------------------------------------------------------------------


class PinnacleBetRequest(BaseModel):
    """Straight bet request body for POST /v1/bets/straight."""

    unique_request_id: str | None = Field(None, alias="uniqueRequestId")
    accept_better_line: bool | None = Field(None, alias="acceptBetterLine")
    customer_reference: str | None = Field(None, alias="customerReference")
    odds_format: str | None = Field(None, alias="oddsFormat")  # AMERICAN | DECIMAL | HONGKONG | INDONESIAN | MALAY
    stake: float | None = None
    win_risk_stake: str | None = Field(None, alias="winRiskStake")  # WIN | RISK
    line_id: int | None = Field(None, alias="lineId")
    alt_line_id: int | None = Field(None, alias="altLineId")
    pitcher1_must_start: bool | None = Field(None, alias="pitcher1MustStart")
    pitcher2_must_start: bool | None = Field(None, alias="pitcher2MustStart")
    bet_type: str | None = Field(None, alias="betType")  # SPREAD | MONEYLINE | TOTAL_POINTS | TEAM_TOTAL_POINTS
    sport_id: int | None = Field(None, alias="sportId")
    event_id: int | None = Field(None, alias="eventId")
    period_number: int | None = Field(None, alias="periodNumber")  # 0 = full match
    team: str | None = None  # TEAM1 | TEAM2 | DRAW (for spread/moneyline)
    side: str | None = None  # OVER | UNDER (for totals)
    handicap: float | None = None


class PinnacleBetResponse(BaseModel):
    """Straight bet response from POST /v1/bets/straight."""

    status: str | None = None  # ACCEPTED | PENDING_ACCEPTANCE | PROCESSED_WITH_ERROR
    error_code: str | None = Field(None, alias="errorCode")
    bet_id: int | None = Field(None, alias="betId")
    unique_request_id: str | None = Field(None, alias="uniqueRequestId")
    better_line_was_accepted: bool | None = Field(None, alias="betterLineWasAccepted")
    price: float | None = None
    handicap: float | None = None
    team1_score: float | None = Field(None, alias="team1Score")
    team2_score: float | None = Field(None, alias="team2Score")


class PinnacleBetEntry(BaseModel):
    """Single bet from GET /v1/bets response."""

    bet_id: int | None = Field(None, alias="betId")
    unique_request_id: str | None = Field(None, alias="uniqueRequestId")
    wager_number: int | None = Field(None, alias="wagerNumber")
    placed_at: str | None = Field(None, alias="placedAt")
    bet_status: str | None = Field(None, alias="betStatus")  # ACCEPTED | CANCELLED | LOSE | REFUNDED | WON
    bet_type: str | None = Field(None, alias="betType")
    win: float | None = None
    risk: float | None = None
    win_loss: float | None = Field(None, alias="winLoss")
    odds_format: str | None = Field(None, alias="oddsFormat")
    customer_reference: str | None = Field(None, alias="customerReference")
    sport_id: int | None = Field(None, alias="sportId")
    event_id: int | None = Field(None, alias="eventId")
    period_number: int | None = Field(None, alias="periodNumber")
    team_1: str | None = Field(None, alias="team1")
    team_2: str | None = Field(None, alias="team2")
    side: str | None = None
    handicap: float | None = None
    price: float | None = None


class PinnacleGetBetsResponse(BaseModel):
    """Response from GET /v1/bets."""

    bets: list[PinnacleBetEntry] | None = None


# ---------------------------------------------------------------------------
# Position / current open bet schema
# ---------------------------------------------------------------------------


class PinnacleCurrentBet(BaseModel):
    """Open (running) bet from GET /v1/bets?betlist=RUNNING.

    A RUNNING bet is an unresolved wager — equivalent to an open position.
    Only bets with bet_status=ACCEPTED and unresolved are returned with betlist=RUNNING.

    price: decimal odds at placement.
    risk / win: stake and potential payout in account currency.
    team / side: the outcome wagered on.
    handicap: spread/total line value.
    is_live: True if bet was placed in-play.
    league_id: Pinnacle league identifier (join with /v1/leagues/{sport_id}).
    """

    bet_id: int | None = Field(None, alias="betId")
    wager_number: int | None = Field(None, alias="wagerNumber")
    placed_at: str | None = Field(None, alias="placedAt")
    bet_type: str | None = Field(None, alias="betType")  # MONEYLINE | SPREAD | TOTAL_POINTS | TEAM_TOTAL_POINTS
    sport_id: int | None = Field(None, alias="sportId")
    event_id: int | None = Field(None, alias="eventId")
    league_id: int | None = Field(None, alias="leagueId")
    period_number: int | None = Field(None, alias="periodNumber")  # 0=match, 1=1st half
    team: str | None = None  # TEAM1 | TEAM2 | DRAW
    side: str | None = None  # OVER | UNDER (totals only)
    handicap: float | None = None
    price: float | None = None  # decimal odds at placement
    risk: float | None = None  # stake (at risk) in account currency
    win: float | None = None  # potential payout in account currency
    is_live: bool | None = Field(None, alias="isLive")
    currency: str | None = None


# =============================================================================
# Source schemas (merged from external/sports/sources/pinnacle/)
# =============================================================================


class PinnacleEventSource(BaseModel):
    """Pinnacle sports event (source schema, simplified)."""

    model_config = ConfigDict(frozen=True)

    event_id: int
    sport_id: int
    league_id: int
    starts: datetime
    home: str
    away: str
    live_status: int | None = None
    status: str | None = None
    parent_id: int | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class PinnacleLine(BaseModel):
    """Pinnacle odds line for a specific market."""

    model_config = ConfigDict(frozen=True)

    event_id: int
    period_number: int
    line_id: int
    market_type: str
    home_odds: Decimal | None = None
    draw_odds: Decimal | None = None
    away_odds: Decimal | None = None
    handicap: Decimal | None = None
    over_odds: Decimal | None = None
    under_odds: Decimal | None = None
    total_points: Decimal | None = None
    max_bet: Decimal | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class PinnacleMatchup(BaseModel):
    """Pinnacle matchup with combined event and line data."""

    model_config = ConfigDict(frozen=True)

    event_id: int
    starts: datetime
    home: str
    away: str
    league_id: int
    moneyline_home: Decimal | None = None
    moneyline_draw: Decimal | None = None
    moneyline_away: Decimal | None = None
    spread_home: Decimal | None = None
    spread_away: Decimal | None = None
    spread_handicap: Decimal | None = None
    total_over: Decimal | None = None
    total_under: Decimal | None = None
    total_points: Decimal | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class PinnacleOdds(BaseModel):
    """Pinnacle aggregated odds for a match."""

    model_config = ConfigDict(frozen=True)

    event_id: int
    home: str
    away: str
    starts: datetime
    lines: list[PinnacleLine]

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)
