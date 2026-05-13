"""Tests for ClientDailyStatement UAC type.

Phase 5.A UAC type tests — 5 tests.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from unified_api_contracts.internal.domain.client_statements import ClientDailyStatement
from unified_api_contracts.internal.domain.hwm_ledger import (
    FeeRecognitionRow,
    FeeRecognitionType,
    HighWaterMarkLedgerRow,
)

_AS_OF = datetime(2026, 5, 13, 0, 0, 0, tzinfo=UTC)
_PERIOD_START = datetime(2026, 5, 1, tzinfo=UTC)
_PERIOD_END = datetime(2026, 6, 1, tzinfo=UTC)


def _make_hwm_row(nav: str = "10000", sc_id: str = "USDC_V1") -> HighWaterMarkLedgerRow:
    return HighWaterMarkLedgerRow(
        client_id="client-001",
        share_class_id=sc_id,
        as_of=_AS_OF,
        nav=Decimal(nav),
        prior_peak_nav=Decimal(nav),
        delta=Decimal("0"),
        crystallization_due=False,
        period_start=_PERIOD_START,
        period_end=_PERIOD_END,
    )


def _make_fee_row(amount: str = "200", sc_id: str = "USDC_V1") -> FeeRecognitionRow:
    return FeeRecognitionRow(
        client_id="client-001",
        share_class_id=sc_id,
        period_start=_PERIOD_START,
        period_end=_PERIOD_END,
        recognition_type=FeeRecognitionType.PERFORMANCE_FEE_CRYSTALLIZATION,
        amount_usd=Decimal(amount),
        recognized_at=_AS_OF,
        source_event_id="evt-001",
    )


class TestClientDailyStatement:
    def test_basic_creation(self) -> None:
        stmt = ClientDailyStatement(
            client_id="client-001",
            as_of_date=date(2026, 5, 13),
            positions={"ETH": Decimal("10"), "BTC": Decimal("0.5")},
            pnl_today_usd=Decimal("500"),
            fees_today_breakdown={"TRADING_FEE": Decimal("10"), "PLATFORM_FEE": Decimal("2")},
            hwm_section=[_make_hwm_row()],
            recent_crystallizations={"USDC_V1": _make_fee_row()},
            generated_at=_AS_OF,
        )
        assert stmt.client_id == "client-001"
        assert stmt.total_fees_today_usd() == Decimal("12")
        assert stmt.net_pnl_today_usd() == Decimal("488")

    def test_empty_positions(self) -> None:
        stmt = ClientDailyStatement(
            client_id="client-001",
            as_of_date=date(2026, 5, 13),
            positions={},
            pnl_today_usd=Decimal("0"),
            fees_today_breakdown={},
            hwm_section=[],
            recent_crystallizations={},
            generated_at=_AS_OF,
        )
        assert stmt.positions == {}
        assert stmt.total_fees_today_usd() == Decimal("0")

    def test_multi_share_class(self) -> None:
        stmt = ClientDailyStatement(
            client_id="client-001",
            as_of_date=date(2026, 5, 13),
            positions={"ETH": Decimal("5")},
            pnl_today_usd=Decimal("100"),
            fees_today_breakdown={"TRADING_FEE": Decimal("5")},
            hwm_section=[_make_hwm_row("10000", "SC1"), _make_hwm_row("5000", "SC2")],
            recent_crystallizations={
                "SC1": _make_fee_row("100", "SC1"),
                "SC2": _make_fee_row("50", "SC2"),
            },
            generated_at=_AS_OF,
        )
        assert len(stmt.hwm_section) == 2
        summary = stmt.crystallization_summary()
        assert summary["SC1"] == Decimal("100")
        assert summary["SC2"] == Decimal("50")

    def test_missing_crystallization_none_handling(self) -> None:
        stmt = ClientDailyStatement(
            client_id="client-001",
            as_of_date=date(2026, 5, 13),
            positions={},
            pnl_today_usd=Decimal("0"),
            fees_today_breakdown={},
            hwm_section=[],
            recent_crystallizations={"SC1": None},  # No crystallization yet
            generated_at=_AS_OF,
        )
        summary = stmt.crystallization_summary()
        assert "SC1" not in summary  # None entries excluded

    def test_zero_pnl(self) -> None:
        stmt = ClientDailyStatement(
            client_id="client-001",
            as_of_date=date(2026, 5, 13),
            positions={"BTC": Decimal("1")},
            pnl_today_usd=Decimal("0"),
            fees_today_breakdown={"TRADING_FEE": Decimal("1")},
            hwm_section=[],
            recent_crystallizations={},
            generated_at=_AS_OF,
        )
        assert stmt.net_pnl_today_usd() == Decimal("-1")
