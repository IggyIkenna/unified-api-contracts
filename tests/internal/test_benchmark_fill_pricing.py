"""Unit tests for the benchmark-fill pricing SSOT (Phase 1 — fill-model unify).

The single per-mode pricing function both the strategy-service and
execution-service benchmark fill engines call, so a simulated fill price cannot
drift between batch and paper.

SSOT: codex/09-strategy/operational/paper-batch-live-reconciliation.md §4.2
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from unified_api_contracts.internal import (
    DEFAULT_BENCHMARK_PRICING_FNS,
    BenchmarkFillMode,
    FillPricingResult,
    benchmark_fill_price,
)


def test_arrival_mid_is_bid_ask_midpoint() -> None:
    r = benchmark_fill_price(BenchmarkFillMode.ARRIVAL_MID, {"bid": Decimal("100"), "ask": Decimal("102")})
    assert isinstance(r, FillPricingResult)
    assert r.mode is BenchmarkFillMode.ARRIVAL_MID
    assert r.price == Decimal("101")


def test_passive_bbo_picks_side() -> None:
    ctx_buy = {"bid": Decimal("100"), "ask": Decimal("102"), "side": Decimal("1")}
    ctx_sell = {"bid": Decimal("100"), "ask": Decimal("102"), "side": Decimal("-1")}
    assert benchmark_fill_price(BenchmarkFillMode.PASSIVE_BBO, ctx_buy).price == Decimal("100")
    assert benchmark_fill_price(BenchmarkFillMode.PASSIVE_BBO, ctx_sell).price == Decimal("102")


@pytest.mark.parametrize(
    ("mode", "ctx", "expected"),
    [
        (BenchmarkFillMode.TWAP_WINDOW, {"twap_price": Decimal("50")}, Decimal("50")),
        (BenchmarkFillMode.VWAP_WINDOW, {"vwap_price": Decimal("51")}, Decimal("51")),
        (BenchmarkFillMode.POOL_MID_AT_BLOCK, {"pool_mid": Decimal("52")}, Decimal("52")),
        (BenchmarkFillMode.FUNDING_SNAPSHOT, {"funding_rate": Decimal("0.0003")}, Decimal("0.0003")),
        (
            BenchmarkFillMode.LIQUIDATION_BONUS,
            {"collateral_price": Decimal("10"), "bonus_multiplier": Decimal("1.05")},
            Decimal("10.50"),
        ),
    ],
)
def test_mode_prices(mode: BenchmarkFillMode, ctx: dict[str, Decimal], expected: Decimal) -> None:
    assert benchmark_fill_price(mode, ctx).price == expected


def test_missing_context_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        benchmark_fill_price(BenchmarkFillMode.TWAP_WINDOW, {"bid": Decimal("1")})


def test_determinism_same_inputs_same_price() -> None:
    ctx = {"bid": Decimal("100.25"), "ask": Decimal("100.75")}
    a = benchmark_fill_price(BenchmarkFillMode.ARRIVAL_MID, ctx)
    b = benchmark_fill_price(BenchmarkFillMode.ARRIVAL_MID, dict(ctx))
    assert a == b


def test_registry_covers_seeded_modes() -> None:
    # Every seeded mode resolves through the single entry point.
    for mode in DEFAULT_BENCHMARK_PRICING_FNS:
        assert DEFAULT_BENCHMARK_PRICING_FNS[mode] is not None
    assert len(DEFAULT_BENCHMARK_PRICING_FNS) == 7
