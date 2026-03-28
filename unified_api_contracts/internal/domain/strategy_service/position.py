"""
Strategy Position Models

Defines StrategyPosition model for tracking positions with raw/normalized
quantities and multi-instrument DeFi support.

PositionType / PositionSide SSOT:
    unified_api_contracts.internal.domain.execution_service.types
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from uuid import uuid4

from unified_api_contracts.internal.domain.execution_service.types import (
    PositionSide,
    PositionType,
)


@dataclass
class StrategyPosition:
    """
    Strategy position with raw and normalized quantities.

    Supports multi-instrument DeFi positions with index-based tracking
    for AAVE aTokens and debtTokens.

    Canonical instrument ID format: VENUE:INSTRUMENT_TYPE:PAYLOAD[@CHAIN]
    Examples:
      - BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN
      - AAVE_V3_ETH:A_TOKEN:AUSDT@ETHEREUM
      - ETHERFI:LST:WEETH@ETHEREUM
    """

    # Core identification
    position_id: str
    strategy_id: str
    instrument_id: str  # Canonical format
    position_type: PositionType

    # Quantities
    quantity_raw: Decimal  # Actual token quantity (e.g., 1.5 BTC)
    quantity_normalized: Decimal  # USD value

    # Pricing
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal

    # Timing
    timestamp: datetime
    entry_timestamp: datetime | None = None

    # Direction (for directional positions)
    side: PositionSide = PositionSide.NEUTRAL

    # For DeFi index-based positions (AAVE aTokens/debtTokens)
    entry_index: Decimal | None = None  # AAVE liquidity_index at entry
    current_index: Decimal | None = None  # Current liquidity_index

    # For tracking realized PnL
    realized_pnl: Decimal = Decimal("0")

    # Additional metadata
    metadata: dict[str, str | int | float | bool | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Generate position_id if not provided."""
        if not self.position_id:
            self.position_id = f"pos_{uuid4().hex[:12]}"
        if self.entry_timestamp is None:
            self.entry_timestamp = self.timestamp

    @property
    def is_index_based(self) -> bool:
        """Check if position uses index-based tracking (AAVE)."""
        return self.position_type in (PositionType.A_TOKEN, PositionType.DEBT_TOKEN)

    @property
    def index_return(self) -> Decimal:
        """Calculate return from index change (for AAVE positions)."""
        if not self.is_index_based or self.entry_index is None or self.current_index is None:
            return Decimal("0")

        if self.entry_index == 0:
            return Decimal("0")

        return (self.current_index - self.entry_index) / self.entry_index

    @property
    def total_pnl(self) -> Decimal:
        """Total PnL (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl

    @property
    def pnl_percentage(self) -> Decimal:
        """PnL as percentage of entry value."""
        entry_value = self.quantity_raw * self.entry_price
        if entry_value == 0:
            return Decimal("0")
        return (self.total_pnl / entry_value) * 100

    def update_price(self, new_price: Decimal, new_index: Decimal | None = None) -> None:
        """
        Update position with new market price.

        Args:
            new_price: New market price
            new_index: New AAVE index (for index-based positions)
        """
        self.current_price = new_price

        if new_index is not None:
            self.current_index = new_index

        # Recalculate unrealized PnL
        if self.side == PositionSide.LONG:
            self.unrealized_pnl = self.quantity_raw * (self.current_price - self.entry_price)
        elif self.side == PositionSide.SHORT:
            self.unrealized_pnl = self.quantity_raw * (self.entry_price - self.current_price)
        else:
            # For neutral positions (lending), PnL comes from index growth
            if self.is_index_based:
                self.unrealized_pnl = self.quantity_raw * self.entry_price * self.index_return
            else:
                self.unrealized_pnl = Decimal("0")

        # Update normalized quantity
        self.quantity_normalized = self.quantity_raw * self.current_price
        self.timestamp = datetime.now(UTC)

    def apply_delta(self, delta: Decimal, price: Decimal) -> None:
        """
        Apply quantity delta to position.

        Args:
            delta: Change in quantity (positive = add, negative = reduce)
            price: Execution price for the delta
        """
        old_quantity = self.quantity_raw
        new_quantity = old_quantity + delta

        if delta < 0:
            # Reducing position - realize PnL
            reduce_pct = abs(delta) / old_quantity if old_quantity != 0 else Decimal("0")
            realized = self.unrealized_pnl * reduce_pct
            self.realized_pnl += realized
            self.unrealized_pnl -= realized
        else:
            # Increasing position - update entry price (weighted average)
            if new_quantity != 0:
                old_value = old_quantity * self.entry_price
                new_value = delta * price
                self.entry_price = (old_value + new_value) / new_quantity

        self.quantity_raw = new_quantity
        self.timestamp = datetime.now(UTC)

    def close(self, close_price: Decimal) -> Decimal:
        """
        Close position and return realized PnL.

        Args:
            close_price: Price at which position is closed

        Returns:
            Total realized PnL from closing
        """
        self.update_price(close_price)
        total_realized = self.unrealized_pnl + self.realized_pnl

        self.realized_pnl = total_realized
        self.unrealized_pnl = Decimal("0")
        self.quantity_raw = Decimal("0")
        self.quantity_normalized = Decimal("0")
        self.timestamp = datetime.now(UTC)

        return total_realized

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for serialization."""
        return {
            "position_id": self.position_id,
            "strategy_id": self.strategy_id,
            "instrument_id": self.instrument_id,
            "position_type": self.position_type.value,
            "side": self.side.value,
            "quantity_raw": str(self.quantity_raw),
            "quantity_normalized": str(self.quantity_normalized),
            "entry_price": str(self.entry_price),
            "current_price": str(self.current_price),
            "unrealized_pnl": str(self.unrealized_pnl),
            "realized_pnl": str(self.realized_pnl),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "entry_timestamp": self.entry_timestamp.isoformat() if self.entry_timestamp else None,
            "entry_index": str(self.entry_index) if self.entry_index else None,
            "current_index": str(self.current_index) if self.current_index else None,
            "metadata": self.metadata,
        }

    @staticmethod
    def _parse_enums(data: dict[str, object]) -> tuple[PositionType, PositionSide]:
        """Parse position_type and side enums from dict values."""
        pt_val = data.get("position_type")
        position_type: PositionType = (
            PositionType(pt_val) if isinstance(pt_val, str) else cast(PositionType, pt_val)
        )
        side_val = data.get("side")
        side: PositionSide = (
            PositionSide(side_val)
            if isinstance(side_val, str)
            else cast(PositionSide, side_val) or PositionSide.NEUTRAL
        )
        return position_type, side

    @staticmethod
    def _parse_timestamps(data: dict[str, object]) -> tuple[datetime, datetime | None]:
        """Parse timestamp and entry_timestamp from dict values."""
        ts_val = data.get("timestamp")
        timestamp: datetime = (
            datetime.fromisoformat(ts_val.rstrip("Z"))
            if isinstance(ts_val, str)
            else cast(datetime, ts_val)
        )
        ets_val = data.get("entry_timestamp")
        entry_timestamp: datetime | None = (
            datetime.fromisoformat(ets_val.rstrip("Z"))
            if isinstance(ets_val, str)
            else cast("datetime | None", ets_val)
        )
        return timestamp, entry_timestamp

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "StrategyPosition":
        """Create StrategyPosition from dictionary."""
        position_type, side = cls._parse_enums(data)
        timestamp, entry_timestamp = cls._parse_timestamps(data)

        def _dec(val: object) -> Decimal:
            return Decimal(str(val))

        def _dec_opt(val: object) -> Decimal | None:
            return Decimal(str(val)) if val is not None else None

        metadata: dict[str, str | int | float | bool | None] = cast(
            "dict[str, str | int | float | bool | None]", data.get("metadata") or {}
        )
        return cls(
            position_id=cast(str, data.get("position_id") or ""),
            strategy_id=cast(str, data.get("strategy_id") or ""),
            instrument_id=cast(str, data.get("instrument_id") or ""),
            position_type=position_type,
            quantity_raw=_dec(data.get("quantity_raw", "0")),
            quantity_normalized=_dec(data.get("quantity_normalized", "0")),
            entry_price=_dec(data.get("entry_price", "0")),
            current_price=_dec(data.get("current_price", "0")),
            unrealized_pnl=_dec(data.get("unrealized_pnl", "0")),
            timestamp=timestamp,
            entry_timestamp=entry_timestamp,
            side=side,
            entry_index=_dec_opt(data.get("entry_index")),
            current_index=_dec_opt(data.get("current_index")),
            realized_pnl=_dec(data.get("realized_pnl", "0")),
            metadata=metadata,
        )


