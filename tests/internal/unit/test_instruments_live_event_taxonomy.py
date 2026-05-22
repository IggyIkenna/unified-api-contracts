"""Tests for instruments-live trigger event taxonomy.

Phase A.5 of ``instruments_master.md`` — adds 7 typed
``LifecycleEventType`` members + 7 Pydantic detail models + 1 sub-model
(``MissingDependency``) for the instruments-live trigger lifecycle.

Per Phase A.4 alerting taxonomy, these event types feed the
``alerting-service`` rule engine (``alerting_service_live_rules_2026_05_07``)
which formats Telegram / PagerDuty messages with operator-actionable detail
— specifically ``missing_dependencies`` payloads name the exact upstream
that's blocking, so the operator can act in seconds rather than diagnosing
from logs.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from unified_api_contracts.internal.events import (
    InstrumentsLivePreflightFailedDetails,
    InstrumentsLivePreflightFailedEvent,
    InstrumentsLiveSchemaDriftDetails,
    InstrumentsLiveSchemaDriftEvent,
    InstrumentsLiveSourceDegradedDetails,
    InstrumentsLiveSourceDegradedEvent,
    InstrumentsLiveT1AuditDiscrepancyDetails,
    InstrumentsLiveT1AuditDiscrepancyEvent,
    InstrumentsLiveTriggerFailedDetails,
    InstrumentsLiveTriggerFailedEvent,
    InstrumentsLiveTriggerFiredDetails,
    InstrumentsLiveTriggerFiredEvent,
    InstrumentsLiveUpstreamStaleDetails,
    InstrumentsLiveUpstreamStaleEvent,
    LifecycleEventType,
    MissingDependency,
)

# ═══════════════════════════════════════════════════════════════════════════
# Enum-member existence + closed-set membership
# ═══════════════════════════════════════════════════════════════════════════


class TestInstrumentsLiveEventEnumMembers:
    """All 7 instruments-live trigger event types exist as valid enum members."""

    def test_trigger_fired_exists(self) -> None:
        assert LifecycleEventType.INSTRUMENTS_LIVE_TRIGGER_FIRED == "INSTRUMENTS_LIVE_TRIGGER_FIRED"

    def test_trigger_failed_exists(self) -> None:
        assert LifecycleEventType.INSTRUMENTS_LIVE_TRIGGER_FAILED == "INSTRUMENTS_LIVE_TRIGGER_FAILED"

    def test_source_degraded_exists(self) -> None:
        assert LifecycleEventType.INSTRUMENTS_LIVE_SOURCE_DEGRADED == "INSTRUMENTS_LIVE_SOURCE_DEGRADED"

    def test_schema_drift_exists(self) -> None:
        assert LifecycleEventType.INSTRUMENTS_LIVE_SCHEMA_DRIFT == "INSTRUMENTS_LIVE_SCHEMA_DRIFT"

    def test_t1_audit_discrepancy_exists(self) -> None:
        assert LifecycleEventType.INSTRUMENTS_LIVE_T1_AUDIT_DISCREPANCY == "INSTRUMENTS_LIVE_T1_AUDIT_DISCREPANCY"

    def test_preflight_failed_exists(self) -> None:
        assert LifecycleEventType.INSTRUMENTS_LIVE_PREFLIGHT_FAILED == "INSTRUMENTS_LIVE_PREFLIGHT_FAILED"

    def test_upstream_stale_exists(self) -> None:
        assert LifecycleEventType.INSTRUMENTS_LIVE_UPSTREAM_STALE == "INSTRUMENTS_LIVE_UPSTREAM_STALE"

    def test_seven_members_added(self) -> None:
        """Phase A.5 declares exactly 7 new INSTRUMENTS_LIVE_* members."""
        instruments_live_members = {m for m in LifecycleEventType if m.value.startswith("INSTRUMENTS_LIVE_")}
        assert len(instruments_live_members) == 7


# ═══════════════════════════════════════════════════════════════════════════
# TRIGGER_FIRED detail + event
# ═══════════════════════════════════════════════════════════════════════════


class TestInstrumentsLiveTriggerFired:
    def test_minimal_construction(self) -> None:
        scheduled = datetime(2026, 5, 8, 12, 0, 0, tzinfo=UTC)
        actual = datetime(2026, 5, 8, 12, 0, 1, tzinfo=UTC)
        details = InstrumentsLiveTriggerFiredDetails(
            asset_group="cefi",
            trigger_name="cefi.ohlcv_15m.wallclock",
            scheduled_fire_at=scheduled,
            actual_fire_at=actual,
        )
        assert details.asset_group == "cefi"
        assert details.correlation_id is None

    def test_event_wrapper_pins_event_type(self) -> None:
        details = InstrumentsLiveTriggerFiredDetails(
            asset_group="sports",
            trigger_name="sports.fixtures.daily_repoll",
            scheduled_fire_at=datetime(2026, 5, 8, 0, 0, 0, tzinfo=UTC),
            actual_fire_at=datetime(2026, 5, 8, 0, 0, 1, tzinfo=UTC),
        )
        evt = InstrumentsLiveTriggerFiredEvent(
            service="instruments-service",
            timestamp=datetime(2026, 5, 8, 0, 0, 1, tzinfo=UTC),
            details=details,
        )
        assert evt.event == LifecycleEventType.INSTRUMENTS_LIVE_TRIGGER_FIRED


# ═══════════════════════════════════════════════════════════════════════════
# TRIGGER_FAILED detail + event
# ═══════════════════════════════════════════════════════════════════════════


class TestInstrumentsLiveTriggerFailed:
    def test_minimal_construction(self) -> None:
        details = InstrumentsLiveTriggerFailedDetails(
            asset_group="tradfi",
            trigger_name="tradfi.ohlcv_15m.wallclock",
            error_type="SourceTimeoutError",
            error_message="Polygon /v2/aggs/ticker timed out after 30s",
        )
        assert details.attempt_number == 1
        assert details.consecutive_failures is None

    def test_event_wrapper(self) -> None:
        details = InstrumentsLiveTriggerFailedDetails(
            asset_group="defi",
            trigger_name="defi.lending_indices.fwd",
            error_type="HTTPError",
            error_message="503",
            attempt_number=2,
            consecutive_failures=3,
        )
        evt = InstrumentsLiveTriggerFailedEvent(
            service="instruments-service",
            timestamp=datetime(2026, 5, 8, 12, 0, 0, tzinfo=UTC),
            details=details,
        )
        assert evt.event == LifecycleEventType.INSTRUMENTS_LIVE_TRIGGER_FAILED
        assert evt.details.attempt_number == 2


# ═══════════════════════════════════════════════════════════════════════════
# SOURCE_DEGRADED detail + event
# ═══════════════════════════════════════════════════════════════════════════


class TestInstrumentsLiveSourceDegraded:
    def test_minimal_construction(self) -> None:
        details = InstrumentsLiveSourceDegradedDetails(
            asset_group="tradfi",
            trigger_name="tradfi.ohlcv_15m.wallclock",
            primary_source="databento",
            degradation_reason="HTTP_5XX",
        )
        assert details.secondary_source is None
        assert details.switched_at is None

    def test_with_fallback_source(self) -> None:
        details = InstrumentsLiveSourceDegradedDetails(
            asset_group="cefi",
            trigger_name="cefi.ohlcv_15m.wallclock",
            primary_source="ccxt",
            secondary_source="venue_native_rest",
            degradation_reason="RATE_LIMIT",
            switched_at=datetime(2026, 5, 8, 12, 5, 0, tzinfo=UTC),
        )
        assert details.secondary_source == "venue_native_rest"


# ═══════════════════════════════════════════════════════════════════════════
# SCHEMA_DRIFT detail + event
# ═══════════════════════════════════════════════════════════════════════════


class TestInstrumentsLiveSchemaDrift:
    def test_minimal_construction(self) -> None:
        details = InstrumentsLiveSchemaDriftDetails(
            asset_group="tradfi",
            trigger_name="tradfi.ohlcv_15m.wallclock",
            source="databento",
            entity_type="ohlcv_15m",
            expected_columns=["ts_event", "open", "high", "low", "close", "volume"],
            observed_columns=["ts_event", "open", "high", "low", "close"],
            missing_columns=["volume"],
        )
        assert details.missing_columns == ["volume"]
        assert details.extra_columns == []

    def test_extra_columns_default_factory(self) -> None:
        details = InstrumentsLiveSchemaDriftDetails(
            asset_group="cefi",
            trigger_name="cefi.ohlcv_15m.wallclock",
            source="ccxt",
            entity_type="ohlcv_15m",
            expected_columns=["a"],
            observed_columns=["a"],
        )
        assert details.missing_columns == []
        assert details.extra_columns == []


# ═══════════════════════════════════════════════════════════════════════════
# T1_AUDIT_DISCREPANCY detail + event
# ═══════════════════════════════════════════════════════════════════════════


class TestInstrumentsLiveT1AuditDiscrepancy:
    def test_minimal_construction(self) -> None:
        details = InstrumentsLiveT1AuditDiscrepancyDetails(
            asset_group="cefi",
            entity_type="instrument-catalog",
            audit_date="2026-05-07",
            live_row_count=12000,
            batch_row_count=12500,
            tolerance_pct=0.01,
            observed_divergence_pct=0.04,
        )
        assert details.mismatch_keys == []
        assert details.observed_divergence_pct > details.tolerance_pct

    def test_with_mismatch_keys(self) -> None:
        details = InstrumentsLiveT1AuditDiscrepancyDetails(
            asset_group="prediction",
            entity_type="market_lifecycle",
            audit_date="2026-05-07",
            live_row_count=24,
            batch_row_count=25,
            mismatch_keys=["(POLYMARKET, BTC_UP_DOWN_HOURLY, 2026-05-07T13:00:00Z)"],
            tolerance_pct=0.0,
            observed_divergence_pct=0.04,
        )
        assert len(details.mismatch_keys) == 1


# ═══════════════════════════════════════════════════════════════════════════
# MissingDependency sub-model
# ═══════════════════════════════════════════════════════════════════════════


class TestMissingDependency:
    def test_minimal_construction(self) -> None:
        dep = MissingDependency(entity_type="fixtures", expected_max_age_seconds=86400)
        assert dep.actual_age_seconds is None
        assert dep.last_seen_at is None

    def test_full_construction(self) -> None:
        dep = MissingDependency(
            entity_type="fixtures",
            expected_max_age_seconds=86400,
            actual_age_seconds=129600,  # 36h
            last_seen_at=datetime(2026, 5, 6, 0, 0, 0, tzinfo=UTC),
        )
        assert dep.actual_age_seconds == 129600
        assert dep.actual_age_seconds > dep.expected_max_age_seconds


# ═══════════════════════════════════════════════════════════════════════════
# PREFLIGHT_FAILED detail + event
# ═══════════════════════════════════════════════════════════════════════════


class TestInstrumentsLivePreflightFailed:
    def test_minimal_construction_with_one_dep(self) -> None:
        dep = MissingDependency(
            entity_type="fixtures",
            expected_max_age_seconds=86400,
            actual_age_seconds=129600,
            last_seen_at=datetime(2026, 5, 6, 0, 0, 0, tzinfo=UTC),
        )
        details = InstrumentsLivePreflightFailedDetails(
            asset_group="sports",
            trigger_name="sports.weather_cascade.-3h",
            missing_dependencies=[dep],
        )
        assert len(details.missing_dependencies) == 1
        assert details.missing_dependencies[0].entity_type == "fixtures"

    def test_missing_dependencies_required_no_default(self) -> None:
        """Per the contract, the event fires BECAUSE deps are missing — empty list is contract violation."""
        with pytest.raises(ValidationError):
            InstrumentsLivePreflightFailedDetails(
                asset_group="sports",
                trigger_name="sports.weather_cascade.-3h",
            )  # type: ignore[call-arg]

    def test_event_wrapper(self) -> None:
        dep = MissingDependency(entity_type="instrument-catalog", expected_max_age_seconds=86400)
        details = InstrumentsLivePreflightFailedDetails(
            asset_group="cefi",
            trigger_name="cefi.ohlcv_15m.wallclock",
            missing_dependencies=[dep],
        )
        evt = InstrumentsLivePreflightFailedEvent(
            service="instruments-service",
            timestamp=datetime(2026, 5, 8, 12, 0, 0, tzinfo=UTC),
            details=details,
        )
        assert evt.event == LifecycleEventType.INSTRUMENTS_LIVE_PREFLIGHT_FAILED


# ═══════════════════════════════════════════════════════════════════════════
# UPSTREAM_STALE detail + event
# ═══════════════════════════════════════════════════════════════════════════


class TestInstrumentsLiveUpstreamStale:
    def test_minimal_construction(self) -> None:
        details = InstrumentsLiveUpstreamStaleDetails(
            asset_group="defi",
            upstream_entity_type="instrument-catalog",
            staleness_threshold_seconds=86400,
            actual_age_seconds=172800,  # 48h
        )
        assert details.last_captured_at is None
        assert details.downstream_triggers_blocked == []

    def test_with_downstream_blockers(self) -> None:
        details = InstrumentsLiveUpstreamStaleDetails(
            asset_group="cefi",
            upstream_entity_type="instrument-catalog",
            last_captured_at=datetime(2026, 5, 6, 0, 0, 0, tzinfo=UTC),
            staleness_threshold_seconds=86400,
            actual_age_seconds=172800,
            downstream_triggers_blocked=[
                "cefi.ohlcv_15m.wallclock",
                "cefi.perp_funding.wallclock",
            ],
        )
        assert len(details.downstream_triggers_blocked) == 2


# ═══════════════════════════════════════════════════════════════════════════
# Integration — closed-set membership across all 7
# ═══════════════════════════════════════════════════════════════════════════


class TestInstrumentsLiveEventTaxonomyIntegration:
    """All 7 instruments-live events have their detail-model + event-wrapper pair."""

    def test_all_seven_event_wrappers_pin_correct_event_type(self) -> None:
        """Each typed event class uses ``Literal[LifecycleEventType.X] = X`` so default is the right type."""
        # Construct the bare minimum for each — the Literal default ensures
        # ``event`` is the correct enum value without explicit pass-in.
        scheduled = datetime(2026, 5, 8, 12, 0, 0, tzinfo=UTC)
        ts = datetime(2026, 5, 8, 12, 0, 1, tzinfo=UTC)
        wrappers: list[tuple[type, dict[str, object], LifecycleEventType]] = [
            (
                InstrumentsLiveTriggerFiredEvent,
                {
                    "details": InstrumentsLiveTriggerFiredDetails(
                        asset_group="cefi",
                        trigger_name="cefi.ohlcv_15m.wallclock",
                        scheduled_fire_at=scheduled,
                        actual_fire_at=ts,
                    )
                },
                LifecycleEventType.INSTRUMENTS_LIVE_TRIGGER_FIRED,
            ),
            (
                InstrumentsLiveTriggerFailedEvent,
                {
                    "details": InstrumentsLiveTriggerFailedDetails(
                        asset_group="cefi",
                        trigger_name="cefi.ohlcv_15m.wallclock",
                        error_type="X",
                        error_message="y",
                    )
                },
                LifecycleEventType.INSTRUMENTS_LIVE_TRIGGER_FAILED,
            ),
            (
                InstrumentsLiveSourceDegradedEvent,
                {
                    "details": InstrumentsLiveSourceDegradedDetails(
                        asset_group="tradfi",
                        trigger_name="tradfi.ohlcv_15m.wallclock",
                        primary_source="databento",
                        degradation_reason="HTTP_5XX",
                    )
                },
                LifecycleEventType.INSTRUMENTS_LIVE_SOURCE_DEGRADED,
            ),
            (
                InstrumentsLiveSchemaDriftEvent,
                {
                    "details": InstrumentsLiveSchemaDriftDetails(
                        asset_group="cefi",
                        trigger_name="cefi.ohlcv_15m.wallclock",
                        source="ccxt",
                        entity_type="ohlcv_15m",
                        expected_columns=["a"],
                        observed_columns=["a"],
                    )
                },
                LifecycleEventType.INSTRUMENTS_LIVE_SCHEMA_DRIFT,
            ),
            (
                InstrumentsLiveT1AuditDiscrepancyEvent,
                {
                    "details": InstrumentsLiveT1AuditDiscrepancyDetails(
                        asset_group="cefi",
                        entity_type="instrument-catalog",
                        audit_date="2026-05-07",
                        live_row_count=10,
                        batch_row_count=11,
                        tolerance_pct=0.01,
                        observed_divergence_pct=0.1,
                    )
                },
                LifecycleEventType.INSTRUMENTS_LIVE_T1_AUDIT_DISCREPANCY,
            ),
            (
                InstrumentsLivePreflightFailedEvent,
                {
                    "details": InstrumentsLivePreflightFailedDetails(
                        asset_group="cefi",
                        trigger_name="cefi.ohlcv_15m.wallclock",
                        missing_dependencies=[
                            MissingDependency(entity_type="instrument-catalog", expected_max_age_seconds=86400)
                        ],
                    )
                },
                LifecycleEventType.INSTRUMENTS_LIVE_PREFLIGHT_FAILED,
            ),
            (
                InstrumentsLiveUpstreamStaleEvent,
                {
                    "details": InstrumentsLiveUpstreamStaleDetails(
                        asset_group="defi",
                        upstream_entity_type="instrument-catalog",
                        staleness_threshold_seconds=86400,
                        actual_age_seconds=172800,
                    )
                },
                LifecycleEventType.INSTRUMENTS_LIVE_UPSTREAM_STALE,
            ),
        ]
        for cls, kwargs, expected_event in wrappers:
            evt = cls(service="instruments-service", timestamp=ts, **kwargs)  # type: ignore[arg-type]
            assert evt.event == expected_event
