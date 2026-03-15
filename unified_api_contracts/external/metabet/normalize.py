"""Metabet normalizers — all normalize_metabet_* functions.

Extracted from normalize_utils/ modules (instruments, errors).
"""

from __future__ import annotations

from datetime import UTC, datetime

from ...canonical.crosscutting.errors import (
    CanonicalError,
    ErrorAction,
)
from ...canonical.domain import CanonicalInstrument
from ...normalize_utils.errors._utils import from_http_status
from .schemas import MetabetMarket

# ---------------------------------------------------------------------------
# Instrument normalizer (from normalize_utils/instruments.py)
# ---------------------------------------------------------------------------


def normalize_metabet_market(
    raw: MetabetMarket,
    venue: str = "metabet",
) -> CanonicalInstrument:
    """Normalize MetabetMarket to CanonicalInstrument."""
    sym = raw.market or ""
    ik = f"{venue.upper()}:MARKET:{sym}"
    return CanonicalInstrument(
        instrument_key=ik,
        venue=venue,
        symbol=sym,
        timestamp=datetime.now(UTC),
        tick_size=None,
        min_size=None,
        contract_size=None,
        base_asset=None,
        quote_asset=None,
        settle_asset=None,
    )


# ---------------------------------------------------------------------------
# Error normalizer (from normalize_utils/errors/_normalize_b.py)
# ---------------------------------------------------------------------------


def normalize_metabet_error(
    error_code: str | int,
    message: str = "",
    venue: str = "metabet",
) -> CanonicalError:
    """Map a Metabet API error to a CanonicalError subclass."""
    code = str(error_code)
    try:
        return from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_metabet_error",
    "normalize_metabet_market",
]
