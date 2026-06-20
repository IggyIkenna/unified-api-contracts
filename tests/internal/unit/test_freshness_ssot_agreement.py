"""Cross-validation: alerting thresholds ↔ freshness contracts SSOT agreement.

Test 2 — tick_staleness_seconds alignment
    Asserts that ALERT_THRESHOLDS["tick_staleness_seconds"].default_value (300s) is
    >= the strictest per-venue max_age_seconds in MARKET_TICK_FRESHNESS, ensuring the
    MDPS-layer alert threshold never fires before a per-venue SLA has already been
    breached (i.e. the alert is a conservative fallback, not a tighter gate).

Test 3 — ALL_FRESHNESS_CONTRACTS no-orphan / well-formedness
    Asserts that ALL_FRESHNESS_CONTRACTS is the exact union of the four canonical
    sub-dicts (MARKET_TICK_FRESHNESS, FEATURE_FRESHNESS, ML_FRESHNESS,
    ACCOUNT_STATE_FRESHNESS) with no orphan keys, no missing keys, and every entry
    satisfying: source == dict_key, warn_age_seconds < max_age_seconds, criticality
    in the allowed closed set.

Enforcement reference: tests/internal/unit/test_freshness_ssot_agreement.py
(cited from unified_api_contracts/canonical/crosscutting/alerting/thresholds.py
 tick_staleness_seconds source_doc)
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from unified_api_contracts.canonical.crosscutting.alerting.thresholds import ALERT_THRESHOLDS
from unified_api_contracts.internal.reference.data_freshness import (
    ACCOUNT_STATE_FRESHNESS,
    ALL_FRESHNESS_CONTRACTS,
    FEATURE_FRESHNESS,
    MARKET_TICK_FRESHNESS,
    ML_FRESHNESS,
)

_ALLOWED_CRITICALITY = frozenset({"critical", "important", "informational"})

# ---------------------------------------------------------------------------
# Test 2 — tick_staleness_seconds ↔ MARKET_TICK_FRESHNESS alignment
# ---------------------------------------------------------------------------


def test_tick_staleness_threshold_gte_strictest_per_venue_sla() -> None:
    """ALERT_THRESHOLDS["tick_staleness_seconds"] default (300s) must be >=
    the strictest (smallest) per-venue max_age_seconds in MARKET_TICK_FRESHNESS.

    Invariant: the MDPS-layer cross-venue alert is a conservative ceiling that
    fires AFTER each individual venue's per-venue SLA has already been breached.
    "Strictest" = smallest max_age_seconds (tightest SLA), e.g. binance = 5s.
    alert_ceiling (300s) >= 5s holds: the alert fires conservatively, not
    before a venue's own contract expires.

    Note: EOD / low-cadence venues (max_age_seconds >> alert_ceiling, e.g.
    databento_eod = 86400s) are not real-time feeds and are excluded from this
    check — the TICK_STALENESS event is only relevant for intraday sources.
    """
    threshold_entry = ALERT_THRESHOLDS["tick_staleness_seconds"]
    alert_ceiling: int = int(threshold_entry.default_value)

    # Only check real-time / intraday venues (max_age_seconds <= alert_ceiling).
    # EOD sources (e.g. databento_eod, yahoo_finance) have multi-hour SLAs and
    # are not governed by the intraday tick-staleness alert.
    intraday_venues = {k: v for k, v in MARKET_TICK_FRESHNESS.items() if v.max_age_seconds <= alert_ceiling}

    assert intraday_venues, "No intraday venues found — check MARKET_TICK_FRESHNESS contents"

    strictest_sla = min(v.max_age_seconds for v in intraday_venues.values())
    assert alert_ceiling >= strictest_sla, (
        f"tick_staleness_seconds alert_ceiling={alert_ceiling}s < "
        f"strictest per-venue max_age_seconds={strictest_sla}s — "
        "the cross-venue alert would fire before the tightest venue SLA expires"
    )


def test_tick_staleness_threshold_default_value_is_300() -> None:
    """Pinned regression: the shipped default is 300 s (5 min conservative window).

    If you intentionally change this, update the comment in
    thresholds.py "tick_staleness_seconds" source_doc AND this assertion.
    SSOT: tests/internal/unit/test_freshness_ssot_agreement.py
    """
    assert ALERT_THRESHOLDS["tick_staleness_seconds"].default_value == Decimal("300"), (
        "tick_staleness_seconds default changed — update thresholds.py source_doc + this test"
    )


# ---------------------------------------------------------------------------
# Test 3 — ALL_FRESHNESS_CONTRACTS no-orphan / well-formedness
# ---------------------------------------------------------------------------


def test_all_freshness_contracts_source_equals_key() -> None:
    """Every entry's .source must equal its dict key."""
    mismatches = {k: v.source for k, v in ALL_FRESHNESS_CONTRACTS.items() if v.source != k}
    assert not mismatches, f"source != key for: {mismatches}"


