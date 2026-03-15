"""OFR normalizers — all normalize_ofr_* functions.

Extracted from normalize_utils/tradfi.py.
Covers Office of Financial Research CDS spread indices.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from ...canonical.domain import CanonicalCdsSpread
from .schemas import OfrCdsResponse, OfrCdsSpreadIndex

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _to_decimal(val: float | str | int | None) -> Decimal | None:
    """Convert any numeric-ish value to Decimal; return None on failure."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _parse_date_to_utc(date_str: str | None) -> datetime:
    """Parse a YYYY-MM-DD date string to an aware UTC datetime (midnight UTC)."""
    if not date_str:
        return datetime.now(UTC)
    with contextlib.suppress(ValueError, TypeError):
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").replace(tzinfo=UTC)
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Normalizers
# ---------------------------------------------------------------------------


def normalize_ofr_cds_spread(
    raw: OfrCdsSpreadIndex,
    venue: str = "ofr",
) -> CanonicalCdsSpread | None:
    """Normalize a single OfrCdsSpreadIndex to CanonicalCdsSpread.

    OFR values are raw float CDS spreads; units depend on the series but are
    typically basis points (bps). Stored as-is in spread_bps.

    Args:
        raw:   OfrCdsSpreadIndex observation.
        venue: Provider tag, defaults to "ofr".
    """
    if raw.value is None:
        return None

    spread = _to_decimal(raw.value)
    if spread is None:
        return None

    timestamp = _parse_date_to_utc(raw.date)

    return CanonicalCdsSpread(
        timestamp=timestamp,
        venue=venue,
        series_id=raw.series_id or "",
        index_name=raw.index_name,
        tenor=raw.tenor,
        sector=raw.sector,
        spread_bps=spread,
    )


def normalize_ofr_cds_response(
    raw: OfrCdsResponse,
    venue: str = "ofr",
) -> list[CanonicalCdsSpread]:
    """Normalize OfrCdsResponse (list of CDS spread observations) to CanonicalCdsSpread list."""
    results: list[CanonicalCdsSpread] = []
    for item in raw.data or []:
        point = normalize_ofr_cds_spread(item, venue=venue)
        if point is not None:
            results.append(point)
    return results


__all__ = [
    "normalize_ofr_cds_response",
    "normalize_ofr_cds_spread",
]
