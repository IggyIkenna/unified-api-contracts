"""Tests for G2.9 gap #6 — IvSurfaceFidelity."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from unified_api_contracts.internal.architecture_v2.iv_surface_fidelity import (
    CONSUMER_CALL_SITES,
    OPTION_VENUE_CAPABILITIES,
    IvSurfaceFidelity,
    OptionVenueCapability,
    OptionVenueNotRegisteredError,
    _validate_registry_invariants,
    option_venue_for,
    venues_at_fidelity,
    venues_trading_underlying,
)


class TestRegistryShape:
    def test_registry_not_empty(self) -> None:
        assert len(OPTION_VENUE_CAPABILITIES) >= 4

    def test_venue_ids_unique(self) -> None:
        ids = [e.venue_id for e in OPTION_VENUE_CAPABILITIES]
        assert len(ids) == len(set(ids))


class TestContent:
    def test_deribit_full_surface(self) -> None:
        entry = option_venue_for("deribit")
        assert entry.iv_surface_fidelity is IvSurfaceFidelity.FULL_SURFACE
        assert entry.supports_multi_leg_combos is True
        assert entry.max_combo_legs == 4

    def test_cme_coarse_grid(self) -> None:
        entry = option_venue_for("cme")
        assert entry.iv_surface_fidelity is IvSurfaceFidelity.COARSE_GRID
        assert "ES" in entry.underlyings

    def test_bit_com_no_combos(self) -> None:
        entry = option_venue_for("bit_com")
        assert entry.supports_multi_leg_combos is False
        assert entry.max_combo_legs == 0


class TestHelpers:
    def test_unknown_venue_raises(self) -> None:
        with pytest.raises(OptionVenueNotRegisteredError):
            option_venue_for("nonexistent")

    def test_venues_at_full_surface(self) -> None:
        results = venues_at_fidelity(IvSurfaceFidelity.FULL_SURFACE)
        ids = {e.venue_id for e in results}
        assert "deribit" in ids
        assert "ibkr" in ids

    def test_venues_trading_btc(self) -> None:
        results = venues_trading_underlying("BTC")
        ids = {e.venue_id for e in results}
        assert "deribit" in ids
        assert "okx" in ids

    def test_venues_trading_es(self) -> None:
        results = venues_trading_underlying("ES")
        ids = {e.venue_id for e in results}
        assert ids == {"cme"}

    def test_venues_trading_unknown_underlying_empty(self) -> None:
        assert venues_trading_underlying("MADEUP") == ()


class TestInvariants:
    def test_duplicate_venue_rejected(self) -> None:
        bad = (
            OptionVenueCapability(
                venue_id="dup",
                underlyings=("BTC",),
                iv_surface_fidelity=IvSurfaceFidelity.FULL_SURFACE,
                strikes_per_expiry_p50=10,
                expiries_per_underlying_p50=5,
                supports_multi_leg_combos=False,
                max_combo_legs=0,
            ),
            OptionVenueCapability(
                venue_id="dup",
                underlyings=("ETH",),
                iv_surface_fidelity=IvSurfaceFidelity.ATM_ONLY,
                strikes_per_expiry_p50=10,
                expiries_per_underlying_p50=5,
                supports_multi_leg_combos=False,
                max_combo_legs=0,
            ),
        )
        with pytest.raises(ValueError, match="duplicate"):
            _validate_registry_invariants(bad)

    def test_empty_underlyings_rejected(self) -> None:
        bad = (
            OptionVenueCapability(
                venue_id="empty",
                underlyings=(),
                iv_surface_fidelity=IvSurfaceFidelity.FULL_SURFACE,
                strikes_per_expiry_p50=10,
                expiries_per_underlying_p50=5,
                supports_multi_leg_combos=False,
                max_combo_legs=0,
            ),
        )
        with pytest.raises(ValueError, match="underlyings"):
            _validate_registry_invariants(bad)

    def test_combo_support_mismatch_rejected(self) -> None:
        bad = (
            OptionVenueCapability(
                venue_id="x",
                underlyings=("BTC",),
                iv_surface_fidelity=IvSurfaceFidelity.FULL_SURFACE,
                strikes_per_expiry_p50=10,
                expiries_per_underlying_p50=5,
                supports_multi_leg_combos=True,
                max_combo_legs=1,
            ),
        )
        with pytest.raises(ValueError, match="max_combo_legs>=2"):
            _validate_registry_invariants(bad)

    def test_none_fidelity_row_rejected(self) -> None:
        bad = (
            OptionVenueCapability(
                venue_id="x",
                underlyings=("BTC",),
                iv_surface_fidelity=IvSurfaceFidelity.NONE,
                strikes_per_expiry_p50=10,
                expiries_per_underlying_p50=5,
                supports_multi_leg_combos=False,
                max_combo_legs=0,
            ),
        )
        with pytest.raises(ValueError, match="NONE fidelity"):
            _validate_registry_invariants(bad)

    def test_negative_strikes_rejected_by_pydantic(self) -> None:
        with pytest.raises(ValidationError):
            OptionVenueCapability(
                venue_id="x",
                underlyings=("BTC",),
                iv_surface_fidelity=IvSurfaceFidelity.FULL_SURFACE,
                strikes_per_expiry_p50=-1,
                expiries_per_underlying_p50=5,
                supports_multi_leg_combos=False,
                max_combo_legs=0,
            )


class TestConsumerReferences:
    def test_consumer_call_sites_non_empty(self) -> None:
        assert len(CONSUMER_CALL_SITES) >= 1
