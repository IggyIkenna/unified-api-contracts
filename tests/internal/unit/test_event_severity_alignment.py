"""Tests for EventSeverity <-> LogLevel alignment and coordination event constants."""

from __future__ import annotations

from unified_api_contracts.internal.events import EventSeverity, LifecycleEventType
from unified_api_contracts.internal.modes import LogLevel


class TestEventSeverityIsLogLevel:
    """EventSeverity must be an alias of LogLevel — same class, same members."""

    def test_event_severity_is_log_level(self) -> None:
        """EventSeverity is literally LogLevel (type alias, not a copy)."""
        assert EventSeverity is LogLevel

    def test_backward_compat_info(self) -> None:
        """Existing EventSeverity.INFO usage still works."""
        assert EventSeverity.INFO == "INFO"

    def test_backward_compat_warning(self) -> None:
        assert EventSeverity.WARNING == "WARNING"

    def test_backward_compat_error(self) -> None:
        assert EventSeverity.ERROR == "ERROR"

    def test_backward_compat_critical(self) -> None:
        assert EventSeverity.CRITICAL == "CRITICAL"

    def test_debug_now_available(self) -> None:
        """LogLevel includes DEBUG; EventSeverity now exposes it too."""
        assert EventSeverity.DEBUG == "DEBUG"

    def test_member_count(self) -> None:
        """5 members: DEBUG, INFO, WARNING, ERROR, CRITICAL."""
        assert len(list(EventSeverity)) == 5

    def test_domain_lifecycle_re_export_is_same(self) -> None:
        """The domain/events_service/lifecycle copy is the same alias."""
        from unified_api_contracts.internal.domain.events_service.lifecycle import (
            EventSeverity as LifecycleEventSeverity,
        )

        assert LifecycleEventSeverity is LogLevel

    def test_package_root_re_export_is_same(self) -> None:
        """The top-level package re-export is the same alias."""
        from unified_api_contracts.internal import EventSeverity as RootEventSeverity

        assert RootEventSeverity is LogLevel


class TestCoordinationEventConstants:
    """Cross-service pipeline readiness signals in LifecycleEventType."""

    def test_data_ready_exists(self) -> None:
        assert LifecycleEventType.DATA_READY == "DATA_READY"

    def test_predictions_ready_exists(self) -> None:
        assert LifecycleEventType.PREDICTIONS_READY == "PREDICTIONS_READY"

    def test_strategy_signals_ready_exists(self) -> None:
        assert LifecycleEventType.STRATEGY_SIGNALS_READY == "STRATEGY_SIGNALS_READY"

    def test_coordination_events_are_valid_lifecycle_events(self) -> None:
        """All three coordination constants are proper LifecycleEventType members."""
        coordination = {
            LifecycleEventType.DATA_READY,
            LifecycleEventType.PREDICTIONS_READY,
            LifecycleEventType.STRATEGY_SIGNALS_READY,
        }
        all_members = set(LifecycleEventType)
        assert coordination.issubset(all_members)

    def test_coordination_events_accessible_from_domain_lifecycle(self) -> None:
        """Coordination events are accessible via the domain sub-package."""
        from unified_api_contracts.internal.domain.events_service.lifecycle import (
            LifecycleEventType as DomainLifecycleEventType,
        )

        assert DomainLifecycleEventType.DATA_READY == "DATA_READY"
        assert DomainLifecycleEventType.PREDICTIONS_READY == "PREDICTIONS_READY"
        assert DomainLifecycleEventType.STRATEGY_SIGNALS_READY == "STRATEGY_SIGNALS_READY"
