"""Closed-set sanity tests for the UAC alerting taxonomy.

Phase 1 of `alerting_service_live_rules_2026_05_07`. Enforces:

1. Every `AlertRule.threshold_key` is in `ALERT_THRESHOLDS`.
2. Every `AlertRule.pattern` matches at least one `AlertCode` member.
3. The catch-all `*` rule is last (otherwise specific rules never match).
4. No duplicate (`pattern`, `severity`) tuples — drift between Phase 1 and
   the legacy `_default_routing_rules` factory.
5. KILL_SWITCH_* rules carry `triggers_kill_switch=True`.
6. `to_routing_dict()` produces the legacy shape consumed by
   `alerting-service/alerting_service/config.py`.
7. `AlertSeverity.to_legacy_filter()` round-trips correctly.
"""

from __future__ import annotations

import fnmatch
import re
from decimal import Decimal

import pytest
from pydantic import ValidationError

from unified_api_contracts.alerting import (
    ALERT_CODES,
    ALERT_THRESHOLDS,
    LIVE_ALERT_RULES,
    AlertChannel,
    AlertCode,
    AlertRule,
    AlertSeverity,
    AlertThreshold,
    ThresholdUnit,
    UnknownAlertCodeError,
    UnknownThresholdKeyError,
)

# ---------------------------------------------------------------------------
# Closed-set sanity
# ---------------------------------------------------------------------------


def test_alert_codes_frozenset_matches_enum() -> None:
    assert frozenset(member.value for member in AlertCode) == ALERT_CODES


def test_alert_codes_no_duplicates() -> None:
    values = [member.value for member in AlertCode]
    assert len(values) == len(set(values))


def test_alert_codes_all_uppercase_snake() -> None:
    for code in AlertCode:
        assert code.value.isupper(), f"{code.value} must be UPPER_SNAKE_CASE"
        assert " " not in code.value
        assert code.value.replace("_", "").isalnum()


# ---------------------------------------------------------------------------
# Severity ↔ legacy filter
# ---------------------------------------------------------------------------


def test_severity_to_legacy_filter_round_trip() -> None:
    assert AlertSeverity.CRITICAL.to_legacy_filter() == "critical"
    assert AlertSeverity.HIGH.to_legacy_filter() == "warning"
    assert AlertSeverity.WARN.to_legacy_filter() is None
    assert AlertSeverity.INFO.to_legacy_filter() is None


# ---------------------------------------------------------------------------
# Threshold registry
# ---------------------------------------------------------------------------


def test_thresholds_keys_match_dataclass_field() -> None:
    for key, threshold in ALERT_THRESHOLDS.items():
        assert threshold.key == key, (
            f"ALERT_THRESHOLDS dict key {key!r} != AlertThreshold.key {threshold.key!r} — registry drift"
        )


def test_threshold_for_archetype_falls_back_to_default() -> None:
    threshold = ALERT_THRESHOLDS["defi_aave_utilization_spike_bps"]
    assert threshold.default_value == Decimal("9500")
    # leveraged_funding_arb override is tighter (9000 = 90%)
    assert threshold.for_archetype("leveraged_funding_arb") == Decimal("9000")
    # Unknown archetype falls back
    assert threshold.for_archetype("unknown_archetype") == Decimal("9500")
    assert threshold.for_archetype(None) == Decimal("9500")


def test_threshold_unit_is_explicit_for_aave_utilization() -> None:
    """Audit 2026-05-07 §3 #5: bps-vs-% ambiguity must be resolved by an
    explicit ThresholdUnit on every numeric threshold."""
    threshold = ALERT_THRESHOLDS["defi_aave_utilization_spike_bps"]
    assert threshold.unit is ThresholdUnit.BPS_OF_ONE
    # bps_of_one means 1 bp = 0.01%, so 9500 bps = 95.00%
    assert threshold.default_value / Decimal("10000") == Decimal("0.95")


