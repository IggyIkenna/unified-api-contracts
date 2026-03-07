"""VersiFi external API schemas (REST + WebSocket).

Exchanges supported: BINANCE_SPOT, BINANCE_FUTURES, OKX_SPOT, OKX_FUTURES, BINANCE_UNIFIED.

Basic order types: MARKET, LIMIT, STOP_LOSS, STOP_LOSS_LIMIT, TAKE_PROFIT, TAKE_PROFIT_LIMIT.
Algo order types: TWAP (Time-Weighted Average Price), VWAP (Volume-Weighted Average Price),
                  IS (Implementation Shortfall).
Pair order types: BASIS (basis/spread trading between spot and futures legs).

Auth headers: X-VERSIFI-API-KEY, X-VERSIFI-API-SIGN (HMAC-SHA256 of request body/query).
WebSocket: wss://.../v1/wss — topics: execution_report, analytics (not yet implemented).
Timestamps: Unix epoch microseconds for start_time; Unix epoch seconds for order timestamps.
Cancellation: DELETE /v2/orders/{id} returns HTTP 204 + WebSocket confirmation.
"""

from __future__ import annotations

__api_version__ = "v1"  # matches provider_api_versions.yaml


import json
from typing import cast

from pydantic import BaseModel

from ..binance.order_schemas import BinanceError
from ..okx.schemas import OKXError

# VersiFi passes the raw exchange error JSON as a string in reject_reason.
# Binance errors: {"code": int, "msg": str}  (negative int codes e.g. -1100)
# OKX errors:    {"code": str, "msg": str}   (string codes e.g. "51002")
# Discriminator: if code parses as int → BinanceError, else → OKXError.
VersiFiRejectReason = BinanceError | OKXError


def parse_reject_reason(raw: str | None) -> VersiFiRejectReason | None:
    """Parse a VersiFi reject_reason string into the typed exchange error.

    Returns BinanceError if the underlying exchange code is an integer
    (Binance/BINANCE_UNIFIED), OKXError if it is a string (OKX_SPOT/FUTURES),
    or None if raw is absent or not valid JSON.
    """
    if not raw:
        return None
    try:
        parsed: object = cast(object, json.loads(raw))
    except (ValueError, TypeError):
        return None
    if not isinstance(parsed, dict):
        return None
    # Extract only the two fields we need, narrowing from dict[Unknown, Unknown]
    items: list[tuple[object, object]] = list(parsed.items())  # type: ignore[union-attr]
    field_map: dict[str, object] = {str(k): v for k, v in items if isinstance(k, str)}
    code: object = field_map.get("code")
    if isinstance(code, int) or (isinstance(code, str) and code.lstrip("-").isdigit()):
        return BinanceError.model_validate(field_map)
    return OKXError.model_validate(field_map)


class VersiFiBasicOrderRequest(BaseModel):
    """POST /v2/orders/basic/ request body.

    Used for non-algorithmic orders: MARKET, LIMIT, STOP_LOSS, STOP_LOSS_LIMIT,
    TAKE_PROFIT, TAKE_PROFIT_LIMIT. Also accepts TWAP/VWAP/IS but without algo params.
    Symbol format: {Asset}/{Currency} e.g. BTC/USDT, ETH/USDT.
    start_time: UTC epoch microseconds (algo start, optional for non-algo orders).
    tif defaults to GTC if not provided.
    """

    client_order_id: int | None = None
    exchange: str  # BINANCE_SPOT | BINANCE_FUTURES | OKX_SPOT | OKX_FUTURES | BINANCE_UNIFIED
    order_type: str  # MARKET | LIMIT | STOP_LOSS | STOP_LOSS_LIMIT | TAKE_PROFIT | TAKE_PROFIT_LIMIT | TWAP | VWAP | IS
    price: str | None = None  # Required for LIMIT orders only
    quantity: str
    quote_order_quantity: str | None = None
    side: str  # BUY | SELL
    start_time: int | None = None  # UTC epoch microseconds (for algo start)
    stop_price: str | None = None  # Required for STOP_LOSS, STOP_LOSS_LIMIT, TAKE_PROFIT, TAKE_PROFIT_LIMIT
    symbol: str  # Format: {Asset}/{Currency} e.g. BTC/USDT
    tif: str | None = None  # FOK | GTC | GTD | IOC | GTX | POST_ON; defaults to GTC
    trailing_delta: str | None = None  # For trailing stop orders


class VersiFiOrderResponse(BaseModel):
    """POST /v2/orders/basic/ response (HTTP 201 Created).

    Minimal creation acknowledgement — full order state delivered via WebSocket
    execution_report topic after the order is live on the exchange.
    """

    client_order_id: int | None = None
    order_id: int | None = None
    status: str | None = None


class VersiFiAlgoOrderParams(BaseModel):
    """Nested params object for algo order configuration (TWAP/VWAP/IS).

    Contains algorithm-specific parameters such as duration, volume percentage,
    and slice size. All fields are optional as parameter set varies by algo type.
    """

    duration: int | None = None  # Algorithm duration in seconds
    volume_pct: str | None = None  # Target volume participation percentage
    slice_size: str | None = None  # Size of each execution slice
    aggressiveness: str | None = None  # Controls pace/market impact balance
    max_participation_rate: str | None = None  # Maximum fraction of market volume (IS)
    urgency_level: str | None = None  # IS urgency: controls speed vs. market impact


