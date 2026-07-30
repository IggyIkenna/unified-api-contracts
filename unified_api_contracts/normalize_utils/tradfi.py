"""Bond, yield curve, and CDS normalizers: raw provider data → canonical schemas.

Covers:
- FRED (Federal Reserve Economic Data) — US Treasury yield observations
- ECB (European Central Bank SDMX REST) — EU OIS/ESTR yield curve
- OFR (Office of Financial Research) — CDS spread indices
"""

from __future__ import annotations

# Baker Hughes (already external)
from ..external.baker_hughes.normalize import normalize_baker_hughes_rig_count

# CFTC (already external)
from ..external.cftc.normalize import (
    normalize_cftc_cot_report,
    normalize_cftc_managed_money_position,
)

# ECB
from ..external.ecb.normalize import (
    normalize_ecb_dataflow_response,
    normalize_ecb_yield_curve_observation,
)

# FRED
from ..external.fred.normalize import (
    normalize_fred_observation,
    normalize_fred_series_response,
)

# OFR
from ..external.ofr.normalize import (
    normalize_ofr_cds_response,
    normalize_ofr_cds_spread,
)

__all__ = [
    "normalize_baker_hughes_rig_count",
    "normalize_cftc_cot_report",
    "normalize_cftc_managed_money_position",
    "normalize_ecb_dataflow_response",
    "normalize_ecb_yield_curve_observation",
    "normalize_fred_observation",
    "normalize_fred_series_response",
    "normalize_ofr_cds_response",
    "normalize_ofr_cds_spread",
]
