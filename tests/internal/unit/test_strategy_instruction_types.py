"""Tests for StrategyInstructionType, Urgency, and typed StrategyInstruction fields.

Validates enum completeness, model serialization round-trips, and the
INSTRUCTION_TYPE_TO_OPERATIONS mapping.
"""

from datetime import UTC, datetime
from decimal import Decimal

from unified_api_contracts.internal.domain.execution_service.multi_leg import LegRole
from unified_api_contracts.internal.domain.execution_service.types import OperationType
from unified_api_contracts.internal.domain.strategy_service.instruction import (
    INSTRUCTION_TYPE_TO_OPERATIONS,
    StrategyInstruction,
    StrategyInstructionType,
    Urgency,
)

# ── StrategyInstructionType enum ──────────────────────────────────────────


class TestStrategyInstructionType:
    """Test StrategyInstructionType enum values and helper methods."""

    def test_all_expected_members_present(self) -> None:
        expected = {
            "MARKET_ORDER",
            "LIMIT_ORDER",
            "SWAP",
            "LEND",
            "BORROW",
            "REPAY",
            "WITHDRAW",
            "STAKE",
            "UNSTAKE",
            "BRIDGE",
            "FLASH_LOAN",
            "HEDGE_BASIS",
            "REBALANCE_LP",
            "REBALANCE_PORTFOLIO",
            "BACK",
            "LAY",
        }
        actual = {member.value for member in StrategyInstructionType}
        assert actual == expected

    def test_defi_primitives(self) -> None:
        primitives = StrategyInstructionType.defi_primitives()
        assert len(primitives) == 8
        for p in primitives:
            assert p not in StrategyInstructionType.composite_types()

    def test_composite_types(self) -> None:
        composites = StrategyInstructionType.composite_types()
        assert StrategyInstructionType.HEDGE_BASIS in composites
        assert StrategyInstructionType.REBALANCE_LP in composites
        assert StrategyInstructionType.REBALANCE_PORTFOLIO in composites
        assert StrategyInstructionType.FLASH_LOAN in composites

    def test_trading_types(self) -> None:
        trading = StrategyInstructionType.trading_types()
        assert StrategyInstructionType.MARKET_ORDER in trading
        assert StrategyInstructionType.LIMIT_ORDER in trading
        assert len(trading) == 2

    def test_sports_types(self) -> None:
        sports = StrategyInstructionType.sports_types()
        assert StrategyInstructionType.BACK in sports
        assert StrategyInstructionType.LAY in sports
        assert len(sports) == 2

    def test_str_enum_behaviour(self) -> None:
        assert StrategyInstructionType.SWAP == "SWAP"
        assert StrategyInstructionType("LEND") == StrategyInstructionType.LEND


# ── Urgency enum ──────────────────────────────────────────────────────────


class TestUrgency:
    """Test Urgency enum values."""

    def test_all_urgency_levels(self) -> None:
        expected = {"LOW", "NORMAL", "HIGH", "IMMEDIATE"}
        actual = {member.value for member in Urgency}
        assert actual == expected

    def test_str_enum_behaviour(self) -> None:
        assert Urgency.NORMAL == "NORMAL"
        assert Urgency("HIGH") == Urgency.HIGH


# ── INSTRUCTION_TYPE_TO_OPERATIONS mapping ────────────────────────────────


class TestInstructionTypeMapping:
    """Test that every StrategyInstructionType has a mapping to OperationType."""

    def test_all_types_covered(self) -> None:
        for instr_type in StrategyInstructionType:
            assert instr_type in INSTRUCTION_TYPE_TO_OPERATIONS, f"Missing mapping for {instr_type}"

    def test_mapping_values_are_operation_types(self) -> None:
        for instr_type, ops in INSTRUCTION_TYPE_TO_OPERATIONS.items():
            assert isinstance(ops, list), f"{instr_type} mapping is not a list"
            for op in ops:
                assert isinstance(op, OperationType), f"{instr_type} maps to non-OperationType: {op}"

    def test_swap_maps_to_swap(self) -> None:
        assert INSTRUCTION_TYPE_TO_OPERATIONS[StrategyInstructionType.SWAP] == [OperationType.SWAP]

    def test_hedge_basis_maps_to_two_trades(self) -> None:
        ops = INSTRUCTION_TYPE_TO_OPERATIONS[StrategyInstructionType.HEDGE_BASIS]
        assert len(ops) == 2
        assert all(op == OperationType.TRADE for op in ops)

    def test_flash_loan_maps_to_borrow_repay(self) -> None:
        ops = INSTRUCTION_TYPE_TO_OPERATIONS[StrategyInstructionType.FLASH_LOAN]
        assert OperationType.FLASH_BORROW in ops
        assert OperationType.FLASH_REPAY in ops


# ── StrategyInstruction typed fields ──────────────────────────────────────


