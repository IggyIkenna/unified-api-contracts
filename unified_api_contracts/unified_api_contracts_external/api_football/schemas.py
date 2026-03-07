"""API-Football: fixtures, teams, leagues, lineups, events, statistics, venues, errors.

Ref: https://www.api-football.com/documentation-v3
Auth: x-apisports-key header
Rate limit: 100 req/day (free), 7500/day (paid)
"""

__api_version__ = "v3"  # matches provider_api_versions.yaml

from pydantic import BaseModel, Field

from unified_api_contracts import ErrorAction

# ---------------------------------------------------------------------------
# Rate limit (response headers)
# ---------------------------------------------------------------------------


class ApiFootballRateLimit(BaseModel):
    """Rate limit info from API-Football response headers.

    Headers: x-ratelimit-requests-limit, x-ratelimit-requests-remaining,
    x-ratelimit-limit, x-ratelimit-remaining.
    """

    x_ratelimit_requests_limit: int | None = None
    x_ratelimit_requests_remaining: int | None = None
    x_ratelimit_limit: int | None = None
    x_ratelimit_remaining: int | None = None


# ---------------------------------------------------------------------------
# Odds (GET /odds, GET /odds/live)
# ---------------------------------------------------------------------------


class ApiFootballOddsBookmaker(BaseModel):
    """Bookmaker in odds response."""

    id: int | None = None
    name: str | None = None


class ApiFootballOddsValue(BaseModel):
    """Single odds value (e.g. Home 1.50, Over 2.5)."""

    value: str | None = None
    odd: str | None = None
    handicap: str | None = None
    main: bool | None = None
    suspended: bool | None = None


class ApiFootballOddsBet(BaseModel):
    """Bet type with values (e.g. Match Winner, Over/Under Goals)."""

    id: int | str | None = None
    name: str | None = None
    values: list[ApiFootballOddsValue] | None = None


class ApiFootballOdds(BaseModel):
    """Odds response for GET /odds and GET /odds/live.

    Each item in response[] (pre-match) or odds[] (live) has bookmaker + bets.
    Live items include fixture_id.
    """

    fixture_id: int | None = None
    bookmaker: ApiFootballOddsBookmaker | None = None
    bets: list[ApiFootballOddsBet] | None = None


class ApiFootballTeam(BaseModel):
    """Team from API-Football."""

    id: int | None = None
    name: str | None = None
    logo: str | None = None
    code: str | None = None
    country: str | None = None


class ApiFootballLeague(BaseModel):
    """League from API-Football."""

    id: int | None = None
    name: str | None = None
    country: str | None = None
    logo: str | None = None
    type: str | None = None
    season: int | None = None


class ApiFootballScore(BaseModel):
    """Score in a fixture."""

    home: int | None = None
    away: int | None = None


class ApiFootballVenue(BaseModel):
    """Venue/stadium from API-Football fixture."""

    id: int | None = None
    name: str | None = None
    city: str | None = None


class ApiFootballFixtureStatus(BaseModel):
    """Fixture status from API-Football."""

    long: str | None = None
    short: str | None = None
    elapsed: int | None = None


class ApiFootballPeriods(BaseModel):
    """Fixture period timestamps (first/second half kickoff)."""

    first: int | None = None
    second: int | None = None


class ApiFootballTeamWithWinner(ApiFootballTeam):
    """Team with winner flag (home/away in fixture)."""

    winner: bool | None = None


class ApiFootballScoreFull(BaseModel):
    """Full score breakdown (halftime, fulltime, extratime, penalty)."""

    halftime: ApiFootballScore | None = None
    fulltime: ApiFootballScore | None = None
    extratime: ApiFootballScore | None = None
    penalty: ApiFootballScore | None = None


class ApiFootballFixture(BaseModel):
    """Fixture from API-Football."""

    id: int | None = None
    referee: str | None = None
    timezone: str | None = None
    date: str | None = None
    timestamp: int | None = None
    venue: ApiFootballVenue | dict[str, object] | None = None
    status: ApiFootballFixtureStatus | dict[str, object] | None = None
    periods: ApiFootballPeriods | None = None
    league: ApiFootballLeague | None = None
    teams: dict[str, ApiFootballTeamWithWinner] | None = None
    goals: dict[str, int] | None = None
    score: ApiFootballScoreFull | dict[str, object] | None = None


class ApiFootballEventTime(BaseModel):
    """Event timing (elapsed, extra time)."""

    elapsed: int | None = None
    extra: int | None = None


class ApiFootballEvent(BaseModel):
    """Match event (goal, card, substitution)."""

    time: ApiFootballEventTime | dict[str, object] | None = None
    team: ApiFootballTeam | None = None
    player: dict[str, object] | None = None
    assist: dict[str, object] | None = None
    type: str | None = None
    detail: str | None = None
    comments: str | None = None


class ApiFootballLineupPlayer(BaseModel):
    """Player in lineup (startXI or substitute)."""

    id: int | None = None
    name: str | None = None
    number: int | None = None
    pos: str | None = None
    grid: str | None = None


class ApiFootballLineup(BaseModel):
    """Lineup (formation, players) for a fixture.

    startXI: starting eleven; substitutes: bench.
    """

    team: ApiFootballTeam | None = None
    coach: dict[str, object] | None = None
    start_xi: list[dict[str, object]] | None = Field(None, alias="startXI")
    substitutes: list[dict[str, object]] | None = None


class ApiFootballStat(BaseModel):
    """Statistic for a fixture."""

    type: str | None = None
    value: int | float | str | None = None


class ApiFootballFixtureStatistics(BaseModel):
    """Team statistics for a fixture (shots, corners, possession, etc.)."""

    team: ApiFootballTeam | None = None
    statistics: list[ApiFootballStat] | None = None


class ApiFootballPlayerStat(BaseModel):
    """Player statistic in a fixture."""

    player: dict[str, object] | None = None
    team: ApiFootballTeam | None = None
    statistics: list[ApiFootballStat] | None = None


class ApiFootballInjury(BaseModel):
    """Injury record from API-Football."""

    fixture: dict[str, object] | None = None
    team: ApiFootballTeam | None = None
    player: dict[str, object] | None = None


class ApiFootballStanding(BaseModel):
    """Standing (table position) in a league."""

    rank: int | None = None
    team: ApiFootballTeam | None = None
    points: int | None = None
    goals_diff: int | None = Field(None, alias="goalsDiff")
    group: str | None = None
    form: str | None = None
    status: str | None = None
    description: str | None = None
    all: dict[str, int] | None = None
    home: dict[str, int] | None = None
    away: dict[str, int] | None = None


class ApiFootballError(BaseModel):
    """API-Football error response."""

    error: str | None = None
    message: str | None = None
    code: int | None = None

    @classmethod
    def classify(cls, code: int | None = None, error: str | None = None) -> ErrorAction:
        """Map API-Football error to retry action."""
        if code == 429 or (error and "rate" in (error or "").lower()):
            return ErrorAction.RETRY_WITH_BACKOFF
        if code is not None and code >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        if code == 401 or (error and "unauthorized" in (error or "").lower()):
            return ErrorAction.FAIL_HARD
        return ErrorAction.FAIL_HARD
