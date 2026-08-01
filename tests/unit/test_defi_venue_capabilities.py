"""Tests for the DeFi expected_unattempted seeder's honest-coverage denominator
(defi_expected_unattempted_seeder_design_2026_07_26).

``get_defi_declared_venues_for_data_type`` is the SINGLE place a
capability-declared-but-not-collectible venue is excluded from the
venue/chain-grain honest-coverage denominator — these tests lock its three
filters (phase=="live", data_type declared + started, not in the exclusion
registry) against the real UAC registry data, plus the exclusion-registry
mechanism itself via a monkeypatched fixture (never mutating the real,
shared module-level dict).
"""

from __future__ import annotations

from datetime import date

import pytest

from unified_api_contracts.registry.defi_venue_capabilities import (
    DEFI_VENUE_COLLECTIBILITY_EXCEPTIONS,
    DEFI_VENUE_DATA_TYPE_CAPABILITIES,
    get_defi_declared_venues_for_data_type,
)
from unified_api_contracts.registry.defi_venues import DEFI_VENUE_PHASE


def test_exceptions_registry_starts_empty() -> None:
    """No venue is disposed 'exclude' yet (FLUID-ETHEREUM lending_indices was
    disposed 'wire', not 'exclude' — defi_expected_unattempted_seeder_design's P0)."""
    assert DEFI_VENUE_COLLECTIBILITY_EXCEPTIONS == {}


def test_returns_only_live_phase_venues() -> None:
    """A capability-declared but phase!='live' ('pipeline'/roadmap) venue must
    never enter the honest-coverage denominator. METEORA-SOLANA declares
    dex_pool_state but stays phase='pipeline' (upstream dead, re-narrowed
    2026-07-22) — it must be excluded."""
    assert DEFI_VENUE_PHASE.get("METEORA-SOLANA") == "pipeline"
    assert "dex_pool_state" in DEFI_VENUE_DATA_TYPE_CAPABILITIES["METEORA-SOLANA"]
    declared = get_defi_declared_venues_for_data_type("dex_pool_state", as_of=date(2026, 8, 1))
    assert ("METEORA", "SOLANA") not in declared


def test_fluid_ethereum_included_in_lending_indices_denominator() -> None:
    """The concrete P0 case this seeder exists for: FLUID-ETHEREUM is declared
    live + capable for lending_indices and carries NO exclusion entry, so it
    MUST appear in the denominator (disposition (a) — wire, not exclude)."""
    declared = get_defi_declared_venues_for_data_type("lending_indices", as_of=date(2026, 8, 1))
    assert ("FLUID", "ETHEREUM") in declared


def test_start_date_filter_excludes_future_capability() -> None:
    """A venue whose declared data_type start_date is AFTER as_of is honestly
    out of scope (not yet expected), not silently included."""
    # AAVE_V3-LINEA lending_indices starts 2025-02-12.
    before_launch = get_defi_declared_venues_for_data_type("lending_indices", as_of=date(2025, 1, 1))
    after_launch = get_defi_declared_venues_for_data_type("lending_indices", as_of=date(2025, 3, 1))
    assert ("AAVE_V3", "LINEA") not in before_launch
    assert ("AAVE_V3", "LINEA") in after_launch


def test_data_type_not_declared_returns_empty() -> None:
    """A data_type no live DeFi venue declares (e.g. the pre-fix 'liquidations'
    manifest key, distinct from the UAC-declared 'liquidation_events') returns
    an empty denominator — a harmless no-op for the seeder's emit call, never
    a KeyError or a spurious stamp."""
    declared = get_defi_declared_venues_for_data_type("liquidations", as_of=date(2026, 8, 1))
    assert declared == []


def test_exclusion_registry_filters_out_excluded_venue(monkeypatch: pytest.MonkeyPatch) -> None:
    """A venue registered in DEFI_VENUE_COLLECTIBILITY_EXCEPTIONS[data_type] is
    stopped from ever entering the denominator — the ONE place a disposed-
    exclude venue is filtered, per the design's anti-drift rationale."""
    monkeypatch.setitem(DEFI_VENUE_COLLECTIBILITY_EXCEPTIONS, "lending_indices", {"FLUID-ETHEREUM"})
    declared = get_defi_declared_venues_for_data_type("lending_indices", as_of=date(2026, 8, 1))
    assert ("FLUID", "ETHEREUM") not in declared
    # A sibling live venue is unaffected by an exclusion scoped to a different key.
    assert ("AAVE_V3", "ETHEREUM") in declared


def test_returned_venues_are_upper_and_chains_populated() -> None:
    """Every returned pair is a normalised (VENUE_UPPER, CHAIN) tuple with a
    non-blank chain — DeFi shards are always chain-scoped (A4)."""
    declared = get_defi_declared_venues_for_data_type("lst_rates", as_of=date(2026, 8, 1))
    assert declared  # sanity: lst_rates has live declared venues
    for venue, chain in declared:
        assert venue == venue.upper()
        assert chain  # never blank
        assert chain == chain.upper()
