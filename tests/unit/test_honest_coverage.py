"""Unit tests for the honest_coverage cluster registries.

Covers the new bits introduced in the writegate-honest-coverage Phase 1B
work — :data:`BUNDLED_DATA_TYPES`, the futures expiry-bucket derivation,
and the re-export surface that delegates to :mod:`unified_api_contracts.registry`.
"""

from __future__ import annotations

from datetime import date

import pytest

from unified_api_contracts.canonical.crosscutting.honest_coverage import (
    BUNDLED_DATA_TYPES,
    DATA_TYPE_TO_CLUSTER_REGISTRY,
    EMPTY_CONFIRMED_REASONS,
    ES_OPTIONS_CLUSTERS,
    EVENT_CONTRACT_ROOT_CLUSTERS,
    FUTURES_CHAIN_BUCKETS,
    EmptyConfirmedReason,
    extract_es_options_cluster,
    futures_expiry_bucket,
    parse_futures_expiry,
)

# ---------------------------------------------------------------------------
# BUNDLED_DATA_TYPES
# ---------------------------------------------------------------------------


def test_bundled_data_types_is_frozenset() -> None:
    assert isinstance(BUNDLED_DATA_TYPES, frozenset)


def test_bundled_data_types_contains_options_chain() -> None:
    assert "options_chain" in BUNDLED_DATA_TYPES


def test_bundled_data_types_contains_futures_chain() -> None:
    assert "futures_chain" in BUNDLED_DATA_TYPES


def test_bundled_data_types_contains_prediction_canonical_question_group() -> None:
    assert "prediction_canonical_question_group" in BUNDLED_DATA_TYPES


def test_bundled_data_types_contains_sports_fixture_bundle() -> None:
    assert "sports_fixture_bundle" in BUNDLED_DATA_TYPES


def test_bundled_data_types_contains_event_contract() -> None:
    assert "event_contract" in BUNDLED_DATA_TYPES


def test_bundled_data_types_excludes_unbundled() -> None:
    # Smoke: per-instrument data_types are NOT in the bundled set.
    assert "ohlcv_1m" not in BUNDLED_DATA_TYPES
    assert "trades" not in BUNDLED_DATA_TYPES
    assert "perpetual" not in BUNDLED_DATA_TYPES


# ---------------------------------------------------------------------------
# EVENT_CONTRACT_ROOT_CLUSTERS
# ---------------------------------------------------------------------------


_EXPECTED_EC_ROOTS = {"ECES", "ECNQ", "ECRTY", "ECYM", "ECGC", "ECCL", "ECNG", "EC6E", "ECBTC"}


def test_event_contract_root_clusters_has_all_9_roots() -> None:
    assert set(EVENT_CONTRACT_ROOT_CLUSTERS.keys()) == _EXPECTED_EC_ROOTS


def test_event_contract_root_clusters_min_rows_is_one() -> None:
    for root, config in EVENT_CONTRACT_ROOT_CLUSTERS.items():
        assert config.get("_per_cluster_min_rows") == 1, f"{root} missing _per_cluster_min_rows=1"


def test_data_type_to_cluster_registry_has_event_contract() -> None:
    assert DATA_TYPE_TO_CLUSTER_REGISTRY["event_contract"] == "EVENT_CONTRACT_ROOT_CLUSTERS"


# ---------------------------------------------------------------------------
# ES_OPTIONS re-export delegation (regression — ensures we don't drift from
# the registry SSOT).
# ---------------------------------------------------------------------------


def test_es_options_clusters_reexport_matches_registry() -> None:
    from unified_api_contracts.registry import (
        ES_OPTIONS_CLUSTERS as REGISTRY_ES_OPTIONS_CLUSTERS,
    )

    assert ES_OPTIONS_CLUSTERS is REGISTRY_ES_OPTIONS_CLUSTERS


def test_extract_es_options_cluster_reexport_works() -> None:
    assert extract_es_options_cluster("ESM6 P5800") == "ES"
    assert extract_es_options_cluster("E1AN4 C5090") == "E1A"


