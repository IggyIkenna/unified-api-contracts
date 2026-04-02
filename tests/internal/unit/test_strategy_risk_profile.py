"""Tests for StrategyRiskProfile schema."""

from unified_api_contracts.internal import StrategyRiskProfile


class TestStrategyRiskProfile:
    def test_basic(self) -> None:
        profile = StrategyRiskProfile(
            strategy_type="MOM",
            subscribed_risks=["delta", "funding", "liquidity", "venue_protocol"],
        )
        assert profile.strategy_type == "MOM"
        assert len(profile.subscribed_risks) == 4

    def test_with_custom_risks(self) -> None:
        profile = StrategyRiskProfile(
            strategy_type="BASIS",
            subscribed_risks=["basis", "funding", "duration"],
            custom_risk_ids=["eth_borrow_rate_sensitivity"],
        )
        assert len(profile.custom_risk_ids) == 1
