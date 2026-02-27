"""Regulatory and compliance reporting schemas.

Covers MiFID II, EMIR, Dodd-Frank trade reporting, trade surveillance,
and best execution monitoring obligations.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class ReportingRegime(StrEnum):
    MIFID_II = "mifid_ii"
    EMIR = "emir"
    DODD_FRANK = "dodd_frank"
    MAS = "mas"
    ASIC = "asic"
    CFTC = "cftc"
    SEC = "sec"


class TradeReportStatus(StrEnum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    AMENDED = "amended"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# MiFID II
# ---------------------------------------------------------------------------


class MifidIIWaiverFlag(StrEnum):
    RFPT = "RFPT"  # Reference price transaction
    NLIQ = "NLIQ"  # Negotiated transaction in illiquid instrument
    OILQ = "OILQ"  # Negotiated transaction subject to conditions
    PRIC = "PRIC"  # Negotiated transaction subject to conditions other than price
    ILQD = "ILQD"  # Illiquid instrument waiver
    SIZE = "SIZE"  # Large in scale waiver
    FWAF = "FWAF"  # Forex waiver above threshold


class MifidIITradeReport(BaseModel):
    """MiFID II transaction report (ESMA RTS 22)."""

    report_id: str
    exec_id: str = Field(description="unique execution identifier")
    transaction_reference_number: str | None = None
    trading_datetime: datetime
    instrument_isin: str = Field(description="ISIN of the financial instrument")
    instrument_full_name: str | None = None
    trading_venue_mic: str = Field(description="ISO 10383 MIC code of execution venue")
    quantity: Decimal
    price: Decimal
    currency: str = Field(description="ISO 4217")
    notional_amount: Decimal | None = None
    client_id: str
    trader_id: str = Field(description="LEI or national client ID of trader")
    investment_firm_lei: str = Field(description="LEI of reporting investment firm")
    country_of_branch: str | None = None
    waiver_flags: list[MifidIIWaiverFlag] = Field(default_factory=list)
    short_selling_indicator: bool = False
    otc_post_trade_indicator: str | None = None
    regime: ReportingRegime = ReportingRegime.MIFID_II
    report_status: TradeReportStatus = TradeReportStatus.PENDING
    submitted_at: datetime | None = None
    trade_repository: str | None = None


class BestExecutionRecord(BaseModel):
    """MiFID II best execution monitoring record (RTS 28)."""

    record_id: str
    order_id: str
    instrument_id: str
    instrument_isin: str | None = None
    order_datetime: datetime
    execution_datetime: datetime | None = None
    order_type: str
    order_size: Decimal
    benchmark_price: Decimal = Field(description="arrival mid-price at order entry")
    execution_price: Decimal | None = None
    slippage_bps: float | None = None
    market_impact_bps: float | None = None
    execution_venue_mic: str | None = None
    venues_considered: list[str] = Field(default_factory=list)
    best_venue_price: Decimal | None = None
    execution_quality_score: float | None = None
    algo_used: str | None = None
    client_id: str | None = None


# ---------------------------------------------------------------------------
# EMIR
# ---------------------------------------------------------------------------


class EmirProductClassification(StrEnum):
    INTEREST_RATE = "INTR"
    FX = "CRCY"
    EQUITY = "EQUI"
    CREDIT = "CRDT"
    COMMODITY = "COMM"
    OTHER = "OTHR"


class EmirTradeReport(BaseModel):
    """EMIR trade report (ESMA Regulatory Technical Standard)."""

    report_id: str
    unique_trade_identifier: str = Field(alias="uti", description="UTI — 52-char max")
    prior_uti: str | None = None
    reporting_counterparty_lei: str
    other_counterparty_lei: str | None = None
    reporting_timestamp: datetime
    event_type: str = Field(description="NEWT/MODI/EROR/VALU/MARU/CORR/TERM")
    product_classification: EmirProductClassification
    asset_class: str | None = None
    underlying_isin: str | None = None
    notional_amount: Decimal | None = None
    notional_currency: str | None = None
    maturity_date: date | None = None
    execution_venue: str | None = None
    cleared: bool = False
    clearing_counterparty_lei: str | None = None
    collateral_posted_usd: Decimal | None = None
    regime: ReportingRegime = ReportingRegime.EMIR
    report_status: TradeReportStatus = TradeReportStatus.PENDING
    submitted_at: datetime | None = None

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Dodd-Frank / CFTC
# ---------------------------------------------------------------------------


class DoddFrankSwapReport(BaseModel):
    """CFTC Dodd-Frank swap data record (SDR submission)."""

    report_id: str
    unique_swap_identifier: str = Field(alias="usi")
    prior_usi: str | None = None
    reporting_counterparty_lei: str
    other_counterparty_lei: str | None = None
    execution_timestamp: datetime
    dissemination_timestamp: datetime | None = None
    product_type: str = Field(description="SD/FX/EQ/IR/CR/CO")
    underlying_asset: str | None = None
    execution_venue: str
    cleared_via_ccp: str | None = Field(default=None, description="CCP LEI or name")
    notional_amount: Decimal | None = None
    notional_currency: str = "USD"
    price: Decimal | None = None
    maturity_date: date | None = None
    regime: ReportingRegime = ReportingRegime.DODD_FRANK
    report_status: TradeReportStatus = TradeReportStatus.PENDING
    sdr_name: str | None = Field(default=None, description="e.g. DTCC, CME SDR, ICE Trade Vault")
    submitted_at: datetime | None = None

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Trade surveillance
# ---------------------------------------------------------------------------


class SurveillancePatternType(StrEnum):
    SPOOFING = "spoofing"
    LAYERING = "layering"
    WASH_TRADING = "wash_trading"
    FRONT_RUNNING = "front_running"
    MARKING_THE_CLOSE = "marking_the_close"
    PUMP_AND_DUMP = "pump_and_dump"
    MOMENTUM_IGNITION = "momentum_ignition"
    EXCESSIVE_CANCELLATIONS = "excessive_cancellations"
    CROSS_MARKET_MANIPULATION = "cross_market_manipulation"


class TradeSurveillanceAlert(BaseModel):
    """Alert generated by trade surveillance engine."""

    alert_id: str
    pattern_type: SurveillancePatternType
    detected_at: datetime
    instruments: list[str]
    accounts: list[str]
    venues: list[str] = Field(default_factory=list)
    confidence_score: float = Field(description="0-1 probability of violation")
    triggered_rules: list[str] = Field(default_factory=list)
    evidence_window_start: datetime | None = None
    evidence_window_end: datetime | None = None
    order_ids: list[str] = Field(default_factory=list)
    fill_ids: list[str] = Field(default_factory=list)
    estimated_pnl_impact: Decimal | None = None
    severity: str = "MEDIUM"
    status: str = "open"
    assigned_to: str | None = None
    resolution_notes: str | None = None


class BestExecutionMonitoringRecord(BaseModel):
    """Periodic aggregated best execution quality report (RTS 27/28 style)."""

    period_start: date
    period_end: date
    venue: str
    instrument_class: str
    total_orders: int
    fill_rate: float = Field(description="fraction of orders filled")
    avg_slippage_bps: float
    median_slippage_bps: float
    p95_slippage_bps: float
    avg_market_impact_bps: float
    avg_time_to_fill_ms: float | None = None
    price_improvement_rate: float | None = Field(
        default=None, description="fraction of orders with better than benchmark price"
    )
    venue_mic: str | None = None
    currency: str = "USD"


class TradeReportingError(BaseModel):
    """Error response from a trade reporting system / trade repository."""

    error_code: str
    message: str
    report_id: str | None = None
    field_name: str | None = None
    timestamp: datetime | None = None
    regime: ReportingRegime | None = None