# ---------------------------------------------------------------------------
# parse_futures_expiry
# ---------------------------------------------------------------------------


def test_parse_futures_expiry_es_jun_2026() -> None:
    # ESM6 = ES June 2026. June 2026: Mondays are 1, 8, 15, 22, 29 →
    # third Friday is 19 June 2026.
    assert parse_futures_expiry("ESM6") == date(2026, 6, 19)


def test_parse_futures_expiry_nq_sep_2024() -> None:
    # NQU24 = NQ September 2024. Third Friday = 20 Sep 2024.
    assert parse_futures_expiry("NQU24") == date(2024, 9, 20)


def test_parse_futures_expiry_returns_none_for_continuous_root() -> None:
    assert parse_futures_expiry("ES") is None


def test_parse_futures_expiry_returns_none_for_equity_ticker() -> None:
    assert parse_futures_expiry("AAPL") is None


def test_parse_futures_expiry_returns_none_for_options_short_form() -> None:
    # CME short-form options have a space + C/P + strike — not a bare future.
    assert parse_futures_expiry("E2AJ6 C6190") is None


def test_parse_futures_expiry_returns_none_for_combo() -> None:
    assert parse_futures_expiry("ESM6-ESU6") is None


def test_parse_futures_expiry_strips_whitespace_and_uppercases() -> None:
    assert parse_futures_expiry("  esm6  ") == date(2026, 6, 19)


# ---------------------------------------------------------------------------
# futures_expiry_bucket
# ---------------------------------------------------------------------------


def test_futures_expiry_bucket_front_within_window() -> None:
    # ESM6 expires 19 Jun 2026; as_of 1 May 2026 → 49 days → front.
    assert futures_expiry_bucket("ESM6", as_of=date(2026, 5, 1)) == "front"


def test_futures_expiry_bucket_back_beyond_window() -> None:
    # ESM6 expires 19 Jun 2026; as_of 1 Jan 2026 → 169 days → back.
    assert futures_expiry_bucket("ESM6", as_of=date(2026, 1, 1)) == "back"


def test_futures_expiry_bucket_back_already_expired() -> None:
    # Past expiry → days_to_expiry < 0 → back (out of front window).
    assert futures_expiry_bucket("ESM6", as_of=date(2026, 7, 1)) == "back"


def test_futures_expiry_bucket_spread_for_dash_combo() -> None:
    assert futures_expiry_bucket("ESM6-ESU6", as_of=date(2026, 5, 1)) == "spread"


def test_futures_expiry_bucket_unknown_for_continuous_root() -> None:
    assert futures_expiry_bucket("ES", as_of=date(2026, 5, 1)) == "unknown"


def test_futures_expiry_bucket_unknown_for_equity() -> None:
    assert futures_expiry_bucket("AAPL", as_of=date(2026, 5, 1)) == "unknown"


def test_futures_expiry_bucket_unknown_for_empty() -> None:
    assert futures_expiry_bucket("", as_of=date(2026, 5, 1)) == "unknown"


def test_futures_expiry_bucket_respects_custom_window() -> None:
    # ESM6 expires 19 Jun 2026; as_of 1 Apr 2026 → 79 days.
    # default 60d window → back; 90d window → front.
    assert futures_expiry_bucket("ESM6", as_of=date(2026, 4, 1)) == "back"
    assert futures_expiry_bucket("ESM6", as_of=date(2026, 4, 1), front_window_days=90) == "front"


# ---------------------------------------------------------------------------
# FUTURES_CHAIN_BUCKETS shape
# ---------------------------------------------------------------------------


def test_futures_chain_buckets_is_frozenset() -> None:
    assert isinstance(FUTURES_CHAIN_BUCKETS, frozenset)


def test_futures_chain_buckets_contains_three_canonical_buckets() -> None:
    assert frozenset({"front", "back", "spread"}) == FUTURES_CHAIN_BUCKETS


