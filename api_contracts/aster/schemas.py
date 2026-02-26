"""Pydantic schemas for Aster adapter. Full surface: market data, order/position, errors, WebSocket."""

from pydantic import BaseModel

from api_contracts.shared import ErrorAction


class AsterMarket(BaseModel):
    """Aster market / perps instrument."""

    market_id: str | None = None
    symbol: str | None = None
    base_asset: str | None = None
    quote_asset: str | None = None
    info: dict | None = None


class AsterOrderBook(BaseModel):
    """Order book snapshot."""

    market_id: str | None = None
    bids: list[list[str | float]] | None = None
    asks: list[list[str | float]] | None = None
    timestamp: int | None = None
    info: dict | None = None


class AsterOrder(BaseModel):
    """Order (submit / status)."""

    order_id: str | None = None
    market_id: str | None = None
    side: str | None = None
    size: str | None = None
    price: str | None = None
    status: str | None = None
    filled_size: str | None = None
    info: dict | None = None


class AsterPosition(BaseModel):
    """Position."""

    market_id: str | None = None
    side: str | None = None
    size: str | None = None
    entry_price: str | None = None
    unrealized_pnl: str | None = None
    info: dict | None = None


class AsterError(BaseModel):
    """Aster API/on-chain error."""

    code: int | str | None = None
    message: str | None = None

    @classmethod
    def classify(cls, code: int) -> ErrorAction:
        """Map Aster error code to retry action (Binance Futures-compatible API).

        Ref: https://github.com/asterdex/api-docs/blob/master/aster-finance-api.md#error-codes
        """
        # 429 = rate limit; 503 = request accepted but timeout (execution unknown — query REST)
        retry_codes = {-1000, -1001, -1003, -1006, -1007, -1008, 429, 503}
        reconnect_codes = {418}  # IP banned — use Retry-After
        if code in retry_codes:
            return ErrorAction.RETRY_WITH_BACKOFF
        if code in reconnect_codes:
            return ErrorAction.RETRY_WITH_BACKOFF  # wait Retry-After
        return ErrorAction.FAIL_HARD


class AsterWebSocketSubscribe(BaseModel):
    """Aster WebSocket subscription request (Binance Futures-compatible format).

    WS: wss://fstream.asterdex.com
    Max 200 streams per connection. Max 10 messages/sec.
    """

    method: str  # "SUBSCRIBE" or "UNSUBSCRIBE" or "LIST_SUBSCRIPTIONS"
    params: list[str]  # e.g. ["btcusdt@aggTrade", "btcusdt@depth"]
    id: int  # request tracking id


class AsterListenKeyCreate(BaseModel):
    """Aster listen key response (POST /fapi/v1/listenKey for user data stream).

    Valid 60 minutes. Extend via PUT. Connection max 24 hours.
    """

    listenKey: str
