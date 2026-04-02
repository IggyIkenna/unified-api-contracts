"""Tests for custom risk type schemas."""

from unified_api_contracts.internal import CustomRiskEvaluationMethod, CustomRiskTypeDefinition


class TestCustomRiskTypes:
    def test_evaluation_method_enum(self) -> None:
        assert CustomRiskEvaluationMethod.RATE_SENSITIVITY == "rate_sensitivity"
        assert len(CustomRiskEvaluationMethod) == 3

    def test_custom_risk_definition(self) -> None:
        defn = CustomRiskTypeDefinition(
            risk_id="eth_borrow_rate_sensitivity",
            display_name="ETH Borrow Rate Sensitivity",
            evaluation_method=CustomRiskEvaluationMethod.RATE_SENSITIVITY,
            applicable_strategies=["RECURSIVE_STAKED_BASIS", "STAKED_BASIS"],
            description="What if ETH borrow rate changes by X bps?",
        )
        assert defn.risk_id == "eth_borrow_rate_sensitivity"
        assert len(defn.applicable_strategies) == 2