class TestStrategyInstructionTypedFields:
    """Test new typed fields on StrategyInstruction."""

    def _make_instruction(self, **overrides: object) -> StrategyInstruction:
        defaults = {
            "instruction_id": "test_001",
            "strategy_id": "TEST_STRAT",
            "timestamp": datetime(2026, 4, 15, tzinfo=UTC),
            "operation": OperationType.SWAP,
            "instrument_id": "UNISWAPV3-ETHEREUM:POOL:WETH-USDC",
            "from_venue": "UNISWAPV3-ETHEREUM",
            "to_venue": "WALLET_ETH",
            "token_in": "WETH",
            "amount": Decimal("1.5"),
        }
        defaults.update(overrides)
        return StrategyInstruction(**defaults)  # pyright: ignore[reportArgumentType]

    def test_defaults(self) -> None:
        instr = self._make_instruction()
        assert instr.instruction_type is None
        assert instr.leg_role == LegRole.AUTO
        assert instr.group_id is None
        assert instr.algo is None
        assert instr.urgency == Urgency.NORMAL
        assert instr.protocol is None
        assert instr.chain is None
        assert instr.source_chain is None
        assert instr.dest_chain is None
        assert instr.client_id is None

    def test_typed_instruction_set(self) -> None:
        instr = self._make_instruction(
            instruction_type=StrategyInstructionType.SWAP,
            leg_role=LegRole.PRIMARY,
            group_id="arb_001",
            algo="SOR",
            urgency=Urgency.HIGH,
            protocol="UNISWAP_V3",
            chain="ETHEREUM",
            client_id="CLIENT_A",
        )
        assert instr.instruction_type == StrategyInstructionType.SWAP
        assert instr.leg_role == LegRole.PRIMARY
        assert instr.group_id == "arb_001"
        assert instr.algo == "SOR"
        assert instr.urgency == Urgency.HIGH
        assert instr.protocol == "UNISWAP_V3"
        assert instr.chain == "ETHEREUM"
        assert instr.client_id == "CLIENT_A"

    def test_bridge_fields(self) -> None:
        instr = self._make_instruction(
            instruction_type=StrategyInstructionType.BRIDGE,
            operation=OperationType.TRANSFER,
            source_chain="ETHEREUM",
            dest_chain="ARBITRUM",
        )
        assert instr.source_chain == "ETHEREUM"
        assert instr.dest_chain == "ARBITRUM"

    def test_to_dict_includes_new_fields(self) -> None:
        instr = self._make_instruction(
            instruction_type=StrategyInstructionType.LEND,
            leg_role=LegRole.HEDGE,
            group_id="group_abc",
            algo="TWAP",
            urgency=Urgency.LOW,
            protocol="AAVE_V3",
            chain="ARBITRUM",
            source_chain="ETHEREUM",
            dest_chain="ARBITRUM",
            client_id="CL_1",
        )
        d = instr.to_dict()
        assert d["instruction_type"] == "LEND"
        assert d["leg_role"] == "HEDGE"
        assert d["group_id"] == "group_abc"
        assert d["algo"] == "TWAP"
        assert d["urgency"] == "LOW"
        assert d["protocol"] == "AAVE_V3"
        assert d["chain"] == "ARBITRUM"
        assert d["source_chain"] == "ETHEREUM"
        assert d["dest_chain"] == "ARBITRUM"
        assert d["client_id"] == "CL_1"

    def test_to_dict_none_instruction_type(self) -> None:
        instr = self._make_instruction()
        d = instr.to_dict()
        assert d["instruction_type"] is None
        assert d["leg_role"] == "AUTO"
        assert d["urgency"] == "NORMAL"

    def test_round_trip_serialization(self) -> None:
        instr = self._make_instruction(
            instruction_type=StrategyInstructionType.HEDGE_BASIS,
            leg_role=LegRole.PRIMARY,
            group_id="basis_001",
            algo="VWAP",
            urgency=Urgency.IMMEDIATE,
            protocol="MORPHO_BLUE",
            chain="BASE",
            client_id="IK_FUND",
        )
        d = instr.to_dict()
        restored = StrategyInstruction.from_dict(d)

        assert restored.instruction_type == StrategyInstructionType.HEDGE_BASIS
        assert restored.leg_role == LegRole.PRIMARY
        assert restored.group_id == "basis_001"
        assert restored.algo == "VWAP"
        assert restored.urgency == Urgency.IMMEDIATE
        assert restored.protocol == "MORPHO_BLUE"
        assert restored.chain == "BASE"
        assert restored.client_id == "IK_FUND"

    def test_from_dict_defaults_when_fields_missing(self) -> None:
        """Backwards compatibility: from_dict with no new fields uses defaults."""
        d = {
            "instruction_id": "old_001",
            "strategy_id": "LEGACY",
            "timestamp": "2026-04-15T00:00:00+00:00",
            "operation": "SWAP",
            "instrument_id": "TEST:POOL:A-B",
            "from_venue": "TEST",
            "to_venue": "WALLET",
            "token_in": "A",
            "amount": "100",
        }
        restored = StrategyInstruction.from_dict(d)
        assert restored.instruction_type is None
        assert restored.leg_role == LegRole.AUTO
        assert restored.group_id is None
        assert restored.algo is None
        assert restored.urgency == Urgency.NORMAL
        assert restored.protocol is None
        assert restored.chain is None
        assert restored.client_id is None
