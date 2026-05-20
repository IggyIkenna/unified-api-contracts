"""Integration tests — StrategyPnlStreamEvent + ArchetypeAllocationDirective round-trip.

Verifies that both models serialize to JSON and deserialize back to identical objects,
and that they are importable from the unified_api_contracts root facade.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

from unified_api_contracts import ArchetypeAllocationDirective, StrategyPnlStreamEvent


_T0 = datetime(2026, 5, 20, 12, 0, 0, tzinfo=UTC)
_T1 = datetime(2026, 5, 20, 13, 0, 0, tzinfo=UTC)
_T2 = datetime(2026, 5, 20, 14, 0, 0, tzinfo=UTC)


def test_strategy_pnl_stream_event_json_roundtrip() -> None:
    original = StrategyPnlStreamEvent(
        archetype_id="carry_staked_basis",
        mode="live",
        pnl_realized=Decimal("1234.56"),
        pnl_unrealized=Decimal("-50.00"),
        equity=Decimal("99999.99"),
        n_trades=42,
        sharpe_window_n=Decimal("1.75"),
        drawdown_window_n=Decimal("0.03"),
        timestamp=_T0,
        available_at=_T1,
    )
    json_str = original.model_dump_json()
    parsed = json.loads(json_str)
    restored = StrategyPnlStreamEvent.model_validate(parsed)
    assert restored.archetype_id == original.archetype_id
    assert restored.mode == original.mode
    assert restored.pnl_realized == original.pnl_realized
    assert restored.equity == original.equity
    assert restored.n_trades == original.n_trades
    assert restored.sharpe_window_n == original.sharpe_window_n
    assert restored.timestamp == original.timestamp
    assert restored.available_at == original.available_at


def test_archetype_allocation_directive_json_roundtrip() -> None:
    original = ArchetypeAllocationDirective(
        archetype_id="arbitrage_price_dispersion",
        allocation_weight=Decimal("0.35"),
        enabled=True,
        param_overrides={"max_position_usd": 50000},
        valid_from=_T0,
        valid_until=_T2,
        source="trading-agent-service-stub",
        available_at=_T1,
    )
    json_str = original.model_dump_json()
    parsed = json.loads(json_str)
    restored = ArchetypeAllocationDirective.model_validate(parsed)
    assert restored.archetype_id == original.archetype_id
    assert restored.allocation_weight == original.allocation_weight
    assert restored.enabled == original.enabled
    assert restored.param_overrides == original.param_overrides
    assert restored.valid_from == original.valid_from
    assert restored.valid_until == original.valid_until
    assert restored.source == original.source
    assert restored.available_at == original.available_at
