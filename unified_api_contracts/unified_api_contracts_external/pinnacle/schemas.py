"""Pinnacle REST API: leagues, events, periods, odds (moneyline, totals, spread), settlements, errors.

Ref: https://github.com/pinnacleapi/openapi-specification
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from unified_api_contracts.shared import ErrorAction

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


class PinnacleError(BaseModel):
    """Pinnacle API error response."""

    error: str | None = None
    message: str | None = None
    code: int | None = None

    @classmethod
    def classify(cls, code: int | None = None, error: str | None = None) -> ErrorAction:
        """Map Pinnacle error to retry action."""
        if code == 429 or (error and "rate" in (error or "").lower()):
            return ErrorAction.RETRY_WITH_BACKOFF
        if code is not None and code >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        if code == 401 or (error and "unauthorized" in (error or "").lower()):
            return ErrorAction.FAIL_HARD
        return ErrorAction.FAIL_HARD
