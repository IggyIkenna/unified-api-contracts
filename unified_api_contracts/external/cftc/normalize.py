"""CFTC normalizers — all normalize_cftc_* functions.

Commitments of Traders (COT) report -> CanonicalOnChainMetric.
Managed money positioning used by features-commodity-service.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ...canonical.domain import CanonicalOnChainMetric
from ...normalize_utils._helpers import to_decimal as _to_decimal
from .schemas import CFTCCOTReport, CFTCManagedMoneyPosition


def _date_to_utc(d: object) -> datetime:
    """Convert date or datetime to aware UTC datetime."""
    if hasattr(d, "year") and hasattr(d, "month") and hasattr(d, "day"):
        dt = d if hasattr(d, "hour") else datetime.combine(d, datetime.min.time())
        return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
    return datetime.now(UTC)


def normalize_cftc_cot_report(
    raw: CFTCCOTReport,
    venue: str = "cftc",
) -> CanonicalOnChainMetric:
    """Convert CFTCCOTReport to CanonicalOnChainMetric.

    metric_type = "cot_managed_money_net"
    value = managed_money_net (long - short)
    entity = commodity
    """
    return CanonicalOnChainMetric(
        timestamp=_date_to_utc(raw.report_date),
        venue=venue,
        metric_type="cot_managed_money_net",
        asset=None,
        value=_to_decimal(raw.managed_money_net),
        secondary_value=_to_decimal(raw.open_interest_total),
        entity=raw.commodity,
        raw={
            "managed_money_long": raw.managed_money_long,
            "managed_money_short": raw.managed_money_short,
            "managed_money_net": raw.managed_money_net,
            "managed_money_spreading": raw.managed_money_spreading,
            "open_interest_total": raw.open_interest_total,
        },
    )


def normalize_cftc_managed_money_position(
    raw: CFTCManagedMoneyPosition,
    venue: str = "cftc",
) -> CanonicalOnChainMetric:
    """Convert CFTCManagedMoneyPosition to CanonicalOnChainMetric.

    metric_type = "cot_squeeze_score"
    value = squeeze_score (normalised net position in [-1.0, 1.0])
    secondary_value = net (contracts)
    entity = commodity
    """
    return CanonicalOnChainMetric(
        timestamp=_date_to_utc(raw.report_date),
        venue=venue,
        metric_type="cot_squeeze_score",
        asset=None,
        value=_to_decimal(raw.squeeze_score),
        secondary_value=_to_decimal(raw.net),
        entity=raw.commodity,
        raw={
            "net": raw.net,
            "net_change_wow": raw.net_change_wow,
            "squeeze_score": raw.squeeze_score,
        },
    )


__all__ = [
    "normalize_cftc_cot_report",
    "normalize_cftc_managed_money_position",
]
