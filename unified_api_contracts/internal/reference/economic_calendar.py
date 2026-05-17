"""Economic calendar internal schemas: macro release results from FRED.

Used by features-calendar-service for macro result GCS output.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class MacroResultRecord(BaseModel):
    """Canonical macro economic result record for GCS storage and feature computation."""

    event_type: str
    series_id: str
    release_date: date
    actual_value: Decimal | None = None
    previous_value: Decimal | None = None
    revision: Decimal | None = None
    unit: str = "unknown"
    source: str = "unknown"
    fetched_at: datetime | None = Field(default=None)

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict for DataFrame construction."""
        return {
            "event_type": self.event_type,
            "series_id": self.series_id,
            "release_date": self.release_date,
            "actual_value": float(self.actual_value) if self.actual_value is not None else None,
            "previous_value": float(self.previous_value) if self.previous_value is not None else None,
            "revision": float(self.revision) if self.revision is not None else None,
            "unit": self.unit,
            "source": self.source,
            "fetched_at": self.fetched_at,
        }
