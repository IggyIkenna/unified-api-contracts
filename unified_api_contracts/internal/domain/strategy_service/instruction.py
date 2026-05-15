"""
Strategy Instruction Models

Defines StrategyInstruction, StrategyInstructionType, and DeFiSignal models
for generating typed trade instructions to execution-services.

Strategy-level instruction types (StrategyInstructionType) represent what
strategies emit — high-level intents like SWAP, LEND, HEDGE_BASIS. The
execution-service interprets these and decomposes them into atomic
OperationType steps.

OperationType and OrderType SSOT: unified_api_contracts.internal.domain.execution_service.types
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal, cast
from uuid import uuid4

from unified_api_contracts.canonical.domain.derivatives.futures import (
    FuturesContractLifecyclePhase,
)
from unified_api_contracts.internal.domain.execution_service.multi_leg import (
    LegRole,
)
from unified_api_contracts.internal.domain.execution_service.types import (
    BenchmarkType,
    OperationType,
    OrderType,
)

MetadataValue = str | int | float | bool | None
MetadataMap = dict[str, MetadataValue]


def _metadata_or_empty(metadata: MetadataMap | None) -> MetadataMap:
    return {} if metadata is None else metadata


# ---------------------------------------------------------------------------
# StrategyInstructionType — high-level instruction vocabulary for strategies
# ---------------------------------------------------------------------------


class StrategyInstructionType(StrEnum):
    """All instruction types a strategy can emit.

    These are higher-level than OperationType. A single StrategyInstructionType
    may decompose into multiple OperationType steps in execution-service.

    For example:
    - HEDGE_BASIS -> [TRADE (spot buy), TRADE (perp short)]
    - FLASH_LOAN -> [FLASH_BORROW, SWAP, LEND, BORROW, FLASH_REPAY]
    - REBALANCE_PORTFOLIO -> multiple SWAP/TRADE operations
    """

    # ── Trading ────────────────────────────────────────────────────────
    MARKET_ORDER = "MARKET_ORDER"
    """Submit a market order on a CLOB venue (CeFi or perp DEX)."""

    LIMIT_ORDER = "LIMIT_ORDER"
    """Submit a limit order on a CLOB venue."""

    # ── DeFi primitives ────────────────────────────────────────────────
    SWAP = "SWAP"
    """DEX token swap (e.g. Uniswap, Curve)."""

    LEND = "LEND"
    """Deposit into a lending protocol (Aave, Morpho)."""

    BORROW = "BORROW"
    """Borrow from a lending protocol."""

    REPAY = "REPAY"
    """Repay a lending protocol debt."""

    WITHDRAW = "WITHDRAW"
    """Withdraw from a lending protocol."""

    STAKE = "STAKE"
    """Stake tokens (Lido, EtherFi, native staking)."""

    UNSTAKE = "UNSTAKE"
    """Unstake / request withdrawal from staking protocol."""

    BRIDGE = "BRIDGE"
    """Cross-chain bridge transfer."""

    FLASH_LOAN = "FLASH_LOAN"
    """Atomic flash loan sequence (borrow + ops + repay in one tx)."""

    # ── Composite instructions ─────────────────────────────────────────
    HEDGE_BASIS = "HEDGE_BASIS"
    """Spot + perp hedge pair for basis trading."""

    REBALANCE_LP = "REBALANCE_LP"
    """Concentrated liquidity LP position rebalancing."""

    REBALANCE_PORTFOLIO = "REBALANCE_PORTFOLIO"
    """Adjust portfolio to target weights across venues."""

    # ── Sports / prediction ────────────────────────────────────────────
    BACK = "BACK"
    """Back bet on a sports exchange (e.g. Betfair)."""

    LAY = "LAY"
    """Lay bet on a sports exchange."""

    # ── Helpers ─────────────────────────────────────────────────────────

    @classmethod
    def defi_primitives(cls) -> list["StrategyInstructionType"]:
        """All single-step DeFi instruction types."""
        return [cls.SWAP, cls.LEND, cls.BORROW, cls.REPAY, cls.WITHDRAW, cls.STAKE, cls.UNSTAKE, cls.BRIDGE]

    @classmethod
    def composite_types(cls) -> list["StrategyInstructionType"]:
        """Instructions that decompose into multiple execution steps."""
        return [cls.HEDGE_BASIS, cls.REBALANCE_LP, cls.REBALANCE_PORTFOLIO, cls.FLASH_LOAN]

    @classmethod
    def trading_types(cls) -> list["StrategyInstructionType"]:
        """CLOB trading instructions."""
        return [cls.MARKET_ORDER, cls.LIMIT_ORDER]

    @classmethod
    def sports_types(cls) -> list["StrategyInstructionType"]:
        """Sports betting instructions."""
        return [cls.BACK, cls.LAY]


# ---------------------------------------------------------------------------
# Urgency — how quickly the instruction should be filled
# ---------------------------------------------------------------------------


class Urgency(StrEnum):
    """Order urgency classification for execution routing.

    Determines algorithm selection and aggression level in execution-service:
    - LOW: Passive fills, maker-preferred, can wait for optimal price.
    - NORMAL: Standard execution, balanced speed/price.
    - HIGH: Aggressive fills, taker-preferred, prioritise speed.
    - IMMEDIATE: Must fill now (IOC/FOK), accept market impact.
    """

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    IMMEDIATE = "IMMEDIATE"


# ---------------------------------------------------------------------------
# INSTRUCTION_TYPE_TO_OPERATIONS — maps strategy types to execution operations
# ---------------------------------------------------------------------------

INSTRUCTION_TYPE_TO_OPERATIONS: dict[StrategyInstructionType, list[OperationType]] = {
    StrategyInstructionType.MARKET_ORDER: [OperationType.TRADE],
    StrategyInstructionType.LIMIT_ORDER: [OperationType.TRADE],
    StrategyInstructionType.SWAP: [OperationType.SWAP],
    StrategyInstructionType.LEND: [OperationType.LEND],
    StrategyInstructionType.BORROW: [OperationType.BORROW],
    StrategyInstructionType.REPAY: [OperationType.REPAY],
    StrategyInstructionType.WITHDRAW: [OperationType.WITHDRAW],
    StrategyInstructionType.STAKE: [OperationType.STAKE],
    StrategyInstructionType.UNSTAKE: [OperationType.UNSTAKE],
    StrategyInstructionType.BRIDGE: [OperationType.TRANSFER],
    StrategyInstructionType.FLASH_LOAN: [
        OperationType.FLASH_BORROW,
        OperationType.FLASH_REPAY,
    ],
    StrategyInstructionType.HEDGE_BASIS: [OperationType.TRADE, OperationType.TRADE],
    StrategyInstructionType.REBALANCE_LP: [
        OperationType.REMOVE_LIQUIDITY,
        OperationType.SWAP,
        OperationType.ADD_LIQUIDITY,
    ],
    StrategyInstructionType.REBALANCE_PORTFOLIO: [OperationType.SWAP],
    StrategyInstructionType.BACK: [OperationType.SPORTS_EXCHANGE_ORDER],
    StrategyInstructionType.LAY: [OperationType.SPORTS_EXCHANGE_ORDER],
}


@dataclass
class StrategyInstruction:
    """
    Single execution instruction generated by strategy service.

    This model defines the interface between strategy-service and execution-services.
    It supports both CEFI/TRADFI trades and DeFi protocol operations.

    Canonical instrument ID format: VENUE:INSTRUMENT_TYPE:PAYLOAD[@CHAIN]
    Examples:
      - BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN
      - AAVE_V3_ETH:A_TOKEN:AUSDT@ETHEREUM
      - HYPERLIQUID:PERPETUAL:ETH-USDC@LIN@HYPERLIQUID
    """

    # Core identification
    instruction_id: str
    strategy_id: str
    timestamp: datetime

    # Operation details
    operation: OperationType
    instrument_id: str  # Canonical format
    from_venue: str
    to_venue: str
    token_in: str
    amount: Decimal

    # Optional trading fields
    token_out: str | None = None
    direction: Literal["LONG", "SHORT", "FLAT"] | None = None
    target_position: Decimal | None = None

    # Pricing
    benchmark_price: Decimal | None = None
    benchmark_type: BenchmarkType = BenchmarkType.ARRIVAL
    limit_price: Decimal | None = None
    order_type: OrderType = OrderType.MARKET

    # Risk management
    stop_loss_price: Decimal | None = None
    take_profit_price: Decimal | None = None
    max_slippage_bps: int = 50  # Default 0.5%

    # Smart order routing for DeFi spot
    allowed_venues: list[str] | None = None

    # Gas parameters for on-chain operations
    gas_limit: int | None = None
    priority_fee_gwei: float | None = None
    deadline_timestamp: datetime | None = None

    # Share class denomination
    share_class: str = field(default="USDT", metadata={"description": "Base currency denomination (USDT, ETH, BTC)"})
    base_currency_amount: Decimal | None = field(default=None, metadata={"description": "Amount in share class terms"})
    base_currency_price: Decimal | None = field(
        default=None, metadata={"description": "FX rate used for share class conversion"}
    )

    # Expected output for instant P&L computation
    expected_output: Decimal | None = field(
        default=None,
        metadata={
            "description": (
                "Expected output amount at benchmark price — used for instant P&L = (actual - expected) * price"
            ),
        },
    )

    # ── Typed instruction fields (strategy instruction bus) ────────────
    instruction_type: StrategyInstructionType | None = field(
        default=None,
        metadata={
            "description": (
                "High-level instruction type from strategy. When set, execution-service "
                "uses this to decompose into execution steps. When None, falls back to "
                "operation field for backwards compatibility."
            ),
        },
    )

    # Multi-leg grouping
    leg_role: LegRole = field(
        default=LegRole.AUTO,
        metadata={"description": "Role of this instruction in a multi-leg group (PRIMARY, HEDGE, AUTO)."},
    )
    group_id: str | None = field(
        default=None,
        metadata={"description": "Groups instructions into multi-leg trades. Same group_id = same atomic group."},
    )

    # Execution preferences
    algo: str | None = field(
        default=None,
        metadata={"description": "Preferred execution algorithm (TWAP, VWAP, SOR, MARKET, etc.)."},
    )
    urgency: Urgency = field(
        default=Urgency.NORMAL,
        metadata={"description": "How urgently the instruction should be filled."},
    )

    # DeFi protocol routing
    protocol: str | None = field(
        default=None,
        metadata={"description": "Target DeFi protocol (AAVE_V3, MORPHO_BLUE, UNISWAP_V3, LIDO, etc.)."},
    )
    chain: str | None = field(
        default=None,
        metadata={"description": "Target chain for DeFi operations (ETHEREUM, ARBITRUM, BASE, etc.)."},
    )
    source_chain: str | None = field(
        default=None,
        metadata={"description": "Source chain for BRIDGE instructions."},
    )
    dest_chain: str | None = field(
        default=None,
        metadata={"description": "Destination chain for BRIDGE instructions."},
    )

    # Client and account routing
    client_id: str = field(default="", metadata={"description": "Client identifier for routing."})
    account_id: str | None = field(default=None, metadata={"description": "Account key (client:venue:label)."})

    # Market making — delta-proxy repricing (see codex/09-strategy/market-making-reference-price.md)
    reference_price: Decimal | None = field(default=None, metadata={"description": "Underlying ref price."})
    underlying_instrument_id: str | None = field(default=None, metadata={"description": "Underlying to track."})
    delta: Decimal | None = field(default=None, metadata={"description": "Instrument delta to underlying."})
    gamma: Decimal | None = field(default=None, metadata={"description": "Second-order delta sensitivity."})
    delta_premium: Decimal | None = field(default=None, metadata={"description": "Options delta-premium."})

    # Additional metadata
    metadata: MetadataMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Generate instruction_id if not provided."""
        if not self.instruction_id:
            self.instruction_id = f"inst_{uuid4().hex[:12]}"

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for serialization."""
        return {
            "instruction_id": self.instruction_id,
            "strategy_id": self.strategy_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "operation": self.operation.value,
            "instrument_id": self.instrument_id,
            "from_venue": self.from_venue,
            "to_venue": self.to_venue,
            "token_in": self.token_in,
            "token_out": self.token_out,
            "amount": str(self.amount) if self.amount else None,
            "direction": self.direction,
            "target_position": str(self.target_position) if self.target_position else None,
            "benchmark_price": str(self.benchmark_price) if self.benchmark_price else None,
            "benchmark_type": self.benchmark_type.value,
            "limit_price": str(self.limit_price) if self.limit_price else None,
            "order_type": self.order_type.value,
            "stop_loss_price": str(self.stop_loss_price) if self.stop_loss_price else None,
            "take_profit_price": str(self.take_profit_price) if self.take_profit_price else None,
            "max_slippage_bps": self.max_slippage_bps,
            "allowed_venues": self.allowed_venues,
            "gas_limit": self.gas_limit,
            "priority_fee_gwei": self.priority_fee_gwei,
            "deadline_timestamp": self.deadline_timestamp.isoformat() if self.deadline_timestamp else None,
            "share_class": self.share_class,
            "base_currency_amount": str(self.base_currency_amount) if self.base_currency_amount is not None else None,
            "base_currency_price": str(self.base_currency_price) if self.base_currency_price is not None else None,
            "expected_output": str(self.expected_output) if self.expected_output is not None else None,
            # Typed instruction bus fields
            "instruction_type": self.instruction_type.value if self.instruction_type else None,
            "leg_role": self.leg_role.value,
            "group_id": self.group_id,
            "algo": self.algo,
            "urgency": self.urgency.value,
            "protocol": self.protocol,
            "chain": self.chain,
            "source_chain": self.source_chain,
            "dest_chain": self.dest_chain,
            "client_id": self.client_id,
            "reference_price": str(self.reference_price) if self.reference_price is not None else None,
            "underlying_instrument_id": self.underlying_instrument_id,
            "delta": str(self.delta) if self.delta is not None else None,
            "gamma": str(self.gamma) if self.gamma is not None else None,
            "delta_premium": str(self.delta_premium) if self.delta_premium is not None else None,
            "metadata": self.metadata,
        }

    @staticmethod
    def _parse_enums(
        data: dict[str, object],
    ) -> tuple[OperationType, BenchmarkType, OrderType]:
        """Parse operation, benchmark_type, and order_type enums from dict."""
        op_val = data.get("operation")
        operation: OperationType = OperationType(op_val) if isinstance(op_val, str) else cast(OperationType, op_val)
        bench_val = data.get("benchmark_type")
        benchmark_type: BenchmarkType = (
            BenchmarkType(bench_val)
            if isinstance(bench_val, str)
            else cast(BenchmarkType, bench_val) or BenchmarkType.ARRIVAL
        )
        order_val = data.get("order_type")
        order_type: OrderType = (
            OrderType(order_val) if isinstance(order_val, str) else cast(OrderType, order_val) or OrderType.MARKET
        )
        return operation, benchmark_type, order_type

    @staticmethod
    def _parse_timestamps(data: dict[str, object]) -> tuple[datetime, datetime | None]:
        """Parse timestamp and deadline_timestamp from dict."""
        ts_val = data.get("timestamp")
        timestamp: datetime = (
            datetime.fromisoformat(ts_val.rstrip("Z")) if isinstance(ts_val, str) else cast(datetime, ts_val)
        )
        deadline_val = data.get("deadline_timestamp")
        deadline_timestamp: datetime | None = (
            datetime.fromisoformat(deadline_val.rstrip("Z"))
            if isinstance(deadline_val, str)
            else cast("datetime | None", deadline_val)
        )
        return timestamp, deadline_timestamp

    @staticmethod
    def _parse_instruction_bus_fields(
        data: dict[str, object],
    ) -> tuple["StrategyInstructionType | None", "LegRole", "Urgency"]:
        """Parse typed instruction bus fields from dict."""
        instr_type_val = data.get("instruction_type")
        instruction_type: StrategyInstructionType | None = (
            StrategyInstructionType(instr_type_val) if isinstance(instr_type_val, str) else None
        )
        leg_role_val = data.get("leg_role")
        leg_role: LegRole = LegRole(leg_role_val) if isinstance(leg_role_val, str) else LegRole.AUTO
        urgency_val = data.get("urgency")
        urgency: Urgency = Urgency(urgency_val) if isinstance(urgency_val, str) else Urgency.NORMAL
        return instruction_type, leg_role, urgency

    @staticmethod
    def _dec(val: object) -> Decimal:
        return Decimal(str(val))

    @staticmethod
    def _dec_opt(val: object) -> "Decimal | None":
        return Decimal(str(val)) if val is not None else None

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "StrategyInstruction":
        """Create StrategyInstruction from dictionary."""
        operation, benchmark_type, order_type = cls._parse_enums(data)
        timestamp, deadline_timestamp = cls._parse_timestamps(data)
        instruction_type, leg_role, urgency = cls._parse_instruction_bus_fields(data)
        return cls(
            instruction_id=cast(str, data.get("instruction_id") or ""),
            strategy_id=cast(str, data.get("strategy_id") or ""),
            timestamp=timestamp,
            operation=operation,
            instrument_id=cast(str, data.get("instrument_id") or ""),
            from_venue=cast(str, data.get("from_venue") or ""),
            to_venue=cast(str, data.get("to_venue") or ""),
            token_in=cast(str, data.get("token_in") or ""),
            amount=cls._dec(data.get("amount", "0")),
            token_out=cast("str | None", data.get("token_out")),
            direction=cast("Literal['LONG', 'SHORT', 'FLAT'] | None", data.get("direction")),
            target_position=cls._dec_opt(data.get("target_position")),
            benchmark_price=cls._dec_opt(data.get("benchmark_price")),
            benchmark_type=benchmark_type,
            limit_price=cls._dec_opt(data.get("limit_price")),
            order_type=order_type,
            stop_loss_price=cls._dec_opt(data.get("stop_loss_price")),
            take_profit_price=cls._dec_opt(data.get("take_profit_price")),
            max_slippage_bps=cast(int, data.get("max_slippage_bps", 50)),
            allowed_venues=cast("list[str] | None", data.get("allowed_venues")),
            gas_limit=cast("int | None", data.get("gas_limit")),
            priority_fee_gwei=cast("float | None", data.get("priority_fee_gwei")),
            deadline_timestamp=deadline_timestamp,
            share_class=cast(str, data.get("share_class") or "USDT"),
            base_currency_amount=cls._dec_opt(data.get("base_currency_amount")),
            base_currency_price=cls._dec_opt(data.get("base_currency_price")),
            expected_output=cls._dec_opt(data.get("expected_output")),
            instruction_type=instruction_type,
            leg_role=leg_role,
            group_id=cast("str | None", data.get("group_id")),
            algo=cast("str | None", data.get("algo")),
            urgency=urgency,
            protocol=cast("str | None", data.get("protocol")),
            chain=cast("str | None", data.get("chain")),
            source_chain=cast("str | None", data.get("source_chain")),
            dest_chain=cast("str | None", data.get("dest_chain")),
            client_id=cast("str | None", data.get("client_id")),
            metadata=_metadata_or_empty(cast("MetadataMap | None", data.get("metadata"))),
        )


@dataclass
class DeFiSignal:
    """
    Output format for DeFi strategies - matches execution-services schema.

    A DeFi signal contains one or more instructions that may be executed
    atomically (all-or-nothing, e.g., flash loan sequence) or sequentially.

    For atomic signals (is_atomic=True):
    - All instructions must succeed or all are rolled back
    - Typically used for flash loan sequences
    - FLASH_BORROW must come before FLASH_REPAY
    - Flash loan amounts must match (repay = borrow + fee)
    """

    signal_id: str
    strategy_id: str
    timestamp: datetime
    is_atomic: bool  # If True, all-or-nothing execution
    instructions: list[StrategyInstruction]

    # Expected outcome
    expected_apy: Decimal | None = None
    ethena_benchmark_apy: Decimal | None = None  # For comparison

    # Risk parameters
    max_total_slippage_bps: int = 100  # Default 1% total slippage
    total_gas_budget: int | None = None

    # Additional metadata
    metadata: MetadataMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Generate signal_id if not provided."""
        if not self.signal_id:
            self.signal_id = f"sig_{uuid4().hex[:12]}"

        # Validate atomic signals
        if self.is_atomic:
            self._validate_atomic_signal()

    def _validate_atomic_signal(self) -> None:
        """Validate atomic signal constraints."""
        flash_borrows = [i for i in self.instructions if i.operation == OperationType.FLASH_BORROW]
        flash_repays = [i for i in self.instructions if i.operation == OperationType.FLASH_REPAY]

        if flash_borrows and len(flash_borrows) != len(flash_repays):
            raise ValueError("Atomic signals with flash loans must have paired FLASH_BORROW/FLASH_REPAY")

        # Verify FLASH_BORROW comes before FLASH_REPAY
        if flash_borrows and flash_repays:
            borrow_indices = [self.instructions.index(fb) for fb in flash_borrows]
            repay_indices = [self.instructions.index(fr) for fr in flash_repays]

            for bi, ri in zip(borrow_indices, repay_indices, strict=False):
                if bi >= ri:
                    raise ValueError("FLASH_BORROW must come before FLASH_REPAY in instruction order")

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for serialization."""
        return {
            "signal_id": self.signal_id,
            "strategy_id": self.strategy_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "is_atomic": self.is_atomic,
            "instructions": [i.to_dict() for i in self.instructions],
            "expected_apy": str(self.expected_apy) if self.expected_apy else None,
            "ethena_benchmark_apy": str(self.ethena_benchmark_apy) if self.ethena_benchmark_apy else None,
            "max_total_slippage_bps": self.max_total_slippage_bps,
            "total_gas_budget": self.total_gas_budget,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "DeFiSignal":
        """Create DeFiSignal from dictionary."""
        # Parse instructions
        instructions_val = data.get("instructions")
        instructions: list[StrategyInstruction] = []
        if instructions_val and isinstance(instructions_val, list):
            instructions = [
                StrategyInstruction.from_dict(cast(dict[str, object], item))
                if isinstance(item, dict)
                else cast(StrategyInstruction, item)
                for item in cast(list[object], instructions_val)
            ]

        # Parse decimals
        def _to_decimal_opt(val: object) -> Decimal | None:
            return Decimal(str(val)) if val is not None else None

        # Parse timestamp
        ts_val = data.get("timestamp")
        timestamp: datetime = (
            datetime.fromisoformat(ts_val.rstrip("Z")) if isinstance(ts_val, str) else cast(datetime, ts_val)
        )

        metadata = _metadata_or_empty(cast("MetadataMap | None", data.get("metadata")))

        return cls(
            signal_id=cast(str, data.get("signal_id") or ""),
            strategy_id=cast(str, data.get("strategy_id") or ""),
            timestamp=timestamp,
            is_atomic=cast(bool, data.get("is_atomic", False)),
            instructions=instructions,
            expected_apy=_to_decimal_opt(data.get("expected_apy")),
            ethena_benchmark_apy=_to_decimal_opt(data.get("ethena_benchmark_apy")),
            max_total_slippage_bps=cast(int, data.get("max_total_slippage_bps", 100)),
            total_gas_budget=cast("int | None", data.get("total_gas_budget")),
            metadata=metadata,
        )


# ---------------------------------------------------------------------------
# Specialized instruction builders for each domain
# ---------------------------------------------------------------------------


@dataclass
class TransferInstruction:
    """Execution instruction for cross-venue asset transfers (CEX <-> DeFi wallet).

    Covers three scenarios:
    - CEX -> DeFi wallet: Fund a DeFi strategy from exchange holdings
    - DeFi wallet -> CEX: Return funds after closing a DeFi position
    - Sweep: Consolidate small balances from multiple wallets to main wallet
    - ETH reserve top-up: Ensure DeFi wallets maintain minimum ETH for gas
    """

    instruction: StrategyInstruction
    transfer_reason: str  # "FUND_DEFI" | "RETURN_TO_CEX" | "SWEEP" | "ETH_RESERVE"

    @staticmethod
    def create(
        *,
        strategy_id: str,
        timestamp: datetime,
        from_venue: str,
        to_venue: str,
        token: str,
        quantity: Decimal,
        transfer_reason: str,
        metadata: MetadataMap | None = None,
    ) -> "TransferInstruction":
        """Create a TRANSFER instruction for moving assets between venues.

        Args:
            strategy_id: Owning strategy identifier.
            timestamp: Signal generation timestamp.
            from_venue: Source venue (e.g. "BINANCE-SPOT" or "AAVE-ETHEREUM").
            to_venue: Destination venue.
            token: Asset to transfer (e.g. "USDC", "ETH").
            quantity: Amount to transfer.
            transfer_reason: Why the transfer is needed.
            metadata: Additional key-value metadata.

        Returns:
            TransferInstruction wrapping a StrategyInstruction with TRANSFER operation.
        """
        combined_metadata: MetadataMap = {
            "transfer_reason": transfer_reason,
            **_metadata_or_empty(metadata),
        }
        instr = StrategyInstruction(
            instruction_id="",
            strategy_id=strategy_id,
            timestamp=timestamp,
            operation=OperationType.TRANSFER,
            instrument_id=f"{from_venue}:TRANSFER:{token}",
            from_venue=from_venue,
            to_venue=to_venue,
            token_in=token,
            amount=quantity,
            metadata=combined_metadata,
        )
        return TransferInstruction(
            instruction=instr,
            transfer_reason=transfer_reason,
        )


@dataclass
class PredictionBetInstruction:
    """Execution instruction for a prediction market bet (e.g. Polymarket, Kalshi)."""

    instruction: StrategyInstruction
    market_id: str
    outcome_side: str  # "YES" or "NO"
    implied_probability: Decimal
    max_cost_usd: Decimal

    @staticmethod
    def create(
        *,
        strategy_id: str,
        timestamp: datetime,
        venue: str,
        instrument_id: str,
        market_id: str,
        outcome_side: str,
        implied_probability: Decimal,
        amount: Decimal,
        max_cost_usd: Decimal,
        limit_price: Decimal | None = None,
        metadata: MetadataMap | None = None,
    ) -> "PredictionBetInstruction":
        instr = StrategyInstruction(
            instruction_id="",
            strategy_id=strategy_id,
            timestamp=timestamp,
            operation=OperationType.PREDICTION_BET,
            instrument_id=instrument_id,
            from_venue=venue,
            to_venue=venue,
            token_in="USDC",
            amount=amount,
            limit_price=limit_price,
            order_type=OrderType.LIMIT if limit_price else OrderType.MARKET,
            metadata=_metadata_or_empty(metadata),
        )
        return PredictionBetInstruction(
            instruction=instr,
            market_id=market_id,
            outcome_side=outcome_side,
            implied_probability=implied_probability,
            max_cost_usd=max_cost_usd,
        )


@dataclass
class SportsBetInstruction:
    """Execution instruction for a fixed-odds sports bet (bookmaker API or web)."""

    instruction: StrategyInstruction
    event_id: str
    outcome: str
    bookmaker: str
    decimal_odds: Decimal
    stake_fraction: Decimal

    @staticmethod
    def create(
        *,
        strategy_id: str,
        timestamp: datetime,
        venue: str,
        instrument_id: str,
        event_id: str,
        outcome: str,
        bookmaker: str,
        decimal_odds: Decimal,
        amount: Decimal,
        stake_fraction: Decimal,
        metadata: MetadataMap | None = None,
    ) -> "SportsBetInstruction":
        instr = StrategyInstruction(
            instruction_id="",
            strategy_id=strategy_id,
            timestamp=timestamp,
            operation=OperationType.SPORTS_BET,
            instrument_id=instrument_id,
            from_venue="BANKROLL",
            to_venue=venue,
            token_in="GBP",
            amount=amount,
            metadata=_metadata_or_empty(metadata),
        )
        return SportsBetInstruction(
            instruction=instr,
            event_id=event_id,
            outcome=outcome,
            bookmaker=bookmaker,
            decimal_odds=decimal_odds,
            stake_fraction=stake_fraction,
        )


@dataclass
class SportsExchangeOrderInstruction:
    """Execution instruction for a sports exchange order (Betfair, Smarkets, etc.)."""

    instruction: StrategyInstruction
    market_id: str
    selection_id: str
    side: str  # "BACK" or "LAY"
    decimal_odds: Decimal
    persistence_type: str = "LAPSE"

    @staticmethod
    def create(
        *,
        strategy_id: str,
        timestamp: datetime,
        venue: str,
        instrument_id: str,
        market_id: str,
        selection_id: str,
        side: str,
        decimal_odds: Decimal,
        amount: Decimal,
        persistence_type: str = "LAPSE",
        metadata: MetadataMap | None = None,
    ) -> "SportsExchangeOrderInstruction":
        instr = StrategyInstruction(
            instruction_id="",
            strategy_id=strategy_id,
            timestamp=timestamp,
            operation=OperationType.SPORTS_EXCHANGE_ORDER,
            instrument_id=instrument_id,
            from_venue=venue,
            to_venue=venue,
            token_in="GBP",
            amount=amount,
            limit_price=decimal_odds,
            order_type=OrderType.LIMIT,
            metadata=_metadata_or_empty(metadata),
        )
        return SportsExchangeOrderInstruction(
            instruction=instr,
            market_id=market_id,
            selection_id=selection_id,
            side=side,
            decimal_odds=decimal_odds,
            persistence_type=persistence_type,
        )


@dataclass
class FuturesRollInstruction:
    """Execution instruction for rolling a futures position from near to far contract."""

    instruction: StrategyInstruction
    near_contract_id: str
    far_contract_id: str
    roll_spread: Decimal | None = None
    lifecycle_phase: FuturesContractLifecyclePhase | None = None

    @staticmethod
    def create(
        *,
        strategy_id: str,
        timestamp: datetime,
        venue: str,
        near_contract_id: str,
        far_contract_id: str,
        amount: Decimal,
        direction: "Literal['LONG', 'SHORT', 'FLAT']",
        roll_spread: Decimal | None = None,
        lifecycle_phase: FuturesContractLifecyclePhase | None = None,
        metadata: MetadataMap | None = None,
    ) -> "FuturesRollInstruction":
        instr = StrategyInstruction(
            instruction_id="",
            strategy_id=strategy_id,
            timestamp=timestamp,
            operation=OperationType.FUTURES_ROLL,
            instrument_id=near_contract_id,
            from_venue=venue,
            to_venue=venue,
            token_in="USD",
            amount=amount,
            direction=direction,
            metadata=_metadata_or_empty(metadata),
        )
        return FuturesRollInstruction(
            instruction=instr,
            near_contract_id=near_contract_id,
            far_contract_id=far_contract_id,
            roll_spread=roll_spread,
            lifecycle_phase=lifecycle_phase,
        )


@dataclass
class OptionsComboInstruction:
    """Execution instruction for a multi-leg options combination."""

    legs: list[StrategyInstruction]
    combo_type: str
    net_premium: Decimal | None = None
    strategy_id: str = ""
    timestamp: datetime | None = None

    @staticmethod
    def create(
        *,
        strategy_id: str,
        timestamp: datetime,
        venue: str,
        legs: list[dict[str, object]],
        combo_type: str,
        net_premium: Decimal | None = None,
        metadata: MetadataMap | None = None,
    ) -> "OptionsComboInstruction":
        built_legs: list[StrategyInstruction] = []
        for leg in legs:
            instrument_id_val = leg.get("instrument_id")
            if not isinstance(instrument_id_val, str) or not instrument_id_val:
                raise ValueError("Each options combo leg requires a non-empty instrument_id")
            amount_val = leg.get("amount")
            if amount_val is None:
                raise ValueError(f"Missing amount for options combo leg {instrument_id_val}")
            instr = StrategyInstruction(
                instruction_id="",
                strategy_id=strategy_id,
                timestamp=timestamp,
                operation=OperationType.OPTIONS_COMBO,
                instrument_id=instrument_id_val,
                from_venue=venue,
                to_venue=venue,
                token_in="USD",
                amount=Decimal(str(amount_val)),
                direction=cast("Literal['LONG', 'SHORT', 'FLAT'] | None", leg.get("direction")),
                limit_price=Decimal(str(leg["limit_price"])) if leg.get("limit_price") else None,
                order_type=OrderType.LIMIT,
                metadata=_metadata_or_empty(metadata),
            )
            built_legs.append(instr)
        return OptionsComboInstruction(
            legs=built_legs,
            combo_type=combo_type,
            net_premium=net_premium,
            strategy_id=strategy_id,
            timestamp=timestamp,
        )
