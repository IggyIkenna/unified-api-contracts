"""Tests for correlation analytics schemas added in p2b."""

from datetime import UTC, datetime
from decimal import Decimal

from unified_api_contracts.internal import (
    CorrelationRegime,
    CorrelationRegimeChange,
    CrossAssetCorrelationMatrix,
)


class TestCorrelationSchemas:
    def test_correlation_regime_enum(self) -> None:
        assert CorrelationRegime.CRISIS == "crisis"
        assert CorrelationRegime.NORMAL == "normal"

    def test_cross_asset_correlation_matrix(self) -> None:
        matrix = CrossAssetCorrelationMatrix(
            computed_at=datetime.now(UTC),
            window_days=60,
            instruments=["BTC", "ETH"],
            correlation_matrix=[
                [Decimal("1.0"), Decimal("0.85")],
                [Decimal("0.85"), Decimal("1.0")],
            ],
            regime=CorrelationRegime.HIGH,
            average_pairwise_correlation=Decimal("0.85"),
        )
        assert matrix.regime == CorrelationRegime.HIGH
        assert len(matrix.correlation_matrix) == 2

    def test_correlation_regime_change(self) -> None:
        change = CorrelationRegimeChange(
            detected_at=datetime.now(UTC),
            regime_before=CorrelationRegime.NORMAL,
            regime_after=CorrelationRegime.HIGH,
            assets_affected=["BTC", "ETH", "SOL"],
            trigger="macro_shock",
            correlation_delta=Decimal("0.25"),
        )
        assert change.regime_after == CorrelationRegime.HIGH
        assert len(change.assets_affected) == 3
