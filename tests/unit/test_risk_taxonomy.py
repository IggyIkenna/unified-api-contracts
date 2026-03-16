"""Tests for risk taxonomy enums and category mapping."""

from unified_api_contracts import RISK_TYPE_CATEGORIES, RiskCategory, RiskType


class TestRiskTaxonomy:
    def test_risk_type_enum(self) -> None:
        assert RiskType.DELTA == "delta"
        assert RiskType.VOLGA == "volga"
        assert RiskType.EDGE_DECAY == "edge_decay"
        assert len(RiskType) == 23

    def test_risk_category_enum(self) -> None:
        assert len(RiskCategory) == 5

    def test_all_risk_types_categorized(self) -> None:
        categorized: set[RiskType] = set()
        for types in RISK_TYPE_CATEGORIES.values():
            categorized.update(types)
        assert categorized == set(RiskType)
