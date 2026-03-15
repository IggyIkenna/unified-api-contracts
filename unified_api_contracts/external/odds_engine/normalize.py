"""Odds Engine normalizers — OddsEngineMarket to CanonicalInstrument."""

from __future__ import annotations

from datetime import UTC, datetime

from ...canonical.domain import CanonicalInstrument
from .schemas import OddsEngineMarket


def normalize_odds_engine_market(
    raw: OddsEngineMarket,
    venue: str = "odds_engine",
) -> CanonicalInstrument:
    """Normalize OddsEngineMarket to CanonicalInstrument."""
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


__all__ = [
    "normalize_odds_engine_market",
]