def test_threshold_health_factor_uses_ratio_unit() -> None:
    threshold = ALERT_THRESHOLDS["defi_health_factor_critical"]
    assert threshold.unit is ThresholdUnit.RATIO
    assert threshold.default_value == Decimal("1.05")


def test_thresholds_have_source_doc() -> None:
    for key, threshold in ALERT_THRESHOLDS.items():
        assert threshold.source_doc, (
            f"ALERT_THRESHOLDS[{key!r}].source_doc must be non-empty — "
            "every threshold needs a citation for reviewer trust"
        )


# ---------------------------------------------------------------------------
# AlertRule construction-time validation
# ---------------------------------------------------------------------------


def test_alert_rule_rejects_unknown_threshold_key() -> None:
    # Pydantic v2 wraps the ValueError-subclass UnknownThresholdKeyError in
    # its own ValidationError; the message-content check pins the typed
    # signal so the validator can't silently swallow the wrong key.
    with pytest.raises(ValidationError, match="ALERT_THRESHOLDS"):
        _ = AlertRule(
            code=AlertCode.SERVICE_DEGRADED,
            pattern="SERVICE_DEGRADED",
            severity=AlertSeverity.WARN,
            channels=(AlertChannel.TELEGRAM,),
            threshold_key="nonexistent_threshold_key",
        )


def test_alert_rule_rejects_pattern_matching_no_code() -> None:
    with pytest.raises(ValidationError, match="matches no AlertCode"):
        _ = AlertRule(
            code=AlertCode.SERVICE_DEGRADED,
            pattern="UNKNOWN_PATTERN_THAT_MATCHES_NO_CODE_*",
            severity=AlertSeverity.WARN,
            channels=(AlertChannel.TELEGRAM,),
        )


def test_alert_rule_rejects_kill_switch_flag_on_non_kill_switch_code() -> None:
    with pytest.raises(ValidationError, match="triggers_kill_switch"):
        _ = AlertRule(
            code=AlertCode.SERVICE_DEGRADED,
            pattern="SERVICE_DEGRADED",
            severity=AlertSeverity.WARN,
            channels=(AlertChannel.TELEGRAM,),
            triggers_kill_switch=True,
        )


def test_unknown_alert_code_error_is_value_error_subclass() -> None:
    """UnknownAlertCodeError + UnknownThresholdKeyError are public typed
    errors. Pydantic wraps them in ValidationError, but they can still be
    raised directly from non-pydantic call sites."""
    assert issubclass(UnknownAlertCodeError, ValueError)
    assert issubclass(UnknownThresholdKeyError, ValueError)


def test_alert_rule_accepts_kill_switch_flag_on_kill_switch_code() -> None:
    rule = AlertRule(
        code=AlertCode.KILL_SWITCH_VENUE_DISCONNECT,
        pattern="KILL_SWITCH_VENUE_DISCONNECT",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
        triggers_kill_switch=True,
    )
    assert rule.triggers_kill_switch is True


def test_alert_rule_rejects_empty_channels() -> None:
    with pytest.raises(ValidationError, match="channels"):
        _ = AlertRule(
            code=AlertCode.SERVICE_DEGRADED,
            pattern="SERVICE_DEGRADED",
            severity=AlertSeverity.WARN,
            channels=(),
        )


def test_alert_rule_rejects_empty_pattern() -> None:
    with pytest.raises(ValidationError):
        _ = AlertRule(
            code=AlertCode.SERVICE_DEGRADED,
            pattern="",
            severity=AlertSeverity.WARN,
            channels=(AlertChannel.TELEGRAM,),
        )


