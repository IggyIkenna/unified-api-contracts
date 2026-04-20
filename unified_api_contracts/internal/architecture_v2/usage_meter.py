"""Usage-metering row schema — Tier A variable-pricing source of truth.

Stage 3E G2 § 3. One row per metered unit of work (API call, data
pull, signal emission, strategy-run minute, etc.). Rows land in
``gs://odum-<env>-usage-metering/day=YYYY-MM-DD/*.jsonl`` and are
aggregated nightly into BigQuery ``<env>_usage.daily_usage`` for
month-end invoicing.

SSOT: codex/14-playbooks/infra-spec/stage-3e-g2-env-split.md § 3.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from unified_api_contracts.internal.architecture_v2.derivation import (
    ClientAudience,
)

MeterKind = Literal[
    "api_call",
    "signal_emission",
    "data_pull",
    "strategy_run_minute",
    "execution_fill",
    "report_generation",
]


class UsageMeterRow(BaseModel):
    """A single usage-metering observation.

    One row per metered unit. Writers (execution-service,
    strategy-service, deployment-api, analytics-service, …) emit
    these to GCS at the point of work — no inline aggregation, no
    service-local batching beyond small write buffers.

    ``org_id`` is required for every billable row. Internal / admin
    traffic SHOULD be tagged with ``caller_audience='admin'`` and no
    ``org_id`` so BigQuery's invoicing query filters it out cleanly.

    ``dims`` is a small free-form string dict for per-meter_kind
    columns (e.g. venue, category, endpoint path, model family) so
    BigQuery can slice the invoice by dimension without schema
    migrations. Keep entries small — oversized dims land in GCS but
    get dropped at BigQuery load.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp_utc: str  # ISO-8601 instant
    org_id: str | None  # None for admin / internal traffic
    caller_audience: ClientAudience
    meter_kind: MeterKind
    unit_count: int  # always >= 1; writers batch N events into one row when safe
    source_service: str  # e.g. "execution-service", "strategy-service"
    env: Literal["dev", "staging", "prod"]
    dims: dict[str, str] = {}


__all__ = [
    "MeterKind",
    "UsageMeterRow",
]
