"""Unit tests for ES.OPT cluster taxonomy + per-day calendar fallback."""

from __future__ import annotations

from datetime import date

from unified_api_contracts.registry import (
    ES_OPTIONS_CLUSTERS,
    ES_OPTIONS_DEFAULT_MIN_ROWS_PER_CLUSTER,
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
