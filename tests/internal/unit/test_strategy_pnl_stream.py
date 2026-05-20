"""Tests for StrategyPnlStreamEvent schema."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from unified_api_contracts.internal.strategy_pnl_stream import StrategyPnlStreamEvent

_NOW = datetime(2026, 5, 20, 12, 0, 0, tzinfo=UTC)
_LATER = datetime(2026, 5, 20, 12, 0, 1, tzinfo=UTC)


def _make(**kwargs: object) -> StrategyPnlStreamEvent:
    defaults: dict[str, object] = {
        "archetype_id": "carry_staked_basis",
        "mode": "live",
        "pnl_realized": Decimal("100.00"),
        "pnl_unrealized": Decimal("50.00"),
        "equity": Decimal("10000.00"),
        "n_trades": 5,
        "sharpe_window_n": Decimal("1.25"),
        "drawdown_window_n": Decimal("0.05"),
        "timestamp": _NOW,
        "available_at": _LATER,
    }
    defaults.update(kwargs)
    return StrategyPnlStreamEvent(**defaults)  # type: ignore[arg-type]


class TestStrategyPnlStreamEventHappyPath:
    def test_live_mode(self) -> None:
        event = _make(mode="live")
        assert event.mode == "live"
        assert event.archetype_id == "carry_staked_basis"

    def test_paper_mode(self) -> None:
        event = _make(mode="paper", archetype_id="arbitrage_price_dispersion")
        assert event.mode == "paper"
        assert event.archetype_id == "arbitrage_price_dispersion"

    def test_backtest_continuation_mode(self) -> None:
        event = _make(mode="backtest_continuation")
        assert event.mode == "backtest_continuation"

    def test_none_sharpe_when_window_not_filled(self) -> None:
        event = _make(sharpe_window_n=None, drawdown_window_n=None)
        assert event.sharpe_window_n is None
        assert event.drawdown_window_n is None

    def test_decimal_fields_preserved(self) -> None:
        event = _make(pnl_realized=Decimal("1234.5678"), equity=Decimal("99999.99"))
        assert event.pnl_realized == Decimal("1234.5678")
        assert event.equity == Decimal("99999.99")

    def test_negative_equity_allowed(self) -> None:
        # Shadow archetypes may have negative equity — no constraint.
        event = _make(equity=Decimal("-500.00"))
        assert event.equity == Decimal("-500.00")


class TestStrategyPnlStreamEventInvalidMode:
    def test_invalid_mode_rejected(self) -> None:
        with pytest.raises(Exception):
            _make(mode="unknown")  # type: ignore[arg-type]
