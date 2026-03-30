"""Corporate actions internal schemas: dividends, splits, earnings results.

Used by features-calendar-service and instruments-service for reference data
processing and GCS output.
"""

from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class DividendType(str, enum.Enum):
    """Dividend classification type."""

    REGULAR = "REGULAR"
    SPECIAL = "SPECIAL"
    QUALIFIED = "QUALIFIED"
    UNSPECIFIED = "UNSPECIFIED"


class DividendRecord(BaseModel):
    """Canonical dividend record for GCS storage and feature computation."""

    ticker: str
    ex_date: date
    pay_date: date | None = None
    record_date: date | None = None
    declaration_date: date | None = None
    amount: float
    dividend_type: DividendType = DividendType.UNSPECIFIED
    currency: str = "USD"
    source: str = "unknown"
    fetched_at: datetime | None = None
    instrument_key: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict for DataFrame construction."""
        return {
            "ticker": self.ticker,
            "ex_date": self.ex_date,
            "pay_date": self.pay_date,
            "record_date": self.record_date,
            "declaration_date": self.declaration_date,
            "amount": self.amount,
            "dividend_type": self.dividend_type.value,
            "currency": self.currency,
            "source": self.source,
            "fetched_at": self.fetched_at,
            "instrument_key": self.instrument_key,
        }


class StockSplitRecord(BaseModel):
    """Canonical stock split record for GCS storage and feature computation."""

    ticker: str
    effective_date: date
    ratio: float
    split_from: int
    split_to: int
    source: str = "unknown"
    fetched_at: datetime | None = None
    instrument_key: str | None = None

    @property
    def is_reverse_split(self) -> bool:
        """True if this is a reverse split (ratio < 1)."""
        return self.ratio < 1.0

    @property
    def adjustment_factor(self) -> float:
        """Price adjustment factor: 1/ratio for forward, ratio for reverse."""
        if self.ratio == 0:
            return 1.0
        return 1.0 / self.ratio

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict for DataFrame construction."""
        return {
            "ticker": self.ticker,
            "effective_date": self.effective_date,
            "ratio": self.ratio,
            "split_from": self.split_from,
            "split_to": self.split_to,
            "is_reverse_split": self.is_reverse_split,
            "adjustment_factor": self.adjustment_factor,
            "source": self.source,
            "fetched_at": self.fetched_at,
            "instrument_key": self.instrument_key,
        }


class EarningsResultRecord(BaseModel):
    """Canonical earnings result record for GCS storage and feature computation."""

    ticker: str
    period_of_report_date: date
    fiscal_period: str | None = None
    fiscal_year: int | None = None
    actual_eps: Decimal | None = None
    estimated_eps: Decimal | None = None
    earnings_surprise_pct: float | None = None
    actual_revenue: Decimal | None = None
    estimated_revenue: Decimal | None = None
    source: str = "unknown"
    fetched_at: datetime | None = Field(default=None)

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict for DataFrame construction."""
        return {
            "ticker": self.ticker,
            "period_of_report_date": self.period_of_report_date,
            "fiscal_period": self.fiscal_period,
            "fiscal_year": self.fiscal_year,
            "actual_eps": float(self.actual_eps) if self.actual_eps is not None else None,
            "estimated_eps": (float(self.estimated_eps) if self.estimated_eps is not None else None),
            "earnings_surprise_pct": self.earnings_surprise_pct,
            "actual_revenue": (float(self.actual_revenue) if self.actual_revenue is not None else None),
            "estimated_revenue": (float(self.estimated_revenue) if self.estimated_revenue is not None else None),
            "source": self.source,
            "fetched_at": self.fetched_at,
        }
