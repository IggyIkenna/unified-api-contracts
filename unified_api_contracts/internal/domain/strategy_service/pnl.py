"""
PnL Attribution Models

Defines PnLAttribution and SettlementDelta models for tracking
profit and loss with detailed attribution breakdown.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import cast
from uuid import uuid4

from unified_api_contracts.internal.execution import SettlementType


@dataclass
class SettlementDelta:
    """
    Discrete settlement events that change token balances.

    Settlements are generated at specific intervals:
    - funding_8h: Every 8 hours for CEX perpetuals
    - seasonal_weekly: Weekly for seasonal rewards programs
    - aave_index: Per-candle for AAVE positions
    - staking_yield: Continuous for LST positions
    """

    settlement_id: str
    timestamp: datetime
    settlement_type: SettlementType
    instrument_id: str  # Canonical format

    # Settlement amount
    delta_amount: Decimal
    delta_usd: Decimal | None = None  # USD value of settlement

    # For index-based settlements (AAVE)
    index_value: Decimal | None = None
    previous_index: Decimal | None = None

    # For funding settlements
    funding_rate: Decimal | None = None
    position_size: Decimal | None = None

    # Strategy reference
    strategy_id: str | None = None

    # Reconciliation fields — populated by FundingReconEngine/YieldReconEngine
    exchange_reported_amount: Decimal | None = None
    reconciliation_status: str | None = None  # "MATCH" | "DISCREPANCY" | "PENDING"
    discrepancy_bps: Decimal | None = None

    metadata: dict[str, str | int | float | bool | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Generate settlement_id if not provided."""
        if not self.settlement_id:
            self.settlement_id = f"settle_{uuid4().hex[:12]}"

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for serialization."""
        return {
            "settlement_id": self.settlement_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "settlement_type": self.settlement_type.value,
            "instrument_id": self.instrument_id,
            "delta_amount": str(self.delta_amount),
            "delta_usd": str(self.delta_usd) if self.delta_usd else None,
            "index_value": str(self.index_value) if self.index_value else None,
            "previous_index": str(self.previous_index) if self.previous_index else None,
            "funding_rate": str(self.funding_rate) if self.funding_rate else None,
            "position_size": str(self.position_size) if self.position_size else None,
            "strategy_id": self.strategy_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "SettlementDelta":
        """Create SettlementDelta from dictionary."""
        # Parse enum
        st_val = data.get("settlement_type")
        settlement_type: SettlementType = (
            SettlementType(st_val) if isinstance(st_val, str) else cast(SettlementType, st_val)
        )

        # Parse decimals
        def _to_decimal(val: object) -> Decimal:
            return Decimal(str(val))

        def _to_decimal_opt(val: object) -> Decimal | None:
            return Decimal(str(val)) if val is not None else None

        # Parse timestamp
        ts_val = data.get("timestamp")
        timestamp: datetime = (
            datetime.fromisoformat(ts_val.rstrip("Z")) if isinstance(ts_val, str) else cast(datetime, ts_val)
        )

        metadata: dict[str, str | int | float | bool | None] = cast(
            "dict[str, str | int | float | bool | None]", data.get("metadata") or {}
        )

        return cls(
            settlement_id=cast(str, data.get("settlement_id") or ""),
            timestamp=timestamp,
            settlement_type=settlement_type,
            instrument_id=cast(str, data.get("instrument_id") or ""),
            delta_amount=_to_decimal(data.get("delta_amount", "0")),
            delta_usd=_to_decimal_opt(data.get("delta_usd")),
            index_value=_to_decimal_opt(data.get("index_value")),
            previous_index=_to_decimal_opt(data.get("previous_index")),
            funding_rate=_to_decimal_opt(data.get("funding_rate")),
            position_size=_to_decimal_opt(data.get("position_size")),
            strategy_id=cast("str | None", data.get("strategy_id")),
            metadata=metadata,
        )


@dataclass
class PnLAttribution:
    """
    Detailed PnL attribution breakdown.

    Balance-based PnL is the source of truth.
    Attribution components should sum to total_pnl (within reconciliation tolerance).

    Alert if unexplained_pnl > 2% annualized.
    """

    attribution_id: str
    timestamp: datetime
    strategy_id: str

    # Balance-based PnL (source of truth)
    total_equity: Decimal
    total_pnl: Decimal  # equity_current - equity_initial

    # Attribution breakdown
    trading_pnl: Decimal = Decimal("0")  # Entry/exit price differences
    funding_pnl: Decimal = Decimal("0")  # Funding rate settlements (8h intervals)
    basis_spread_pnl: Decimal = Decimal("0")  # Spot-perp spread changes
    staking_yield_pnl: Decimal = Decimal("0")  # LST yield accrual (weETH/ETH rate)
    lending_yield_pnl: Decimal = Decimal("0")  # aToken interest (liquidity_index growth)
    borrow_cost_pnl: Decimal = Decimal("0")  # debtToken interest (borrow_index growth)
    transaction_costs: Decimal = Decimal("0")  # Trading fees + gas

    # Reconciliation
    unexplained_pnl: Decimal = Decimal("0")  # total_pnl - sum(attributed)

    # Confirmed reconciliation amounts — populated by recon engines
    fee_recon_confirmed: Decimal = Decimal("0")
    funding_recon_confirmed: Decimal = Decimal("0")
    staking_recon_confirmed: Decimal = Decimal("0")
    eigenlayer_recon_confirmed: Decimal = Decimal("0")

    # Period information
    period_start: datetime | None = None
    period_end: datetime | None = None

    # Settlement events in this period
    settlements: list[SettlementDelta] = field(default_factory=list)

    metadata: dict[str, str | int | float | bool | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Generate attribution_id if not provided and calculate reconciliation."""
        if not self.attribution_id:
            self.attribution_id = f"pnl_{uuid4().hex[:12]}"

        self._calculate_unexplained()

    def _calculate_unexplained(self) -> None:
        """Calculate unexplained PnL from attribution components."""
        attributed = (
            self.trading_pnl
            + self.funding_pnl
            + self.basis_spread_pnl
            + self.staking_yield_pnl
            + self.lending_yield_pnl
            + self.borrow_cost_pnl
            + self.transaction_costs
        )
        self.unexplained_pnl = self.total_pnl - attributed

    @property
    def attributed_pnl(self) -> Decimal:
        """Sum of all attributed PnL components."""
        return (
            self.trading_pnl
            + self.funding_pnl
            + self.basis_spread_pnl
            + self.staking_yield_pnl
            + self.lending_yield_pnl
            + self.borrow_cost_pnl
            + self.transaction_costs
        )

    @property
    def reconciliation_ratio(self) -> Decimal:
        """Ratio of attributed to total PnL."""
        if self.total_pnl == 0:
            return Decimal("1") if self.attributed_pnl == 0 else Decimal("0")
        return self.attributed_pnl / self.total_pnl

    @property
    def is_reconciled(self) -> bool:
        """Check if PnL is reconciled within 2% tolerance."""
        if self.total_pnl == 0:
            return abs(self.unexplained_pnl) < Decimal("0.01")  # $0.01 tolerance for zero PnL

        unexplained_ratio = abs(self.unexplained_pnl) / abs(self.total_pnl)
        return unexplained_ratio <= Decimal("0.02")  # 2% tolerance

    @property
    def unexplained_pnl_post_recon(self) -> Decimal:
        """Unexplained PnL after subtracting confirmed reconciliation amounts.

        Each recon engine (fee, funding, staking, EigenLayer) sets its
        *_recon_confirmed field when a discrepancy is resolved.  This property
        narrows the unexplained residual toward zero as dimensions are confirmed.
        """
        recon_total = (
            self.fee_recon_confirmed
            + self.funding_recon_confirmed
            + self.staking_recon_confirmed
            + self.eigenlayer_recon_confirmed
        )
        return self.unexplained_pnl - recon_total

    def add_settlement(self, settlement: SettlementDelta) -> None:
        """Add a settlement event and update attributed PnL."""
        self.settlements.append(settlement)

        # Update appropriate attribution bucket
        if (
            settlement.settlement_type == SettlementType.FUNDING_8H
            or settlement.settlement_type == SettlementType.FUNDING_CONTINUOUS
        ):
            self.funding_pnl += settlement.delta_usd or settlement.delta_amount
        elif settlement.settlement_type == SettlementType.AAVE_INDEX:
            # Positive index change = lending yield, negative = borrow cost
            if settlement.delta_amount >= 0:
                self.lending_yield_pnl += settlement.delta_usd or settlement.delta_amount
            else:
                self.borrow_cost_pnl += settlement.delta_usd or settlement.delta_amount
        elif settlement.settlement_type == SettlementType.STAKING_YIELD:
            self.staking_yield_pnl += settlement.delta_usd or settlement.delta_amount
        elif settlement.settlement_type == SettlementType.TRANSACTION_FEE:
            self.transaction_costs += abs(settlement.delta_usd or settlement.delta_amount)
        elif settlement.settlement_type == SettlementType.FLASH_LOAN_FEE:
            # Flash loan fees are transaction costs
            self.transaction_costs += abs(settlement.delta_usd or settlement.delta_amount)

        # Recalculate unexplained
        self._calculate_unexplained()

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for serialization."""
        return {
            "attribution_id": self.attribution_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "strategy_id": self.strategy_id,
            "total_equity": str(self.total_equity),
            "total_pnl": str(self.total_pnl),
            "trading_pnl": str(self.trading_pnl),
            "funding_pnl": str(self.funding_pnl),
            "basis_spread_pnl": str(self.basis_spread_pnl),
            "staking_yield_pnl": str(self.staking_yield_pnl),
            "lending_yield_pnl": str(self.lending_yield_pnl),
            "borrow_cost_pnl": str(self.borrow_cost_pnl),
            "transaction_costs": str(self.transaction_costs),
            "unexplained_pnl": str(self.unexplained_pnl),
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "settlements": [s.to_dict() for s in self.settlements],
            "reconciliation_ratio": str(self.reconciliation_ratio),
            "is_reconciled": self.is_reconciled,
            "metadata": self.metadata,
        }

    @staticmethod
    def _parse_timestamps(
        data: dict[str, object],
    ) -> tuple[datetime, datetime | None, datetime | None]:
        """Parse timestamp, period_start, and period_end from dict."""
        ts_val = data.get("timestamp")
        timestamp: datetime = (
            datetime.fromisoformat(ts_val.rstrip("Z")) if isinstance(ts_val, str) else cast(datetime, ts_val)
        )
        ps_val = data.get("period_start")
        period_start: datetime | None = (
            datetime.fromisoformat(ps_val.rstrip("Z")) if isinstance(ps_val, str) else cast("datetime | None", ps_val)
        )
        pe_val = data.get("period_end")
        period_end: datetime | None = (
            datetime.fromisoformat(pe_val.rstrip("Z")) if isinstance(pe_val, str) else cast("datetime | None", pe_val)
        )
        return timestamp, period_start, period_end

    @staticmethod
    def _parse_settlements(data: dict[str, object]) -> list[SettlementDelta]:
        """Parse settlements list from dict."""
        settlements_val = data.get("settlements")
        if not settlements_val or not isinstance(settlements_val, list):
            return []
        return [
            SettlementDelta.from_dict(cast(dict[str, object], item))
            if isinstance(item, dict)
            else cast(SettlementDelta, item)
            for item in cast(list[object], settlements_val)
        ]

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "PnLAttribution":
        """Create PnLAttribution from dictionary."""
        timestamp, period_start, period_end = cls._parse_timestamps(data)

        def _dec(val: object) -> Decimal:
            return Decimal(str(val))

        def _dec_d(val: object, default: str = "0") -> Decimal:
            return Decimal(str(val)) if val is not None else Decimal(default)

        return cls(
            attribution_id=cast(str, data.get("attribution_id") or ""),
            timestamp=timestamp,
            strategy_id=cast(str, data.get("strategy_id") or ""),
            total_equity=_dec(data.get("total_equity", "0")),
            total_pnl=_dec(data.get("total_pnl", "0")),
            trading_pnl=_dec_d(data.get("trading_pnl")),
            funding_pnl=_dec_d(data.get("funding_pnl")),
            basis_spread_pnl=_dec_d(data.get("basis_spread_pnl")),
            staking_yield_pnl=_dec_d(data.get("staking_yield_pnl")),
            lending_yield_pnl=_dec_d(data.get("lending_yield_pnl")),
            borrow_cost_pnl=_dec_d(data.get("borrow_cost_pnl")),
            transaction_costs=_dec_d(data.get("transaction_costs")),
            unexplained_pnl=_dec_d(data.get("unexplained_pnl")),
            period_start=period_start,
            period_end=period_end,
            settlements=cls._parse_settlements(data),
            metadata=cast("dict[str, str | int | float | bool | None]", data.get("metadata") or {}),
        )


@dataclass
class PnLSummary:
    """
    Summary of PnL over a time period.

    Aggregates multiple PnLAttribution records for reporting.
    """

    summary_id: str
    strategy_id: str
    start_date: datetime
    end_date: datetime

    # Total metrics
    initial_equity: Decimal
    final_equity: Decimal
    total_return: Decimal  # (final - initial) / initial
    total_return_pct: Decimal

    # Attribution totals
    total_trading_pnl: Decimal = Decimal("0")
    total_funding_pnl: Decimal = Decimal("0")
    total_basis_pnl: Decimal = Decimal("0")
    total_staking_pnl: Decimal = Decimal("0")
    total_lending_pnl: Decimal = Decimal("0")
    total_borrow_costs: Decimal = Decimal("0")
    total_fees: Decimal = Decimal("0")

    # Risk metrics
    sharpe_ratio: Decimal | None = None
    sortino_ratio: Decimal | None = None
    max_drawdown: Decimal | None = None
    calmar_ratio: Decimal | None = None

    # Settlement statistics
    total_settlements: int = 0
    total_funding_settlements: int = 0
    total_yield_settlements: int = 0

    metadata: dict[str, str | int | float | bool | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Generate summary_id if not provided."""
        if not self.summary_id:
            self.summary_id = f"summary_{uuid4().hex[:12]}"

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for serialization."""
        result: dict[str, object] = {
            "summary_id": self.summary_id,
            "strategy_id": self.strategy_id,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "initial_equity": str(self.initial_equity),
            "final_equity": str(self.final_equity),
            "total_return": str(self.total_return),
            "total_return_pct": str(self.total_return_pct),
            "total_trading_pnl": str(self.total_trading_pnl),
            "total_funding_pnl": str(self.total_funding_pnl),
            "total_basis_pnl": str(self.total_basis_pnl),
            "total_staking_pnl": str(self.total_staking_pnl),
            "total_lending_pnl": str(self.total_lending_pnl),
            "total_borrow_costs": str(self.total_borrow_costs),
            "total_fees": str(self.total_fees),
            "sharpe_ratio": str(self.sharpe_ratio) if self.sharpe_ratio else None,
            "sortino_ratio": str(self.sortino_ratio) if self.sortino_ratio else None,
            "max_drawdown": str(self.max_drawdown) if self.max_drawdown else None,
            "calmar_ratio": str(self.calmar_ratio) if self.calmar_ratio else None,
            "total_settlements": self.total_settlements,
            "total_funding_settlements": self.total_funding_settlements,
            "total_yield_settlements": self.total_yield_settlements,
            "metadata": self.metadata,
        }
        return result
