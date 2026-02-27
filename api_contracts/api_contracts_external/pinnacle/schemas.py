"""Pinnacle REST API: leagues, events, periods, odds (moneyline, totals, spread), settlements, errors.

Ref: https://github.com/pinnacleapi/openapi-specification
"""

from pydantic import BaseModel, Field

from api_contracts.shared import ErrorAction


class PinnacleLeague(BaseModel):
    """League from Pinnacle API."""

    id: int | None = None
    name: str | None = None
    home_country: str | None = Field(None, alias="homeCountry")
    sport_id: int | None = Field(None, alias="sportId")


class PinnacleEvent(BaseModel):
    """Event (match) from Pinnacle API."""

    id: int | None = None
    league_id: int | None = Field(None, alias="leagueId")
    home: str | None = None
    away: str | None = None
    starts: str | None = None
    status: str | None = None
    rotation_number_home: str | None = Field(None, alias="rotationNumberHome")
    rotation_number_away: str | None = Field(None, alias="rotationNumberAway")


class PinnaclePeriod(BaseModel):
    """Period (half, quarter) within an event."""

    number: int | None = None
    spread: object | None = None
    money_line: object | None = Field(None, alias="moneyLine")
    total: object | None = None
    team_1_total: object | None = Field(None, alias="team1Total")
    team_2_total: object | None = Field(None, alias="team2Total")


class PinnacleMoneyline(BaseModel):
    """Moneyline odds."""

    home: float | None = None
    away: float | None = None
    draw: float | None = None


class PinnacleTotals(BaseModel):
    """Totals (over/under) odds."""

    over: float | None = None
    under: float | None = None
    points: float | None = None


class PinnacleSpread(BaseModel):
    """Spread (handicap) odds."""

    home: float | None = None
    away: float | None = None
    hdp: float | None = None


class PinnacleOddsResponse(BaseModel):
    """Odds response from Pinnacle API."""

    sport_id: int | None = Field(None, alias="sportId")
    last: int | None = None
    leagues: list[dict[str, object]] | None = None
    events: list[dict[str, object]] | None = None


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
