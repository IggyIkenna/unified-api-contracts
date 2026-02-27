"""Pydantic schemas for OpenBB Platform API.

TreasuryPrices (bid, offer, ytm) for US Treasuries via TMX/government_us providers.
Ref: OpenBB Python SDK — openbb-fixedincome
"""

from pydantic import BaseModel, Field

from api_contracts.shared import ErrorAction


class OpenBBTreasuryPrice(BaseModel):
    """Single US Treasury price from OpenBB government_us provider."""

    symbol: str | None = None
    name: str | None = None
    bid: float | None = Field(None, description="Bid price")
    ask: float | None = Field(None, description="Ask/offer price")
    last: float | None = None
    change: float | None = None
    change_percent: float | None = None
    volume: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    previous_close: float | None = None
    yield_to_maturity: float | None = Field(None, description="YTM in percent")
    date: str | None = None


class OpenBBTreasuryPricesResponse(BaseModel):
    """Response from OpenBB treasury prices endpoint."""

    results: list[OpenBBTreasuryPrice] | None = None
    provider: str | None = None
    chart: dict[str, object] | None = None
    metadata: dict | None = None


class OpenBBError(BaseModel):
    """OpenBB error response."""

    message: str | None = None
    detail: str | None = None
    status_code: int | None = None

    @classmethod
    def classify(cls, status_code: int | None = None, message: str | None = None) -> ErrorAction:
        """Map OpenBB error to retry action."""
        if status_code == 429 or (message and "rate" in (message or "").lower()):
            return ErrorAction.RETRY_WITH_BACKOFF
        if status_code is not None and status_code >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        return ErrorAction.FAIL_HARD
