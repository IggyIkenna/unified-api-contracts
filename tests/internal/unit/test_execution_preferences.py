"""Tests for ExecutionPreferencesConfig and related types."""

from __future__ import annotations

from unified_api_contracts.internal.domain.execution_service.execution_preferences import (
    ExecutionMode,
    ExecutionPreferencesConfig,
    UrgencyLevel,
)
from unified_api_contracts.internal.execution import SettlementType


class TestExecutionMode:
    """Verify ExecutionMode enum values."""

    def test_all_modes_exist(self) -> None:
        expected = {"AGGRESSIVE", "PASSIVE", "NEUTRAL", "TWAP", "VWAP"}
        actual = {m.value for m in ExecutionMode}
        assert actual == expected

    def test_modes_are_str_enum(self) -> None:
        for mode in ExecutionMode:
            assert isinstance(mode, str)
            assert mode == mode.value


class TestUrgencyLevel:
    """Verify UrgencyLevel enum values."""

    def test_all_levels_exist(self) -> None:
        expected = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        actual = {m.value for m in UrgencyLevel}
        assert actual == expected


class TestExecutionPreferencesConfig:
    """Verify ExecutionPreferencesConfig TypedDict structure."""

    def test_can_construct_valid_config(self) -> None:
        config: ExecutionPreferencesConfig = {
            "execution_mode": ExecutionMode.AGGRESSIVE,
            "max_slippage_bps": 50,
            "urgency_level": UrgencyLevel.HIGH,
            "prefer_maker": False,
            "allow_partial_fill": True,
        }
        assert config["execution_mode"] == ExecutionMode.AGGRESSIVE
        assert config["max_slippage_bps"] == 50
        assert config["urgency_level"] == UrgencyLevel.HIGH
        assert config["prefer_maker"] is False
        assert config["allow_partial_fill"] is True

    def test_passive_maker_config(self) -> None:
        config: ExecutionPreferencesConfig = {
            "execution_mode": ExecutionMode.PASSIVE,
            "max_slippage_bps": 10,
            "urgency_level": UrgencyLevel.LOW,
            "prefer_maker": True,
            "allow_partial_fill": True,
        }
        assert config["execution_mode"] == ExecutionMode.PASSIVE
        assert config["prefer_maker"] is True


class TestSettlementType:
    """Verify SettlementType enum in UIC."""

    def test_all_settlement_types_exist(self) -> None:
        expected = {
            "funding_8h",
            "funding_continuous",
            "seasonal_weekly",
            "aave_index",
            "staking_yield",
            "transaction_fee",
            "liquidation",
            "lp_fee",
            "flash_loan_fee",
            "lst_yield",
            "gas_rebate",
        }
        actual = {m.value for m in SettlementType}
        assert actual == expected

    def test_flash_loan_fee_value(self) -> None:
        assert SettlementType.FLASH_LOAN_FEE == "flash_loan_fee"

    def test_lp_fee_value(self) -> None:
        assert SettlementType.LP_FEE == "lp_fee"

    def test_settlement_type_is_str_enum(self) -> None:
        for st in SettlementType:
            assert isinstance(st, str)
            assert st == st.value
