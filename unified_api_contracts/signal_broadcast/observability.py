"""Observability envelopes for the signal-broadcast REST-pull surface.

These pydantic models shape the JSON responses served by
``strategy-service`` under ``/signal_broadcast/{delivery-health,
backtest-paper-live, pnl-attribution}``. The UI
(`unified-trading-system-ui/lib/signal-broadcast/hooks.ts`) consumes the
same JSON via typed fetch hooks; the TypeScript mirrors live in
`unified-trading-system-ui/lib/signal-broadcast/types.ts` and MUST stay
aligned with the field names + types below (field renames in either
surface are breaking changes and require a coordinated PR).

Plan SSOT:
    unified-trading-pm/plans/active/signal_leasing_broadcast_architecture_2026_04_20.plan.md
    § Phase 10 — strategy-service observability read endpoints (follow-up 2026-04-20)
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeliveryHealth(BaseModel):
    """Rolling-24h delivery health snapshot for one counterparty.

    Populated in-process by ``WebhookTransport`` on every dispatch attempt
    (retry / success / permanent-failure) and served as a point-in-time
    aggregate. Numeric fields are bounded: ``success_rate`` is a float in
    [0, 1]; counters are non-negative.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    success_rate: float = Field(ge=0.0, le=1.0)
    retries_24h: int = Field(ge=0)
    avg_latency_ms: float = Field(ge=0.0)
    last_delivery_at: datetime | None
    total_deliveries_24h: int = Field(ge=0)


class BacktestPaperLiveRow(BaseModel):
    """Three-way parity row for one entitled slot over a shared window.

    Null paper / live_return fields are first-class — they signal "this
    slot has not yet reached the PAPER_TRADING or LIVE_ALLOCATED stage of
    the maturity ladder" and the UI renders em-dashes. All metrics on a
    single row are computed over ``[window_start, window_end)`` so the
    backtest / paper / live columns are comparable.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    slot_label: str = Field(min_length=1)
    window_start: datetime
    window_end: datetime
    backtest_sharpe: float
    backtest_return_pct: float
    paper_sharpe: float | None
    paper_return_pct: float | None
    paper_signal_count: int | None = Field(default=None, ge=0)
    live_signal_count: int = Field(ge=0)
    live_signal_hit_rate: float = Field(ge=0.0, le=1.0)
    live_return_pct: float | None


class PnlAttributionRow(BaseModel):
    """Counterparty-reported P&L attribution for one slot + window.

    Opt-in (per ``Counterparty.pnl_reporting_enabled``). Populated by
    counterparty-initiated POSTs to ``/signal_broadcast/pnl-attribution``
    and served back unchanged via the matching GET. Odum does not observe
    counterparty fills — values are whatever the counterparty reports.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    slot_label: str = Field(min_length=1)
    reported_pnl_usd: float
    reported_signal_count: int = Field(ge=0)
    reporting_window_start: datetime
    reporting_window_end: datetime


class DeliveryHealthEnvelope(BaseModel):
    """Response envelope for ``GET /signal_broadcast/delivery-health``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    health: DeliveryHealth


class BacktestPaperLiveEnvelope(BaseModel):
    """Response envelope for ``GET /signal_broadcast/backtest-paper-live``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rows: list[BacktestPaperLiveRow] = Field(default_factory=list)


class PnlAttributionEnvelope(BaseModel):
    """Response envelope for ``GET /signal_broadcast/pnl-attribution``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rows: list[PnlAttributionRow] = Field(default_factory=list)


class PnlAttributionReport(BaseModel):
    """Counterparty-initiated POST body for ``/signal_broadcast/pnl-attribution``.

    Opt-in counterparties push their own P&L attribution back to Odum so the
    observability dashboard can render the optional ``<PnlAttributionPanel>``.
    Odum stores and serves these unchanged — there is no reconciliation
    against fills (by D10 design Odum does not observe counterparty fills).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    counterparty_id: str = Field(min_length=1)
    rows: list[PnlAttributionRow] = Field(default_factory=list)


__all__ = [
    "BacktestPaperLiveEnvelope",
    "BacktestPaperLiveRow",
    "DeliveryHealth",
    "DeliveryHealthEnvelope",
    "PnlAttributionEnvelope",
    "PnlAttributionReport",
    "PnlAttributionRow",
]
