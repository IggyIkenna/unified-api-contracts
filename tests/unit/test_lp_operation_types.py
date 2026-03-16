"""Tests for LP operation type additions to UAC enums."""

from __future__ import annotations

from unified_api_contracts.execution import OperationType
from unified_api_contracts.reference import InstructionType
from unified_api_contracts.registry.venue_constants import (
    INSTRUCTION_VALID_DOMAINS,
    INSTRUCTION_VALID_INSTRUMENT_TYPES,
)


class TestLPOperationTypes:
    """Verify new LP operation types in OperationType."""

    def test_add_liquidity_exists(self) -> None:
        assert OperationType.ADD_LIQUIDITY == "ADD_LIQUIDITY"

    def test_remove_liquidity_exists(self) -> None:
        assert OperationType.REMOVE_LIQUIDITY == "REMOVE_LIQUIDITY"

    def test_collect_fees_exists(self) -> None:
        assert OperationType.COLLECT_FEES == "COLLECT_FEES"

    def test_lp_operations_are_valid_str_enum(self) -> None:
        """LP operations should be valid StrEnum members."""
        for op in ("ADD_LIQUIDITY", "REMOVE_LIQUIDITY", "COLLECT_FEES"):
            parsed = OperationType(op)
            assert parsed.value == op


class TestLPInstructionTypes:
    """Verify new LP instruction types in InstructionType."""

    def test_add_liquidity_instruction_type(self) -> None:
        assert InstructionType.ADD_LIQUIDITY == "ADD_LIQUIDITY"

    def test_remove_liquidity_instruction_type(self) -> None:
        assert InstructionType.REMOVE_LIQUIDITY == "REMOVE_LIQUIDITY"

    def test_collect_fees_instruction_type(self) -> None:
        assert InstructionType.COLLECT_FEES == "COLLECT_FEES"

    def test_lp_instruction_types_in_valid_domains(self) -> None:
        """LP instruction types should be registered in INSTRUCTION_VALID_DOMAINS."""
        for inst_type in ("ADD_LIQUIDITY", "REMOVE_LIQUIDITY", "COLLECT_FEES"):
            assert inst_type in INSTRUCTION_VALID_DOMAINS, f"{inst_type} not in INSTRUCTION_VALID_DOMAINS"
            assert INSTRUCTION_VALID_DOMAINS[inst_type] == {"defi"}, f"{inst_type} should only be valid for defi domain"

    def test_lp_instruction_types_in_valid_instrument_types(self) -> None:
        """LP instruction types should map to POOL instrument type."""
        for inst_type in ("ADD_LIQUIDITY", "REMOVE_LIQUIDITY", "COLLECT_FEES"):
            assert inst_type in INSTRUCTION_VALID_INSTRUMENT_TYPES, (
                f"{inst_type} not in INSTRUCTION_VALID_INSTRUMENT_TYPES"
            )
            assert INSTRUCTION_VALID_INSTRUMENT_TYPES[inst_type] == {"POOL"}, (
                f"{inst_type} should only allow POOL instrument type"
            )

    def test_original_operation_types_preserved(self) -> None:
        """Original OperationType values should still be valid."""
        original = ["BUY", "SELL", "SWAP", "LEND", "BORROW", "REPAY", "WITHDRAW", "DEPOSIT", "REBALANCE"]
        for op in original:
            assert OperationType(op).value == op

    def test_original_instruction_types_preserved(self) -> None:
        """Original InstructionType values should still be valid."""
        original = [
            "TRADE",
            "SWAP",
            "ZERO_ALPHA",
            "PREDICTION_BET",
            "SPORTS_BET",
            "SPORTS_EXCHANGE_ORDER",
            "FUTURES_ROLL",
            "OPTIONS_COMBO",
        ]
        for inst in original:
            assert InstructionType(inst).value == inst
