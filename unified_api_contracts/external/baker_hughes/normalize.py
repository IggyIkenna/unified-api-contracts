"""Baker Hughes normalizers — all normalize_baker_hughes_* functions.

North America rotary rig count (gas, oil, total) -> CanonicalOnChainMetric.
Commodity/energy supply indicator used by features-commodity-service.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from ...canonical.domain import CanonicalOnChainMetric
from ...normalize_utils._helpers import to_decimal
from .schemas import BakerHughesRigCount


def _date_to_utc(d: date | datetime | object) -> datetime:
    """Convert date or datetime to aware UTC datetime."""
    if isinstance(d, datetime):
        return d.replace(tzinfo=UTC) if d.tzinfo is None else d.astimezone(UTC)
    if isinstance(d, date):
        return datetime.combine(d, datetime.min.time(), tzinfo=UTC)
    return datetime.now(UTC)


def normalize_baker_hughes_rig_count(
    raw: BakerHughesRigCount,
    venue: str = "baker_hughes",
) -> CanonicalOnChainMetric:
    """Convert BakerHughesRigCount to CanonicalOnChainMetric.

    metric_type = "rig_count"
    value = total_rigs
    secondary_value = gas_rigs (for gas/oil split)
    entity = "na" (North America)
    """
    return CanonicalOnChainMetric(
        timestamp=_date_to_utc(raw.report_date),
        venue=venue,
        metric_type="rig_count",
        asset=None,
        value=to_decimal(raw.total_rigs),
        secondary_value=to_decimal(raw.gas_rigs),
        entity="na",
        raw={
            "gas_rigs": raw.gas_rigs,
            "oil_rigs": raw.oil_rigs,
            "total_rigs": raw.total_rigs,
            "gas_rigs_wow_change": raw.gas_rigs_wow_change,
            "oil_rigs_wow_change": raw.oil_rigs_wow_change,
        },
    )


__all__ = [
    "normalize_baker_hughes_rig_count",
]
