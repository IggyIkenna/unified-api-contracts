"""Hyperliquid HTTP + S3/stats: market data, order/position, errors, WebSocket."""

from pydantic import BaseModel

from api_contracts.shared import ErrorAction


class HyperliquidMeta(BaseModel):
    """Universe/meta (instruments)."""

    universe: list[dict] | None = None
    info: dict | None = None


class HyperliquidTicker(BaseModel):
    """Ticker / mid / mark from HTTP API."""

    coin: str | None = None
    markPx: str | None = None
    midPx: str | None = None
    prevDayPx: str | None = None
    dayNtlVlm: str | None = None
    funding: str | None = None
    openInterest: str | None = None
    info: dict | None = None


class HyperliquidOrder(BaseModel):
    """Order (REST or WebSocket)."""

    coin: str | None = None
    side: str | None = None
    limitPx: str | None = None
    sz: str | None = None
    orderType: dict | None = None
    oid: int | None = None
    timestamp: int | None = None
    status: str | None = None
    info: dict | None = None


class HyperliquidPosition(BaseModel):
    """Position from user state / fills."""

    coin: str | None = None
    entryPx: str | None = None
    positionValue: str | None = None
    unrealizedPnl: str | None = None
    szi: str | None = None  # size (signed)
    leverage: dict | None = None
    info: dict | None = None


class HyperliquidError(BaseModel):
    """Hyperliquid API error."""

    response: dict | None = None
    message: str | None = None

    @classmethod
    def classify(cls, http_status: int | None = None, message: str | None = None) -> ErrorAction:
        """Map Hyperliquid error to retry action.

        Hyperliquid uses HTTP status codes primarily; no structured error codes.
        """
        if http_status is not None and http_status >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        return ErrorAction.FAIL_HARD


# --- S3 / stats bucket (e.g. daily stats) ---
class HyperliquidStatsRow(BaseModel):
    """Single row from stats bucket (e.g. daily volume)."""

    coin: str | None = None
    volume: str | float | None = None
    openInterest: str | float | None = None
    info: dict | None = None


class HyperliquidWebSocketSubscribe(BaseModel):
    """Hyperliquid WebSocket subscription request.

    WS: wss://api.hyperliquid.xyz/ws
    Auth: Ethereum wallet address (user field in private subscriptions)
    """

    method: str  # "subscribe" or "unsubscribe"
    subscription: dict[str, object]  # {"type": "trades", "coin": "BTC"} or {"type": "orderUpdates", "user": "0x..."}


class HyperliquidWebSocketPost(BaseModel):
    """Hyperliquid WebSocket POST request (for sending orders via WS)."""

    method: str = "post"
    id: int  # request tracking id
    request: dict[str, object]  # {"type": "order", ...} — same format as REST /exchange POST body
