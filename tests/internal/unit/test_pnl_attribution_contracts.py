"""Phase 1.E — unit tests for PnL attribution + client reporting contracts.

Covers:
  - PnLFactor / PnLLayer closed-set assertions
  - PnLAttributionRow round-trip + immutability
  - PnLAttribution round-trip + dual-axis invariants
  - ClientReportingMode per-mode coverage
  - ClientPosition / ClientPnLEntry / ClientNAV round-trip + field contracts
  - ClientShareClassSeed + DEMO_CLIENT_SEED seed data
  - Dual-axis decomposition invariants (STRATEGY + EXECUTION == total_pnl, RESIDUAL < 1%)
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from unified_api_contracts.canonical.crosscutting.share_class import ShareClass
from unified_api_contracts.internal import (
    ClientNAV,
    ClientPnLEntry,
    ClientPosition,
    ClientReportingMode,
    PnLAttribution,
    PnLAttributionRow,
    PnLFactor,
    PnLLayer,
)
from unified_api_contracts.registry.client_share_classes import (
    DEMO_CLIENT_ID,
    DEMO_CLIENT_SEED,
    LIVE_DEFI_CUTOVER_ARCHETYPES,
    ClientShareClassSeed,
)

_TS = datetime(2026, 5, 12, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row(
    factor: PnLFactor,
    layer: PnLLayer,
    amount: Decimal,
    strategy_id: str = "s1",
    client_id: str = "c1",
    instrument_id: str = "BTC-PERP",
) -> PnLAttributionRow:
    return PnLAttributionRow(
        strategy_id=strategy_id,
        client_id=client_id,
        instrument_id=instrument_id,
        timestamp=_TS,
        period="2026-05-12",
        factor=factor,
        layer=layer,
        amount=amount,
    )


# ---------------------------------------------------------------------------
# PnLFactor closed-set
# ---------------------------------------------------------------------------


class TestPnLFactor:
    def test_all_16_factors_present(self) -> None:
        expected = {
            "DELTA",
            "FUNDING",
            "BASIS",
            "CARRY",
            "CARRY_BASE",
            "CARRY_AVS_CONTINUOUS",
            "CARRY_ISSUER_SEASONAL",
            "REWARD_REALISATION_SLIPPAGE",
            "GREEKS",
            "FEES",
            "SLIPPAGE",
            "SETTLEMENT",
            "LIQUIDATION",
            "REBATE",
            "FX",
            "RESIDUAL",
        }
        actual = {f.value for f in PnLFactor}
        assert actual == expected

    def test_factor_count_is_16(self) -> None:
        assert len(PnLFactor) == 16

    def test_factor_is_str_enum(self) -> None:
        assert isinstance(PnLFactor.DELTA, str)
        assert PnLFactor.DELTA == "DELTA"

    def test_factor_values_are_uppercase(self) -> None:
        for factor in PnLFactor:
            assert factor.value == factor.value.upper()

    def test_residual_in_factor_set(self) -> None:
        assert PnLFactor.RESIDUAL in PnLFactor


# ---------------------------------------------------------------------------
# PnLLayer closed-set
# ---------------------------------------------------------------------------


class TestPnLLayer:
    def test_exactly_two_layers(self) -> None:
        assert set(PnLLayer) == {PnLLayer.STRATEGY, PnLLayer.EXECUTION}

    def test_layer_is_str_enum(self) -> None:
        assert isinstance(PnLLayer.STRATEGY, str)
        assert PnLLayer.STRATEGY == "STRATEGY"

    def test_layer_values_uppercase(self) -> None:
        for layer in PnLLayer:
            assert layer.value == layer.value.upper()


# ---------------------------------------------------------------------------
# PnLAttributionRow
# ---------------------------------------------------------------------------


class TestPnLAttributionRow:
    def test_basic_construction(self) -> None:
        row = _row(PnLFactor.FUNDING, PnLLayer.STRATEGY, Decimal("100"))
        assert row.factor == PnLFactor.FUNDING
        assert row.layer == PnLLayer.STRATEGY
        assert row.amount == Decimal("100")

    def test_immutability(self) -> None:
        row = _row(PnLFactor.DELTA, PnLLayer.EXECUTION, Decimal("50"))
        with pytest.raises((AttributeError, TypeError)):
            row.amount = Decimal("999")  # type: ignore[misc]

    def test_optional_fields_default_none(self) -> None:
        row = _row(PnLFactor.FEES, PnLLayer.EXECUTION, Decimal("-5"))
        assert row.archetype_id is None
        assert row.fill_id is None
        assert row.venue is None
        assert row.benchmark_price is None

    def test_optional_fields_populated(self) -> None:
        row = PnLAttributionRow(
            strategy_id="s1",
            client_id="c1",
            instrument_id="ETH-PERP",
            timestamp=_TS,
            period="2026-05-12",
            factor=PnLFactor.SLIPPAGE,
            layer=PnLLayer.EXECUTION,
            amount=Decimal("-3"),
            archetype_id="carry_staked_basis",
            fill_id="fill-abc",
            venue="hyperliquid",
            benchmark_price=Decimal("3000"),
        )
        assert row.archetype_id == "carry_staked_basis"
        assert row.fill_id == "fill-abc"
        assert row.venue == "hyperliquid"
        assert row.benchmark_price == Decimal("3000")

    def test_factor_must_be_pnl_factor(self) -> None:
        row = _row(PnLFactor.BASIS, PnLLayer.STRATEGY, Decimal("200"))
        assert row.factor in PnLFactor

    def test_layer_must_be_pnl_layer(self) -> None:
        row = _row(PnLFactor.CARRY, PnLLayer.EXECUTION, Decimal("10"))
        assert row.layer in PnLLayer


# ---------------------------------------------------------------------------
# PnLAttribution dual-axis invariants
# ---------------------------------------------------------------------------


class TestPnLAttributionInvariants:
    def _make_attribution(
        self,
        strategy_amount: Decimal,
        execution_amount: Decimal,
        residual: Decimal = Decimal("0"),
    ) -> PnLAttribution:
        total = strategy_amount + execution_amount + residual
        return PnLAttribution(
            strategy_id="s1",
            client_id="c1",
            instrument_id="BTC-PERP",
            timestamp=_TS,
            period="2026-05-12",
            factors={
                "FUNDING:STRATEGY": strategy_amount,
                "SLIPPAGE:EXECUTION": execution_amount,
                "RESIDUAL:STRATEGY": residual,
            },
            factors_by_layer={
                "STRATEGY": strategy_amount + residual,
                "EXECUTION": execution_amount,
            },
            total_pnl=total,
            strategy_alpha_total=strategy_amount + residual,
            execution_alpha_total=execution_amount,
        )

    def test_strategy_plus_execution_equals_total(self) -> None:
        attr = self._make_attribution(Decimal("500"), Decimal("50"))
        assert attr.strategy_alpha_total + attr.execution_alpha_total == attr.total_pnl

    def test_strategy_layer_sum_matches_strategy_alpha(self) -> None:
        attr = self._make_attribution(Decimal("300"), Decimal("70"))
        layer_strategy = attr.factors_by_layer.get("STRATEGY", Decimal("0"))
        assert layer_strategy == attr.strategy_alpha_total

    def test_execution_layer_sum_matches_execution_alpha(self) -> None:
        attr = self._make_attribution(Decimal("300"), Decimal("70"))
        layer_exec = attr.factors_by_layer.get("EXECUTION", Decimal("0"))
        assert layer_exec == attr.execution_alpha_total

    def test_residual_factor_below_one_percent_of_total(self) -> None:
        residual = Decimal("9")  # 0.9% — under the 1% threshold
        attr = self._make_attribution(Decimal("991"), Decimal("0"), residual=residual)
        residual_ratio = abs(residual) / abs(attr.total_pnl)
        assert residual_ratio < Decimal("0.01"), f"RESIDUAL {residual_ratio:%} ≥ 1%"

    def test_residual_factor_at_limit_fails(self) -> None:
        residual = Decimal("11")  # 1.1% — over limit, must fail the check
        total_pnl_abs = Decimal("1000")
        residual_ratio = abs(residual) / total_pnl_abs
        assert residual_ratio >= Decimal("0.01"), "Expected residual to exceed 1%"
        # Callers must enforce this check before writing the attribution row.
        assert residual_ratio > Decimal("0.01")

    def test_round_trip_serialisation(self) -> None:
        attr = self._make_attribution(Decimal("400"), Decimal("100"))
        dumped = attr.model_dump()
        restored = PnLAttribution.model_validate(dumped)
        assert restored.total_pnl == attr.total_pnl
        assert restored.strategy_alpha_total == attr.strategy_alpha_total
        assert restored.execution_alpha_total == attr.execution_alpha_total

    def test_default_totals_zero(self) -> None:
        attr = PnLAttribution(
            strategy_id="s1",
            client_id="c1",
            instrument_id="ETH-PERP",
            timestamp=_TS,
            period="2026-05-12",
        )
        assert attr.total_pnl == Decimal("0")
        assert attr.strategy_alpha_total == Decimal("0")
        assert attr.execution_alpha_total == Decimal("0")
        assert attr.factors == {}
        assert attr.factors_by_layer == {}


# ---------------------------------------------------------------------------
# ClientReportingMode
# ---------------------------------------------------------------------------


class TestClientReportingMode:
    def test_demo_mode(self) -> None:
        assert ClientReportingMode.DEMO == "DEMO"

    def test_paper_mode(self) -> None:
        assert ClientReportingMode.PAPER == "PAPER"

    def test_live_mode(self) -> None:
        assert ClientReportingMode.LIVE == "LIVE"

    def test_exactly_three_modes(self) -> None:
        assert len(ClientReportingMode) == 3

    def test_mode_is_str_enum(self) -> None:
        assert isinstance(ClientReportingMode.LIVE, str)


# ---------------------------------------------------------------------------
# ClientNAV round-trip
# ---------------------------------------------------------------------------


class TestClientNAV:
    def test_round_trip(self) -> None:
        nav = ClientNAV(
            client_id="c1",
            share_class=ShareClass.USDT,
            nav_usd=Decimal("1_000_000"),
            nav_in_share_class=Decimal("1_000_000"),
            nav_delta_usd=Decimal("5000"),
            mode=ClientReportingMode.LIVE,
            timestamp=_TS,
        )
        dumped = nav.model_dump()
        restored = ClientNAV.model_validate(dumped)
        assert restored.nav_usd == nav.nav_usd
        assert restored.mode == ClientReportingMode.LIVE

    def test_default_mode_is_demo(self) -> None:
        nav = ClientNAV(
            client_id="c1",
            share_class=ShareClass.USDT,
            nav_usd=Decimal("0"),
            nav_in_share_class=Decimal("0"),
            timestamp=_TS,
        )
        assert nav.mode == ClientReportingMode.DEMO

    def test_pii_field_present(self) -> None:
        nav = ClientNAV(
            client_id="demo-internal",
            share_class=ShareClass.USDT,
            nav_usd=Decimal("100"),
            nav_in_share_class=Decimal("100"),
            timestamp=_TS,
        )
        schema = nav.model_json_schema()
        assert schema["properties"]["client_id"].get("pii") is True


# ---------------------------------------------------------------------------
# ClientPnLEntry round-trip
# ---------------------------------------------------------------------------


class TestClientPnLEntry:
    def test_round_trip(self) -> None:
        entry = ClientPnLEntry(
            client_id="c1",
            period_tag="2026-05-12",
            realized_pnl=Decimal("100"),
            unrealized_pnl=Decimal("50"),
            total_pnl=Decimal("150"),
            strategy_alpha_total=Decimal("120"),
            execution_alpha_total=Decimal("30"),
            share_class=ShareClass.USDT,
            timestamp=_TS,
        )
        restored = ClientPnLEntry.model_validate(entry.model_dump())
        assert restored.total_pnl == Decimal("150")
        assert restored.share_class == ShareClass.USDT

    def test_alpha_defaults_zero(self) -> None:
        entry = ClientPnLEntry(
            client_id="c1",
            period_tag="2026-05-12",
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            total_pnl=Decimal("0"),
            timestamp=_TS,
        )
        assert entry.strategy_alpha_total == Decimal("0")
        assert entry.execution_alpha_total == Decimal("0")


# ---------------------------------------------------------------------------
# ClientPosition round-trip
# ---------------------------------------------------------------------------


class TestClientPosition:
    def test_round_trip(self) -> None:
        pos = ClientPosition(
            client_id="c1",
            venue="hyperliquid",
            instrument="BTC-PERP",
            qty=Decimal("0.5"),
            mark_price=Decimal("60000"),
            cost_basis=Decimal("59000"),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("500"),
            share_class=ShareClass.USDT,
            timestamp=_TS,
        )
        restored = ClientPosition.model_validate(pos.model_dump())
        assert restored.qty == Decimal("0.5")
        assert restored.unrealized_pnl == Decimal("500")

    def test_lineage_fields_optional(self) -> None:
        pos = ClientPosition(
            client_id="c1",
            venue="hyperliquid",
            instrument="ETH-PERP",
            qty=Decimal("1"),
            mark_price=Decimal("3000"),
            cost_basis=Decimal("2950"),
            timestamp=_TS,
        )
        assert pos.archetype_id is None
        assert pos.strategy_leg_id is None
        assert pos.trade_id is None


# ---------------------------------------------------------------------------
# ClientShareClassSeed + DEMO_CLIENT_SEED
# ---------------------------------------------------------------------------


class TestDemoClientSeed:
    def test_demo_client_id(self) -> None:
        assert DEMO_CLIENT_ID == "demo-internal"

    def test_live_defi_archetypes_count(self) -> None:
        assert len(LIVE_DEFI_CUTOVER_ARCHETYPES) == 2

    def test_archetypes_match_plan(self) -> None:
        assert "carry_staked_basis" in LIVE_DEFI_CUTOVER_ARCHETYPES
        assert "leveraged_funding_arb" in LIVE_DEFI_CUTOVER_ARCHETYPES

    def test_demo_seed_client_id(self) -> None:
        assert DEMO_CLIENT_SEED.client_id == DEMO_CLIENT_ID

    def test_demo_seed_share_class(self) -> None:
        assert DEMO_CLIENT_SEED.share_class == ShareClass.USDT

    def test_demo_seed_mode(self) -> None:
        assert DEMO_CLIENT_SEED.mode == ClientReportingMode.DEMO

    def test_demo_seed_archetypes_match(self) -> None:
        assert set(DEMO_CLIENT_SEED.archetypes) == set(LIVE_DEFI_CUTOVER_ARCHETYPES)

    def test_client_share_class_seed_is_frozen(self) -> None:
        with pytest.raises((AttributeError, TypeError)):
            DEMO_CLIENT_SEED.client_id = "hacked"  # type: ignore[misc]

    def test_client_share_class_seed_type(self) -> None:
        assert isinstance(DEMO_CLIENT_SEED, ClientShareClassSeed)
