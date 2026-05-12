"""Client reporting contracts — per-client NAV, PnL, positions, and attribution.

SSOT: plans/active/client_reporting_pnl_attribution_mvp_2026_05_10.md Phase 1.
Companion codex: codex/04-architecture/client-reporting-architecture.md (Phase 7.A).

Types:
  ClientReportingMode — DEMO / PAPER / LIVE (closed set).
  ClientPosition      — per-position lineage with cost-basis + PnL.
  ClientPnLEntry      — per-period realized + unrealized PnL summary.
  ClientNAV           — per-client NAV snapshot (mark-to-market).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field

from unified_api_contracts.canonical.crosscutting.share_class import ShareClass


class ClientReportingMode(StrEnum):
    """Operational mode for a client reporting context.

    DEMO   — internal demo client; paper-trade data; no real assets.
    PAPER  — external paper-trade client; real venue connectivity; no assets.
    LIVE   — live client; real assets under management.
    """

    DEMO = "DEMO"
    PAPER = "PAPER"
    LIVE = "LIVE"


class ClientPosition(BaseModel):
    """Per-position snapshot with cost-basis lineage for a single client.

    Carries the full trade lineage (archetype_id, strategy_leg_id, trade_id)
    required by the PnL attribution emitter to join position events to fills.
    """

    client_id: str = Field(..., json_schema_extra={"pii": True})
    archetype_id: str | None = None
    strategy_leg_id: str | None = None
    trade_id: str | None = None
    venue: str
    instrument: str
    qty: Decimal
    mark_price: Decimal
    cost_basis: Decimal
    realized_pnl: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    share_class: ShareClass = ShareClass.USDT
    timestamp: datetime


class ClientPnLEntry(BaseModel):
    """Per-period PnL summary for a single client.

    period_tag examples: '2026-05-12' (daily) | '2026-05-12T08:00' (intraday).
    Detailed attribution rows (factor x layer breakdown) are stored separately
    as PnLAttributionRow parquets per Phase 2.B — not embedded here.
    """

    client_id: str = Field(..., json_schema_extra={"pii": True})
    period_tag: str
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_pnl: Decimal
    strategy_alpha_total: Decimal = Decimal("0")
    """Derived from PnLAttributionRow parquet: sum where layer=STRATEGY."""
    execution_alpha_total: Decimal = Decimal("0")
    """Derived from PnLAttributionRow parquet: sum where layer=EXECUTION."""
    share_class: ShareClass = ShareClass.USDT
    timestamp: datetime


class ClientNAV(BaseModel):
    """Per-client NAV snapshot (mark-to-market equity).

    nav_delta is the change since the previous snapshot of the same period
    granularity.  Signed: positive = NAV increased, negative = decreased.
    """

    client_id: str = Field(..., json_schema_extra={"pii": True})
    share_class: ShareClass
    nav_usd: Decimal
    nav_in_share_class: Decimal
    nav_delta_usd: Decimal = Decimal("0")
    mode: ClientReportingMode = ClientReportingMode.DEMO
    timestamp: datetime
