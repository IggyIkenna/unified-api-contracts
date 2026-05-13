"""Tests for STABLECOIN_EMERGENCY_EXIT_ROUTES registry and get_emergency_exit_routes helper (D.6).

Coverage: registry lookup, sort by cost, missing stable, size-overflow handling,
route validation, multi-target routes, edge case (no routes for stable), ≥30 seeded
routes coverage, priority_rank ordering, all 8 stables present.
"""

from __future__ import annotations

from decimal import Decimal

from unified_api_contracts.registry.stablecoin_exit_routes import (
    STABLECOIN_EMERGENCY_EXIT_ROUTES,
    ExitRoute,
    get_emergency_exit_routes,
)

# ── Test 1: Registry contains all 8 required stables ─────────────────────


def test_registry_contains_all_stables() -> None:
    """Registry has all 8 required stablecoin entries."""
    required = {"USDC", "USDT", "DAI", "USDE", "FRAX", "GHO", "CRVUSD", "PYUSD"}
    assert required.issubset(set(STABLECOIN_EMERGENCY_EXIT_ROUTES.keys()))


# ── Test 2: At least 30 total routes seeded ──────────────────────────────


def test_at_least_30_routes_total() -> None:
    """Registry has ≥30 routes seeded across all stables."""
    total = sum(len(routes) for routes in STABLECOIN_EMERGENCY_EXIT_ROUTES.values())
    assert total >= 30, f"Expected ≥30 routes, got {total}"


# ── Test 3: Registry lookup returns correct routes ────────────────────────


def test_registry_lookup_usdc() -> None:
    """Direct registry lookup for USDC returns its routes."""
    routes = STABLECOIN_EMERGENCY_EXIT_ROUTES.get("USDC")
    assert routes is not None
    assert len(routes) >= 4  # spec requires ≥4 paths for USDC
    route_ids = [r.route_id for r in routes]
    assert any("USDC" in rid for rid in route_ids)


# ── Test 4: get_emergency_exit_routes sorts by cost ascending ────────────


def test_get_emergency_exit_routes_sorted_cheapest_first() -> None:
    """Helper returns routes sorted by (slippage + gas) cost ascending."""
    routes = get_emergency_exit_routes("USDC", Decimal("100000"))
    assert len(routes) >= 1

    # Cost of each route should be ≥ cost of previous
    costs: list[Decimal] = []
    for r in routes:
        slippage_cost = (r.expected_slippage_bps_at_size / Decimal("10000")) * Decimal("100000")
        total = slippage_cost + r.estimated_gas_cost_usd
        costs.append(total)

    for i in range(1, len(costs)):
        assert costs[i] >= costs[i - 1], (
            f"Route at index {i} (cost={costs[i]}) is cheaper than index {i - 1} (cost={costs[i - 1]})"
        )


# ── Test 5: Missing stable returns empty list ─────────────────────────────


def test_missing_stable_returns_empty_list() -> None:
    """get_emergency_exit_routes returns [] for unknown stable."""
    result = get_emergency_exit_routes("LUSD", Decimal("100000"))
    assert result == []


# ── Test 6: Case-insensitive stable lookup ────────────────────────────────


def test_case_insensitive_stable_lookup() -> None:
    """Helper normalises stable symbol to uppercase."""
    result_upper = get_emergency_exit_routes("USDC", Decimal("100000"))
    result_lower = get_emergency_exit_routes("usdc", Decimal("100000"))
    assert result_upper == result_lower


# ── Test 7: Size-overflow handling — undersized routes rank last ──────────


