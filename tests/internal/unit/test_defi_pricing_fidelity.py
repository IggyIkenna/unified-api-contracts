"""Tests for G2.9 gap #8 — DeFi spot PricingFidelity."""

from __future__ import annotations

import pytest

from unified_api_contracts.internal.architecture_v2.defi_pricing_fidelity import (
    CONSUMER_CALL_SITES,
    DEFI_SPOT_VENUE_FIDELITY,
    DefiPoolNotRegisteredError,
    DefiSpotVenueCapability,
    PricingFidelity,
    _validate_registry_invariants,
    fidelity_for,
    pools_at_fidelity,
    pools_for_pair,
)


class TestRegistryShape:
    def test_registry_not_empty(self) -> None:
        assert len(DEFI_SPOT_VENUE_FIDELITY) >= 5

    def test_all_pools_unique(self) -> None:
        keys = [(e.venue_id, e.chain, e.pool_id) for e in DEFI_SPOT_VENUE_FIDELITY]
        assert len(keys) == len(set(keys))


class TestContent:
    def test_uniswap_usdc_weth_tick_stream(self) -> None:
        pools = pools_for_pair("USDC", "WETH")
        assert len(pools) >= 1
        eth_main = [p for p in pools if p.chain == "ETHEREUM" and p.venue_id == "uniswap_v3"]
        assert eth_main[0].pricing_fidelity is PricingFidelity.TICK_STREAM

    def test_pancakeswap_twap_only(self) -> None:
        results = pools_at_fidelity(PricingFidelity.DERIVED_TWAP)
        assert any(p.venue_id == "pancakeswap" for p in results)

    def test_curve_3pool(self) -> None:
        results = pools_for_pair("USDC", "USDT")
        assert any(p.venue_id == "curve" for p in results)

    def test_long_tail_snapshot_only(self) -> None:
        snapshots = pools_at_fidelity(PricingFidelity.SNAPSHOT)
        assert len(snapshots) >= 1


class TestHelpers:
    def test_fidelity_for_unknown_pool_raises(self) -> None:
        with pytest.raises(DefiPoolNotRegisteredError):
            fidelity_for("nonexistent", "ETHEREUM", "0xdeadbeef")

    def test_pools_for_pair_order_insensitive(self) -> None:
        forward = pools_for_pair("USDC", "WETH")
        reverse = pools_for_pair("WETH", "USDC")
        assert {p.pool_id for p in forward} == {p.pool_id for p in reverse}

    def test_pools_at_tick_stream(self) -> None:
        results = pools_at_fidelity(PricingFidelity.TICK_STREAM)
        assert len(results) >= 3

    def test_pools_for_unknown_pair_empty(self) -> None:
        assert pools_for_pair("MADEUP1", "MADEUP2") == ()


class TestInvariants:
    def test_duplicate_pool_rejected(self) -> None:
        bad = (
            DefiSpotVenueCapability(
                venue_id="dex",
                chain="ETHEREUM",
                pool_id="0x1",
                token_pair=("A", "B"),
                pricing_fidelity=PricingFidelity.TICK_STREAM,
                tick_stream_source="subgraph_events",
                pool_tvl_usd_min_for_fidelity=1000,
            ),
            DefiSpotVenueCapability(
                venue_id="dex",
                chain="ETHEREUM",
                pool_id="0x1",
                token_pair=("C", "D"),
                pricing_fidelity=PricingFidelity.SNAPSHOT,
                tick_stream_source="rpc_poll",
                pool_tvl_usd_min_for_fidelity=1000,
            ),
        )
        with pytest.raises(ValueError, match="duplicate"):
            _validate_registry_invariants(bad)

    def test_same_tokens_rejected(self) -> None:
        bad = (
            DefiSpotVenueCapability(
                venue_id="dex",
                chain="ETHEREUM",
                pool_id="0x1",
                token_pair=("USDC", "USDC"),
                pricing_fidelity=PricingFidelity.TICK_STREAM,
                tick_stream_source="subgraph_events",
                pool_tvl_usd_min_for_fidelity=1000,
            ),
        )
        with pytest.raises(ValueError, match="tokens must differ"):
            _validate_registry_invariants(bad)

    def test_lowercase_tokens_rejected(self) -> None:
        bad = (
            DefiSpotVenueCapability(
                venue_id="dex",
                chain="ETHEREUM",
                pool_id="0x1",
                token_pair=("usdc", "WETH"),
                pricing_fidelity=PricingFidelity.TICK_STREAM,
                tick_stream_source="subgraph_events",
                pool_tvl_usd_min_for_fidelity=1000,
            ),
        )
        with pytest.raises(ValueError, match="uppercase"):
            _validate_registry_invariants(bad)

    def test_none_fidelity_rejected(self) -> None:
        bad = (
            DefiSpotVenueCapability(
                venue_id="dex",
                chain="ETHEREUM",
                pool_id="0x1",
                token_pair=("A", "B"),
                pricing_fidelity=PricingFidelity.NONE,
                tick_stream_source="none",
                pool_tvl_usd_min_for_fidelity=0,
            ),
        )
        with pytest.raises(ValueError, match="NONE fidelity"):
            _validate_registry_invariants(bad)


class TestConsumerReferences:
    def test_consumer_call_sites_non_empty(self) -> None:
        assert len(CONSUMER_CALL_SITES) >= 1
