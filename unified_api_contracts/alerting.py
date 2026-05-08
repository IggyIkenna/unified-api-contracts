"""Alerting facade — workspace-public surface for AlertCode taxonomy + thresholds + rules.

Consumers MUST import from this facade, not from the deep
``unified_api_contracts.canonical.crosscutting.alerting.*`` paths
(per UAC import-surface rules).

Example::

    from unified_api_contracts.alerting import AlertCode, AlertSeverity, LIVE_ALERT_RULES

    payload = {"event": AlertCode.DEFI_HEALTH_FACTOR_CRITICAL.value, ...}

The legacy :class:`unified_api_contracts.errors.DefiAlertType` enum continues
to exist for backwards compatibility on the DeFi-only emitter path; new code
should prefer ``AlertCode`` for cross-asset-group consistency.
"""

from __future__ import annotations

from .canonical.crosscutting.alerting import (
    ALERT_CODES,
    ALERT_THRESHOLDS,
    LIVE_ALERT_RULES,
    AlertChannel,
    AlertCode,
    AlertRule,
    AlertSeverity,
    AlertThreshold,
    KillSwitchScope,
    ThresholdUnit,
    UnknownAlertCodeError,
    UnknownThresholdKeyError,
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
