from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import AwareDatetime

from ..domain._base import CanonicalBase


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


class WebSocketConnectionState(StrEnum):
    """WebSocket connection state machine states."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"


class CanonicalWsMessage(CanonicalBase):
    """Normalized WebSocket message envelope."""

    venue: str
    channel: str
    timestamp: AwareDatetime
    payload: str
    message_type: str = "data"
    sequence: int | None = None
    schema_version: str = "1.0"


@dataclass
class HeartbeatMessage:
    """WebSocket heartbeat/keepalive message."""

    venue: str
    timestamp: AwareDatetime
    interval_ms: int = 30000


@dataclass
class SubscribeRequest:
    """WebSocket channel subscription request."""

    channels: list[str]
    venue: str
    auth_token: str | None = None


@dataclass
class UnsubscribeRequest:
    """WebSocket channel unsubscription request."""

    channels: list[str]
    venue: str


@dataclass
class WebSocketPingFrame:
    """WebSocket ping frame."""

    venue: str
    timestamp: AwareDatetime
    payload: bytes = b""


@dataclass
class WebSocketPongFrame:
    """WebSocket pong frame."""

    venue: str
    timestamp: AwareDatetime
    payload: bytes = b""
