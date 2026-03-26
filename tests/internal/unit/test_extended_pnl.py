"""Tests for ExtendedPnLAttribution schema."""

from datetime import UTC, datetime
from decimal import Decimal

from unified_api_contracts.internal import ExtendedPnLAttribution


class TestExtendedPnLAttribution:
    def test_basic(self) -> None:
        attr = ExtendedPnLAttribution(
            client_id="c1",
            strategy_id="MOM_MACD",
            level="strategy",
            timestamp=datetime.now(UTC),
            pnl_by_risk_type={
                "delta": Decimal("500"),
                "funding": Decimal("-10"),
                "fees": Decimal("-5"),
            },
            total_pnl=Decimal("485"),
            residual_pnl=Decimal("0"),
        )
        assert attr.total_pnl == Decimal("485")
        assert attr.pnl_by_risk_type["delta"] == Decimal("500")

    def test_residual_tracking(self) -> None:
        attr = ExtendedPnLAttribution(
            client_id="c1",
            level="instrument",
            timestamp=datetime.now(UTC),
            pnl_by_risk_type={"delta": Decimal("100")},
            total_pnl=Decimal("120"),
            residual_pnl=Decimal("20"),
        )
        assert attr.residual_pnl == Decimal("20")

    def test_defaults(self) -> None:
        attr = ExtendedPnLAttribution(
            client_id="c1",
            level="client",
            timestamp=datetime.now(UTC),
            pnl_by_risk_type={"delta": Decimal("50")},
            total_pnl=Decimal("50"),
            residual_pnl=Decimal("0"),
        )
        assert attr.strategy_id is None
        assert attr.underlying is None
        assert attr.instrument_id is None
        assert attr.fees == Decimal("0")

    def test_fees_override(self) -> None:
        attr = ExtendedPnLAttribution(
            client_id="c1",
            level="instrument",
            instrument_id="BTC-PERP",
            timestamp=datetime.now(UTC),
            pnl_by_risk_type={"delta": Decimal("200")},
            total_pnl=Decimal("195"),
            residual_pnl=Decimal("0"),
            fees=Decimal("5"),
        )
        assert attr.fees == Decimal("5")
        assert attr.instrument_id == "BTC-PERP"
