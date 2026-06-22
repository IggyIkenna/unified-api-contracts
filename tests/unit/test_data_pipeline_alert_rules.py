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
    assert len(DATA_PIPELINE_ALERT_RULES) >= 38


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
