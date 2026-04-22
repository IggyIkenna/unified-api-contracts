"""Tests for G2.9 gap #7 — MultiLegOrderCapability."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from unified_api_contracts.internal.architecture_v2.multi_leg_order_capability import (
    CONSUMER_CALL_SITES,
    MULTI_LEG_ORDER_CAPABILITY_REGISTRY,
    ListedComboType,
    MultiLegOrderCapability,
    VenueNotRegisteredError,
    _validate_registry_invariants,
    multi_leg_capability_for,
    venues_supporting_combo_type,
    venues_supporting_legs,
)


class TestConsumerReferences:
    """G2.9 no-orphan rule: every UAC declaration has >=1 consumer call-site."""

    def test_consumer_call_sites_non_empty(self) -> None:
        assert len(CONSUMER_CALL_SITES) >= 1

    def test_consumer_call_sites_point_to_execution_service(self) -> None:
        # Gap #7 gates G2.5 execution algo catalogue; all refs must live there.
        assert all(site.startswith("execution-service/") for site in CONSUMER_CALL_SITES)


class TestRegistryShape:
    def test_registry_not_empty(self) -> None:
        assert len(MULTI_LEG_ORDER_CAPABILITY_REGISTRY) >= 6

    def test_venue_ids_unique(self) -> None:
        ids = [e.venue_id for e in MULTI_LEG_ORDER_CAPABILITY_REGISTRY]
        assert len(ids) == len(set(ids))

    def test_every_entry_frozen(self) -> None:
        for entry in MULTI_LEG_ORDER_CAPABILITY_REGISTRY:
            with pytest.raises(ValidationError):
                entry.max_legs = 99  # type: ignore[misc]


class TestRegistryContent:
    def test_cme_supports_listed_calendar_spread(self) -> None:
        entry = multi_leg_capability_for("cme")
        assert entry.supports_listed_combos is True
        assert ListedComboType.CALENDAR_SPREAD in entry.listed_combo_types
        assert entry.max_legs >= 2

    def test_deribit_supports_both_listed_and_synthetic(self) -> None:
        entry = multi_leg_capability_for("deribit")
        assert entry.supports_listed_combos is True
        assert entry.supports_synthetic_combos is True
        assert entry.max_legs >= 4

    def test_binance_has_no_multi_leg(self) -> None:
        entry = multi_leg_capability_for("binance")
        assert entry.supports_listed_combos is False
        assert entry.supports_synthetic_combos is False
        assert entry.max_legs == 0

    def test_okx_synthetic_only(self) -> None:
        entry = multi_leg_capability_for("okx")
        assert entry.supports_listed_combos is False
        assert entry.supports_synthetic_combos is True
        assert entry.listed_combo_types == ()


class TestHelpers:
    def test_unknown_venue_raises(self) -> None:
        with pytest.raises(VenueNotRegisteredError, match="not in"):
            multi_leg_capability_for("nonexistent_venue_xyz")

    def test_venues_supporting_calendar_spread(self) -> None:
        results = venues_supporting_combo_type(ListedComboType.CALENDAR_SPREAD)
        ids = {e.venue_id for e in results}
        assert "cme" in ids
        assert "deribit" in ids
        assert "ice" in ids
        assert "binance" not in ids

    def test_venues_supporting_iron_condor_only_deribit(self) -> None:
        results = venues_supporting_combo_type(ListedComboType.IRON_CONDOR)
        ids = {e.venue_id for e in results}
        assert ids == {"deribit"}

    def test_venues_supporting_4_legs(self) -> None:
        results = venues_supporting_legs(4)
        ids = {e.venue_id for e in results}
        assert "deribit" in ids
        assert "binance" not in ids

    def test_venues_supporting_2_legs_require_atomic(self) -> None:
        results = venues_supporting_legs(2, require_atomic=True)
        ids = {e.venue_id for e in results}
        assert "cme" in ids
        assert "deribit" in ids
        # Binance has max_legs=0 so it's excluded regardless.
        assert "binance" not in ids


class TestInvariants:
    def test_duplicate_venue_id_rejected(self) -> None:
        bad = (
            MultiLegOrderCapability(
                venue_id="dup",
                supports_listed_combos=False,
                supports_synthetic_combos=False,
                max_legs=0,
            ),
            MultiLegOrderCapability(
                venue_id="dup",
                supports_listed_combos=False,
                supports_synthetic_combos=False,
                max_legs=0,
            ),
        )
        with pytest.raises(ValueError, match="duplicate venue_id"):
            _validate_registry_invariants(bad)

    def test_max_legs_zero_with_combo_support_rejected(self) -> None:
        bad = (
            MultiLegOrderCapability(
                venue_id="broken",
                supports_listed_combos=True,
                supports_synthetic_combos=False,
                max_legs=0,
                listed_combo_types=(ListedComboType.CALENDAR_SPREAD,),
            ),
        )
        with pytest.raises(ValueError, match="max_legs=0 contradicts"):
            _validate_registry_invariants(bad)

    def test_listed_combos_without_types_rejected(self) -> None:
        bad = (
            MultiLegOrderCapability(
                venue_id="broken",
                supports_listed_combos=True,
                supports_synthetic_combos=False,
                max_legs=4,
                listed_combo_types=(),
            ),
        )
        with pytest.raises(ValueError, match="listed_combo_types is empty"):
            _validate_registry_invariants(bad)

    def test_listed_types_without_listed_flag_rejected(self) -> None:
        bad = (
            MultiLegOrderCapability(
                venue_id="broken",
                supports_listed_combos=False,
                supports_synthetic_combos=True,
                max_legs=4,
                listed_combo_types=(ListedComboType.BUTTERFLY,),
            ),
        )
        with pytest.raises(ValueError, match="supports_listed_combos=False"):
            _validate_registry_invariants(bad)

    def test_max_legs_negative_rejected_by_pydantic(self) -> None:
        with pytest.raises(ValidationError):
            MultiLegOrderCapability(
                venue_id="x",
                supports_listed_combos=False,
                supports_synthetic_combos=False,
                max_legs=-1,
            )
