"""Unit tests for DATA_PIPELINE_ALERT_RULES (data-pipeline self-monitoring).

Transcription contract from
``codex/05-infrastructure/data-pipeline-alerts.registry.yaml`` — the tuple is
non-empty, well-formed, every event maps to a valid severity, routing matches
the registry severity-routing block (SLACK mirror always; CRITICAL pages).
Plan: ``data_pipeline_hardening_self_monitoring_2026_06_22.md`` Phase 0.
"""

from __future__ import annotations

from unified_api_contracts import (
    DATA_PIPELINE_ALERT_RULES,
    DATA_PIPELINE_SLACK_CHANNEL,
    AlertChannel,
    AlertSeverity,
    DataPipelineAlertCategory,
    DataPipelineAlertRule,
    DataPipelineEscalation,
)

_VALID_SEVERITIES = {AlertSeverity.CRITICAL, AlertSeverity.WARN, AlertSeverity.INFO}


def test_non_empty() -> None:
    assert len(DATA_PIPELINE_ALERT_RULES) >= 39


def test_every_rule_is_well_formed() -> None:
    for rule in DATA_PIPELINE_ALERT_RULES:
        assert isinstance(rule, DataPipelineAlertRule)
        assert rule.registry_id.startswith("DP-")
        assert rule.event
        assert isinstance(rule.category, DataPipelineAlertCategory)
        assert isinstance(rule.escalation, DataPipelineEscalation)


def test_every_event_maps_to_a_valid_severity() -> None:
    for rule in DATA_PIPELINE_ALERT_RULES:
        assert rule.severity in _VALID_SEVERITIES, rule.registry_id


def test_registry_ids_and_events_are_unique() -> None:
    ids = [r.registry_id for r in DATA_PIPELINE_ALERT_RULES]
    events = [r.event for r in DATA_PIPELINE_ALERT_RULES]
    assert len(ids) == len(set(ids)), "duplicate registry_id"
    assert len(events) == len(set(events)), "duplicate event"


def test_slack_channel_token() -> None:
    assert DATA_PIPELINE_SLACK_CHANNEL == "data_pipeline_slack"


def test_every_rule_mirrors_to_slack() -> None:
    for rule in DATA_PIPELINE_ALERT_RULES:
        assert AlertChannel.SLACK in rule.channels, rule.registry_id


def test_critical_rules_page_via_telegram_and_pagerduty() -> None:
    for rule in DATA_PIPELINE_ALERT_RULES:
        if rule.severity is AlertSeverity.CRITICAL:
            assert AlertChannel.TELEGRAM in rule.channels, rule.registry_id
            assert AlertChannel.PAGERDUTY in rule.channels, rule.registry_id
        else:
            # WARN/INFO are channel-only (Slack mirror), no paging.
            assert AlertChannel.PAGERDUTY not in rule.channels, rule.registry_id


def test_keystone_fetch_001_present_and_critical() -> None:
    by_id = {r.registry_id: r for r in DATA_PIPELINE_ALERT_RULES}
    keystone = by_id["DP-FETCH-001"]
    assert keystone.event == "DP_UNPROVEN_HONEST_ABSENCE"
    assert keystone.severity is AlertSeverity.CRITICAL
    assert keystone.escalation is DataPipelineEscalation.FILE_ISSUE


def test_all_registry_categories_represented() -> None:
    seen = {r.category for r in DATA_PIPELINE_ALERT_RULES}
    assert seen == set(DataPipelineAlertCategory)


def test_dp_fleet_monitor_lifecycle_events_registered() -> None:
    """dp-fleet-monitor's run_lifecycle() events must be exact-match registered.

    Regression test (2026-07-27): without these entries, DP_FLEET_MONITOR_RUN_STARTED
    / _COMPLETED / _FAILED miss alerting-service's data_pipeline_rule_for() exact-match
    lookup and fall through to the generic catch-all routing rule, paging the incident
    channel instead of the batch #data-pipeline-alerts mirror (or, for _FAILED, silently
    routing as if it were routine INFO with no incident page at all).
    """
    by_event = {r.event: r for r in DATA_PIPELINE_ALERT_RULES}

    started = by_event["DP_FLEET_MONITOR_RUN_STARTED"]
    completed = by_event["DP_FLEET_MONITOR_RUN_COMPLETED"]
    failed = by_event["DP_FLEET_MONITOR_RUN_FAILED"]

    assert started.severity is AlertSeverity.INFO
    assert completed.severity is AlertSeverity.INFO
    assert AlertChannel.PAGERDUTY not in started.channels
    assert AlertChannel.PAGERDUTY not in completed.channels

    assert failed.severity is AlertSeverity.CRITICAL
    assert AlertChannel.PAGERDUTY in failed.channels
    assert AlertChannel.TELEGRAM in failed.channels


def test_consolidator_scheduler_paused_has_own_registry_id() -> None:
    """DP_CONSOLIDATOR_SCHEDULER_PAUSED must not collide with DP_FLEET_MONITOR_RUN_FAILED.

    Regression test (dp_consolidator_scheduler_paused_prediction_recurrence_2026_07_31.md):
    the watcher previously emitted DP_CONSOLIDATOR_SCHEDULER_PAUSED reusing
    "DP-WATCHER-003", which the registry already assigns to the DISTINCT
    DP_FLEET_MONITOR_RUN_FAILED event — the DP-DIGEST-003/004 / DP-VM-008..011
    failure class. Without its own exact-match entry, the event would miss
    alerting-service's data_pipeline_rule_for() lookup and fall through to the
    generic catch-all routing.
    """
    by_event = {r.event: r for r in DATA_PIPELINE_ALERT_RULES}

    paused = by_event["DP_CONSOLIDATOR_SCHEDULER_PAUSED"]
    fleet_monitor_failed = by_event["DP_FLEET_MONITOR_RUN_FAILED"]

    assert paused.registry_id != fleet_monitor_failed.registry_id
    assert paused.registry_id == "DP-WATCHER-004"
    assert paused.category is DataPipelineAlertCategory.WATCHER
    assert paused.severity is AlertSeverity.CRITICAL
    assert paused.escalation is DataPipelineEscalation.PAGE_OPERATOR
