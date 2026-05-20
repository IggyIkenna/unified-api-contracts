"""Tests for ArchetypeAllocationDirective schema."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from unified_api_contracts.internal.strategy_directives import ArchetypeAllocationDirective

_T0 = datetime(2026, 5, 20, 12, 0, 0, tzinfo=UTC)
_T1 = datetime(2026, 5, 20, 13, 0, 0, tzinfo=UTC)
_T2 = datetime(2026, 5, 20, 14, 0, 0, tzinfo=UTC)


def _make(**kwargs: object) -> ArchetypeAllocationDirective:
    defaults: dict[str, object] = {
        "archetype_id": "carry_staked_basis",
        "allocation_weight": Decimal("0.5"),
        "enabled": True,
        "param_overrides": {},
        "valid_from": _T0,
        "valid_until": _T2,
        "source": "trading-agent-service-stub",
        "available_at": _T1,
    }
    defaults.update(kwargs)
    return ArchetypeAllocationDirective(**defaults)  # type: ignore[arg-type]


class TestArchetypeAllocationDirectiveHappyPath:
    def test_no_op_default(self) -> None:
        d = _make()
        assert d.archetype_id == "carry_staked_basis"
        assert d.allocation_weight == Decimal("0.5")
        assert d.enabled is True
        assert d.source == "trading-agent-service-stub"

    def test_weight_zero(self) -> None:
        d = _make(allocation_weight=Decimal("0.0"))
        assert d.allocation_weight == Decimal("0.0")

    def test_weight_one(self) -> None:
        d = _make(allocation_weight=Decimal("1.0"))
        assert d.allocation_weight == Decimal("1.0")

    def test_no_expiry(self) -> None:
        d = _make(valid_until=None)
        assert d.valid_until is None

    def test_param_overrides_carried(self) -> None:
        d = _make(param_overrides={"max_leverage": 3, "fee_tier": "vip"})
        assert d.param_overrides["max_leverage"] == 3


class TestArchetypeAllocationDirectiveValidation:
    def test_weight_above_one_rejected(self) -> None:
        with pytest.raises(Exception):
            _make(allocation_weight=Decimal("1.01"))

    def test_weight_below_zero_rejected(self) -> None:
        with pytest.raises(Exception):
            _make(allocation_weight=Decimal("-0.01"))

    def test_valid_from_after_valid_until_rejected(self) -> None:
        with pytest.raises(Exception):
            _make(valid_from=_T2, valid_until=_T0, available_at=_T2)

    def test_valid_from_equal_valid_until_rejected(self) -> None:
        with pytest.raises(Exception):
            _make(valid_from=_T1, valid_until=_T1, available_at=_T1)

    def test_available_at_before_valid_from_rejected(self) -> None:
        with pytest.raises(Exception):
            _make(valid_from=_T1, valid_until=_T2, available_at=_T0)