class VersiFiAlgoOrderRequest(BaseModel):
    """POST /v2/orders/algo/ request body.

    Dedicated endpoint for algorithmic orders: TWAP, VWAP, IS.
    These use the params sub-object for algorithm-specific configuration.
    Symbol format: {Asset}/{Currency} e.g. BTC/USDT.
    """

    client_order_id: int | None = None
    exchange: str  # BINANCE_SPOT | BINANCE_FUTURES | OKX_SPOT | OKX_FUTURES | BINANCE_UNIFIED
    order_type: str  # TWAP | VWAP | IS
    params: VersiFiAlgoOrderParams | None = None
    quantity: str
    quote_order_quantity: str | None = None
    side: str  # BUY | SELL
    symbol: str  # Format: {Asset}/{Currency} e.g. BTC/USDT


class VersiFiAlgoOrderLegStatus(BaseModel):
    """Status for a single leg in an algo order creation response."""

    leg_id: int | None = None
    status: str | None = None


class VersiFiAlgoOrderResponse(BaseModel):
    """POST /v2/orders/algo/ and POST /v2/orders/pair/ response (HTTP 201 Created).

    Contains lead and secondary leg statuses for pair/algo orders with two legs.
    """

    client_order_id: int | None = None
    lead: VersiFiAlgoOrderLegStatus | None = None
    order_id: int | None = None
    secondary: VersiFiAlgoOrderLegStatus | None = None
    status: str | None = None


class VersiFiPairLegParams(BaseModel):
    """Params sub-object for pair order lead leg configuration.

    Controls spread-based entry/exit, position sizing, and legging strategy
    for the Basis Algo. spread_price_formula, entry/exit thresholds etc.
    are specified here when using BASIS order type.
    """

    entry_spread_threshold: str | None = None
    exit_spread_threshold: str | None = None
    spread_price_formula: str | None = None
    legging_strategy: str | None = None  # SYNC | ASYNC | TWAP
    max_drawdown: str | None = None
    max_slippage: str | None = None
    recalibration_frequency: int | None = None
    max_position_long: str | None = None
    max_position_short: str | None = None
    max_notional_long: str | None = None
    max_notional_short: str | None = None


class VersiFiPairOrderLeg(BaseModel):
    """Lead or secondary leg specification in a pair order request.

    style values: SYNC (both legs aggressive), ASYNC (first passive then aggressive),
    TWAP (each leg independently executed using TWAP params).
    """

    order_type: str  # BASIS for lead leg
    params: VersiFiPairLegParams | None = None
    style: str | None = None  # SYNC | ASYNC | TWAP


class VersiFiPairOrderRequest(BaseModel):
    """POST /v2/orders/pair/ request body.

    Pair/basis trading: simultaneous long spot + short futures positions.
    The lead_leg uses BASIS order_type; secondary leg mirrors the lead.
    client_order_id auto-generated if not provided.
    """

    client_order_id: int | None = None
    lead: VersiFiPairOrderLeg
    secondary: VersiFiPairOrderLeg | None = None


class VersiFiChildOrderTrade(BaseModel):
    """Individual trade/fill within a child order (GET /v2/orders/{id} response)."""

    child_order_id: int | None = None
    exchange: str | None = None
    exchange_trade_id: str | None = None
    fee: str | None = None
    leg_id: int | None = None
    order_id: int | None = None
    price: str | None = None
    quantity: str | None = None
    side: str | None = None
    symbol: str | None = None
    trade_id: int | None = None
    # WebSocket execution_report extra fields
    average_price: str | None = None
    cummulative_filled_quantity: str | None = None
    executed_price: str | None = None
    executed_quantity: str | None = None


class VersiFiChildOrder(BaseModel):
    """Child order details (exchange-level child of the parent VersiFi order)."""

    average_price: str | None = None
    child_order_id: int | None = None
    exchange: str | None = None
    exchange_order_id: str | None = None
    filled_quantity: str | None = None
    id: int | None = None
    leg_id: int | None = None
    order_id: int | None = None
    order_status: str | None = None
    order_type: str | None = None
    price: str | None = None
    quantity: str | None = None
    reject_reason: str | None = None
    side: str | None = None
    symbol: str | None = None
    trades: list[VersiFiChildOrderTrade] = []


class VersiFiAlgoOrder(BaseModel):
    """Algo order detail object (nested in GET /api/v2/orders list and GET /v2/orders/{id}).

    Covers TWAP, VWAP, IS order types.
    Child orders represent the individual exchange-level slices executed by the algorithm.
    """

    average_price: str | None = None
    child_orders: list[VersiFiChildOrder] = []
    exchange: str | None = None
    filled_quantity: str | None = None
    order_id: int | None = None
    order_params: str | None = None  # JSON-serialized algorithm parameters
    order_type: str | None = None  # TWAP | VWAP | IS
    quantity: str | None = None
    quote_order_quantity: str | None = None
    reject_reason: str | None = None
    side: str | None = None
    status: str | None = None
    symbol: str | None = None
    tif: str | None = None