def test_size_overflow_routes_ranked_last() -> None:
    """Routes with typical_exit_size_usd < 10% of exit_size_usd rank after normal routes."""
    # Create a tiny route and a normal route and verify tiny ranks last
    tiny_route = ExitRoute(
        route_id="USDC_TINY",
        stable="USDC",
        target="ETH",
        venue="UNISWAP_V3",
        typical_exit_size_usd=Decimal("100"),  # tiny vs 10M exit
        expected_slippage_bps_at_size=Decimal("1"),  # cheapest slippage
        estimated_gas_cost_usd=Decimal("1"),
        priority_rank=1,
    )
    normal_route = ExitRoute(
        route_id="USDC_NORMAL",
        stable="USDC",
        target="ETH",
        venue="BINANCE_SPOT",
        typical_exit_size_usd=Decimal("1000000"),
        expected_slippage_bps_at_size=Decimal("50"),  # higher slippage
        estimated_gas_cost_usd=Decimal("0"),
        priority_rank=2,
    )

    from unittest.mock import patch

    from unified_api_contracts.registry import stablecoin_exit_routes as mod

    patched_registry = {"USDC": (tiny_route, normal_route)}
    with patch.object(mod, "STABLECOIN_EMERGENCY_EXIT_ROUTES", patched_registry):
        routes = get_emergency_exit_routes("USDC", Decimal("10000000"))

    # Normal route (despite higher slippage) should rank before the tiny undersized route
    assert routes[0].route_id == "USDC_NORMAL"
    assert routes[1].route_id == "USDC_TINY"


# ── Test 8: Route validation — required fields present ───────────────────


def test_all_routes_have_required_fields() -> None:
    """Every seeded route has all required fields set."""
    for stable, routes in STABLECOIN_EMERGENCY_EXIT_ROUTES.items():
        for r in routes:
            assert r.route_id, f"{stable} route missing route_id"
            assert r.stable == stable, f"route.stable ({r.stable}) != registry key ({stable})"
            assert r.target, f"{stable}/{r.route_id} missing target"
            assert r.venue, f"{stable}/{r.route_id} missing venue"
            assert r.typical_exit_size_usd > Decimal("0"), (
                f"{stable}/{r.route_id} has non-positive typical_exit_size_usd"
            )
            assert r.expected_slippage_bps_at_size >= Decimal("0"), f"{stable}/{r.route_id} has negative slippage"
            assert r.estimated_gas_cost_usd >= Decimal("0"), f"{stable}/{r.route_id} has negative gas cost"
            assert r.priority_rank >= 1, f"{stable}/{r.route_id} priority_rank < 1"


# ── Test 9: Multi-target routes (ETH and WBTC for USDC) ──────────────────


def test_usdc_has_multi_target_routes() -> None:
    """USDC registry has routes targeting both ETH and WBTC."""
    routes = STABLECOIN_EMERGENCY_EXIT_ROUTES["USDC"]
    targets = {r.target for r in routes}
    assert "ETH" in targets
    assert "WBTC" in targets


# ── Test 10: Edge case — no routes for stable ─────────────────────────────


def test_helper_with_no_registry_entry() -> None:
    """get_emergency_exit_routes returns [] for stables with no registry entry."""
    result = get_emergency_exit_routes("NONEXISTENT_STABLE", Decimal("500000"))
    assert result == []


# ── Test 11: DEX routes have non-empty pool_address ──────────────────────


def test_dex_routes_have_pool_addresses() -> None:
    """Routes on UNISWAP_V3 and CURVE have non-empty pool_address."""
    for stable, routes in STABLECOIN_EMERGENCY_EXIT_ROUTES.items():
        for r in routes:
            if r.venue in ("UNISWAP_V3", "CURVE"):
                assert r.pool_address, f"{stable}/{r.route_id}: DEX route on {r.venue} missing pool_address"


# ── Test 12: CEX routes have empty pool_address ──────────────────────────


def test_cex_routes_have_no_pool_address() -> None:
    """Routes on CEX venues (BINANCE_SPOT, COINBASE_SPOT) have empty pool_address."""
    for stable, routes in STABLECOIN_EMERGENCY_EXIT_ROUTES.items():
        for r in routes:
            if r.venue in ("BINANCE_SPOT", "COINBASE_SPOT"):
                assert r.pool_address == "", (
                    f"{stable}/{r.route_id}: CEX route has unexpected pool_address={r.pool_address!r}"
                )
