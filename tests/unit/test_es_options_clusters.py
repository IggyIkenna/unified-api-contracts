"""Unit tests for ES.OPT cluster taxonomy + per-day calendar fallback."""

from __future__ import annotations

from datetime import date

import pytest

from unified_api_contracts.registry import (
    ES_OPTIONS_CLUSTERS,
    ES_OPTIONS_DEFAULT_MIN_ROWS_PER_CLUSTER,
    derive_expiry_bucket,
    extract_es_options_cluster,
    get_active_es_options_clusters_for_date,
)


def test_es_options_clusters_taxonomy_size() -> None:
    assert len(ES_OPTIONS_CLUSTERS) == 11
    assert {"ES", "EW", "EW1", "EW2", "EW4", "E1A", "E2A", "E3A", "E4A", "E5A", "EOM"} == set(
        ES_OPTIONS_CLUSTERS.keys()
    )


def test_extract_cluster_quarterly() -> None:
    assert extract_es_options_cluster("ESM4 P5800") == "ES"


def test_extract_cluster_weekly_monday() -> None:
    assert extract_es_options_cluster("EW1J4 C5400") == "EW1"


def test_extract_cluster_daily_monday() -> None:
    assert extract_es_options_cluster("E1AN4 C5090") == "E1A"


def test_extract_cluster_eom() -> None:
    assert extract_es_options_cluster("EOMG5 C5100") == "EOM"


def test_extract_cluster_synthetic_combo_returns_head() -> None:
    # UD: combo spreads don't match the outright pattern; head-token returned unchanged.
    assert extract_es_options_cluster("UD:1V: VT 2888228") == "UD:1V:"


def test_active_clusters_weekday_returns_5_baseline() -> None:
    # Mon 2024-06-17
    active = get_active_es_options_clusters_for_date(date(2024, 6, 17))
    assert set(active.keys()) == {"ES", "EW", "EW1", "EW2", "EW4"}
    assert all(v == ES_OPTIONS_DEFAULT_MIN_ROWS_PER_CLUSTER for v in active.values())


def test_active_clusters_friday_same_baseline() -> None:
    # Fri 2024-06-21
    active = get_active_es_options_clusters_for_date(date(2024, 6, 21))
    assert set(active.keys()) == {"ES", "EW", "EW1", "EW2", "EW4"}


def test_active_clusters_saturday_empty() -> None:
    # Sat 2024-06-22
    assert get_active_es_options_clusters_for_date(date(2024, 6, 22)) == {}


def test_active_clusters_sunday_empty() -> None:
    # Sun 2024-06-23
    assert get_active_es_options_clusters_for_date(date(2024, 6, 23)) == {}


def test_active_clusters_custom_min_rows() -> None:
    active = get_active_es_options_clusters_for_date(date(2024, 6, 17), min_rows_per_cluster=42)
    assert all(v == 42 for v in active.values())
    assert len(active) == 5


# ---------------------------------------------------------------------------
# derive_expiry_bucket tests
# ---------------------------------------------------------------------------


def test_derive_expiry_bucket_spread() -> None:
    # 2-leg calendar spread — not date-dependent
    assert derive_expiry_bucket("ESM6-ESU6", date(2026, 5, 19)) == "spread"


def test_derive_expiry_bucket_butterfly() -> None:
    # 3-leg butterfly — not date-dependent
    assert derive_expiry_bucket("ESH6-ESM6-ESU6", date(2026, 5, 19)) == "butterfly"


def test_derive_expiry_bucket_butterfly_4_legs() -> None:
    # 4-leg condor also maps to butterfly (3+ leg rule)
    assert derive_expiry_bucket("ESH6-ESM6-ESU6-ESZ6", date(2026, 5, 19)) == "butterfly"


def test_derive_expiry_bucket_front() -> None:
    # ESM6 = June 2026; last day of June = 2026-06-30.
    # today = 2026-05-19; days_remaining = 42 < 90 → front
    assert derive_expiry_bucket("ESM6", date(2026, 5, 19)) == "front"


def test_derive_expiry_bucket_back() -> None:
    # ESZ6 = December 2026; last day = 2026-12-31.
    # today = 2026-05-19; days_remaining = 226 >= 90 → back
    assert derive_expiry_bucket("ESZ6", date(2026, 5, 19)) == "back"


@pytest.mark.parametrize(
    ("symbol", "today", "expected"),
    [
        ("CLF7", date(2026, 12, 15), "front"),  # Jan 2027; last day 2027-01-31, 47 days < 90
        ("CLZ7", date(2026, 12, 15), "back"),  # Dec 2027; last day 2027-12-31, 381 days >= 90
        ("NQH7", date(2026, 12, 15), "back"),  # Mar 2027; last day 2027-03-31, 106 days >= 90
        ("NQU7", date(2026, 12, 15), "back"),  # Sep 2027; last day 2027-09-30, 290 days >= 90
        ("ESZ6", date(2026, 12, 15), "front"),  # Dec 2026; last day 2026-12-31, 16 days < 90
    ],
)
def test_derive_expiry_bucket_parametrize(symbol: str, today: date, expected: str) -> None:
    assert derive_expiry_bucket(symbol, today) == expected
