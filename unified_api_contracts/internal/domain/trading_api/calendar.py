"""Calendar domain schemas — economic events and corporate actions."""

from __future__ import annotations

from pydantic import BaseModel


class EconomicResultItem(BaseModel):
    """Single macro economic event with actual and previous values."""

    id: str = ""  # noqa: qg-empty-fallback
    event_type: str  # NFP | CPI | FOMC | GDP | CLAIMS | PCE
    release_date: str  # ISO date YYYY-MM-DD
    release_time_utc: str  # HH:MM e.g. "13:30"
    actual_value: float | None = None
    previous_value: float | None = None
    unit: str = ""  # noqa: qg-empty-fallback
    status: str  # "released" | "upcoming"


class CorporateActionItem(BaseModel):
    """Single corporate action event."""

    id: str = ""  # noqa: qg-empty-fallback
    ticker: str
    event_type: str  # "dividend" | "earnings" | "split"
    event_date: str  # ISO date YYYY-MM-DD
    amount: float | None = None  # dividend cash amount per share
    actual_eps: float | None = None
    estimated_eps: float | None = None
    status: str  # "confirmed" | "upcoming"
