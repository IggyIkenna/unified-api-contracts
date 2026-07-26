"""Tests for registry/data_type_capability.py — DATA_TYPE_CAPABILITY_REGISTRY."""

from __future__ import annotations

import pytest

from unified_api_contracts.canonical.gcs_paths import AssetGroup
from unified_api_contracts.registry.data_type_capability import (
    DATA_TYPE_CAPABILITY_REGISTRY,
)

# Regression test for plans/active/issues/cefi_hl_aster_batch_data_gaps_2026_06_22.md's
# "add DATA_TYPE_CAPABILITY_REGISTRY cefi entries for KRAKEN-SPOT/KRAKEN-FUTURES/
# BITGET-SPOT/BITGET-FUTURES/BITFINEX-SPOT/BITFINEX-FUTURES/ASTER" todo — these venues
# showed EMPTY venue_data_types in the cefi full-catalogue CSV export (2026-06-23)
# because they were absent from this registry at the time. Entries were added, but no
# test locked in the fix — this closes that gap.
_PREVIOUSLY_MISSING_CEFI_VENUES = (
    "KRAKEN-SPOT",
    "KRAKEN-FUTURES",
    "BITGET-SPOT",
    "BITGET-FUTURES",
    "BITFINEX-SPOT",
    "BITFINEX-FUTURES",
    "ASTER",
)


@pytest.mark.parametrize("venue", _PREVIOUSLY_MISSING_CEFI_VENUES)
def test_previously_missing_cefi_venue_has_registry_entries(venue: str) -> None:
    """Each named venue must have at least one CEFI capability entry (non-empty
    venue_data_types) — the exact regression the source issue doc's CSV export caught.
    """
    entries = [c for c in DATA_TYPE_CAPABILITY_REGISTRY if c.venue == venue]
    assert entries, f"{venue} has no DATA_TYPE_CAPABILITY_REGISTRY entries"
    assert all(c.asset_group == AssetGroup.CEFI for c in entries)


def test_previously_missing_spot_venues_have_trades_and_book_snapshot() -> None:
    """The 3 Tardis spot venues must carry the same minimum spot surface as the
    other Tardis spot venues (COINBASE-SPOT/UPBIT): trades + book_snapshot_5.
    """
    for venue in ("KRAKEN-SPOT", "BITGET-SPOT", "BITFINEX-SPOT"):
        data_types = {c.data_type for c in DATA_TYPE_CAPABILITY_REGISTRY if c.venue == venue}
        assert {"trades", "book_snapshot_5"}.issubset(data_types), (
            f"{venue} missing minimum spot data_types, has: {data_types}"
        )


def test_previously_missing_futures_venues_have_full_derivatives_surface() -> None:
    """The 3 Tardis futures/perp venues must carry the full derivatives surface:
    trades + book_snapshot_5 + derivative_ticker + liquidations + futures_chain.
    """
    expected = {
        "trades",
        "book_snapshot_5",
        "derivative_ticker",
        "liquidations",
        "futures_chain",
    }
    for venue in ("KRAKEN-FUTURES", "BITGET-FUTURES", "BITFINEX-FUTURES"):
        data_types = {c.data_type for c in DATA_TYPE_CAPABILITY_REGISTRY if c.venue == venue}
        assert expected.issubset(data_types), f"{venue} missing derivatives data_types, has: {data_types}"
