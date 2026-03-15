"""VersiFi order and fill normalizers.

Converts VersiFi REST API responses to CanonicalOrder and CanonicalFill.

VersiFi algo order types and their canonical mapping:
- TWAP (Time-Weighted Average Price) -> OrderType.TWAP
- VWAP (Volume-Weighted Average Price) -> OrderType.VWAP
- IS (Implementation Shortfall) -> OrderType.LIMIT (no direct canonical equivalent)
- MARKET -> OrderType.MARKET
- LIMIT -> OrderType.LIMIT
- STOP_LOSS | STOP_LOSS_LIMIT -> OrderType.STOP
- TAKE_PROFIT | TAKE_PROFIT_LIMIT -> OrderType.STOP_LIMIT

Status mapping from VersiFi to canonical:
- NEW, OPEN, ACTIVE, PENDING_NEW, ACK -> OrderStatus.OPEN
- PARTIALLY_FILLED -> OrderStatus.PARTIALLY_FILLED
- FILLED, DONE, CLOSED -> OrderStatus.FILLED
- CANCELLED, CANCELED -> OrderStatus.CANCELLED
- REJECTED -> OrderStatus.REJECTED

Timestamp notes:
- order list timestamp: Unix epoch seconds
- start_time (algo): UTC epoch microseconds
- WebSocket fill timestamps: nested in child_order.trades

Fill extraction: VersiFi fills are nested in child_order.trades within the order
sub-object. Use normalize_versifi_trade_to_fill() for each trade record.
"""

from __future__ import annotations

from ..external.versifi.normalize import (
    _extract_algo_order_fields,
    _extract_basic_order_fields,
    _parse_decimal,
    _parse_versifi_order_type,
    _parse_versifi_side,
    _parse_versifi_status,
    _parse_versifi_tif,
    _ts_epoch_seconds_to_datetime,
    normalize_versifi_order_detail,
    normalize_versifi_order_list_item,
    normalize_versifi_order_response,
    normalize_versifi_trade_to_fill,
    resolve_versifi_reject_reason,
)

__all__ = [
    "_extract_algo_order_fields",
    "_extract_basic_order_fields",
    "_parse_decimal",
    "_parse_versifi_order_type",
    "_parse_versifi_side",
    "_parse_versifi_status",
    "_parse_versifi_tif",
    "_ts_epoch_seconds_to_datetime",
    "normalize_versifi_order_detail",
    "normalize_versifi_order_list_item",
    "normalize_versifi_order_response",
    "normalize_versifi_trade_to_fill",
    "resolve_versifi_reject_reason",
]
