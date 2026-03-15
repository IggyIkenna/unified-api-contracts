"""WebSocket lifecycle normalizers — connect, disconnect, ping/pong per venue."""

# --- Functions without external counterparts (kept inline) ---
from __future__ import annotations

from datetime import UTC, datetime

from ..canonical.domain import CanonicalWebSocketLifecycle, WebSocketEvent
from ..external.aster.normalize import (
    normalize_aster_ws_close,
    normalize_aster_ws_subscription,
)
from ..external.binance.normalize import normalize_binance_ws_subscription
from ..external.bybit.normalize import normalize_bybit_ws_subscription
from ..external.coinbase.normalize import normalize_coinbase_ws_subscription
from ..external.deribit.normalize import normalize_deribit_ws_heartbeat
from ..external.hyperliquid.normalize import normalize_hyperliquid_ws_subscription
from ..external.ibkr.normalize import normalize_ibkr_ws_close
from ..external.kalshi.normalize import normalize_kalshi_ws_lifecycle
from ..external.okx.normalize import normalize_okx_ws_subscription
from ..external.tardis.normalize import normalize_tardis_ws_subscription
from ..external.upbit.normalize import normalize_upbit_ws_close
from ..external.versifi.normalize import normalize_versifi_ws_message


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
