"""Machine-readable instruction constraint registry.

Maps each InstructionType to its allowed order types, instrument types,
venue categories, and operation types. Replaces ad-hoc validation scattered
across execution-service.

Consumers: execution-service, strategy-service, risk-and-exposure-service.
Import via: ``from unified_api_contracts.registry import INSTRUCTION_CONSTRAINTS``
"""

from __future__ import annotations

from enum import StrEnum
from typing import TypedDict


class ConstraintOrderType(StrEnum):
    """Order types allowed in instruction constraints."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"
    TWAP = "TWAP"
    VWAP = "VWAP"


class InstructionConstraint(TypedDict):
    """Constraint specification for a single instruction type."""

    order_types: frozenset[str]
    instrument_types: frozenset[str]
    venue_categories: frozenset[str]
    operation_types: frozenset[str]
    requires_price: bool
    allows_partial_fill: bool


INSTRUCTION_CONSTRAINTS: dict[str, InstructionConstraint] = {
    "TRADE": InstructionConstraint(
        order_types=frozenset(
            {
                "MARKET",
                "LIMIT",
                "STOP",
                "STOP_LIMIT",
                "TRAILING_STOP",
                "TWAP",
                "VWAP",
            }
        ),
        instrument_types=frozenset(
            {
                "PERPETUAL",
                "SPOT",
                "SPOT_PAIR",
                "FUTURE",
                "OPTION",
                "EQUITY",
                "ETF",
                "INDEX",
                "BOND",
                "COMMODITY",
                "CURRENCY",
                "CDS",
            }
        ),
        venue_categories=frozenset({"cefi", "tradfi"}),
        operation_types=frozenset({"BUY", "SELL"}),
        requires_price=False,
        allows_partial_fill=True,
    ),
    "SWAP": InstructionConstraint(
        order_types=frozenset({"MARKET", "LIMIT"}),
        instrument_types=frozenset({"POOL"}),
        venue_categories=frozenset({"defi"}),
        operation_types=frozenset({"SWAP"}),
        requires_price=False,
        allows_partial_fill=False,
    ),
    "ZERO_ALPHA": InstructionConstraint(
        order_types=frozenset({"MARKET"}),
        instrument_types=frozenset(
            {
                "YIELD_BEARING",
                "DEBT_TOKEN",
                "LST",
                "A_TOKEN",
                "LENDING",
                "STAKING",
            }
        ),
        venue_categories=frozenset({"defi"}),
        operation_types=frozenset(
            {
                "LEND",
                "BORROW",
                "REPAY",
                "WITHDRAW",
                "DEPOSIT",
                "STAKE",
                "UNSTAKE",
            }
        ),
        requires_price=False,
        allows_partial_fill=False,
    ),
    "PREDICTION_BET": InstructionConstraint(
        order_types=frozenset({"MARKET", "LIMIT"}),
        instrument_types=frozenset({"PREDICTION_MARKET"}),
        venue_categories=frozenset({"sports"}),
        operation_types=frozenset({"BUY", "SELL"}),
        requires_price=True,
        allows_partial_fill=True,
    ),
    "SPORTS_BET": InstructionConstraint(
        order_types=frozenset({"MARKET"}),
        instrument_types=frozenset({"FIXED_ODDS", "PROP"}),
        venue_categories=frozenset({"sports"}),
        operation_types=frozenset({"BUY"}),
        requires_price=True,
        allows_partial_fill=False,
    ),
    "SPORTS_EXCHANGE_ORDER": InstructionConstraint(
        order_types=frozenset({"MARKET", "LIMIT"}),
        instrument_types=frozenset({"EXCHANGE_ODDS"}),
        venue_categories=frozenset({"sports"}),
        operation_types=frozenset({"BUY", "SELL"}),
        requires_price=True,
        allows_partial_fill=True,
    ),
    "FUTURES_ROLL": InstructionConstraint(
        order_types=frozenset({"MARKET", "LIMIT"}),
        instrument_types=frozenset({"FUTURE"}),
        venue_categories=frozenset({"cefi", "tradfi"}),
        operation_types=frozenset({"BUY", "SELL"}),
        requires_price=False,
        allows_partial_fill=True,
    ),
    "OPTIONS_COMBO": InstructionConstraint(
        order_types=frozenset({"MARKET", "LIMIT"}),
        instrument_types=frozenset({"OPTION"}),
        venue_categories=frozenset({"cefi", "tradfi"}),
        operation_types=frozenset({"BUY", "SELL"}),
        requires_price=True,
        allows_partial_fill=True,
    ),
    "ADD_LIQUIDITY": InstructionConstraint(
        order_types=frozenset({"MARKET"}),
        instrument_types=frozenset({"POOL"}),
        venue_categories=frozenset({"defi"}),
        operation_types=frozenset({"ADD_LIQUIDITY"}),
        requires_price=False,
        allows_partial_fill=False,
    ),
    "REMOVE_LIQUIDITY": InstructionConstraint(
        order_types=frozenset({"MARKET"}),
        instrument_types=frozenset({"POOL"}),
        venue_categories=frozenset({"defi"}),
        operation_types=frozenset({"REMOVE_LIQUIDITY"}),
        requires_price=False,
        allows_partial_fill=False,
    ),
    "COLLECT_FEES": InstructionConstraint(
        order_types=frozenset({"MARKET"}),
        instrument_types=frozenset({"POOL"}),
        venue_categories=frozenset({"defi"}),
        operation_types=frozenset({"COLLECT_FEES"}),
        requires_price=False,
        allows_partial_fill=False,
    ),
}


class InstructionValidationError(ValueError):
    """Raised when an instruction fails constraint validation."""

    def __init__(self, instruction_type: str, field: str, value: str, allowed: frozenset[str]) -> None:
        self.instruction_type = instruction_type
        self.field = field
        self.value = value
        self.allowed = allowed
        super().__init__(
            f"Invalid {field}={value!r} for instruction_type={instruction_type!r}. Allowed: {sorted(allowed)}"
        )


def validate_instruction(
    instruction_type: str,
    order_type: str | None = None,
    instrument_type: str | None = None,
    venue_category: str | None = None,
    operation_type: str | None = None,
) -> None:
    """Validate an instruction against the constraint registry.

    Raises:
        InstructionValidationError: If any field violates constraints.
        KeyError: If instruction_type is not registered.
    """
    if instruction_type not in INSTRUCTION_CONSTRAINTS:
        raise KeyError(f"Unknown instruction_type={instruction_type!r}. Registered: {sorted(INSTRUCTION_CONSTRAINTS)}")

    constraint = INSTRUCTION_CONSTRAINTS[instruction_type]

    if order_type is not None and order_type not in constraint["order_types"]:
        raise InstructionValidationError(instruction_type, "order_type", order_type, constraint["order_types"])

    if instrument_type is not None and instrument_type not in constraint["instrument_types"]:
        raise InstructionValidationError(
            instruction_type, "instrument_type", instrument_type, constraint["instrument_types"]
        )

    if venue_category is not None and venue_category not in constraint["venue_categories"]:
        raise InstructionValidationError(
            instruction_type, "venue_category", venue_category, constraint["venue_categories"]
        )

    if operation_type is not None and operation_type not in constraint["operation_types"]:
        raise InstructionValidationError(
            instruction_type, "operation_type", operation_type, constraint["operation_types"]
        )


__all__ = [
    "INSTRUCTION_CONSTRAINTS",
    "ConstraintOrderType",
    "InstructionConstraint",
    "InstructionValidationError",
    "validate_instruction",
]
