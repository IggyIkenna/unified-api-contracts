"""Unit tests for cross-venue position aggregation schemas.

Covers:
- AggregatedPosition, PortfolioView, PortfolioGreeksSnapshot, PortfolioPnLAttribution,
  RiskGroupSummary, DeFiAggregatedHealth, DeFiLPAggregatedMetrics,
  DeFiStakingAggregatedMetrics, SportsArbPosition
- Serialize / deserialize round-trip (model_dump -> model_validate)
- Decimal field precision preserved (no float corruption)
- extra="forbid" rejects unknown fields
- AggregatedPosition satisfies PositionQuantityProtocol (quantity, price, symbol properties)
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from unified_api_contracts import (
    AggregatedPosition,
    DeFiAggregatedHealth,
    DeFiLPAggregatedMetrics,
    DeFiStakingAggregatedMetrics,
    PortfolioGreeksSnapshot,
    PortfolioPnLAttribution,
    PortfolioView,
    RiskGroupSummary,
    SportsArbLeg,
    SportsArbPosition,
)

pytestmark = pytest.mark.unit

_TS = datetime(2026, 3, 16, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_aggregated_position(**overrides: object) -> AggregatedPosition:
    defaults: dict[str, object] = {
        "instrument_id": "BTC-USD-PERP",
        "net_quantity": Decimal("2.5"),
        "net_side": "LONG",
        "gross_quantity": Decimal("2.5"),
        "weighted_avg_entry_price": Decimal("50000"),
        "total_unrealized_pnl": Decimal("1250"),
        "mark_price": Decimal("50500"),
        "timestamp": _TS,
    }
    defaults.update(overrides)
    return AggregatedPosition(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# AggregatedPosition
# ---------------------------------------------------------------------------


def test_aggregated_position_round_trip() -> None:
    """AggregatedPosition serializes and deserializes without data loss."""
    pos = _make_aggregated_position(
        asset_class="crypto",
        instrument_type="PERPETUAL",
        strategy_id="trend-v1",
        underlying="BTC",
        denomination_currency="USD",
    )
    data = pos.model_dump(mode="python")
    restored = AggregatedPosition.model_validate(data)

    assert restored.instrument_id == pos.instrument_id
    assert restored.net_quantity == pos.net_quantity
    assert restored.gross_quantity == pos.gross_quantity
    assert restored.weighted_avg_entry_price == pos.weighted_avg_entry_price
    assert restored.total_unrealized_pnl == pos.total_unrealized_pnl
    assert restored.mark_price == pos.mark_price
    assert restored.asset_class == pos.asset_class
    assert restored.strategy_id == pos.strategy_id


def test_aggregated_position_decimal_precision_preserved() -> None:
    """High-precision Decimal values must not be truncated during serialization."""
    precise_qty = Decimal("1.23456789012345678")
    precise_price = Decimal("50123.456789")
    pos = _make_aggregated_position(
        net_quantity=precise_qty,
        gross_quantity=precise_qty,
        weighted_avg_entry_price=precise_price,
        mark_price=precise_price,
    )
    data = pos.model_dump(mode="python")
    restored = AggregatedPosition.model_validate(data)
    assert restored.net_quantity == precise_qty
    assert restored.weighted_avg_entry_price == precise_price


def test_aggregated_position_extra_fields_forbidden() -> None:
    """Unknown fields must be rejected (extra='forbid')."""
    with pytest.raises(ValidationError):
        AggregatedPosition(  # type: ignore[call-arg]
            instrument_id="BTC-USD-PERP",
            net_quantity=Decimal("1"),
            net_side="LONG",
            gross_quantity=Decimal("1"),
            unknown_field="should_fail",
        )


def test_aggregated_position_satisfies_position_quantity_protocol() -> None:
    """AggregatedPosition must expose .quantity, .price, .symbol (PositionQuantityProtocol)."""
    pos = _make_aggregated_position()
    # Protocol properties
    assert pos.quantity == pos.net_quantity
    assert pos.price == pos.weighted_avg_entry_price
    assert pos.symbol == pos.instrument_id


def test_aggregated_position_decimal_not_float() -> None:
    """All numeric fields must be Decimal instances, not float."""
    pos = _make_aggregated_position()
    assert isinstance(pos.net_quantity, Decimal)
    assert isinstance(pos.gross_quantity, Decimal)
    assert isinstance(pos.weighted_avg_entry_price, Decimal)
    assert isinstance(pos.total_unrealized_pnl, Decimal)
    assert isinstance(pos.mark_price, Decimal)


# ---------------------------------------------------------------------------
# PortfolioView
# ---------------------------------------------------------------------------


def test_portfolio_view_round_trip() -> None:
    """PortfolioView serializes and deserializes without data loss."""
    pos = _make_aggregated_position()
    view = PortfolioView(
        client_id="client-1",
        snapshot_id="snap-001",
        timestamp=_TS,
        positions=[pos],
        total_equity_usd=Decimal("100000"),
        total_unrealized_pnl=Decimal("1250"),
        gross_exposure=Decimal("125000"),
        net_exposure=Decimal("125000"),
        venue_count=1,
        instrument_count=1,
    )
    data = view.model_dump(mode="python")
    restored = PortfolioView.model_validate(data)

    assert restored.client_id == view.client_id
    assert restored.snapshot_id == view.snapshot_id
    assert restored.total_equity_usd == view.total_equity_usd
    assert restored.total_unrealized_pnl == view.total_unrealized_pnl
    assert len(restored.positions) == 1
    assert restored.positions[0].instrument_id == pos.instrument_id


def test_portfolio_view_extra_fields_forbidden() -> None:
    """Unknown fields on PortfolioView must be rejected."""
    with pytest.raises(ValidationError):
        PortfolioView(  # type: ignore[call-arg]
            client_id="c1",
            snapshot_id="s1",
            timestamp=_TS,
            not_a_field="oops",
        )


def test_portfolio_view_decimal_fields_are_decimal() -> None:
    """PortfolioView numeric fields must be Decimal."""
    view = PortfolioView(
        client_id="c1",
        snapshot_id="s1",
        timestamp=_TS,
        total_equity_usd=Decimal("50000"),
        gross_exposure=Decimal("25000"),
        net_exposure=Decimal("25000"),
    )
    assert isinstance(view.total_equity_usd, Decimal)
    assert isinstance(view.gross_exposure, Decimal)
    assert isinstance(view.net_exposure, Decimal)


# ---------------------------------------------------------------------------
# PortfolioGreeksSnapshot
# ---------------------------------------------------------------------------


def test_portfolio_greeks_snapshot_round_trip() -> None:
    """PortfolioGreeksSnapshot serializes and deserializes."""
    snap = PortfolioGreeksSnapshot(
        total_delta=Decimal("100"),
        total_gamma=Decimal("5"),
        total_theta=Decimal("-20"),
        total_vega=Decimal("50"),
        total_rho=Decimal("2"),
        timestamp=_TS,
    )
    data = snap.model_dump(mode="python")
    restored = PortfolioGreeksSnapshot.model_validate(data)
    assert restored.total_delta == snap.total_delta
    assert restored.total_gamma == snap.total_gamma
    assert restored.total_theta == snap.total_theta
    assert restored.total_vega == snap.total_vega


def test_portfolio_greeks_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        PortfolioGreeksSnapshot(total_delta=Decimal("1"), mystery_greek=Decimal("0"))  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# PortfolioPnLAttribution
# ---------------------------------------------------------------------------


def test_portfolio_pnl_attribution_round_trip() -> None:
    """All 11 PnL dimensions round-trip correctly."""
    pnl = PortfolioPnLAttribution(
        delta_pnl=Decimal("100"),
        gamma_pnl=Decimal("20"),
        theta_pnl=Decimal("-5"),
        vega_pnl=Decimal("30"),
        rho_pnl=Decimal("2"),
        funding_pnl=Decimal("-10"),
        basis_pnl=Decimal("5"),
        interest_rate_pnl=Decimal("1"),
        carry_pnl=Decimal("3"),
        fx_pnl=Decimal("-2"),
        residual_pnl=Decimal("1"),
        total_pnl=Decimal("145"),
        by_asset_class={"crypto": Decimal("145")},
        by_strategy={"trend-v1": Decimal("145")},
        timestamp=_TS,
    )
    data = pnl.model_dump(mode="python")
    restored = PortfolioPnLAttribution.model_validate(data)

    assert restored.delta_pnl == pnl.delta_pnl
    assert restored.gamma_pnl == pnl.gamma_pnl
    assert restored.theta_pnl == pnl.theta_pnl
    assert restored.vega_pnl == pnl.vega_pnl
    assert restored.rho_pnl == pnl.rho_pnl
    assert restored.funding_pnl == pnl.funding_pnl
    assert restored.basis_pnl == pnl.basis_pnl
    assert restored.interest_rate_pnl == pnl.interest_rate_pnl
    assert restored.carry_pnl == pnl.carry_pnl
    assert restored.fx_pnl == pnl.fx_pnl
    assert restored.residual_pnl == pnl.residual_pnl
    assert restored.total_pnl == pnl.total_pnl


def test_portfolio_pnl_attribution_extra_forbidden() -> None:
    with pytest.raises(ValidationError):
        PortfolioPnLAttribution(delta_pnl=Decimal("0"), phantom=Decimal("0"))  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# RiskGroupSummary
# ---------------------------------------------------------------------------


def test_risk_group_summary_round_trip() -> None:
    rgs = RiskGroupSummary(
        risk_group_id="btc-perp",
        underlying="BTC",
        asset_class="crypto",
        net_delta=Decimal("2.5"),
        net_gamma=Decimal("0.1"),
        gross_exposure=Decimal("125000"),
        net_exposure=Decimal("125000"),
        position_count=3,
        venues=["binance", "bybit"],
        instruments=["BTC-USD-PERP", "BTC-USD-FUT"],
    )
    data = rgs.model_dump(mode="python")
    restored = RiskGroupSummary.model_validate(data)
    assert restored.risk_group_id == rgs.risk_group_id
    assert restored.net_delta == rgs.net_delta
    assert restored.gross_exposure == rgs.gross_exposure
    assert restored.venues == rgs.venues
    assert restored.position_count == rgs.position_count


def test_risk_group_extra_forbidden() -> None:
    with pytest.raises(ValidationError):
        RiskGroupSummary(  # type: ignore[call-arg]
            risk_group_id="x",
            underlying="BTC",
            asset_class="crypto",
            extra_key="bad",
        )


# ---------------------------------------------------------------------------
# DeFiAggregatedHealth
# ---------------------------------------------------------------------------


def test_defi_aggregated_health_round_trip() -> None:
    health = DeFiAggregatedHealth(
        client_id="c1",
        combined_collateral_usd=Decimal("10000"),
        combined_debt_usd=Decimal("5000"),
        combined_health_factor=Decimal("2.0"),
        weighted_net_apy=Decimal("0.05"),
        riskiest_protocol="aave",
        per_chain_health={"ethereum": Decimal("2.0"), "polygon": Decimal("1.8")},
        timestamp=_TS,
    )
    data = health.model_dump(mode="python")
    restored = DeFiAggregatedHealth.model_validate(data)
    assert restored.combined_health_factor == health.combined_health_factor
    assert restored.per_chain_health["ethereum"] == Decimal("2.0")
    assert restored.riskiest_protocol == "aave"


def test_defi_aggregated_health_no_debt_health_factor_none() -> None:
    """combined_health_factor may be None when no debt exists."""
    health = DeFiAggregatedHealth(
        client_id="c1",
        combined_collateral_usd=Decimal("10000"),
        combined_debt_usd=Decimal("0"),
        combined_health_factor=None,
    )
    assert health.combined_health_factor is None


def test_defi_aggregated_health_decimal_fields() -> None:
    health = DeFiAggregatedHealth(
        client_id="c1",
        combined_collateral_usd=Decimal("10000"),
        combined_debt_usd=Decimal("5000"),
        combined_health_factor=Decimal("2"),
    )
    assert isinstance(health.combined_collateral_usd, Decimal)
    assert isinstance(health.combined_debt_usd, Decimal)
    assert isinstance(health.combined_health_factor, Decimal)


# ---------------------------------------------------------------------------
# DeFiLPAggregatedMetrics
# ---------------------------------------------------------------------------


def test_defi_lp_aggregated_metrics_round_trip() -> None:
    lp = DeFiLPAggregatedMetrics(
        client_id="c1",
        total_lp_value_usd=Decimal("50000"),
        total_fees_earned_usd=Decimal("500"),
        total_impermanent_loss_usd=Decimal("-100"),
        timestamp=_TS,
    )
    data = lp.model_dump(mode="python")
    restored = DeFiLPAggregatedMetrics.model_validate(data)
    assert restored.total_lp_value_usd == lp.total_lp_value_usd
    assert restored.total_fees_earned_usd == lp.total_fees_earned_usd
    assert restored.total_impermanent_loss_usd == lp.total_impermanent_loss_usd


def test_defi_lp_decimal_precision() -> None:
    """High-precision LP value must round-trip without loss."""
    precise = Decimal("12345.678901234567")
    lp = DeFiLPAggregatedMetrics(client_id="c1", total_lp_value_usd=precise)
    data = lp.model_dump(mode="python")
    restored = DeFiLPAggregatedMetrics.model_validate(data)
    assert restored.total_lp_value_usd == precise


# ---------------------------------------------------------------------------
# DeFiStakingAggregatedMetrics
# ---------------------------------------------------------------------------


def test_defi_staking_aggregated_metrics_round_trip() -> None:
    staking = DeFiStakingAggregatedMetrics(
        client_id="c1",
        total_staked_value_usd=Decimal("100000"),
        total_rewards_earned_usd=Decimal("2000"),
        weighted_apy=Decimal("0.042"),
        timestamp=_TS,
    )
    data = staking.model_dump(mode="python")
    restored = DeFiStakingAggregatedMetrics.model_validate(data)
    assert restored.total_staked_value_usd == staking.total_staked_value_usd
    assert restored.weighted_apy == staking.weighted_apy
    assert isinstance(restored.weighted_apy, Decimal)


def test_defi_staking_extra_forbidden() -> None:
    with pytest.raises(ValidationError):
        DeFiStakingAggregatedMetrics(client_id="c1", mystery_field="bad")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# SportsArbPosition
# ---------------------------------------------------------------------------


def test_sports_arb_position_round_trip() -> None:
    """SportsArbPosition with two legs serializes and deserializes."""
    leg_back = SportsArbLeg(
        venue="betfair",
        side="BACK",
        stake=Decimal("100"),
        odds=Decimal("2.1"),
        commission_rate=Decimal("0.05"),
        commission_amount=Decimal("5"),
    )
    leg_lay = SportsArbLeg(
        venue="smarkets",
        side="LAY",
        stake=Decimal("95"),
        odds=Decimal("2.0"),
        commission_rate=Decimal("0.02"),
        commission_amount=Decimal("1.9"),
    )
    arb = SportsArbPosition(
        fixture_id="match-2026-03-16-001",
        market_type="match_winner",
        selection="home_team",
        legs=[leg_back, leg_lay],
        net_exposure=Decimal("5"),
        guaranteed_pnl=Decimal("3.1"),
        total_commission=Decimal("6.9"),
        net_pnl_after_commission=Decimal("3.1"),
        is_arb=True,
        timestamp=_TS,
    )
    data = arb.model_dump(mode="python")
    restored = SportsArbPosition.model_validate(data)

    assert restored.fixture_id == arb.fixture_id
    assert restored.market_type == arb.market_type
    assert restored.selection == arb.selection
    assert restored.is_arb is True
    assert restored.guaranteed_pnl == arb.guaranteed_pnl
    assert restored.net_pnl_after_commission == arb.net_pnl_after_commission
    assert len(restored.legs) == 2
    assert restored.legs[0].venue == "betfair"
    assert restored.legs[1].venue == "smarkets"


def test_sports_arb_position_decimal_fields() -> None:
    arb = SportsArbPosition(
        fixture_id="f1",
        market_type="match_winner",
        selection="home",
        net_exposure=Decimal("10"),
        guaranteed_pnl=Decimal("5"),
        net_pnl_after_commission=Decimal("4"),
    )
    assert isinstance(arb.net_exposure, Decimal)
    assert isinstance(arb.guaranteed_pnl, Decimal)
    assert isinstance(arb.net_pnl_after_commission, Decimal)


def test_sports_arb_leg_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        SportsArbLeg(  # type: ignore[call-arg]
            venue="betfair",
            side="BACK",
            stake=Decimal("100"),
            odds=Decimal("2.0"),
            not_a_field="bad",
        )


def test_sports_arb_position_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        SportsArbPosition(  # type: ignore[call-arg]
            fixture_id="f1",
            market_type="m",
            selection="s",
            unknown_field="bad",
        )


# ---------------------------------------------------------------------------
# Cross-schema: Decimal precision (0.1 + 0.2 = 0.3 boundary)
# ---------------------------------------------------------------------------


def test_decimal_no_float_0_1_plus_0_2_boundary() -> None:
    """The classic float 0.1+0.2 must equal Decimal('0.3') when using Decimal."""
    pos1 = _make_aggregated_position(net_quantity=Decimal("0.1"))
    pos2 = _make_aggregated_position(net_quantity=Decimal("0.2"))
    combined = pos1.net_quantity + pos2.net_quantity
    # Decimal arithmetic is exact; this would fail with float
    assert combined == Decimal("0.3")
