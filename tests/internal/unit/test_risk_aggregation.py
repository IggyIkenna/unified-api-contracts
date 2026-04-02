"""Tests for risk aggregation hierarchy schemas."""

from decimal import Decimal

from unified_api_contracts.internal import (
    DurationBucket,
    RiskAggregationLevel,
    RiskPnLNode,
    TermStructureExposure,
)


class TestRiskAggregation:
    def test_aggregation_level_enum(self) -> None:
        assert RiskAggregationLevel.COMPANY == "company"
        assert RiskAggregationLevel.INSTRUMENT == "instrument"
        assert len(RiskAggregationLevel) == 6

    def test_risk_pnl_node_basic(self) -> None:
        node = RiskPnLNode(
            level=RiskAggregationLevel.INSTRUMENT,
            level_id="BTC-PERP",
            risk_by_type={"delta": Decimal("1000"), "funding": Decimal("50")},
            pnl_by_type={"delta": Decimal("500"), "funding": Decimal("-10")},
            subscribed_risks=["delta", "funding"],
        )
        assert node.risk_by_type["delta"] == Decimal("1000")

    def test_risk_pnl_node_hierarchy(self) -> None:
        instrument = RiskPnLNode(
            level=RiskAggregationLevel.INSTRUMENT,
            level_id="BTC-PERP",
            risk_by_type={"delta": Decimal("1000")},
        )
        underlying = RiskPnLNode(
            level=RiskAggregationLevel.UNDERLYING,
            level_id="BTC",
            risk_by_type={"delta": Decimal("1000")},
            children=[instrument],
        )
        strategy = RiskPnLNode(
            level=RiskAggregationLevel.STRATEGY,
            level_id="MOM_MACD",
            risk_by_type={"delta": Decimal("1000")},
            children=[underlying],
        )
        assert len(strategy.children) == 1
        assert strategy.children[0].level == RiskAggregationLevel.UNDERLYING

    def test_duration_bucket(self) -> None:
        assert DurationBucket.TWO_YEAR_PLUS == "2y+"

    def test_term_structure_exposure(self) -> None:
        ts = TermStructureExposure(
            underlying="BTC",
            exposures_by_bucket={
                "overnight": Decimal("5000"),
                "1m": Decimal("3000"),
                "3m": Decimal("2000"),
            },
        )
        assert ts.exposures_by_bucket["overnight"] == Decimal("5000")
