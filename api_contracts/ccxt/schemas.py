"""CCXT responses: fetch_markets, fetch_ticker, order_book, order, my_trades, balance, positions, errors."""

from typing import Literal

from pydantic import BaseModel, Field

# --- Order status (CCXT unified) ---
CcxtOrderStatus = Literal["open", "closed", "canceled", "cancelled", "expired", "rejected"]


# --- Fee (nested in trade) ---
class CcxtFee(BaseModel):
    """Fee object in CCXT trade."""

    cost: float | None = None
    currency: str | None = None


# --- Order (fetch_order response) ---
class CcxtOrder(BaseModel):
    """CCXT unified order structure."""

    id: str = Field(..., description="Exchange order ID")
    clientOrderId: str | None = None
    timestamp: int | None = Field(None, description="Milliseconds since epoch")
    datetime: str | None = None
    symbol: str | None = None
    type: str | None = None  # market, limit, etc.
    side: str | None = None  # buy, sell
    price: float | None = None
    amount: float | None = None
    filled: float | None = None
    remaining: float | None = None
    average: float | None = None
    status: str | None = None  # open, closed, canceled, etc.
    timeInForce: str | None = None
    info: dict | None = None


# --- Trade (fetch_my_trades item) ---
class CcxtTrade(BaseModel):
    """CCXT unified trade (fill) structure."""

    id: str | None = None
    order: str | None = Field(None, description="Order ID this fill belongs to")
    timestamp: int | None = None
    datetime: str | None = None
    symbol: str | None = None
    side: str | None = None
    price: float | None = None
    amount: float | None = None
    cost: float | None = None
    fee: CcxtFee | dict | None = None
    info: dict | None = None


# --- Balance (per-currency in fetch_balance) ---
class CcxtBalance(BaseModel):
    """Per-currency balance in CCXT fetch_balance."""

    free: float | None = None
    used: float | None = None
    total: float | None = None


# --- Balance response (fetch_balance) ---
# Top-level keys: info, free, used, total, plus one key per currency (e.g. USDT, BTC)
# We model the per-currency part as dict[str, CcxtBalance]; 'info' can be list or dict (e.g. Binance futures)
class CcxtBalanceResponse(BaseModel):
    """CCXT fetch_balance response. Extra currency keys allowed via model_config."""

    model_config = {"extra": "allow"}  # CCXT adds dynamic currency keys

    info: list | dict | None = None
    free: dict | None = None
    used: dict | None = None
    total: dict | None = None


# --- Position (fetch_positions item) ---
class CcxtPosition(BaseModel):
    """CCXT unified position structure (futures)."""

    symbol: str | None = None
    side: str | None = None  # long, short, both
    contracts: float | None = None
    contractSize: float | None = None
    entryPrice: float | None = None
    markPrice: float | None = None
    lastPrice: float | None = None
    unrealizedPnl: float | None = None
    leverage: float | int | None = None
    info: dict | None = None


# --- Market (fetch_markets item) ---
class CcxtMarket(BaseModel):
    """CCXT market structure."""

    id: str | None = None
    symbol: str | None = None
    base: str | None = None
    quote: str | None = None
    active: bool | None = None
    info: dict | None = None


# --- Ticker (fetch_ticker) ---
class CcxtTicker(BaseModel):
    """CCXT ticker structure."""

    symbol: str | None = None
    last: float | None = None
    bid: float | None = None
    ask: float | None = None
    high: float | None = None
    low: float | None = None
    volume: float | None = None
    info: dict | None = None


# --- Order book (fetch_order_book) ---
class CcxtOrderBook(BaseModel):
    """CCXT order book structure."""

    symbol: str | None = None
    bids: list[list[float]] = Field(default_factory=list)  # [[price, size], ...]
    asks: list[list[float]] = Field(default_factory=list)
    timestamp: int | None = None
    datetime: str | None = None
    nonce: int | None = None
    info: dict | None = None


# --- Error (CCXT exception payload) ---
class CcxtErrorPayload(BaseModel):
    """Typical CCXT error response shape."""

    code: str | None = None
    message: str | None = None
    info: dict | None = None
