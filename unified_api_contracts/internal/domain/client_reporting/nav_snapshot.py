"""Fund NAV snapshot schemas for external operations partner integration.

FundNAVSnapshot is the payload pushed to external operations partners (e.g. POD/Elysium)
at each NAV cut-off point. It aggregates cross-venue balances and positions into a
structured payload suitable for NAV calculation and on-chain settlement.

The strategy-service builds these snapshots and pushes them via webhook.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, Field


class NAVSnapshotFrequency(StrEnum):
    """How often NAV snapshots are produced."""

    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    ON_DEMAND = "ON_DEMAND"


class NAVSnapshotStatus(StrEnum):
    """Delivery status of a NAV snapshot."""

    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    ACKNOWLEDGED = "ACKNOWLEDGED"


class AssetBalanceSummary(BaseModel, frozen=True):
    """Per-asset balance across all venues for a fund."""

    currency: str = Field(description="Asset symbol (e.g. BTC, ETH, USDT)")
    free: Decimal = Field(description="Available for trading")
    locked: Decimal = Field(description="Locked in open orders / collateral")
    total: Decimal = Field(description="free + locked")
    usd_value: Decimal = Field(description="Total converted to USD at mark price")


class VenueBalanceSummary(BaseModel, frozen=True):
    """Per-venue balance summary for a fund."""

    venue: str = Field(description="Venue identifier (e.g. BINANCE, AAVE_V3_ETHEREUM)")
    total_usd: Decimal = Field(description="Total balance at this venue in USD")
    position_count: int = Field(description="Number of open positions at this venue")
    asset_count: int = Field(description="Number of distinct assets held")


class PositionSummary(BaseModel, frozen=True):
    """Aggregated position statistics for the fund."""

    total_positions: int = Field(description="Count of open positions")
    gross_exposure_usd: Decimal = Field(description="Sum of abs(notional) across all positions")
    net_exposure_usd: Decimal = Field(description="Net directional exposure in USD")
    total_unrealized_pnl_usd: Decimal = Field(description="Sum of unrealized P&L across positions")
    total_realized_pnl_usd: Decimal = Field(description="Sum of realized P&L since last snapshot")
    long_count: int = Field(default=0, description="Number of long positions")
    short_count: int = Field(default=0, description="Number of short positions")


class DeFiHealthSummary(BaseModel, frozen=True):
    """DeFi-specific health metrics for the fund (Aave, Morpho, etc.)."""

    total_collateral_usd: Decimal = Field(
        default=Decimal("0"), description="Total collateral deposited across protocols"
    )
    total_debt_usd: Decimal = Field(default=Decimal("0"), description="Total debt across protocols")
    weighted_health_factor: Decimal | None = Field(
        default=None, description="Weighted average health factor (Aave-style)"
    )
    total_staked_usd: Decimal = Field(default=Decimal("0"), description="Total staked value (Lido, EtherFi)")
    total_lp_value_usd: Decimal = Field(default=Decimal("0"), description="Total LP position value (Uniswap, Curve)")


class TradeActivitySummary(BaseModel, frozen=True):
    """Trade activity since the previous NAV snapshot."""

    trade_count: int = Field(default=0, description="Number of trades since last snapshot")
    total_volume_usd: Decimal = Field(default=Decimal("0"), description="Total traded volume in USD")
    total_fees_usd: Decimal = Field(default=Decimal("0"), description="Total fees paid in USD")
    period_start: AwareDatetime | None = Field(default=None, description="Start of the activity window")
    period_end: AwareDatetime | None = Field(
        default=None, description="End of the activity window (= snapshot timestamp)"
    )


class WebhookDeliveryConfig(BaseModel, frozen=True):
    """Configuration for webhook delivery to an external operations partner."""

    webhook_url: str = Field(description="HTTPS endpoint to POST the NAV snapshot")
    auth_header_name: str = Field(default="X-API-Key", description="HTTP header name for authentication")
    auth_header_value_secret: str = Field(description="Secret Manager secret name containing the auth token")
    timeout_seconds: int = Field(default=30, description="HTTP request timeout")
    retry_count: int = Field(default=3, description="Number of retries on failure")
    ops_partner_name: str = Field(default="pod", description="Identifier for the operations partner (for logging)")


class FundNAVSnapshot(BaseModel, frozen=True):
    """NAV snapshot payload pushed to external operations partners.

    This is the contract between Odum's strategy-service and
    external operations partners (e.g. POD/Elysium). At each NAV cut-off point,
    a snapshot is built from cross-venue balances and positions, then POSTed
    to the configured webhook endpoint.

    The operations partner uses this to compute official NAV, update smart contract
    settlement layers, and generate investor reports.
    """

    # Identification
    snapshot_id: str = Field(description="Unique snapshot identifier (UUID)")
    fund_id: str = Field(description="Fund identifier in Odum's system")
    fund_name: str = Field(default="", description="Human-readable fund name")
    client_ids: list[str] = Field(
        default_factory=list,
        description="Client IDs that roll up into this fund",
        json_schema_extra={"pii": True},
    )

    # Timing
    snapshot_timestamp: AwareDatetime = Field(description="NAV cut-off timestamp (UTC)")
    previous_snapshot_id: str | None = Field(
        default=None, description="ID of the previous snapshot (for delta tracking)"
    )
    frequency: NAVSnapshotFrequency = Field(default=NAVSnapshotFrequency.DAILY, description="Snapshot cadence")

    # NAV
    nav_usd: Decimal = Field(description="Net Asset Value in USD (total_equity)")
    nav_change_usd: Decimal | None = Field(default=None, description="NAV change since previous snapshot")
    nav_change_pct: Decimal | None = Field(default=None, description="NAV change as percentage")

    # Breakdowns
    asset_balances: list[AssetBalanceSummary] = Field(default_factory=list, description="Per-asset balance breakdown")
    venue_balances: list[VenueBalanceSummary] = Field(default_factory=list, description="Per-venue balance breakdown")
    position_summary: PositionSummary | None = Field(default=None, description="Aggregated position statistics")
    defi_health: DeFiHealthSummary | None = Field(default=None, description="DeFi-specific health metrics")
    trade_activity: TradeActivitySummary | None = Field(default=None, description="Trade activity since last snapshot")

    # Exposure by asset class / strategy
    asset_class_exposures_usd: dict[str, Decimal] = Field(
        default_factory=dict, description="Exposure by asset class (CeFi, DeFi, TradFi, etc.)"
    )
    strategy_exposures_usd: dict[str, Decimal] = Field(default_factory=dict, description="Exposure by strategy ID")

    # Metadata
    schema_version: str = Field(default="1.0", description="Schema version for evolution")
    source_service: str = Field(
        default="strategy-service",
        description="Service that produced this snapshot",
    )
    reconciliation_status: str = Field(
        default="CLEAN",
        description="CLEAN if no active discrepancies, DISCREPANCY if unresolved",
    )
