"""Tests for the CostCapacityModel (Wave-2 #8, capability-wizard plan).

Validates: construction + frozen/extra-forbid; the fee stack sums the cited
``FEES_REGISTRY`` numbers; breakeven-AUM monotonicity (higher cost -> higher
breakeven); determinism; Decimal usage throughout; and the honest
capacity-ceiling gap.

Plan: ``plans/active/capability_wizard_and_manifest_2026_06_11.md`` Wave-2 #8.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from unified_api_contracts.canonical.crosscutting.lifecycle_class import LifecycleClass
from unified_api_contracts.internal.architecture_v2.cost_capacity import (
    CostCapacityModel,
    VenueFeeBreakdown,
    compute_cost_capacity,
)
from unified_api_contracts.internal.architecture_v2.fees_registry import (
    FEES_REGISTRY,
    FeeComponent,
    FeeUnit,
)

# Standard inputs reused across tests.
_NOTIONAL = Decimal("100000")
_GAS_GWEI = Decimal("20")
_ETH_USD = Decimal("3000")


def _model(
    *,
    venues: tuple[str, ...] = ("hyperliquid",),
    instrument_types: tuple[str, ...] = ("perp",),
    funding_rate_bps: Decimal = Decimal("0"),
    slippage_bps: Decimal = Decimal("0"),
    gas_price_gwei: Decimal = _GAS_GWEI,
    infra_cost_usd_per_day: Decimal = Decimal("0"),
    gross_edge_bps_per_year: Decimal = Decimal("100"),
    trades_per_year: Decimal = Decimal("1"),
    capacity_liquidity_bound_usd: Decimal | None = None,
) -> CostCapacityModel:
    return compute_cost_capacity(
        venues=venues,
        instrument_types=instrument_types,
        notional=_NOTIONAL,
        funding_rate_bps=funding_rate_bps,
        slippage_bps=slippage_bps,
        gas_price_gwei=gas_price_gwei,
        infra_cost_usd_per_day=infra_cost_usd_per_day,
        native_token_price_usd=_ETH_USD,
        gross_edge_bps_per_year=gross_edge_bps_per_year,
        trades_per_year=trades_per_year,
        capacity_liquidity_bound_usd=capacity_liquidity_bound_usd,
    )


# ---------------------------------------------------------------------------
# Construction + schema invariants
# ---------------------------------------------------------------------------


def test_constructs_and_is_frozen() -> None:
    m = _model()
    assert isinstance(m, CostCapacityModel)
    with pytest.raises(ValidationError):
        m.notional_usd = Decimal("1")  # type: ignore[misc]  # frozen


def test_extra_forbidden() -> None:
    with pytest.raises(ValidationError):
        VenueFeeBreakdown(
            venue_id="x",
            instrument_type="perp",
            notional_usd=Decimal("1"),
            taker_fee_bps=Decimal("0"),
            taker_fee_usd=Decimal("0"),
            slippage_bps=Decimal("0"),
            slippage_usd=Decimal("0"),
            funding_bps=Decimal("0"),
            funding_usd=Decimal("0"),
            gas_usd=Decimal("0"),
            total_usd=Decimal("0"),
            bogus="nope",  # type: ignore[call-arg]
        )


def test_all_money_fields_are_decimal() -> None:
    m = _model(slippage_bps=Decimal("3"), funding_rate_bps=Decimal("5"))
    for value in (
        m.notional_usd,
        m.total_fee_stack_usd,
        m.total_fee_stack_bps,
        m.annualised_trading_cost_usd,
        m.annualised_infra_cost_usd,
        m.annualised_total_cost_usd,
    ):
        assert isinstance(value, Decimal)
    assert m.breakeven_aum_usd is None or isinstance(m.breakeven_aum_usd, Decimal)
    for b in m.per_venue:
        assert isinstance(b.total_usd, Decimal)


# ---------------------------------------------------------------------------
# Fee stack sums the cited FEES_REGISTRY numbers
# ---------------------------------------------------------------------------


def _registry_taker_bps(venue_id: str, instrument_type: str) -> Decimal:
    for e in FEES_REGISTRY:
        if (
            e.venue_id == venue_id
            and e.component is FeeComponent.EXCHANGE_TAKER
            and e.unit is FeeUnit.BPS
            and e.instrument_type == instrument_type
        ):
            return e.value
    raise AssertionError(f"no taker entry for {venue_id}/{instrument_type}")


def test_taker_fee_transcribed_from_registry() -> None:
    """Hyperliquid perp taker fee in the model == the FEES_REGISTRY number."""
    m = _model(venues=("hyperliquid",), instrument_types=("perp",))
    cell = m.per_venue[0]
    expected_bps = _registry_taker_bps("hyperliquid", "perp")
    assert cell.taker_fee_bps == expected_bps
    assert cell.taker_fee_usd == _NOTIONAL * (expected_bps / Decimal("10000"))


def test_total_fee_stack_is_sum_of_cells() -> None:
    m = _model(venues=("hyperliquid", "binance"), instrument_types=("perp",), slippage_bps=Decimal("2"))
    assert m.total_fee_stack_usd == sum((b.total_usd for b in m.per_venue), Decimal("0"))
    assert len(m.per_venue) == 2


def test_defi_gas_uses_registry_units() -> None:
    """Uniswap v3 swap gas_usd = registry GAS units x gwei->ETH x ETH price."""
    m = _model(venues=("uniswap_v3",), instrument_types=("swap",))
    cell = m.per_venue[0]
    # FEES_REGISTRY: uniswap_v3 swap GAS = 150000 units.
    expected_gas_usd = Decimal("150000") * (_GAS_GWEI / Decimal("1000000000")) * _ETH_USD
    assert cell.gas_usd == expected_gas_usd
    assert cell.gas_usd > Decimal("0")


def test_cefi_venue_has_zero_gas() -> None:
    m = _model(venues=("binance",), instrument_types=("perp",))
    assert m.per_venue[0].gas_usd == Decimal("0")


def test_funding_only_applies_to_perp() -> None:
    perp = _model(venues=("binance",), instrument_types=("perp",), funding_rate_bps=Decimal("8"))
    spot = _model(venues=("binance",), instrument_types=("spot",), funding_rate_bps=Decimal("8"))
    assert perp.per_venue[0].funding_bps == Decimal("8")
    assert spot.per_venue[0].funding_bps == Decimal("0")


# ---------------------------------------------------------------------------
# Breakeven AUM
# ---------------------------------------------------------------------------


def test_breakeven_formula() -> None:
    m = _model(infra_cost_usd_per_day=Decimal("100"), gross_edge_bps_per_year=Decimal("200"))
    expected = m.annualised_total_cost_usd / (Decimal("200") / Decimal("10000"))
    assert m.breakeven_aum_usd == expected


def test_breakeven_none_when_no_positive_edge() -> None:
    assert _model(gross_edge_bps_per_year=Decimal("0")).breakeven_aum_usd is None
    assert _model(gross_edge_bps_per_year=Decimal("-5")).breakeven_aum_usd is None


def test_breakeven_monotonic_in_cost() -> None:
    """Higher cost (more infra, more slippage) -> strictly higher breakeven AUM."""
    cheap = _model(infra_cost_usd_per_day=Decimal("10"), slippage_bps=Decimal("1"))
    dear = _model(infra_cost_usd_per_day=Decimal("500"), slippage_bps=Decimal("10"))
    assert cheap.breakeven_aum_usd is not None
    assert dear.breakeven_aum_usd is not None
    assert dear.breakeven_aum_usd > cheap.breakeven_aum_usd


def test_breakeven_monotonic_decreasing_in_edge() -> None:
    """Higher gross edge -> lower breakeven AUM (same cost)."""
    lo_edge = _model(infra_cost_usd_per_day=Decimal("100"), gross_edge_bps_per_year=Decimal("50"))
    hi_edge = _model(infra_cost_usd_per_day=Decimal("100"), gross_edge_bps_per_year=Decimal("500"))
    assert lo_edge.breakeven_aum_usd is not None
    assert hi_edge.breakeven_aum_usd is not None
    assert hi_edge.breakeven_aum_usd < lo_edge.breakeven_aum_usd


def test_annualised_cost_components() -> None:
    m = _model(infra_cost_usd_per_day=Decimal("100"), trades_per_year=Decimal("250"))
    assert m.annualised_infra_cost_usd == Decimal("100") * Decimal("365")
    assert m.annualised_trading_cost_usd == m.total_fee_stack_usd * Decimal("250")
    assert m.annualised_total_cost_usd == m.annualised_trading_cost_usd + m.annualised_infra_cost_usd


# ---------------------------------------------------------------------------
# Capacity ceiling — honest gap
# ---------------------------------------------------------------------------


def test_capacity_ceiling_is_honest_gap_by_default() -> None:
    m = _model()
    assert m.capacity_ceiling_usd is None
    assert "HONEST GAP" in m.capacity_ceiling_note


def test_capacity_ceiling_populated_from_caller_bound() -> None:
    m = _model(capacity_liquidity_bound_usd=Decimal("5000000"))
    assert m.capacity_ceiling_usd == Decimal("5000000")
    assert "caller-supplied" in m.capacity_ceiling_note


def test_lifecycle_class_defaults_long_lived() -> None:
    assert _model().infra_lifecycle_class is LifecycleClass.LONG_LIVED_LIVE


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_deterministic() -> None:
    a = _model(slippage_bps=Decimal("3"), funding_rate_bps=Decimal("7"), infra_cost_usd_per_day=Decimal("42"))
    b = _model(slippage_bps=Decimal("3"), funding_rate_bps=Decimal("7"), infra_cost_usd_per_day=Decimal("42"))
    assert a == b
    assert a.model_dump() == b.model_dump()
