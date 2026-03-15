"""OpenBB normalizers — all normalize_openbb_* functions.

Extracted from normalize_utils/tradfi.py.
Covers OpenBB Platform Treasury bond bid/ask/YTM data.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from ...canonical.domain import CanonicalBondData
from .schemas import OpenBBTreasuryPrice, OpenBBTreasuryPricesResponse

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


def normalize_openbb_treasury_price(
    raw: OpenBBTreasuryPrice,
    venue: str = "openbb",
) -> CanonicalBondData | None:
    """Normalize a single OpenBBTreasuryPrice to CanonicalBondData.

    OpenBB treasury prices contain bid, ask, last (price), yield_to_maturity.
    date is a string in YYYY-MM-DD format.

    Args:
        raw:   OpenBBTreasuryPrice row.
        venue: Provider tag, defaults to "openbb".
    """
    if raw.symbol is None and raw.name is None:
        return None

    timestamp = _parse_date_to_utc(raw.date)

    return CanonicalBondData(
        timestamp=timestamp,
        venue=venue,
        symbol=raw.symbol or "",
        name=raw.name,
        bid=_to_decimal(raw.bid),
        ask=_to_decimal(raw.ask),
        last=_to_decimal(raw.last),
        yield_to_maturity=_to_decimal(raw.yield_to_maturity),
        currency=None,  # OpenBB does not expose currency directly in this schema
    )


def normalize_openbb_treasury_prices_response(
    raw: OpenBBTreasuryPricesResponse,
    venue: str = "openbb",
) -> list[CanonicalBondData]:
    """Normalize OpenBBTreasuryPricesResponse to a list of CanonicalBondData."""
    results: list[CanonicalBondData] = []
    for item in raw.results or []:
        point = normalize_openbb_treasury_price(item, venue=venue)
        if point is not None:
            results.append(point)
    return results


__all__ = [
    "normalize_openbb_treasury_price",
    "normalize_openbb_treasury_prices_response",
]
