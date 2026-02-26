"""WebSocket subscription/heartbeat schemas for live-trading venues."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


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
