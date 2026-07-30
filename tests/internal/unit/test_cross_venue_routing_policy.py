"""Tests for G2.9 gap #10 — CrossVenueRoutingPolicy."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from unified_api_contracts.internal.architecture_v2.cross_venue_routing_policy import (
    CONSUMER_CALL_SITES,
    CROSS_VENUE_ROUTING_POLICIES,
    CrossVenueLegRole,
    CrossVenueRoutingPolicy,
    PolicyNotFoundError,
    RoutingPriority,
    _validate_registry_invariants,
    policies_for_settlement_currency,
    policies_for_venue_pair,
    routing_policy_for,
)


class TestRegistryShape:
    def test_registry_not_empty(self) -> None:
        assert len(CROSS_VENUE_ROUTING_POLICIES) >= 6

    def test_policy_ids_unique(self) -> None:
        ids = [p.policy_id for p in CROSS_VENUE_ROUTING_POLICIES]
        assert len(ids) == len(set(ids))

    def test_every_policy_frozen(self) -> None:
        for policy in CROSS_VENUE_ROUTING_POLICIES:
            with pytest.raises(ValidationError):
                policy.policy_id = "mutated"  # type: ignore[misc]


class TestContent:
    def test_ibkr_spy_cme_es_basis_policy(self) -> None:
        policy = routing_policy_for("ibkr_spy_cme_es_basis")
        assert policy.leg_venues == ("ibkr", "cme")
        assert policy.leg_roles == (
            CrossVenueLegRole.SPOT_LEG,
            CrossVenueLegRole.FUTURE_LEG,
        )
        assert policy.settlement_currency == "USD"

    def test_usdt_settled_policy_exists(self) -> None:
        policy = routing_policy_for("binance_spot_binance_perp_basis")
        assert policy.settlement_currency == "USDT"
        assert policy.priority is RoutingPriority.LATENCY

    def test_cross_product_commodity_spread(self) -> None:
        policy = routing_policy_for("cme_wti_ice_brent_spread")
        assert set(policy.leg_venues) == {"cme", "ice"}
        assert all(r is CrossVenueLegRole.FUTURE_LEG for r in policy.leg_roles)

    def test_ice_cme_cl_basis_policy(self) -> None:
        # ICE(spot)/CME(future) crude cash-and-carry — distinct from the
        # cme_wti_ice_brent_spread cross-product spread above: same instrument
        # (CL) on both legs, SPOT_LEG/FUTURE_LEG (not FUTURE_LEG/FUTURE_LEG).
        policy = routing_policy_for("ice_cme_cl_basis")
        assert policy.leg_venues == ("ice", "cme")
        assert policy.leg_roles == (
            CrossVenueLegRole.SPOT_LEG,
            CrossVenueLegRole.FUTURE_LEG,
        )
        assert policy.settlement_currency == "USD"


class TestHelpers:
    def test_unknown_policy_id_raises(self) -> None:
        with pytest.raises(PolicyNotFoundError, match="not in"):
            routing_policy_for("nonexistent_xyz")

    def test_policies_for_venue_pair_order_insensitive(self) -> None:
        forward = policies_for_venue_pair("ibkr", "cme")
        reverse = policies_for_venue_pair("cme", "ibkr")
        assert {p.policy_id for p in forward} == {p.policy_id for p in reverse}
        assert len(forward) >= 3  # 3 index basis + 1 option hedge

    def test_policies_for_usd_settlement(self) -> None:
        usd_policies = policies_for_settlement_currency("USD")
        assert len(usd_policies) >= 5
        assert all(p.settlement_currency == "USD" for p in usd_policies)

    def test_policies_for_usdt_settlement(self) -> None:
        usdt_policies = policies_for_settlement_currency("USDT")
        assert len(usdt_policies) >= 1

    def test_policies_for_missing_pair_empty(self) -> None:
        assert policies_for_venue_pair("deribit", "pancakeswap") == ()


class TestInvariants:
    def test_duplicate_policy_id_rejected(self) -> None:
        bad = (
            CrossVenueRoutingPolicy(
                policy_id="dup",
                leg_venues=("a", "b"),
                leg_roles=(CrossVenueLegRole.SPOT_LEG, CrossVenueLegRole.FUTURE_LEG),
                settlement_currency="USD",
                max_execution_spread_bps=10,
                leg_latency_p50_ms=100,
            ),
            CrossVenueRoutingPolicy(
                policy_id="dup",
                leg_venues=("c", "d"),
                leg_roles=(CrossVenueLegRole.SPOT_LEG, CrossVenueLegRole.FUTURE_LEG),
                settlement_currency="USD",
                max_execution_spread_bps=10,
                leg_latency_p50_ms=100,
            ),
        )
        with pytest.raises(ValueError, match="duplicate policy_id"):
            _validate_registry_invariants(bad)

    def test_mismatched_leg_lengths_rejected(self) -> None:
        bad = (
            CrossVenueRoutingPolicy(
                policy_id="p1",
                leg_venues=("a", "b", "c"),
                leg_roles=(CrossVenueLegRole.SPOT_LEG, CrossVenueLegRole.FUTURE_LEG),
                settlement_currency="USD",
                max_execution_spread_bps=10,
                leg_latency_p50_ms=100,
            ),
        )
        with pytest.raises(ValueError, match="equal length"):
            _validate_registry_invariants(bad)

    def test_single_leg_rejected(self) -> None:
        bad = (
            CrossVenueRoutingPolicy(
                policy_id="p1",
                leg_venues=("a",),
                leg_roles=(CrossVenueLegRole.SPOT_LEG,),
                settlement_currency="USD",
                max_execution_spread_bps=10,
                leg_latency_p50_ms=100,
            ),
        )
        with pytest.raises(ValueError, match=">=2 legs"):
            _validate_registry_invariants(bad)

    def test_lowercase_settlement_currency_rejected(self) -> None:
        bad = (
            CrossVenueRoutingPolicy(
                policy_id="p1",
                leg_venues=("a", "b"),
                leg_roles=(CrossVenueLegRole.SPOT_LEG, CrossVenueLegRole.FUTURE_LEG),
                settlement_currency="usd",
                max_execution_spread_bps=10,
                leg_latency_p50_ms=100,
            ),
        )
        with pytest.raises(ValueError, match="settlement_currency"):
            _validate_registry_invariants(bad)

    def test_negative_spread_rejected_by_pydantic(self) -> None:
        with pytest.raises(ValidationError):
            CrossVenueRoutingPolicy(
                policy_id="p1",
                leg_venues=("a", "b"),
                leg_roles=(CrossVenueLegRole.SPOT_LEG, CrossVenueLegRole.FUTURE_LEG),
                settlement_currency="USD",
                max_execution_spread_bps=-1,
                leg_latency_p50_ms=100,
            )


class TestConsumerReferences:
    def test_consumer_call_sites_non_empty(self) -> None:
        assert len(CONSUMER_CALL_SITES) >= 1

    def test_consumer_call_sites_target_routing_surfaces(self) -> None:
        # Must route to execution-service or strategy-service.
        assert any(s.startswith("execution-service/") for s in CONSUMER_CALL_SITES)
