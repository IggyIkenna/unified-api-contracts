"""Client reporting domain schemas — document management, invoicing, compliance, NAV.

SSOT for:
- DocumentMetadata: document lifecycle tracking
- DocumentCategory: document classification
- DocumentStatus: document state machine
- FundNAVSnapshot: NAV snapshot payload for external operations partners
- PerformanceSummary: equity curves, monthly returns, stats
- TradeRecord: individual trade/fill records
- Invoice: dual HWM invoice lifecycle
- HourlyBalanceSnapshot: hourly equity snapshots
"""

from .balance_snapshot import (
    DailyBalanceSummary,
    HourlyBalanceSnapshot,
    PositionSnapshot,
    SnapshotSource,
)
from .invoice import (
    FeeLineType,
    HWMState,
    Invoice,
    InvoiceHistoryEntry,
    InvoiceLineItem,
    InvoiceStatus,
)
from .nav_snapshot import (
    AssetBalanceSummary,
    DeFiHealthSummary,
    FundNAVSnapshot,
    NAVSnapshotFrequency,
    NAVSnapshotStatus,
    PositionSummary,
    TradeActivitySummary,
    VenueBalanceSummary,
    WebhookDeliveryConfig,
)
from .performance import (
    EquityCurvePoint,
    MonthlyReturn,
    PerformanceStats,
    PerformanceSummary,
)
from .schemas import DocumentCategory, DocumentMetadata, DocumentStatus
from .trades import (
    CoinPnLBreakdown,
    PortfolioAllocation,
    TradeRecord,
    TradeSide,
    TradeType,
    TransferRecord,
)

__all__ = [
    "AssetBalanceSummary",
    "CoinPnLBreakdown",
    "DailyBalanceSummary",
    "DeFiHealthSummary",
    "DocumentCategory",
    "DocumentMetadata",
    "DocumentStatus",
    "EquityCurvePoint",
    "FeeLineType",
    "FundNAVSnapshot",
    "HWMState",
    "HourlyBalanceSnapshot",
    "Invoice",
    "InvoiceHistoryEntry",
    "InvoiceLineItem",
    "InvoiceStatus",
    "MonthlyReturn",
    "NAVSnapshotFrequency",
    "NAVSnapshotStatus",
    "PerformanceStats",
    "PerformanceSummary",
    "PortfolioAllocation",
    "PositionSnapshot",
    "PositionSummary",
    "SnapshotSource",
    "TradeActivitySummary",
    "TradeRecord",
    "TradeSide",
    "TradeType",
    "TransferRecord",
    "VenueBalanceSummary",
    "WebhookDeliveryConfig",
]
