"""Matchbook Exchange API: authentication, events, markets, runners, prices, offers, balances.

Ref: https://www.matchbook.com/api-documentation
"""

from __future__ import annotations

__api_version__ = "v1"  # matches provider_api_versions.yaml


from pydantic import BaseModel, Field


class MatchbookAuthResponse(BaseModel, frozen=True):
    """Matchbook session authentication response."""

    session_token: str = Field("", alias="session-token")

    model_config = {"populate_by_name": True}


class MatchbookErrorResponse(BaseModel, frozen=True):
    """Matchbook API error response."""

    message: str = ""
    code: str = ""


class MatchbookBackPrice(BaseModel, frozen=True):
    odds: float = 0.0


class MatchbookPrices(BaseModel, frozen=True):
    back: list[MatchbookBackPrice] = []


class MatchbookRunner(BaseModel, frozen=True):
    id: int | str = 0
    name: str = ""
    type: str = ""
    prices: MatchbookPrices = MatchbookPrices()


class MatchbookMarket(BaseModel, frozen=True):
    id: int | str = 0
    type: str = ""
    marketType: str | None = None  # API field name alias for type
    handicap: float = 0.0
    runners: list[MatchbookRunner] = []
    status: str | None = None
    eventId: int | str | None = None


class MatchbookEvent(BaseModel, frozen=True):
    id: int | str = 0
    name: str = ""


class MatchbookEventsResponse(BaseModel, frozen=True):
    events: list[MatchbookEvent] = []


class MatchbookMarketsResponse(BaseModel, frozen=True):
    markets: list[MatchbookMarket] = []


class MatchbookOfferResponse(BaseModel, frozen=True):
    id: str = ""


class MatchbookBalanceInfo(BaseModel, frozen=True):
    available: str = "0"


class MatchbookAccountResponse(BaseModel, frozen=True):
    balance: MatchbookBalanceInfo = MatchbookBalanceInfo()


class MatchbookOdds(BaseModel, frozen=True):
    """Matchbook odds — runner-level back/lay prices."""

    runner_id: int | str | None = None
    back_odds: list[dict[str, object]] = []
    lay_odds: list[dict[str, object]] = []
