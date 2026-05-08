"""Alerting taxonomy SSOT — closed-set codes, severity, channels, thresholds, live rules.

Phase 1 of `alerting_service_live_rules_2026_05_07`. All emitters MUST use
`AlertCode` enum members, never raw strings. The alerting-service consumes
`LIVE_ALERT_RULES` instead of an inline default-factory (single SSOT).

Severity is orthogonal to AlertCode — CRITICAL / HIGH / WARN / INFO.
KillSwitchBus integration is a separate axis: rules with
`triggers_kill_switch=True` propagate to execution-service halt subscribers
on top of routing to the paging channels.

Cross-references:
- `unified-trading-pm/codex/15-runbooks/alerting/alert-code-taxonomy.md`
- `unified-trading-pm/plans/active/alerting_service_live_rules_2026_05_07.md`
"""

from __future__ import annotations

from .codes import (
    ALERT_CODES,
    AlertChannel,
    AlertCode,
    AlertSeverity,
    KillSwitchScope,
)
from .rules import (
    LIVE_ALERT_RULES,
    AlertRule,
    UnknownAlertCodeError,
    UnknownThresholdKeyError,
)
from .thresholds import (
    ALERT_THRESHOLDS,
    AlertThreshold,
    ThresholdUnit,
)

__all__ = [
    "ALERT_CODES",
    "ALERT_THRESHOLDS",
    "LIVE_ALERT_RULES",
    "AlertChannel",
    "AlertCode",
    "AlertRule",
    "AlertSeverity",
    "AlertThreshold",
    "KillSwitchScope",
    "ThresholdUnit",
    "UnknownAlertCodeError",
    "UnknownThresholdKeyError",
]
