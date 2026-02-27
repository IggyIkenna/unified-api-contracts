"""WebSocket subscription/heartbeat schemas for live-trading venues."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class HealthPingResponse:
    """Generic health/ping endpoint response (status, latency_ms)."""

    status: str  # ok, healthy, etc.
    latency_ms: float | None = None
    timestamp: datetime | None = None


@dataclass
class WebSocketConnectionOpened:
    """WebSocket connection opened lifecycle event."""

    venue: str
    url: str
    timestamp: datetime
    connection_id: str | None = None


@dataclass
class WebSocketConnectionClosed:
    """WebSocket connection closed lifecycle event."""

    venue: str
    code: int
    reason: str | None = None
    timestamp: datetime | None = None
    was_clean: bool = False


@dataclass
class WebSocketPingFrame:
    """WebSocket ping frame (client→server or server→client)."""

    venue: str
    timestamp: datetime
    payload: bytes | None = None


@dataclass
class WebSocketPongFrame:
    """WebSocket pong frame (response to ping)."""

    venue: str
    timestamp: datetime
    payload: bytes | None = None


@dataclass
class SubscribeRequest:
    venue: str
    channel: str
    symbols: list[str] = field(default_factory=list)
    params: dict[str, str] = field(default_factory=dict)


@dataclass
class UnsubscribeRequest:
    venue: str
    channel: str
    symbols: list[str] = field(default_factory=list)


@dataclass
class HeartbeatMessage:
    venue: str
    timestamp: datetime
    ping_interval_seconds: float = 20.0


@dataclass
class WebSocketConnectionState:
    venue: str
    connected: bool
    last_heartbeat: datetime | None = None
    reconnect_count: int = 0
    subscriptions: list[str] = field(default_factory=list)
