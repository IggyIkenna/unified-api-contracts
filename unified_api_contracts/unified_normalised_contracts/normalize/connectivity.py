"""WebSocket lifecycle normalizers — connect, disconnect, ping/pong per venue."""

from __future__ import annotations

from datetime import UTC, datetime

from ..domain import CanonicalWebSocketLifecycle, WebSocketEvent


def normalize_ws_connect(
    venue: str,
    channel: str = "",
    timestamp: datetime | None = None,
) -> CanonicalWebSocketLifecycle:
    """Generic connect event (used when WS connection is established)."""
    return CanonicalWebSocketLifecycle(
        venue=venue,
        event=WebSocketEvent.CONNECT,
        timestamp=timestamp or datetime.now(UTC),
        channel=channel or None,
    )


def normalize_ws_disconnect(
    venue: str,
    code: int | None = None,
    reason: str | None = None,
    channel: str = "",
    timestamp: datetime | None = None,
) -> CanonicalWebSocketLifecycle:
    """Generic disconnect event."""
    return CanonicalWebSocketLifecycle(
        venue=venue,
        event=WebSocketEvent.DISCONNECT,
        timestamp=timestamp or datetime.now(UTC),
        channel=channel or None,
        code=code,
        reason=reason,
    )


def normalize_ws_ping(
    venue: str,
    timestamp: datetime | None = None,
    latency_ms: float | None = None,
) -> CanonicalWebSocketLifecycle:
    """Generic ping event."""
    return CanonicalWebSocketLifecycle(
        venue=venue,
        event=WebSocketEvent.PING,
        timestamp=timestamp or datetime.now(UTC),
        latency_ms=latency_ms,
    )


def normalize_ws_pong(
    venue: str,
    timestamp: datetime | None = None,
    latency_ms: float | None = None,
) -> CanonicalWebSocketLifecycle:
    """Generic pong event."""
    return CanonicalWebSocketLifecycle(
        venue=venue,
        event=WebSocketEvent.PONG,
        timestamp=timestamp or datetime.now(UTC),
        latency_ms=latency_ms,
    )


def normalize_binance_ws_subscription(
    result: str | None,
    channel: str = "",
    venue: str = "binance",
) -> CanonicalWebSocketLifecycle:
    """Normalize Binance WS subscription response.

    Binance sends {"result": null, "id": 1} on successful subscription.
    A non-null result indicates an error.
    """
    event = WebSocketEvent.SUBSCRIBE if result is None else WebSocketEvent.ERROR
    return CanonicalWebSocketLifecycle(
        venue=venue,
        event=event,
        timestamp=datetime.now(UTC),
        channel=channel or None,
        reason=result,
    )


def normalize_bybit_ws_subscription(
    success: bool,
    topic: str = "",
    venue: str = "bybit",
) -> CanonicalWebSocketLifecycle:
    """Normalize Bybit WS subscription response.

    Bybit sends {"op": "subscribe", "success": true, "conn_id": "..."}.
    """
    return CanonicalWebSocketLifecycle(
        venue=venue,
        event=WebSocketEvent.SUBSCRIBE if success else WebSocketEvent.ERROR,
        timestamp=datetime.now(UTC),
        channel=topic or None,
    )


def normalize_okx_ws_subscription(
    event_str: str,
    channel: str = "",
    venue: str = "okx",
) -> CanonicalWebSocketLifecycle:
    """Normalize OKX WS subscription response.

    OKX sends {"event": "subscribe", "arg": {"channel": "..."}} or "unsubscribe".
    """
    if event_str == "subscribe":
        evt = WebSocketEvent.SUBSCRIBE
    elif event_str == "unsubscribe":
        evt = WebSocketEvent.UNSUBSCRIBE
    else:
        evt = WebSocketEvent.ERROR
    return CanonicalWebSocketLifecycle(
        venue=venue,
        event=evt,
        timestamp=datetime.now(UTC),
        channel=channel or None,
    )


def normalize_deribit_ws_heartbeat(
    method: str,
    venue: str = "deribit",
) -> CanonicalWebSocketLifecycle:
    """Normalize Deribit WS heartbeat event.

    Deribit sends heartbeat with method=heartbeat or test_request.
    """
    evt = WebSocketEvent.PING if method == "heartbeat" else WebSocketEvent.PONG
    return CanonicalWebSocketLifecycle(
        venue=venue,
        event=evt,
        timestamp=datetime.now(UTC),
    )


def normalize_coinbase_ws_subscription(
    type_str: str,
    channel: str = "",
    venue: str = "coinbase",
) -> CanonicalWebSocketLifecycle:
    """Normalize Coinbase Advanced Trade WS subscription response.

    Coinbase sends {"type": "subscriptions", "channels": [...]} on subscribe.
    type_str is the value of the "type" field from the response.
    """
    if type_str == "subscriptions":
        evt = WebSocketEvent.SUBSCRIBE
    elif type_str == "error":
        evt = WebSocketEvent.ERROR
    else:
        evt = WebSocketEvent.SUBSCRIBE
    return CanonicalWebSocketLifecycle(
        venue=venue,
        event=evt,
        timestamp=datetime.now(UTC),
        channel=channel or None,
    )