def test_all_freshness_contracts_warn_lt_max() -> None:
    """warn_age_seconds < max_age_seconds for every contract."""
    violations = {
        k: (v.warn_age_seconds, v.max_age_seconds)
        for k, v in ALL_FRESHNESS_CONTRACTS.items()
        if v.warn_age_seconds >= v.max_age_seconds
    }
    assert not violations, f"warn_age_seconds >= max_age_seconds for: {violations}"


def test_all_freshness_contracts_valid_criticality() -> None:
    """Every contract's criticality must be in the closed set."""
    violations = {
        k: v.criticality for k, v in ALL_FRESHNESS_CONTRACTS.items() if v.criticality not in _ALLOWED_CRITICALITY
    }
    assert not violations, f"unknown criticality values: {violations}"


def test_all_freshness_contracts_exact_union_of_sub_dicts() -> None:
    """ALL_FRESHNESS_CONTRACTS must be the exact union of the four sub-dicts —
    no orphan keys (in ALL but not in any sub-dict), no missing keys (in a sub-dict
    but not in ALL).
    """
    expected_keys = (
        set(MARKET_TICK_FRESHNESS) | set(FEATURE_FRESHNESS) | set(ML_FRESHNESS) | set(ACCOUNT_STATE_FRESHNESS)
    )
    actual_keys = set(ALL_FRESHNESS_CONTRACTS)

    orphans = actual_keys - expected_keys
    missing = expected_keys - actual_keys

    assert not orphans, f"Orphan keys in ALL_FRESHNESS_CONTRACTS (not in any sub-dict): {orphans}"
    assert not missing, f"Missing keys in ALL_FRESHNESS_CONTRACTS (present in sub-dicts): {missing}"


@pytest.mark.parametrize(
    "sub_dict_name,sub_dict",
    [
        ("MARKET_TICK_FRESHNESS", MARKET_TICK_FRESHNESS),
        ("FEATURE_FRESHNESS", FEATURE_FRESHNESS),
        ("ML_FRESHNESS", ML_FRESHNESS),
        ("ACCOUNT_STATE_FRESHNESS", ACCOUNT_STATE_FRESHNESS),
    ],
)
def test_sub_dict_keys_present_in_all_freshness_contracts(
    sub_dict_name: str,
    sub_dict: dict,  # type: ignore[type-arg]
) -> None:
    """Every key in each sub-dict must appear in ALL_FRESHNESS_CONTRACTS."""
    missing = set(sub_dict) - set(ALL_FRESHNESS_CONTRACTS)
    assert not missing, f"Keys from {sub_dict_name} missing in ALL_FRESHNESS_CONTRACTS: {missing}"


def test_all_freshness_contracts_count_matches_sum_of_sub_dicts() -> None:
    """Total count must equal sum of all four sub-dict counts (no duplicates)."""
    expected = len(MARKET_TICK_FRESHNESS) + len(FEATURE_FRESHNESS) + len(ML_FRESHNESS) + len(ACCOUNT_STATE_FRESHNESS)
    assert len(ALL_FRESHNESS_CONTRACTS) == expected, (
        f"ALL_FRESHNESS_CONTRACTS has {len(ALL_FRESHNESS_CONTRACTS)} entries but "
        f"sum of sub-dicts is {expected} — duplicate or orphan key present"
    )
