"""Bond, yield curve, and CDS normalizers: raw provider data → canonical schemas.

Covers:
- FRED (Federal Reserve Economic Data) — US Treasury yield observations
- ECB (European Central Bank SDMX REST) — EU OIS/ESTR yield curve
- OFR (Office of Financial Research) — CDS spread indices
- OpenBB Platform — Treasury bond bid/ask/YTM data

All monetary / rate values are converted to Decimal for precision.
"""

from __future__ import annotations

from ..external.ecb.normalize import (
    normalize_ecb_dataflow_response,
    normalize_ecb_yield_curve_observation,
)
from ..external.fred.normalize import (
    normalize_fred_observation,
    normalize_fred_series_response,
)
from ..external.ofr.normalize import (
    normalize_ofr_cds_response,
    normalize_ofr_cds_spread,
)
from ..external.openbb.normalize import (
    _parse_date_to_utc,
    normalize_openbb_treasury_price,
    normalize_openbb_treasury_prices_response,
)
from ..external.tardis.normalize import _to_decimal

__all__ = [
    "_parse_date_to_utc",
    "_to_decimal",
    "normalize_ecb_dataflow_response",
    "normalize_ecb_yield_curve_observation",
    "normalize_fred_observation",
    "normalize_fred_series_response",
    "normalize_ofr_cds_response",
    "normalize_ofr_cds_spread",
    "normalize_openbb_treasury_price",
    "normalize_openbb_treasury_prices_response",
]