def test_alert_rule_to_routing_dict_legacy_shape() -> None:
    """Phase 2 migration target — alerting-service/config.py default-factory
    becomes [r.to_routing_dict() for r in LIVE_ALERT_RULES]; this test
    enforces byte-equivalence with the legacy shape."""
    rule = AlertRule(
        code=AlertCode.DEFI_HEALTH_FACTOR_CRITICAL,
        pattern="DEFI_HEALTH_FACTOR_CRITICAL",
        severity=AlertSeverity.CRITICAL,
        channels=(AlertChannel.PAGERDUTY, AlertChannel.TELEGRAM),
    )
    routing = rule.to_routing_dict()
    assert routing == {
        "event_pattern": "DEFI_HEALTH_FACTOR_CRITICAL",
        "channels": ["pagerduty", "telegram"],
        "severity_filter": "critical",
    }


def test_alert_rule_to_routing_dict_omits_log_only_channel() -> None:
    rule = AlertRule(
        code=AlertCode.SERVICE_DEGRADED,
        pattern="SERVICE_DEGRADED",
        severity=AlertSeverity.INFO,
        channels=(AlertChannel.LOG_ONLY, AlertChannel.TELEGRAM),
    )
    routing = rule.to_routing_dict()
    # LOG_ONLY is filtered out — it's a sentinel, not a dispatchable channel.
    assert routing["channels"] == ["telegram"]
    assert routing["severity_filter"] is None


# ---------------------------------------------------------------------------
# LIVE_ALERT_RULES integrity
# ---------------------------------------------------------------------------


def test_live_alert_rules_non_empty() -> None:
    assert len(LIVE_ALERT_RULES) > 0


def test_live_alert_rules_threshold_keys_in_registry() -> None:
    """Plan Phase 1 sanity test — every threshold_key referenced by a rule
    is in ALERT_THRESHOLDS."""
    for rule in LIVE_ALERT_RULES:
        if rule.threshold_key is not None:
            assert rule.threshold_key in ALERT_THRESHOLDS, (
                f"AlertRule(code={rule.code}, threshold_key={rule.threshold_key!r}) "
                "references missing ALERT_THRESHOLDS key"
            )


def test_live_alert_rules_patterns_match_at_least_one_code() -> None:
    """Plan Phase 1 sanity test — every pattern matches at least one
    AlertCode (the catch-all `*` is the only acceptable exception)."""
    for rule in LIVE_ALERT_RULES:
        if rule.pattern == "*":
            continue
        matched = [c for c in ALERT_CODES if fnmatch.fnmatchcase(c, rule.pattern)]
        assert matched, f"AlertRule.pattern={rule.pattern!r} matches no AlertCode — rule is dead and would never fire"


def test_live_alert_rules_catch_all_is_last() -> None:
    """Plan Phase 1 sanity test — catch-all `*` MUST be last so specific
    rules win during fnmatch dispatch."""
    catch_all_indexes = [i for i, r in enumerate(LIVE_ALERT_RULES) if r.pattern == "*"]
    assert catch_all_indexes, "LIVE_ALERT_RULES must contain a catch-all `*` rule"
    assert catch_all_indexes == [len(LIVE_ALERT_RULES) - 1], (
        "catch-all `*` rule must be the last entry; otherwise specific rules after it never match"
    )


def test_live_alert_rules_no_duplicate_pattern_severity_pairs() -> None:
    """Drift guard against the alerting-service legacy factory — two rules
    with the same (pattern, severity) tuple is almost always a copy-paste
    bug. Explicitly different rules (e.g. catch-all vs DEFI_FEATURE_STALE
    both at WARN/Telegram) are distinguished by pattern."""
    seen: set[tuple[str, AlertSeverity]] = set()
    for rule in LIVE_ALERT_RULES:
        key = (rule.pattern, rule.severity)
        assert key not in seen, f"LIVE_ALERT_RULES has duplicate (pattern, severity)={key!r}"
        seen.add(key)


