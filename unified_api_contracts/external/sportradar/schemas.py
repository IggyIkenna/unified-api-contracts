"""Sportradar REST API schemas: sports events, competitors, betting markets.

Ref: https://developer.sportradar.com/docs/read/Home
     https://developer.sportradar.com/docs/read/football/Football_v4

Auth: api_key query parameter
Base URL: https://api.sportradar.us/{sport}/production/{version}/

Sport-specific base URLs:
  Soccer:      https://api.sportradar.us/soccer/production/v4/en/
  Basketball:  https://api.sportradar.us/nba/production/v7/en/
  Tennis:      https://api.sportradar.us/tennis/production/v3/en/
  Am. Football: https://api.sportradar.us/nfl/production/v7/en/

Access tiers:
  Trial:      100 calls/day (30-day trial, free)
  Basic:      ~$499/mo for one sport (5K calls/day)
  Advanced:   ~$1,199/mo (unlimited history, real-time)
"""

__api_version__ = "v4"  # Soccer v4; varies per sport

from pydantic import BaseModel, Field

from unified_api_contracts.canonical.crosscutting.errors import ErrorAction


class SportradarCompetitor(BaseModel):
    """Team or player competing in a sport event."""

    id: str | None = None
    name: str | None = None
    abbreviation: str | None = None
    qualifier: str | None = None  # "home" | "away"
    country: str | None = None
    country_code: str | None = None
    gender: str | None = None


class SportradarSport(BaseModel):
    """Sport category."""

    id: str | None = None
    name: str | None = None


class SportradarCategory(BaseModel):
    """Sport category (e.g. "International", "England")."""

    id: str | None = None
    name: str | None = None
    country_code: str | None = None
    sport: SportradarSport | None = None


class SportradarTournament(BaseModel):
    """Tournament / competition (e.g. "Premier League", "Champions League")."""

    id: str | None = None
    name: str | None = None
    type: str | None = None
    category: SportradarCategory | None = None


class SportradarSeason(BaseModel):
    """Competition season."""

    id: str | None = None
    name: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    year: str | None = None
    tournament_id: str | None = None


class SportradarVenue(BaseModel):
    """Match venue."""

    id: str | None = None
    name: str | None = None
    city_name: str | None = None
    country_name: str | None = None
    country_code: str | None = None
    map_coordinates: str | None = None
    capacity: int | None = None


class SportradarEventConditions(BaseModel):
    """Match scheduling conditions."""

    attendance: int | None = None
    weather: str | None = None  # free-text from API
    venue: SportradarVenue | None = None
    referee: dict[str, object] | None = None


class SportradarSportEvent(BaseModel):
    """A single sport event (match, game, bout)."""

    id: str | None = None
    start_time: str | None = None  # ISO 8601
    start_time_confirmed: bool | None = None
    sport_event_context: dict[str, object] | None = Field(None, alias="sport_event_context")
    competitors: list[SportradarCompetitor] | None = None
    venue: SportradarVenue | None = None
    coverage: dict[str, object] | None = None


class SportradarSportEventStatus(BaseModel):
    """Live status of a sport event."""

    status: str | None = None  # "not_started" | "live" | "ended" | "closed"
    match_status: str | None = None  # "not_started" | "1st_half" | "half_time" | "2nd_half" | "ended"
    home_score: int | None = None
    away_score: int | None = None
    period_scores: list[dict[str, object]] | None = None
    clock: dict[str, object] | None = None  # {"played": "45:00"}


class SportradarSportEventSummary(BaseModel):
    """Combined event + status (from schedule/results endpoints)."""

    sport_event: SportradarSportEvent | None = None
    sport_event_status: SportradarSportEventStatus | None = None


class SportradarScheduleResponse(BaseModel):
    """Response from GET /{sport}/schedules/{date}/schedule.json."""

    generated_at: str | None = None
    sport_events: list[SportradarSportEvent] | None = None


class SportradarResultsResponse(BaseModel):
    """Response from GET /{sport}/schedules/{date}/results.json."""

    generated_at: str | None = None
    results: list[SportradarSportEventSummary] | None = None


class SportradarOddsOutcome(BaseModel):
    """Single odds outcome (e.g. 'Home Win', 'Draw', 'Away Win')."""

    id: str | None = None
    odds: float | None = None
    type: str | None = None  # "home" | "draw" | "away"
    name: str | None = None


class SportradarMarket(BaseModel):
    """A betting market (e.g. '3-Way' for match result)."""

    id: int | None = None
    name: str | None = None
    outcomes: list[SportradarOddsOutcome] | None = None
    favourite: str | None = None


class SportradarBook(BaseModel):
    """Bookmaker offering odds on markets."""

    id: int | None = None
    name: str | None = None
    markets: list[SportradarMarket] | None = None


class SportradarOddsResponse(BaseModel):
    """Response from GET /{sport}/sport_events/{id}/odds/summary.json."""

    generated_at: str | None = None
    sport_event: SportradarSportEvent | None = None
    books: list[SportradarBook] | None = None


class SportradarError(BaseModel):
    """Sportradar API error response."""

    response_code: int | None = None
    message: str | None = None

    @classmethod
    def classify(cls, code: int | None = None, message: str | None = None) -> ErrorAction:
        """Map Sportradar error to retry action."""
        if code == 429:
            return ErrorAction.RETRY
        if code in (401, 403):
            return ErrorAction.FAIL
        if code is not None and code >= 500:
            return ErrorAction.RETRY
        return ErrorAction.FAIL
