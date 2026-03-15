"""PredictIt normalizers — all normalize_predictit_* functions.

Extracted from normalize_utils/ modules (instruments).
"""

from __future__ import annotations

from datetime import UTC, datetime

from ...canonical.domain import CanonicalInstrument
from .schemas import PredictItMarket

# ---------------------------------------------------------------------------
# Instrument normalizer (from normalize_utils/instruments.py)
# ---------------------------------------------------------------------------


def normalize_predictit_market(
    raw: PredictItMarket,
    venue: str = "predictit",
) -> CanonicalInstrument:
    """Normalize PredictItMarket to CanonicalInstrument."""
    sym = raw.short_name or raw.name or str(raw.id or "")
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


__all__ = [
    "normalize_predictit_market",
]
