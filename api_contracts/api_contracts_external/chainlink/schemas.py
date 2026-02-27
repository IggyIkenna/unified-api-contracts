"""Pydantic schemas for Chainlink Data Streams SSE API.

Ref: https://docs.chain.link/data-streams/reference/data-streams-api
SSE/WebSocket: feedId, observationsTimestamp, price, bid, ask, validFromTimestamp.
"""

from pydantic import BaseModel, Field

from api_contracts.shared import ErrorAction


class ChainlinkDataStreamReport(BaseModel):
    """Report from Chainlink Data Streams API (SSE/WebSocket).

    Price and bid/ask use 18 decimal places (int192).
    """

    feed_id: str | None = Field(None, alias="feedId")  # bytes32
    observations_timestamp: int | None = Field(None, alias="observationsTimestamp")  # seconds
    valid_from_timestamp: int | None = Field(None, alias="validFromTimestamp")  # seconds
    price: int | None = None  # DON consensus median, 18 decimals
    bid: int | None = None  # simulated buy impact at X% liquidity
    ask: int | None = None  # simulated sell impact at X% liquidity

    model_config = {"populate_by_name": True}


class ChainlinkSseEvent(BaseModel):
    """SSE event envelope for Chainlink Data Streams."""

    event: str | None = None
    data: str | dict | None = None  # JSON string or parsed dict


class ChainlinkError(BaseModel):
    """Chainlink Data Streams API error."""

    error: str | None = None
    message: str | None = None
    code: int | None = None

    @classmethod
    def classify(cls, code: int | None = None, error: str | None = None) -> ErrorAction:
        """Map Chainlink error to retry action."""
        if code == 429 or (error and "rate" in (error or "").lower()):
            return ErrorAction.RETRY_WITH_BACKOFF
        if code is not None and code >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        return ErrorAction.FAIL_HARD