@dataclass
class PositionSnapshot:
    """
    Snapshot of all positions at a point in time.

    Used for tracking portfolio state across multiple instruments
    in multi-leg strategies like DeFi basis trades.
    """

    snapshot_id: str
    strategy_id: str
    timestamp: datetime
    positions: list[StrategyPosition]

    # Aggregated metrics
    total_equity_usd: Decimal = Decimal("0")
    total_unrealized_pnl: Decimal = Decimal("0")
    total_realized_pnl: Decimal = Decimal("0")

    metadata: dict[str, str | int | float | bool | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Calculate aggregated metrics."""
        if not self.snapshot_id:
            self.snapshot_id = f"snap_{uuid4().hex[:12]}"

        self.total_equity_usd = sum((p.quantity_normalized for p in self.positions), Decimal("0"))
        self.total_unrealized_pnl = sum((p.unrealized_pnl for p in self.positions), Decimal("0"))
        self.total_realized_pnl = sum((p.realized_pnl for p in self.positions), Decimal("0"))

    def get_position(self, instrument_id: str) -> StrategyPosition | None:
        """Get position by instrument ID."""
        for pos in self.positions:
            if pos.instrument_id == instrument_id:
                return pos
        return None

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for serialization."""
        return {
            "snapshot_id": self.snapshot_id,
            "strategy_id": self.strategy_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "positions": [p.to_dict() for p in self.positions],
            "total_equity_usd": str(self.total_equity_usd),
            "total_unrealized_pnl": str(self.total_unrealized_pnl),
            "total_realized_pnl": str(self.total_realized_pnl),
            "metadata": self.metadata,
        }