def test_kill_switch_rules_trigger_kill_switch_flag() -> None:
    """Every KILL_SWITCH_* AlertCode rule MUST have triggers_kill_switch=True
    so the kill_switch_bus_subscriber publishes the event downstream."""
    for rule in LIVE_ALERT_RULES:
        if rule.code.value.startswith("KILL_SWITCH_"):
            assert rule.triggers_kill_switch is True, (
                f"AlertRule(code={rule.code}) is in the KILL_SWITCH_ family but "
                "triggers_kill_switch=False — execution-service won't halt on fire"
            )


def test_critical_rules_page_pagerduty() -> None:
    """Every CRITICAL-severity rule MUST include PagerDuty in its channels —
    otherwise on-call won't be paged."""
    for rule in LIVE_ALERT_RULES:
        if rule.severity is AlertSeverity.CRITICAL:
            assert AlertChannel.PAGERDUTY in rule.channels, (
                f"AlertRule(code={rule.code}, severity=CRITICAL) is missing "
                "PagerDuty channel — operators won't be paged"
            )


def test_cross_cloud_egress_detected_rule_present() -> None:
    """Audit 2026-05-07 added CROSS_CLOUD_EGRESS_DETECTED to the taxonomy as
    a data-locality safety net for the dual-cloud-active policy."""
    codes = [r.code for r in LIVE_ALERT_RULES]
    assert AlertCode.CROSS_CLOUD_EGRESS_DETECTED in codes


def test_legacy_routing_dict_shape_round_trip() -> None:
    """Phase 2 migration enforcer — every LIVE_ALERT_RULES entry round-trips
    through to_routing_dict() to the legacy default-factory shape."""
    for rule in LIVE_ALERT_RULES:
        routing = rule.to_routing_dict()
        assert set(routing.keys()) == {"event_pattern", "channels", "severity_filter"}
        assert isinstance(routing["event_pattern"], str)
        assert isinstance(routing["channels"], list)
        assert routing["severity_filter"] in {"critical", "warning", None}


# ---------------------------------------------------------------------------
# Plan-required AlertCodes are present
# ---------------------------------------------------------------------------

_PLAN_REQUIRED_CODES: tuple[AlertCode, ...] = (
    AlertCode.KILL_SWITCH_DEFI_LIQUIDATION_RISK,
    AlertCode.KILL_SWITCH_PORTFOLIO_DRAWDOWN,
    AlertCode.KILL_SWITCH_VENUE_DISCONNECT,
    AlertCode.CIRCUIT_BREAKER_OPEN,
    AlertCode.DEFI_HEALTH_FACTOR_CRITICAL,
    AlertCode.DEFI_WEETH_DEPEG,
    AlertCode.DEFI_AAVE_UTILIZATION_SPIKE,
    AlertCode.DEFI_FUNDING_RATE_FLIP,
    AlertCode.DEFI_FEATURE_STALE,
    AlertCode.PREFLIGHT_FAILED,
    AlertCode.SERVICE_DEGRADED,
    AlertCode.BALANCE_DRIFT,
    AlertCode.ORDER_REJECTION_SPIKE,
    AlertCode.MARGIN_THRESHOLD_BREACH,
    AlertCode.POSITION_DRIFT,
)

# ML lifecycle codes added 2026-05-08 (cefi_ml_may_23_2026.epic Tab 5 Item 6).
_ML_LIFECYCLE_CODES: tuple[AlertCode, ...] = (
    AlertCode.ML_SIGNAL_STALENESS,
    AlertCode.ML_MODEL_DRIFT_DETECTED,
    AlertCode.ML_PNL_DEVIATION,
    AlertCode.ML_INFERENCE_LATENCY_BREACH,
    AlertCode.ML_MODEL_VERSION_MISMATCH,
    AlertCode.KILL_SWITCH_ML_MODEL_FAILURE,
)


def test_plan_required_codes_present_in_enum() -> None:
    """Plan Phase 1 §"Add `AlertCode` StrEnum" enumerated 15 codes that MUST
    be in the closed set."""
    for code in _PLAN_REQUIRED_CODES:
        assert code in AlertCode


