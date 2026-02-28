from __future__ import annotations

from pydantic import BaseModel


class CostExplorerDateInterval(BaseModel):
    """Date range for Cost Explorer queries."""

    Start: str | None = None
    End: str | None = None


class CostExplorerGetCostRequest(BaseModel):
    """Request for ce.get_cost_and_usage()"""

    TimePeriod: CostExplorerDateInterval | None = None
    Granularity: str | None = None
    Filter: dict[str, object] | None = None
    Metrics: list[str] | None = None
    GroupBy: list[dict[str, object]] | None = None


class CostExplorerResultByTime(BaseModel):
    """Cost result for a single time period. One entry per granularity period."""

    TimePeriod: dict[str, str] | None = None
    Total: dict[str, object] | None = None
    Groups: list[dict[str, object]] | None = None
    Estimated: bool | None = None


class CostExplorerGetCostResponse(BaseModel):
    """Response from ce.get_cost_and_usage()"""

    ResultsByTime: list[CostExplorerResultByTime] | None = None
    NextPageToken: str | None = None
    DimensionValueAttributes: list[dict[str, object]] | None = None


class CostExplorerBudget(BaseModel):
    """AWS Budget. budgets.describe_budget()"""

    BudgetName: str | None = None
    BudgetLimit: dict[str, object] | None = None
    PlannedBudgetLimits: dict[str, object] | None = None
    CostFilters: dict[str, object] | None = None
    CostTypes: dict[str, object] | None = None
    TimeUnit: str | None = None
    TimePeriod: dict[str, str] | None = None
    CalculatedSpend: dict[str, object] | None = None
    BudgetType: str | None = None
    LastUpdatedTime: str | None = None
    AutoAdjustData: dict[str, object] | None = None