class VersiFiBasicOrder(BaseModel):
    """Basic order detail object (nested in GET /api/v2/orders list and GET /v2/orders/{id}).

    Covers MARKET, LIMIT, STOP_LOSS, STOP_LOSS_LIMIT, TAKE_PROFIT, TAKE_PROFIT_LIMIT.
    price is encoded as float64 in the API but returned as string.
    """

    average_price: str | None = None
    child_orders: list[VersiFiChildOrder] = []
    exchange: str | None = None
    filled_quantity: str | None = None
    order_type: str | None = None  # MARKET | LIMIT | STOP_LOSS | STOP_LOSS_LIMIT | TAKE_PROFIT | TAKE_PROFIT_LIMIT
    price: str | None = None  # Encoded as float64
    quantity: str | None = None
    quote_order_quantity: str | None = None
    reject_reason: str | None = None
    side: str | None = None
    status: str | None = None
    stop_price: str | None = None
    symbol: str | None = None
    tif: str | None = None
    trailing_delta: str | None = None


class VersiFiPairOrderLegDetail(BaseModel):
    """Detail for a single leg of a pair order (GET /v2/orders/{id} response)."""

    child_order: VersiFiChildOrder | None = None
    exchange: str | None = None
    leg_ratio: int | None = None
    max_notional_long: str | None = None
    max_notional_short: str | None = None
    max_position_long: str | None = None
    max_position_short: str | None = None
    order_type: str | None = None
    symbol: str | None = None


class VersiFiPairOrder(BaseModel):
    """Pair order detail object (nested in GET /api/v2/orders list and GET /v2/orders/{id}).

    Lead leg = spot (long), secondary/leg = futures (short) for basis trading.
    """

    lead_leg: VersiFiPairOrderLegDetail | None = None
    order_params: str | None = None
    reject_reason: str | None = None
    secondary: VersiFiPairOrderLegDetail | None = None
    style: str | None = None  # SYNC | ASYNC | TWAP


class VersiFiOrderListItem(BaseModel):
    """Item in GET /api/v2/orders paginated list response.

    Exactly one of algo_order, basic_order, pair_order will be non-None
    depending on request_order_type.
    timestamp is a Unix epoch integer (seconds, not microseconds).
    """

    algo_order: VersiFiAlgoOrder | None = None
    basic_order: VersiFiBasicOrder | None = None
    client_api_key: str | None = None
    client_id: int | None = None
    client_order_id: int | None = None
    order_id: int | None = None
    pair_order: VersiFiPairOrder | None = None
    reject_reason: str | None = None
    request_order_type: str | None = None  # "basic" | "algo" | "pair"
    status: str | None = None
    timestamp: int | None = None  # Unix epoch seconds


class VersiFiOrderDetail(BaseModel):
    """GET /v2/orders/{id} single order response.

    order field contains the raw order details (BasicResponseV2, AlgoResponseV2,
    or PairResponseV2) serialized as a string in the API spec, but modelled here
    as the union of possible sub-objects for normalizer convenience.
    algo_order and basic_order are the parsed sub-objects.
    """

    algo_order: VersiFiAlgoOrder | None = None
    basic_order: VersiFiBasicOrder | None = None
    client_order_id: int | None = None
    order_id: int | None = None
    pair_order: VersiFiPairOrder | None = None
    reject_reason: str | None = None
    request_order_type: str | None = None  # "basic" | "algo" | "pair"
    status: str | None = None
    timestamp: int | None = None  # Unix epoch seconds


class VersiFiWebSocketMessage(BaseModel):
    """VersiFi WebSocket envelope (execution_report topic).

    All execution_report messages share this outer envelope.
    The message field has the same schema as GET /v2/orders/{id} with
    additional fill-specific fields (cummulative_filled_quantity, average_price,
    executed_price, executed_quantity) nested inside child_order.trades.
    op values: "auth", "subscribe", "ping", "execution_report".
    """

    message: VersiFiOrderDetail | None = None
    op: str | None = None  # "auth" | "subscribe" | "ping" | "execution_report"
    success: bool | None = None


__all__ = [
    "VersiFiAlgoOrder",
    "VersiFiAlgoOrderLegStatus",
    "VersiFiAlgoOrderParams",
    "VersiFiAlgoOrderRequest",
    "VersiFiAlgoOrderResponse",
    "VersiFiBasicOrder",
    "VersiFiBasicOrderRequest",
    "VersiFiChildOrder",
    "VersiFiChildOrderTrade",
    "VersiFiOrderDetail",
    "VersiFiOrderListItem",
    "VersiFiOrderResponse",
    "VersiFiPairLegParams",
    "VersiFiPairOrder",
    "VersiFiPairOrderLeg",
    "VersiFiPairOrderLegDetail",
    "VersiFiPairOrderRequest",
    "VersiFiWebSocketMessage",
]