def test_plan_required_codes_have_a_routing_rule() -> None:
    """Every required code must have at least one matching rule in
    LIVE_ALERT_RULES (matched either exactly or via wildcard)."""
    for code in _PLAN_REQUIRED_CODES:
        matches = [r for r in LIVE_ALERT_RULES if fnmatch.fnmatchcase(code.value, r.pattern)]
        assert matches, f"AlertCode.{code.name} has no matching AlertRule in LIVE_ALERT_RULES"


# ---------------------------------------------------------------------------
# AlertThreshold is hashable + frozen
# ---------------------------------------------------------------------------


def test_alert_threshold_is_frozen() -> None:
    threshold = ALERT_THRESHOLDS["defi_health_factor_critical"]
    with pytest.raises((AttributeError, TypeError)):
        threshold.default_value = Decimal("99")  # type: ignore[misc]


def test_alert_threshold_construction_with_overrides() -> None:
    t = AlertThreshold(
        key="example",
        unit=ThresholdUnit.BPS_OF_ONE,
        default_value=Decimal("100"),
        source_doc="test",
        per_archetype_overrides={"archetype_a": Decimal("50")},
    )
    assert t.for_archetype("archetype_a") == Decimal("50")
    assert t.for_archetype("archetype_b") == Decimal("100")


# ---------------------------------------------------------------------------
# ML lifecycle codes (2026-05-08, cefi_ml_may_23_2026.epic Tab 5 Item 6)
# ---------------------------------------------------------------------------


def test_ml_lifecycle_codes_present_in_enum() -> None:
    """6 ML lifecycle codes added 2026-05-08 must be in the closed AlertCode set."""
    for code in _ML_LIFECYCLE_CODES:
        assert code in AlertCode


def test_ml_lifecycle_codes_have_routing_rule() -> None:
    """Every ML lifecycle code must have at least one matching AlertRule in
    LIVE_ALERT_RULES — either an explicit rule or a wildcard match (e.g.
    KILL_SWITCH_ML_MODEL_FAILURE matches the existing KILL_SWITCH_* rule)."""
    for code in _ML_LIFECYCLE_CODES:
        matches = [r for r in LIVE_ALERT_RULES if fnmatch.fnmatchcase(code.value, r.pattern)]
        assert matches, f"AlertCode.{code.name} has no matching AlertRule in LIVE_ALERT_RULES"


def test_ml_thresholds_present_in_registry() -> None:
    """Every ML threshold key referenced by an ML AlertRule must exist in
    ALERT_THRESHOLDS with explicit ThresholdUnit. Resolves the bps-vs-PSI-vs-ms
    ambiguity that would otherwise lurk across model-monitoring code."""
    expected_ml_keys = {
        "ml_signal_staleness_minutes": ThresholdUnit.MINUTES,
        "ml_model_drift_psi": ThresholdUnit.PSI,
        "ml_pnl_deviation_bps": ThresholdUnit.BPS_OF_ONE,
        "ml_inference_latency_p99_ms": ThresholdUnit.MILLISECONDS,
        "ml_model_version_mismatch_minutes": ThresholdUnit.MINUTES,
    }
    for key, expected_unit in expected_ml_keys.items():
        assert key in ALERT_THRESHOLDS, f"ALERT_THRESHOLDS missing {key!r} for ML lifecycle"
        assert ALERT_THRESHOLDS[key].unit is expected_unit, (
            f"ALERT_THRESHOLDS[{key!r}].unit={ALERT_THRESHOLDS[key].unit} != expected {expected_unit}"
        )


