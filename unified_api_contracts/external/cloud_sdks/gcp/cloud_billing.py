"""Google Cloud Billing API schemas.

Covers billing account management, project billing info, cost/usage data (via
Cloud Billing export to BigQuery), and budget alerts.

REST API base: https://cloudbilling.googleapis.com/v1
Billing data export: typically via BigQuery dataset - not a real-time API.

Key use: understand GCP expenditure breakdown by service (Cloud Run, BigQuery,
GCS, Cloud Build, etc.) per project, per SKU, per day.
"""

from __future__ import annotations

from pydantic import BaseModel

from unified_api_contracts.canonical.errors import ErrorAction


class BillingAccount(BaseModel):
    """GCP billing account. GET https://cloudbilling.googleapis.com/v1/billingAccounts/{id}

    One billing account can be linked to multiple projects.
    """

    name: str | None = None
    open: bool | None = None
    display_name: str | None = None
    master_billing_account: str | None = None
    currency_code: str | None = None


class ProjectBillingInfo(BaseModel):
    """Billing info for a GCP project.

    GET https://cloudbilling.googleapis.com/v1/projects/{project}/billingInfo
    """

    name: str | None = None
    project_id: str | None = None
    billing_account_name: str | None = None
    billing_enabled: bool | None = None


class BillingService(BaseModel):
    """GCP service entry from billing catalog.

    GET https://cloudbilling.googleapis.com/v1/services
    """

    name: str | None = None
    service_id: str | None = None
    display_name: str | None = None
    business_entity_name: str | None = None


class BillingSku(BaseModel):
    """Billing SKU (pricing item within a service).

    GET https://cloudbilling.googleapis.com/v1/services/{id}/skus
    SKU = specific billable resource (e.g. "CPU allocation time")
    """

    name: str | None = None
    sku_id: str | None = None
    description: str | None = None
    service_display_name: str | None = None
    category: dict[str, object] | None = None
    service_regions: list[str] | None = None
    pricing_info: list[dict[str, object]] | None = None
    geo_taxonomy: dict[str, object] | None = None


class BudgetAlert(BaseModel):
    """Cloud Billing budget and alert threshold.

    REST: https://billingbudgets.googleapis.com/v1/billingAccounts/{ba}/budgets
    """

    name: str | None = None
    display_name: str | None = None
    budget_filter: dict[str, object] | None = None
    amount: dict[str, object] | None = None
    threshold_rules: list[dict[str, object]] | None = None
    notifications_rule: dict[str, object] | None = None
    etag: str | None = None


class BillingCostEntry(BaseModel):
    """Cost entry row from BigQuery billing export table.

    Table: {dataset}.gcp_billing_export_v1_{billing_account_id_underscored}
    This captures the schema of each row in the export - used for downstream
    cost analysis queries.
    """

    billing_account_id: str | None = None
    service: dict[str, object] | None = None
    sku: dict[str, object] | None = None
    usage_start_time: str | None = None
    usage_end_time: str | None = None
    project: dict[str, object] | None = None
    labels: list[dict[str, object]] | None = None
    system_labels: list[dict[str, object]] | None = None
    location: dict[str, object] | None = None
    resource: dict[str, object] | None = None
    export_time: str | None = None
    cost: float | None = None
    currency: str | None = None
    currency_conversion_rate: float | None = None
    usage: dict[str, object] | None = None
    credits: list[dict[str, object]] | None = None
    invoice: dict[str, object] | None = None
    cost_type: str | None = None
    adjustment_info: dict[str, object] | None = None
    tags: list[dict[str, object]] | None = None
    price: dict[str, object] | None = None


class BillingCostSummary(BaseModel):
    """Aggregated cost summary (computed from BigQuery export, not a native API response).

    Used for dashboards, budget reporting, and cost allocation.
    """

    period: str | None = None
    project_id: str | None = None
    service_description: str | None = None
    sku_description: str | None = None
    total_cost_usd: float | None = None
    total_usage_amount: float | None = None
    usage_unit: str | None = None
    location: str | None = None
    credits_applied: float | None = None
    net_cost_usd: float | None = None


class BillingError(BaseModel):
    """Cloud Billing API error."""

    code: int | None = None
    message: str | None = None
    status: str | None = None

    @classmethod
    def classify(cls, code: int | None = None, http_status: int | None = None):
        if http_status == 429 or code == 429:
            return ErrorAction.RETRY
        return ErrorAction.FAIL
