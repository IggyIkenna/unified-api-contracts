"""HFT and latency measurement schemas — tick-to-trade, co-location, order latency."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class LatencyComponent(StrEnum):
    MARKET_DATA_DECODE = "market_data_decode"
    SIGNAL_GENERATION = "signal_generation"
    RISK_CHECK = "risk_check"
    ORDER_ENCODING = "order_encoding"
    NETWORK_SEND = "network_send"
    EXCHANGE_PROCESSING = "exchange_processing"
    NETWORK_RECEIVE = "network_receive"
    FILL_DECODE = "fill_decode"


class OrderLatencyRecord(BaseModel):
    """Per-order end-to-end latency record stored to GCS for analysis."""

    order_id: str
    venue: str
    strategy: str | None = None
    instrument_id: str
    order_type: str
    side: str
    timestamp: datetime
    component_latencies: dict[str, float] = Field(
        default_factory=dict,
        description="LatencyComponent -> microseconds breakdown",
    )
    total_us: float
    is_outlier: bool = False
    outlier_reason: str | None = None


class NetworkJitterMetric(BaseModel):
    """Short-window network jitter measurement."""

    measured_at: datetime
    measurement_window_ms: int = Field(description="measurement window in milliseconds")
    venue: str
    datacenter: str | None = None
    jitter_p50_us: float
    jitter_p99_us: float
    jitter_p999_us: float
    packet_loss_pct: float = 0.0
    sample_count: int | None = None