def test_ml_kill_switch_rule_carries_kill_switch_flag() -> None:
    """KILL_SWITCH_ML_MODEL_FAILURE rule must opt into triggers_kill_switch=True
    so the kill-switch publisher hook (alerting Phase 2 follow-up) emits the
    KillSwitchEvent on fire — required for archetype halt without operator
    intervention."""
    matched = [r for r in LIVE_ALERT_RULES if r.code is AlertCode.KILL_SWITCH_ML_MODEL_FAILURE]
    assert matched, "Expected at least one explicit AlertRule for KILL_SWITCH_ML_MODEL_FAILURE"
    for rule in matched:
        assert rule.triggers_kill_switch is True, (
            f"AlertRule(code=KILL_SWITCH_ML_MODEL_FAILURE) must have triggers_kill_switch=True;"
            f" got {rule.triggers_kill_switch}"
        )


def test_ml_critical_rules_include_pagerduty() -> None:
    """Every CRITICAL-severity ML rule must page on-call. ML_MODEL_VERSION_MISMATCH
    + KILL_SWITCH_ML_MODEL_FAILURE both qualify; ML_PNL_DEVIATION is HIGH not
    CRITICAL but should still page (PagerDuty P2)."""
    critical_ml_codes = {AlertCode.ML_MODEL_VERSION_MISMATCH, AlertCode.KILL_SWITCH_ML_MODEL_FAILURE}
    for rule in LIVE_ALERT_RULES:
        if rule.code in critical_ml_codes:
            assert rule.severity is AlertSeverity.CRITICAL, (
                f"AlertRule(code={rule.code}) expected CRITICAL severity; got {rule.severity}"
            )
            assert AlertChannel.PAGERDUTY in rule.channels, (
                f"AlertRule(code={rule.code}, severity=CRITICAL) is missing PagerDuty channel"
            )


def test_ml_psi_threshold_unit_is_explicit() -> None:
    """PSI is a distinct unit from RATIO — distributional drift, not a
    multiplicative factor. ml_model_drift_psi MUST carry ThresholdUnit.PSI so
    consumers don't accidentally compare a PSI value against a ratio threshold."""
    threshold = ALERT_THRESHOLDS["ml_model_drift_psi"]
    assert threshold.unit is ThresholdUnit.PSI
    # Industry rule-of-thumb: 0.10 < PSI < 0.25 = moderate drift; default 0.20.
    assert threshold.default_value == Decimal("0.20")


def test_ml_inference_latency_threshold_unit_is_milliseconds() -> None:
    """Inference SLO is naturally in milliseconds, NOT minutes. Wrong unit
    here would make a 500min p99 SLO (8 hours) the ratchet — silent disaster."""
    threshold = ALERT_THRESHOLDS["ml_inference_latency_p99_ms"]
    assert threshold.unit is ThresholdUnit.MILLISECONDS
    assert threshold.default_value == Decimal("500")


# ---------------------------------------------------------------------------
# Phase 6 of alerting_service_live_rules_2026_05_07 — `runbook_doc` field
# wiring tests. Each `AlertRule.runbook_doc` should resolve to a stable path
# under `unified-trading-pm/codex/14-playbooks/alerting/<filename>.md`.
#
# Cross-repo file existence at unit-test time isn't feasible (UAC test runs
# don't have the PM repo on path), so we verify path FORMAT only — the
# structure check catches the most common foot-gun (typo in slug, wrong
# directory, missing `.md` extension).
# ---------------------------------------------------------------------------


_RUNBOOK_PATH_PATTERN: re.Pattern[str] = re.compile(r"^unified-trading-pm/codex/14-playbooks/alerting/[a-z0-9_]+\.md$")


def test_every_alert_rule_runbook_doc_is_non_empty() -> None:
    """Every rule MUST point at SOME runbook — empty string is a code smell
    that means a future operator has nothing to read on the alert."""
    for rule in LIVE_ALERT_RULES:
        assert rule.runbook_doc, (
            f"AlertRule(code={rule.code}, pattern={rule.pattern!r}) has empty"
            " runbook_doc; populate per Phase 6 of"
            " alerting_service_live_rules_2026_05_07.md."
        )