@pytest.mark.parametrize(
    ("symbol", "as_of", "expected"),
    [
        ("ESM6", date(2026, 5, 1), "front"),
        ("NQU24", date(2024, 9, 1), "front"),
        ("CLZ24", date(2024, 1, 1), "back"),
        ("GCJ25", date(2024, 1, 1), "back"),
        ("ESH5-ESM5", date(2026, 1, 1), "spread"),
    ],
)
def test_futures_expiry_bucket_parametric(symbol: str, as_of: date, expected: str) -> None:
    assert futures_expiry_bucket(symbol, as_of=as_of) == expected


# ---------------------------------------------------------------------------
# EmptyConfirmedReason — refdata cadence migration values (added 2026-05-07
# under manifest_migration_master § Audit findings → C.1 + C.11)
# ---------------------------------------------------------------------------


def test_expected_deprecated_data_type_in_taxonomy() -> None:
    """C.1 LEAGUES kill (and any future data_type retirement) flips manifest rows
    via ``record_empty(reason=EXPECTED_DEPRECATED_DATA_TYPE)``. UTL ManifestWriter
    validates the reason against ``EMPTY_CONFIRMED_REASONS`` — the new value must
    be in the closed set or migration scripts hit ``UnknownEmptyConfirmedReasonError``.
    """
    assert EmptyConfirmedReason.EXPECTED_DEPRECATED_DATA_TYPE.value == "EXPECTED_DEPRECATED_DATA_TYPE"
    assert "EXPECTED_DEPRECATED_DATA_TYPE" in EMPTY_CONFIRMED_REASONS


def test_expected_refdata_cadence_change_in_taxonomy() -> None:
    """C.11 TEAMS per-(team, season) migration flips legacy daily shards via
    ``record_empty(reason=EXPECTED_REFDATA_CADENCE_CHANGE)``. Same UTL validation
    contract as above; the new value must be in the closed set."""
    assert EmptyConfirmedReason.EXPECTED_REFDATA_CADENCE_CHANGE.value == "EXPECTED_REFDATA_CADENCE_CHANGE"
    assert "EXPECTED_REFDATA_CADENCE_CHANGE" in EMPTY_CONFIRMED_REASONS


def test_refdata_cadence_reasons_have_expected_prefix() -> None:
    """Both new reasons start with ``EXPECTED_`` so ``record_expected_empty`` accepts
    them (it rejects bare ``SOURCE_RETURNED_ZERO``-class reasons because those are
    write-time honest-absence, not calendar-pre-skip / refdata-deprecation)."""
    from unified_api_contracts.canonical.crosscutting.honest_coverage import EXPECTED_EMPTY_REASON_PREFIX

    assert EmptyConfirmedReason.EXPECTED_DEPRECATED_DATA_TYPE.value.startswith(EXPECTED_EMPTY_REASON_PREFIX)
    assert EmptyConfirmedReason.EXPECTED_REFDATA_CADENCE_CHANGE.value.startswith(EXPECTED_EMPTY_REASON_PREFIX)


def test_expected_known_source_gap_value_present() -> None:
    """Added 2026-05-11 (operator-approved per wave3x_track_d_findings_2026_05_11.md § TL;DR 2).

    Reference uses: VIX 15m mid-history gap (currently written as NaN-OHLC placeholder, see
    ``plans/active/issues/wave3x_track_d_findings_2026_05_11.md`` P0-2) + sports
    ``KNOWN_COVERAGE_GAPS`` ranges. Distinct from ``EXPECTED_PRE_SOURCE_COVERAGE_START`` /
    ``EXPECTED_INSTRUMENT_NOT_LISTED`` — those are pre-launch absence; this is mid-history
    accepted gap.
    """
    from unified_api_contracts.canonical.crosscutting.honest_coverage import EXPECTED_EMPTY_REASON_PREFIX

    assert EmptyConfirmedReason.EXPECTED_KNOWN_SOURCE_GAP.value == "EXPECTED_KNOWN_SOURCE_GAP"
    assert "EXPECTED_KNOWN_SOURCE_GAP" in EMPTY_CONFIRMED_REASONS
    assert EmptyConfirmedReason.EXPECTED_KNOWN_SOURCE_GAP.value.startswith(EXPECTED_EMPTY_REASON_PREFIX)
