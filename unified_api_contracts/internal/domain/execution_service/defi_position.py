"""
DeFi Position Model

Defines position types and tracking for DeFi protocols:
- aTokens (AAVE supply positions)
- debtTokens (AAVE borrow positions)
- LSTs (Liquid staking tokens)
- LP positions (DEX liquidity)

PositionType SSOT: unified_api_contracts.internal.domain.execution_service.types
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import cast

from unified_api_contracts.internal.domain.execution_service.types import PositionType, ensure_dict


@dataclass
class DeFiPosition:
    """
    DeFi protocol position.

    Tracks holdings across different DeFi protocols with proper
    accounting for interest accrual, exchange rates, and health factors.

    Attributes:
        position_id: Unique identifier
        position_type: Type of position (A_TOKEN, DEBT_TOKEN, LST, etc.)
        venue: Protocol/venue (AAVE_V3-ETHEREUM, ETHERFI-ETHEREUM, etc.)
        token: Position token symbol (aWETH, weETH, etc.)
        underlying: Underlying token symbol (WETH, ETH, etc.)
        amount: Current position amount (in token units)
        entry_timestamp: When position was opened
        entry_price: Price at entry (for P&L)
        entry_index: Interest index at entry (for accrual)
    """

    # Identification
    position_id: str
    position_type: PositionType
    venue: str

    # Token details
    token: str
    underlying: str

    # Position size
    amount: Decimal

    # Entry details
    entry_timestamp: datetime
    entry_price: Decimal = Decimal("0")
    entry_index: Decimal = Decimal("1")  # For interest accrual

    # Current state
    current_price: Decimal = Decimal("0")
    current_index: Decimal = Decimal("1")

    # Lending-specific
    health_factor: Decimal | None = None
    ltv: Decimal | None = None
    liquidation_threshold: Decimal | None = None

    # Perp-specific
    leverage: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    funding_accrued: Decimal | None = None

    # Metadata
    chain: str = "ETHEREUM"
    contract_address: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure Decimal types."""
        decimal_fields = [
            "amount",
            "entry_price",
            "entry_index",
            "current_price",
            "current_index",
            "health_factor",
            "ltv",
            "liquidation_threshold",
            "leverage",
            "unrealized_pnl",
            "funding_accrued",
        ]
        for field_name in decimal_fields:
            val: object = cast(object, getattr(self, field_name))
            if val is not None and not isinstance(val, Decimal):
                setattr(self, field_name, Decimal(str(val)))

    @property
    def is_supply(self) -> bool:
        """Check if this is a supply/deposit position."""
        return self.position_type in [
            PositionType.A_TOKEN,
            PositionType.LST,
            PositionType.YIELD_BEARING,
        ]

    @property
    def is_borrow(self) -> bool:
        """Check if this is a borrow/debt position."""
        return self.position_type == PositionType.DEBT_TOKEN

    @property
    def is_perp(self) -> bool:
        """Check if this is a perpetual position."""
        return self.position_type == PositionType.PERPETUAL

    @property
    def accrued_interest(self) -> Decimal:
        """
        Calculate accrued interest based on index change.

        For AAVE: interest = amount * (current_index / entry_index - 1)
        """
        if self.entry_index == 0:
            return Decimal("0")

        index_growth = self.current_index / self.entry_index - Decimal("1")
        return self.amount * index_growth

    @property
    def current_amount(self) -> Decimal:
        """Get current amount including accrued interest."""
        return self.amount + self.accrued_interest

    @property
    def entry_value(self) -> Decimal:
        """Calculate entry value in quote currency."""
        return self.amount * self.entry_price

    @property
    def current_value(self) -> Decimal:
        """Calculate current value in quote currency."""
        return self.current_amount * self.current_price

    @property
    def unrealized_pnl_price(self) -> Decimal:
        """Calculate unrealized P&L from price change only."""
        return self.amount * (self.current_price - self.entry_price)

    @property
    def unrealized_pnl_total(self) -> Decimal:
        """Calculate total unrealized P&L (price + interest)."""
        return self.current_value - self.entry_value

    @property
    def is_at_risk(self) -> bool:
        """
        Check if position is at liquidation risk.

        For lending: health_factor < 1.1 is risky
        """
        if self.health_factor is not None:
            return self.health_factor < Decimal("1.1")
        return False

    def update_state(
        self,
        current_price: Decimal,
        current_index: Decimal | None = None,
        health_factor: Decimal | None = None,
        unrealized_pnl: Decimal | None = None,
        funding_accrued: Decimal | None = None,
    ):
        """Update position state with current market data."""
        self.current_price = current_price
        if current_index is not None:
            self.current_index = current_index
        if health_factor is not None:
            self.health_factor = health_factor
        if unrealized_pnl is not None:
            self.unrealized_pnl = unrealized_pnl
        if funding_accrued is not None:
            self.funding_accrued = funding_accrued

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for serialization."""
        return {
            "position_id": self.position_id,
            "position_type": self.position_type.value,
            "venue": self.venue,
            "token": self.token,
            "underlying": self.underlying,
            "amount": str(self.amount),
            "entry_timestamp": self.entry_timestamp.isoformat(),
            "entry_price": str(self.entry_price),
            "entry_index": str(self.entry_index),
            "current_price": str(self.current_price),
            "current_index": str(self.current_index),
            "current_amount": str(self.current_amount),
            "health_factor": str(self.health_factor) if self.health_factor else None,
            "ltv": str(self.ltv) if self.ltv else None,
            "liquidation_threshold": str(self.liquidation_threshold) if self.liquidation_threshold else None,
            "leverage": str(self.leverage) if self.leverage else None,
            "unrealized_pnl": str(self.unrealized_pnl) if self.unrealized_pnl else None,
            "funding_accrued": str(self.funding_accrued) if self.funding_accrued else None,
            "chain": self.chain,
            "contract_address": self.contract_address,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "DeFiPosition":
        """Create from dictionary."""
        return cls(
            position_id=cast(str, data["position_id"]),
            position_type=PositionType(cast(str, data["position_type"])),
            venue=cast(str, data["venue"]),
            token=cast(str, data["token"]),
            underlying=cast(str, data["underlying"]),
            amount=Decimal(cast(str, data["amount"])),
            entry_timestamp=datetime.fromisoformat(cast(str, data["entry_timestamp"])),
            entry_price=Decimal(cast(str, data.get("entry_price", "0"))),
            entry_index=Decimal(cast(str, data.get("entry_index", "1"))),
            current_price=Decimal(cast(str, data.get("current_price", "0"))),
            current_index=Decimal(cast(str, data.get("current_index", "1"))),
            health_factor=Decimal(cast(str, data["health_factor"])) if data.get("health_factor") else None,
            ltv=Decimal(cast(str, data["ltv"])) if data.get("ltv") else None,
            liquidation_threshold=Decimal(cast(str, data["liquidation_threshold"]))
            if data.get("liquidation_threshold")
            else None,
            leverage=Decimal(cast(str, data["leverage"])) if data.get("leverage") else None,
            unrealized_pnl=Decimal(cast(str, data["unrealized_pnl"])) if data.get("unrealized_pnl") else None,
            funding_accrued=Decimal(cast(str, data["funding_accrued"])) if data.get("funding_accrued") else None,
            chain=cast(str, data.get("chain", "ETHEREUM")),
            contract_address=cast(str | None, data.get("contract_address")),
            metadata=ensure_dict(cast(dict[str, object] | None, data.get("metadata"))),
        )


@dataclass
class PositionPortfolio:
    """
    Collection of DeFi positions for a strategy.

    Tracks all positions and calculates aggregate metrics.
    """

    strategy_id: str
    positions: list[DeFiPosition] = field(default_factory=list)

    @property
    def total_supply_value(self) -> Decimal:
        """Total value of supply positions."""
        return sum((p.current_value for p in self.positions if p.is_supply), Decimal("0"))

    @property
    def total_borrow_value(self) -> Decimal:
        """Total value of borrow positions."""
        return sum((p.current_value for p in self.positions if p.is_borrow), Decimal("0"))

    @property
    def net_value(self) -> Decimal:
        """Net portfolio value (supply - borrow)."""
        return self.total_supply_value - self.total_borrow_value

    @property
    def overall_health_factor(self) -> Decimal | None:
        """
        Calculate overall health factor.

        health_factor = Σ(collateral * liquidation_threshold) / Σ(borrow)
        """
        supply_positions = [p for p in self.positions if p.is_supply and p.liquidation_threshold]
        borrow_positions = [p for p in self.positions if p.is_borrow]

        if not borrow_positions:
            return None  # No borrows = infinite health

        weighted_collateral = sum(
            (p.current_value * p.liquidation_threshold for p in supply_positions if p.liquidation_threshold),
            Decimal("0"),
        )
        total_borrow = sum((p.current_value for p in borrow_positions), Decimal("0"))

        if total_borrow == 0:
            return None

        return weighted_collateral / total_borrow

    def get_positions_by_venue(self, venue: str) -> list[DeFiPosition]:
        """Get all positions for a specific venue."""
        return [p for p in self.positions if p.venue == venue]

    def get_positions_by_type(self, position_type: PositionType) -> list[DeFiPosition]:
        """Get all positions of a specific type."""
        return [p for p in self.positions if p.position_type == position_type]

    def add_position(self, position: DeFiPosition):
        """Add a position to the portfolio."""
        self.positions.append(position)

    def remove_position(self, position_id: str):
        """Remove a position from the portfolio."""
        self.positions = [p for p in self.positions if p.position_id != position_id]

    def get_position(self, position_id: str) -> DeFiPosition | None:
        """Get a position by ID."""
        for p in self.positions:
            if p.position_id == position_id:
                return p
        return None