def test_every_alert_rule_runbook_doc_path_format() -> None:
    """All runbook_doc paths conform to the canonical shape:
    `unified-trading-pm/codex/14-playbooks/alerting/<slug>.md` with a
    lowercase-slug filename. Catches typos / wrong-extension / wrong-dir."""
    for rule in LIVE_ALERT_RULES:
        assert _RUNBOOK_PATH_PATTERN.fullmatch(rule.runbook_doc), (
            f"AlertRule(code={rule.code}).runbook_doc={rule.runbook_doc!r} does"
            " not match canonical format"
            f" {_RUNBOOK_PATH_PATTERN.pattern!r}; expected"
            " unified-trading-pm/codex/14-playbooks/alerting/<slug>.md."
        )


def test_kill_switch_wildcard_rule_runbook_anchors_at_liquidation_risk() -> None:
    """The `KILL_SWITCH_*` wildcard rule pattern matches all 3 KILL_SWITCH
    codes. Its runbook_doc anchors at kill_switch_defi_liquidation_risk.md
    (the highest-impact variant); the runbook itself cross-references the
    sibling kill_switch_portfolio_drawdown.md +
    kill_switch_venue_disconnect.md so operators reach the right one."""
    matching_rules = [r for r in LIVE_ALERT_RULES if r.pattern == "KILL_SWITCH_*"]
    assert len(matching_rules) == 1, f"Expected exactly one KILL_SWITCH_* wildcard rule; found {len(matching_rules)}."
    rule = matching_rules[0]
    assert rule.runbook_doc.endswith("kill_switch_defi_liquidation_risk.md"), (
        f"KILL_SWITCH_* wildcard rule.runbook_doc={rule.runbook_doc!r}"
        " expected to anchor at kill_switch_defi_liquidation_risk.md."
    )


def test_phase6_required_runbook_slugs_present_in_live_alert_rules() -> None:
    """The Phase 6 plan-required 15 per-AlertCode runbooks each correspond to
    at least one rule whose runbook_doc points at the matching slug."""
    plan_required_slugs = {
        "kill_switch_defi_liquidation_risk",
        "kill_switch_portfolio_drawdown",
        "kill_switch_venue_disconnect",
        "circuit_breaker_open",
        "defi_health_factor_critical",
        "defi_weeth_depeg",
        "defi_aave_utilization_spike",
        "defi_funding_rate_flip",
        "defi_feature_stale",
        "preflight_failed",
        "service_degraded",
        "balance_drift",
        "order_rejection_spike",
        "margin_threshold_breach",
        "position_drift",
    }
    referenced_slugs: set[str] = set()
    for rule in LIVE_ALERT_RULES:
        # Strip the `unified-trading-pm/codex/14-playbooks/alerting/` prefix
        # and the `.md` suffix. Path validated by the format test above.
        slug = rule.runbook_doc.rsplit("/", 1)[-1].removesuffix(".md")
        referenced_slugs.add(slug)
    missing = plan_required_slugs - referenced_slugs
    # KILL_SWITCH_PORTFOLIO_DRAWDOWN + KILL_SWITCH_VENUE_DISCONNECT are
    # routed via the `KILL_SWITCH_*` wildcard rule whose runbook_doc anchors
    # at kill_switch_defi_liquidation_risk.md. The two sibling slugs are
    # cross-referenced from the anchor runbook + reachable via the README
    # index, so this test allows their absence from the runbook_doc set.
    expected_missing_due_to_wildcard = {
        "kill_switch_portfolio_drawdown",
        "kill_switch_venue_disconnect",
    }
    assert missing <= expected_missing_due_to_wildcard, (
        f"Phase 6 plan-required runbook slugs missing from LIVE_ALERT_RULES"
        f" runbook_doc set (excluding kill-switch siblings reached via the"
        f" wildcard anchor): {sorted(missing - expected_missing_due_to_wildcard)}"
    )
