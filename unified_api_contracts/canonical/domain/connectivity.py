from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from pydantic import AwareDatetime, Field

from ._base import CanonicalBase


class CanonicalWsMessage(CanonicalBase):
    """Normalised WebSocket message — minimal envelope."""

    channel: str
    timestamp: AwareDatetime
    venue: str
    payload: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class WebSocketEvent(StrEnum):
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    PING = "ping"
    PONG = "pong"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    ERROR = "error"
    RECONNECT = "reconnect"


class CanonicalWebSocketLifecycle(CanonicalBase):
    """Normalized WebSocket lifecycle event."""

    venue: str
    event: WebSocketEvent
    timestamp: AwareDatetime
    channel: str | None = None
    reason: str | None = None
    code: int | None = None
    latency_ms: float | None = None
    schema_version: str = "1.0"


@dataclass
class HealthPingResponse:
    """Generic health/ping endpoint response."""

    status: str
    latency_ms: float | None = None
    timestamp: AwareDatetime | None = None


@dataclass
class WebSocketConnectionOpened:
    """WebSocket connection opened lifecycle event."""

    venue: str
    url: str
    timestamp: AwareDatetime
    connection_id: str | None = None


@dataclass
class WebSocketConnectionClosed:
    """WebSocket connection closed lifecycle event."""

    venue: str
    code: int
    reason: str | None = None
    timestamp: AwareDatetime | None = None
    was_clean: bool = False


@dataclass
class WebSocketPingFrame:
    venue: str
    timestamp: AwareDatetime
    payload: bytes | None = None


@dataclass
class WebSocketPongFrame:
    venue: str
    timestamp: AwareDatetime
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
    timestamp: AwareDatetime
    ping_interval_seconds: float = 20.0


@dataclass
class WebSocketConnectionState:
    venue: str
    connected: bool
    last_heartbeat: AwareDatetime | None = None
    reconnect_count: int = 0
    subscriptions: list[str] = field(default_factory=list)
