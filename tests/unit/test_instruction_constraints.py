"""Tests for the instruction constraint registry."""

from __future__ import annotations

import pytest

from unified_api_contracts.registry.instruction_constraints import (
    INSTRUCTION_CONSTRAINTS,
    InstructionValidationError,
    validate_instruction,
)
from unified_api_contracts.registry.venue_constants import (
    INSTRUCTION_VALID_DOMAINS,
    INSTRUCTION_VALID_INSTRUMENT_TYPES,
    VENUE_CAPABILITIES,
    VENUE_CATEGORY_MAP,
)


class TestInstructionConstraintsCompleteness:
    """Verify every instruction type has valid constraint data."""

    def test_all_instruction_types_have_constraints(self) -> None:
        """Every key in INSTRUCTION_CONSTRAINTS must have non-empty fields."""
        for inst_type, constraint in INSTRUCTION_CONSTRAINTS.items():
            assert constraint["order_types"], f"{inst_type} has empty order_types"
            assert constraint["instrument_types"], f"{inst_type} has empty instrument_types"
            assert constraint["venue_categories"], f"{inst_type} has empty venue_categories"
            assert constraint["operation_types"], f"{inst_type} has empty operation_types"

    def test_all_venue_categories_exist(self) -> None:
        """All venue_categories in constraints must exist in VENUE_CATEGORY_MAP values."""
        known_categories = set(VENUE_CATEGORY_MAP.values())
        for inst_type, constraint in INSTRUCTION_CONSTRAINTS.items():
            for cat in constraint["venue_categories"]:
                assert cat in known_categories, f"{inst_type} references unknown venue_category={cat!r}"

    def test_constraint_instrument_types_align_with_existing(self) -> None:
        """Constraint instrument_types should align with INSTRUCTION_VALID_INSTRUMENT_TYPES."""
        for inst_type, constraint in INSTRUCTION_CONSTRAINTS.items():
            if inst_type in INSTRUCTION_VALID_INSTRUMENT_TYPES:
                existing = INSTRUCTION_VALID_INSTRUMENT_TYPES[inst_type]
                assert constraint["instrument_types"] == frozenset(existing), (
                    f"{inst_type}: constraint instrument_types {constraint['instrument_types']} != existing {existing}"
                )

    def test_constraint_venue_categories_align_with_existing(self) -> None:
        """Constraint venue_categories should align with INSTRUCTION_VALID_DOMAINS."""
        for inst_type, constraint in INSTRUCTION_CONSTRAINTS.items():
            if inst_type in INSTRUCTION_VALID_DOMAINS:
                existing = INSTRUCTION_VALID_DOMAINS[inst_type]
                assert constraint["venue_categories"] == frozenset(existing), (
                    f"{inst_type}: constraint venue_categories {constraint['venue_categories']} != existing {existing}"
                )

    def test_all_venues_in_capabilities_have_category(self) -> None:
        """Every venue in VENUE_CAPABILITIES should appear in VENUE_CATEGORY_MAP."""
        for venue in VENUE_CAPABILITIES:
            assert venue in VENUE_CATEGORY_MAP, f"Venue {venue!r} in VENUE_CAPABILITIES but not in VENUE_CATEGORY_MAP"


class TestInstructionValidation:
    """Test the validate_instruction function."""

    def test_valid_trade_instruction(self) -> None:
        validate_instruction(
            instruction_type="TRADE",
            order_type="MARKET",
            instrument_type="PERPETUAL",
            venue_category="cefi",
            operation_type="BUY",
        )

    def test_valid_swap_instruction(self) -> None:
        validate_instruction(
            instruction_type="SWAP",
            order_type="MARKET",
            instrument_type="POOL",
            venue_category="defi",
            operation_type="SWAP",
        )

    def test_invalid_order_type_raises(self) -> None:
        with pytest.raises(InstructionValidationError, match="order_type"):
            validate_instruction(
                instruction_type="SWAP",
                order_type="TRAILING_STOP",
            )

    def test_invalid_instrument_type_raises(self) -> None:
        with pytest.raises(InstructionValidationError, match="instrument_type"):
            validate_instruction(
                instruction_type="SWAP",
                instrument_type="EQUITY",
            )

    def test_invalid_venue_category_raises(self) -> None:
        with pytest.raises(InstructionValidationError, match="venue_category"):
            validate_instruction(
                instruction_type="SWAP",
                venue_category="cefi",
            )

    def test_invalid_operation_type_raises(self) -> None:
        with pytest.raises(InstructionValidationError, match="operation_type"):
            validate_instruction(
                instruction_type="TRADE",
                operation_type="SWAP",
            )

    def test_unknown_instruction_type_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="NONEXISTENT"):
            validate_instruction(instruction_type="NONEXISTENT")

    def test_none_fields_skip_validation(self) -> None:
        """None values should be skipped (partial validation)."""
        validate_instruction(
            instruction_type="TRADE",
            order_type=None,
            instrument_type=None,
            venue_category=None,
            operation_type=None,
        )

    def test_lp_instruction_types(self) -> None:
        """New LP instruction types validate correctly."""
        validate_instruction(
            instruction_type="ADD_LIQUIDITY",
            order_type="MARKET",
            instrument_type="POOL",
            venue_category="defi",
            operation_type="ADD_LIQUIDITY",
        )
        validate_instruction(
            instruction_type="REMOVE_LIQUIDITY",
            order_type="MARKET",
            instrument_type="POOL",
            venue_category="defi",
            operation_type="REMOVE_LIQUIDITY",
        )
        validate_instruction(
            instruction_type="COLLECT_FEES",
            order_type="MARKET",
            instrument_type="POOL",
            venue_category="defi",
            operation_type="COLLECT_FEES",
        )
