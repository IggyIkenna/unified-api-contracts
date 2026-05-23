"""Circuit breaker helper functions — event constructors."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from ..alerting.codes import AlertCode
from ._models import BreakerConfig, BreakerFiredEvent


def breaker_fired_event(
    config: BreakerConfig,
    *,
    fired_at: datetime,
    alert_code: AlertCode,
    state: Literal["armed", "disarmed"],
    metadata: dict[str, str] | None = None,
) -> BreakerFiredEvent:
    """Convenience constructor that hydrates :class:`BreakerFiredEvent` from a
    :class:`BreakerConfig`.
    """
    recovery_mode = config.recovery_mode
    assert recovery_mode is not None  # model_validator always fills this field
    return BreakerFiredEvent(
        breaker_id=config.breaker_id,
        scope=config.scope,
        applies_to=config.applies_to,
        action=config.action,
        recovery_mode=recovery_mode,
        cooldown_seconds=config.cooldown_seconds,
        alerting_severity=config.alerting_severity,
        alert_code=alert_code,
        fired_at=fired_at,
        state=state,
        metadata=metadata or {},
    )


__all__ = [
    "breaker_fired_event",
]
