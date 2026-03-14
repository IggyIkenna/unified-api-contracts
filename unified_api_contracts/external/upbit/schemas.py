"""Upbit: market data, order/position feed, errors, WebSocket, FIX, corner cases."""

__api_version__ = "v1"  # matches provider_api_versions.yaml

from pydantic import BaseModel

from unified_api_contracts.canonical.crosscutting.errors import ErrorAction


class UpbitMarket(BaseModel):
    """Upbit market."""

    market: str | None = None
    korean_name: str | None = None
    english_name: str | None = None
    info: dict[str, object] | None = None


class UpbitTicker(BaseModel):
    """Upbit ticker."""

    market: str | None = None
    trade_price: float | None = None
    bid_price: float | None = None
    ask_price: float | None = None
    acc_trade_volume_24h: float | None = None
    info: dict[str, object] | None = None


class UpbitTrade(BaseModel):
    """Upbit public trade (REST: GET /v1/trades/ticks, WS: trade)."""

    market: str | None = None
    trade_price: float | None = None
    trade_volume: float | None = None
    sequential_id: int | None = None
    timestamp: int | None = None  # ms
    ask_bid: str | None = None  # BID=buy, ASK=sell


class UpbitOrderBookUnit(BaseModel):
    """Single level in Upbit order book (orderbook_units item)."""

    ask_price: float | None = None
    bid_price: float | None = None
    ask_size: float | None = None
    bid_size: float | None = None


class UpbitOrderBook(BaseModel):
    """Upbit order book (REST: GET /v1/orderbook)."""

    market: str | None = None
    timestamp: int | None = None
    total_ask_size: float | None = None
    total_bid_size: float | None = None
    orderbook_units: list[UpbitOrderBookUnit] = []


class UpbitOrder(BaseModel):
    """Upbit order."""

    uuid: str | None = None
    side: str | None = None
    ord_type: str | None = None
    price: float | None = None
    state: str | None = None
    volume: str | None = None
    executed_volume: str | None = None
    info: dict[str, object] | None = None


class UpbitBalance(BaseModel):
    """Upbit balance."""

    currency: str | None = None
    balance: float | None = None
    locked: float | None = None
    info: dict[str, object] | None = None


class UpbitWebSocketClose(BaseModel):
    """Upbit WebSocket close frame (RFC 6455).

    Codes: 1000=normal, 1006=abnormal, 1008=policy.
    """

    code: int
    reason: str | None = None


class UpbitError(BaseModel):
    """Upbit API error."""

    error: dict[str, object] | None = None
    message: str | None = None

    @classmethod
    def classify(cls, error_key: str | None = None, http_status: int | None = None) -> ErrorAction:
        """Map Upbit error to retry action.

        error_key: key from error dict[str, object] (e.g. 'invalid_access_key', 'too_many_requests').
        """
        if http_status == 429:
            return ErrorAction.RETRY
        if error_key == "too_many_requests":
            return ErrorAction.RETRY
        if error_key in ("invalid_access_key", "invalid_query_payload"):
            return ErrorAction.FAIL
        return ErrorAction.FAIL


# --- CEX Order Submit / Ack / Cancel ---


class UpbitOrderSubmitRequest(BaseModel):
    """Upbit order submit request (POST /v1/orders).

    ord_type: limit, price (market buy), market (market sell), best (best bid/ask).
    side: bid, ask. Market format: KRW-BTC.
    """

    market: str  # e.g. KRW-BTC, BTC-ETH
    side: str  # bid, ask
    ord_type: str  # limit, price, market, best
    volume: str | None = None  # for limit/best ask, market sell
    price: str | None = None  # for limit, price (market buy total), best (market buy total)
    time_in_force: str | None = None  # ioc, fok, post_only
    smp_type: str | None = None  # cancel_maker, cancel_taker, reduce
    identifier: str | None = None  # client order id


class UpbitOrderSubmitResponse(BaseModel):
    """Upbit order submit response."""

    uuid: str | None = None
    side: str | None = None
    ord_type: str | None = None
    price: str | None = None
    state: str | None = None
    volume: str | None = None
    executed_volume: str | None = None
    remaining_volume: str | None = None
    reserved_fee: str | None = None
    remaining_fee: str | None = None
    locked: str | None = None
    created_at: str | None = None
    identifier: str | None = None


class UpbitOrderCancelRequest(BaseModel):
    """Upbit order cancel request (DELETE /v1/order)."""

    uuid: str | None = None  # order uuid
    identifier: str | None = None  # or client identifier


class UpbitOrderCancelResponse(BaseModel):
    """Upbit order cancel response."""

    uuid: str | None = None
    side: str | None = None
    ord_type: str | None = None
    state: str | None = None  # cancel, cancelled


# --- Position, Margin (Upbit is spot-only; no positions/margin) ---


class UpbitBalanceQueryResponse(BaseModel):
    """Upbit balance query (GET /v1/accounts). Spot-only; no margin/positions."""

    currency: str | None = None
    balance: str | None = None
    locked: str | None = None
    avg_buy_price: str | None = None
    avg_buy_price_modified: bool | None = None
    unit_currency: str | None = None


# --- Withdrawal ---


class UpbitWithdrawalRequest(BaseModel):
    """Upbit withdrawal request (POST /v1/withdraws/coin).

    Address must be pre-registered in Upbit Settings > Withdrawal Wallet Management.
    """

    currency: str
    net_type: str  # withdrawal network
    amount: str
    address: str
    secondary_address: str | None = None  # memo/destination tag
    transaction_type: str | None = None  # default, internal (lightning)


class UpbitWithdrawalResponse(BaseModel):
    """Upbit withdrawal response."""

    type: str | None = None  # withdraw
    uuid: str | None = None
    currency: str | None = None
    net_type: str | None = None
    txid: str | None = None
    state: str | None = None
    created_at: str | None = None
    done_at: str | None = None
    amount: str | None = None
    fee: str | None = None
    transaction_type: str | None = None


# --- Institutional: Fee Rate, Deposit, Withdrawal lifecycle ---


class UpbitFeeRate(BaseModel):
    """Upbit fee rate (maker/taker). Spot: 0.25% flat for both."""

    maker_fee_rate: float | None = None
    taker_fee_rate: float | None = None
    currency: str | None = None
    market: str | None = None
    info: dict[str, object] | None = None


class UpbitDeposit(BaseModel):
    """Upbit deposit record (GET /v1/deposits). Deposit lifecycle status."""

    uuid: str | None = None
    currency: str | None = None
    net_type: str | None = None
    txid: str | None = None
    state: str | None = None  # submitting, submitted, almost_accepted, processing, done, canceled
    created_at: str | None = None
    done_at: str | None = None
    amount: str | None = None
    fee: str | None = None
    transaction_type: str | None = None
    info: dict[str, object] | None = None


class UpbitWithdrawal(BaseModel):
    """Upbit withdrawal record (GET /v1/withdraws). Withdrawal lifecycle status."""

    uuid: str | None = None
    currency: str | None = None
    net_type: str | None = None
    txid: str | None = None
    state: str | None = None  # submitting, submitted, almost_accepted, processing, done, canceled
    created_at: str | None = None
    done_at: str | None = None
    amount: str | None = None
    fee: str | None = None
    transaction_type: str | None = None
    info: dict[str, object] | None = None