def normalize_hyperliquid_ws_subscription(
    status: str,
    channel: str = "",
    venue: str = "hyperliquid",
) -> CanonicalWebSocketLifecycle:
    """Normalize Hyperliquid WS subscription response.

    Hyperliquid sends {"channel": "subscriptionResponse", "data": {"method": "subscribe", ...}}.
    status is "subscribed" on success.
    """
    evt = WebSocketEvent.SUBSCRIBE if status == "subscribed" else WebSocketEvent.ERROR
    return CanonicalWebSocketLifecycle(
        venue=venue,
        event=evt,
        timestamp=datetime.now(UTC),
        channel=channel or None,
    )


def normalize_tardis_ws_subscription(
    subscribed: bool,
    channel: str = "",
    venue: str = "tardis",
) -> CanonicalWebSocketLifecycle:
    """Normalize Tardis replay WS subscription acknowledgement."""
    return CanonicalWebSocketLifecycle(
        venue=venue,
        event=WebSocketEvent.SUBSCRIBE if subscribed else WebSocketEvent.ERROR,
        timestamp=datetime.now(UTC),
        channel=channel or None,
    )


def normalize_aster_ws_subscription(
    method: str,
    channel: str = "",
    venue: str = "aster",
) -> CanonicalWebSocketLifecycle:
    """Normalize Aster WS subscription request/response (Binance Futures-compatible).

    method: "SUBSCRIBE" | "UNSUBSCRIBE" | "LIST_SUBSCRIPTIONS".
    """
    if method.upper() == "SUBSCRIBE":
        evt = WebSocketEvent.SUBSCRIBE
    elif method.upper() == "UNSUBSCRIBE":
        evt = WebSocketEvent.UNSUBSCRIBE
    else:
        evt = WebSocketEvent.SUBSCRIBE
    return CanonicalWebSocketLifecycle(
        venue=venue,
        event=evt,
        timestamp=datetime.now(UTC),
        channel=channel or None,
    )


def normalize_aster_ws_close(
    code: int,
    reason: str | None = None,
    venue: str = "aster",
) -> CanonicalWebSocketLifecycle:
    """Normalize Aster WebSocket close frame."""
    return normalize_ws_disconnect(venue=venue, code=code, reason=reason)


def normalize_ibkr_ws_close(
    code: int,
    reason: str | None = None,
    venue: str = "ibkr",
) -> CanonicalWebSocketLifecycle:
    """Normalize IBKR WebSocket close frame."""
    return normalize_ws_disconnect(venue=venue, code=code, reason=reason)


def normalize_upbit_ws_close(
    code: int,
    reason: str | None = None,
    venue: str = "upbit",
) -> CanonicalWebSocketLifecycle:
    """Normalize Upbit WebSocket close frame."""
    return normalize_ws_disconnect(venue=venue, code=code, reason=reason)


def normalize_kalshi_ws_lifecycle(
    action: str,
    market_ticker: str = "",
    venue: str = "kalshi",
) -> CanonicalWebSocketLifecycle:
    """Normalize Kalshi WebSocket market lifecycle event (open/close/settle)."""
    if action in ("opened",):
        evt = WebSocketEvent.CONNECT
    elif action in ("closed", "settled"):
        evt = WebSocketEvent.DISCONNECT
    else:
        evt = WebSocketEvent.SUBSCRIBE
    return CanonicalWebSocketLifecycle(
        venue=venue,
        event=evt,
        timestamp=datetime.now(UTC),
        channel=market_ticker or None,
    )


def normalize_versifi_ws_message(
    op: str,
    channel: str = "",
    venue: str = "versifi",
) -> CanonicalWebSocketLifecycle:
    """Normalize VersiFi WebSocket envelope op field.

    op: "auth" | "subscribe" | "ping" | "execution_report".
    """
    if op == "subscribe":
        evt = WebSocketEvent.SUBSCRIBE
    elif op == "ping":
        evt = WebSocketEvent.PING
    elif op == "auth":
        evt = WebSocketEvent.CONNECT
    else:
        evt = WebSocketEvent.SUBSCRIBE
    return CanonicalWebSocketLifecycle(
        venue=venue,
        event=evt,
        timestamp=datetime.now(UTC),
        channel=channel or None,
    )


__all__ = [
    "normalize_aster_ws_close",
    "normalize_aster_ws_subscription",
    "normalize_binance_ws_subscription",
    "normalize_bybit_ws_subscription",
    "normalize_coinbase_ws_subscription",
    "normalize_deribit_ws_heartbeat",
    "normalize_hyperliquid_ws_subscription",
    "normalize_ibkr_ws_close",
    "normalize_kalshi_ws_lifecycle",
    "normalize_okx_ws_subscription",
    "normalize_tardis_ws_subscription",
    "normalize_upbit_ws_close",
    "normalize_versifi_ws_message",
    "normalize_ws_connect",
    "normalize_ws_disconnect",
    "normalize_ws_ping",
    "normalize_ws_pong",
]
