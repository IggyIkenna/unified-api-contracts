"""EIA (U.S. Energy Information Administration) API v2 response schemas.

API base: https://api.eia.gov/v2/
Authentication: None required for public series.
Rate limit: Not officially documented; practical limit ~100 req/min.

Key series used by features-commodity-service:
  Natural Gas Weekly Storage: api.eia.gov/v2/natural-gas/stor/wkly/data/
  Crude Oil Weekly Storage:   api.eia.gov/v2/petroleum/stoc/wstk/data/
"""

from __future__ import annotations

__api_version__ = "v2"

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass
class EIAStorageReport:
    """Weekly EIA Natural Gas storage report (Working Gas in Underground Storage).

    period: ISO week date string from EIA, e.g. '2024-01-05'
    value_bcf: reported storage level in billion cubic feet
    year_ago_bcf: same-week prior-year level (for YoY comparison)
    five_year_avg_bcf: 5-year average for the same week (EIA-computed)
    deviation_bcf: value_bcf - five_year_avg_bcf (surplus positive, deficit negative)
    deviation_pct: deviation_bcf / five_year_avg_bcf as a fraction (e.g. 0.05 = +5%)
    """

    period: date
    value_bcf: Decimal
    year_ago_bcf: Decimal | None
    five_year_avg_bcf: Decimal | None
    deviation_bcf: Decimal | None
    deviation_pct: float | None
    retrieved_at: datetime


@dataclass
class EIAWeeklyCrudeStorageReport:
    """Weekly EIA Crude Oil storage report (Commercial Crude Oil Inventories).

    Series: Weekly U.S. Ending Stocks of Crude Oil (Thousand Barrels).
    deviation fields are vs. 5-year seasonal average (same computation as NG).
    """

    period: date
    value_mb: Decimal  # thousand barrels
    year_ago_mb: Decimal | None
    five_year_avg_mb: Decimal | None
    deviation_mb: Decimal | None
    deviation_pct: float | None
    retrieved_at: datetime


@dataclass
class EIASeriesObservation:
    """Single observation from an EIA v2 series endpoint (generic).

    Used for raw API response parsing before normalisation into typed reports.
    """

    period: str  # raw string from EIA (may be date, week, month depending on series)
    value: str | None  # EIA returns null as literal None; non-null values are strings
    series_id: str
    units: str
