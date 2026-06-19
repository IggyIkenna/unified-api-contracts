"""Benchmark fill pricing — the SINGLE simulation-fill pricing SSOT.

The canonical per-mode pricing primitives for ``BenchmarkFillMode``. BOTH the
strategy-service ``BenchmarkFillEngine`` (Group B backtest) AND the
execution-service ``BenchmarkFillRegistry`` (paper / Group C) import these, so
the simulated fill PRICE for a given (mode, market context) is computed by ONE
function and cannot drift between batch and paper.

This is the heart of the determinism spine: paper(W) ≡ batch-rerun(W) requires a
single fill model. ``BenchmarkFillMode`` (the enum) was already shared; this
module makes the PRICING shared too.

SSOT: codex/09-strategy/operational/paper-batch-live-reconciliation.md §4.2
Plan: plans/active/citadel_paper_batch_live_reconciliation_2026_06_19.md Phase 1.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal

from unified_api_contracts.internal.architecture_v2.enums import BenchmarkFillMode

BenchmarkPricingContext = Mapping[str, Decimal]
"""Market-context keys a pricing fn may read: ``bid``, ``ask``, ``side``,
``twap_price``, ``vwap_price``, ``pool_mid``, ``collateral_price``,
``bonus_multiplier``, ``funding_rate``. Both engines build this mapping."""


@dataclass(frozen=True)
class FillPricingResult:
    """The benchmark price for a mode + a short provenance note."""

    mode: BenchmarkFillMode
    price: Decimal
    notes: str = ""


def _arrival_mid(ctx: BenchmarkPricingContext) -> FillPricingResult:
    bid = ctx["bid"]
    ask = ctx["ask"]
    return FillPricingResult(BenchmarkFillMode.ARRIVAL_MID, (bid + ask) / Decimal("2"), "arrival mid")


def _twap_window(ctx: BenchmarkPricingContext) -> FillPricingResult:
    if "twap_price" not in ctx:
        raise KeyError("twap_window benchmark requires 'twap_price'")
    return FillPricingResult(BenchmarkFillMode.TWAP_WINDOW, ctx["twap_price"], "TWAP over window")


def _vwap_window(ctx: BenchmarkPricingContext) -> FillPricingResult:
    if "vwap_price" not in ctx:
        raise KeyError("vwap_window benchmark requires 'vwap_price'")
    return FillPricingResult(BenchmarkFillMode.VWAP_WINDOW, ctx["vwap_price"], "VWAP over window")


def _passive_bbo(ctx: BenchmarkPricingContext) -> FillPricingResult:
    side = ctx.get("side", Decimal("0"))
    price = ctx["bid"] if side > 0 else ctx["ask"]
    return FillPricingResult(BenchmarkFillMode.PASSIVE_BBO, price, "passive BBO")


def _pool_mid_at_block(ctx: BenchmarkPricingContext) -> FillPricingResult:
    if "pool_mid" not in ctx:
        raise KeyError("pool_mid_at_block benchmark requires 'pool_mid'")
    return FillPricingResult(BenchmarkFillMode.POOL_MID_AT_BLOCK, ctx["pool_mid"], "AMM pool mid at block")


def _liquidation_bonus(ctx: BenchmarkPricingContext) -> FillPricingResult:
    if "collateral_price" not in ctx or "bonus_multiplier" not in ctx:
        raise KeyError("liquidation_bonus benchmark requires 'collateral_price' and 'bonus_multiplier'")
    return FillPricingResult(
        BenchmarkFillMode.LIQUIDATION_BONUS,
        ctx["collateral_price"] * ctx["bonus_multiplier"],
        "liquidation bonus applied",
    )


def _funding_snapshot(ctx: BenchmarkPricingContext) -> FillPricingResult:
    if "funding_rate" not in ctx:
        raise KeyError("funding_snapshot benchmark requires 'funding_rate'")
    return FillPricingResult(BenchmarkFillMode.FUNDING_SNAPSHOT, ctx["funding_rate"], "funding rate snapshot")


BenchmarkPricingFn = Callable[[BenchmarkPricingContext], FillPricingResult]

DEFAULT_BENCHMARK_PRICING_FNS: dict[BenchmarkFillMode, BenchmarkPricingFn] = {
    BenchmarkFillMode.ARRIVAL_MID: _arrival_mid,
    BenchmarkFillMode.TWAP_WINDOW: _twap_window,
    BenchmarkFillMode.VWAP_WINDOW: _vwap_window,
    BenchmarkFillMode.PASSIVE_BBO: _passive_bbo,
    BenchmarkFillMode.POOL_MID_AT_BLOCK: _pool_mid_at_block,
    BenchmarkFillMode.LIQUIDATION_BONUS: _liquidation_bonus,
    BenchmarkFillMode.FUNDING_SNAPSHOT: _funding_snapshot,
}
"""The canonical default pricing fn per mode. A runtime registry seeds from
this; both batch and paper resolve a benchmark price through it."""


def benchmark_fill_price(mode: BenchmarkFillMode, ctx: BenchmarkPricingContext) -> FillPricingResult:
    """Resolve the canonical benchmark fill price for ``mode`` given ``ctx``.

    The single entry point both the strategy-service and execution-service
    benchmark fill engines call — guaranteeing one price per (mode, context).
    """

    fn = DEFAULT_BENCHMARK_PRICING_FNS.get(mode)
    if fn is None:
        raise KeyError(f"no benchmark pricing fn for {mode.value}")
    return fn(ctx)


__all__ = [
    "DEFAULT_BENCHMARK_PRICING_FNS",
    "BenchmarkPricingContext",
    "BenchmarkPricingFn",
    "FillPricingResult",
    "benchmark_fill_price",
]
