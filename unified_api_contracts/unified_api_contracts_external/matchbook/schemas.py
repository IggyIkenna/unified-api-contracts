"""Matchbook API response schemas."""

from pydantic import BaseModel


class MatchbookRunner(BaseModel):
    """Matchbook runner/selection."""

    id: int | None = None
    name: str | None = None
    selection_id: int | None = None


class MatchbookOdds(BaseModel):
    """Matchbook odds schema."""

    market_id: int | None = None
    runner_id: int | None = None
    runners: list[MatchbookRunner] | None = None
    back_odds: list[dict[str, object]] | None = None
    lay_odds: list[dict[str, object]] | None = None


class MatchbookMarket(BaseModel):
    """Matchbook market schema."""

    id: int | None = None
    name: str | None = None


class MatchbookEvent(BaseModel):
    """Matchbook event schema."""

    id: int | None = None
    name: str | None = None
    markets: list[MatchbookMarket] | None = None
