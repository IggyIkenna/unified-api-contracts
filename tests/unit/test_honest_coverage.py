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
    EXPECTED_BOOKMAKER_MARKET_SETS,
    EXPECTED_EMPTY_REASON_PREFIX,
    FUTURES_CHAIN_BUCKETS,
    OUT_OF_COVERAGE_WINDOW_REASONS,
    CaptureStatusCounts,
    EmptyConfirmedReason,
    LayeredCoverage,
    compute_honest_coverage,
    compute_layered_coverage,
    extract_es_options_cluster,
    futures_expiry_bucket,
    parse_futures_expiry,
    was_instrument_alive,
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

    assert EmptyConfirmedReason.EXPECTED_KNOWN_SOURCE_GAP.value == "EXPECTED_KNOWN_SOURCE_GAP"
    assert "EXPECTED_KNOWN_SOURCE_GAP" in EMPTY_CONFIRMED_REASONS
    assert EmptyConfirmedReason.EXPECTED_KNOWN_SOURCE_GAP.value.startswith(EXPECTED_EMPTY_REASON_PREFIX)


# ---------------------------------------------------------------------------
# was_instrument_alive — EmptyFromLiveInstrumentError backstop primitive (A10a)
# ---------------------------------------------------------------------------
def test_was_instrument_alive_within_window() -> None:
    # listed 2024-01-01, still active (available_to=None) → alive on a later day.
    assert was_instrument_alive(available_from=date(2024, 1, 1), available_to=None, day=date(2024, 6, 1)) is True


def test_was_instrument_alive_before_listing() -> None:
    assert was_instrument_alive(available_from=date(2024, 1, 1), available_to=None, day=date(2023, 12, 31)) is False


def test_was_instrument_alive_on_or_after_delisting() -> None:
    # available_to is the latest available date — day >= available_to ⇒ not alive (half-open window).
    assert (
        was_instrument_alive(available_from=date(2024, 1, 1), available_to=date(2024, 5, 1), day=date(2024, 5, 1))
        is False
    )
    assert (
        was_instrument_alive(available_from=date(2024, 1, 1), available_to=date(2024, 5, 1), day=date(2024, 4, 30))
        is True
    )


def test_was_instrument_alive_unknown_listing_is_conservative_false() -> None:
    # No available_from ⇒ liveness cannot be CONFIRMED ⇒ False (backstop never fires on unknowns).
    assert was_instrument_alive(available_from=None, available_to=None, day=date(2024, 6, 1)) is False


def test_was_instrument_alive_accepts_datetime_and_iso_string() -> None:
    from datetime import datetime

    assert (
        was_instrument_alive(
            available_from=datetime(2024, 1, 1, 12, 0, 0), available_to=None, day=datetime(2024, 6, 1, 0, 0, 0)
        )
        is True
    )
    assert was_instrument_alive(available_from="2024-01-01", available_to=None, day="2024-06-01T08:00:00Z") is True
    # unparseable day → conservative False
    assert was_instrument_alive(available_from="2024-01-01", available_to=None, day="not-a-date") is False


def test_out_of_coverage_window_partition() -> None:
    """The out-of-window reason set excludes lifecycle/scope cells but keeps calendar gaps."""
    from unified_api_contracts import (
        OUT_OF_COVERAGE_WINDOW_REASONS,
        WITHIN_WINDOW_EXPECTED_ABSENCE_REASONS,
        is_out_of_coverage_window,
        is_within_window_absence,
    )

    # lifecycle / scope → out of window (excluded from coverage denominator)
    for r in (
        "EXPECTED_PRE_GENESIS_CHAIN",
        "EXPECTED_PRE_VENUE_LAUNCH",
        "EXPECTED_INSTRUMENT_NOT_LISTED",
        "EXPECTED_INSTRUMENT_DELISTED",
        "EXPECTED_PRE_SEASON",
        "EXPECTED_OUT_OF_COVERAGE_WINDOW",
    ):
        assert is_out_of_coverage_window(r) is True
        assert r in OUT_OF_COVERAGE_WINDOW_REASONS
    # calendar empties → within window (count in the denominator)
    for r in ("EXPECTED_WEEKEND", "EXPECTED_HOLIDAY", "EXPECTED_PAUSED_LEAGUE"):
        assert is_out_of_coverage_window(r) is False
        assert is_within_window_absence(r) is True
        assert r in WITHIN_WINDOW_EXPECTED_ABSENCE_REASONS
    # blank/None → within (counts) — a blank-reason empty is a gap by default
    assert is_out_of_coverage_window(None) is False
    assert is_out_of_coverage_window("") is False
    # the two sets partition the full taxonomy with no overlap
    from unified_api_contracts import EMPTY_CONFIRMED_REASONS

    assert OUT_OF_COVERAGE_WINDOW_REASONS | WITHIN_WINDOW_EXPECTED_ABSENCE_REASONS == EMPTY_CONFIRMED_REASONS
    assert not (OUT_OF_COVERAGE_WINDOW_REASONS & WITHIN_WINDOW_EXPECTED_ABSENCE_REASONS)


def test_schedule_defining_fixtures_empty_is_resolved() -> None:
    """A schedule-defining FIXTURES SOURCE_RETURNED_ZERO is RESOLVED (no-match-day),
    NOT a coverage gap — but an enrichment's SOURCE_RETURNED_ZERO still IS a gap.

    Operator direction 2026-06-23: FIXTURES (API-Football) IS the schedule
    source-of-truth, so zero matches = complete, not missing data.
    """
    from unified_api_contracts import (
        SCHEDULE_DEFINING_DATA_TYPES,
        is_out_of_coverage_window,
        is_resolved_schedule_empty,
        is_within_window_absence,
    )

    # Only the schedule-defining FIXTURES data_type is in the closed set.
    assert set(SCHEDULE_DEFINING_DATA_TYPES) == {"FIXTURES"}

    # FIXTURES + SOURCE_RETURNED_ZERO → resolved / out-of-window (no matches that day).
    assert is_resolved_schedule_empty("FIXTURES", "SOURCE_RETURNED_ZERO") is True
    assert is_out_of_coverage_window("SOURCE_RETURNED_ZERO", "FIXTURES") is True
    assert is_within_window_absence("SOURCE_RETURNED_ZERO", "FIXTURES") is False
    # Case-insensitive on the data_type token.
    assert is_resolved_schedule_empty("fixtures", "SOURCE_RETURNED_ZERO") is True

    # Enrichment data_types: SOURCE_RETURNED_ZERO stays an in-window gap (its zero
    # may be a real miss when a fixture exists). NOT blanket-excluded.
    for enrichment in ("FIXTURE_STATS", "PLAYER_STATS", "ODDS", "MATCHES", "FIXTURE_EVENTS"):
        assert is_resolved_schedule_empty(enrichment, "SOURCE_RETURNED_ZERO") is False
        assert is_out_of_coverage_window("SOURCE_RETURNED_ZERO", enrichment) is False
        assert is_within_window_absence("SOURCE_RETURNED_ZERO", enrichment) is True

    # Legacy reason-only call (no data_type): SOURCE_RETURNED_ZERO is still a gap.
    assert is_out_of_coverage_window("SOURCE_RETURNED_ZERO") is False

    # Only SOURCE_RETURNED_ZERO triggers the schedule-empty resolution — other
    # reasons on FIXTURES route through the normal reason-set / blank rules.
    assert is_resolved_schedule_empty("FIXTURES", "EXPECTED_HOLIDAY") is False
    # EXPECTED_NO_FIXTURE is already an out-of-window lifecycle reason regardless.
    assert is_out_of_coverage_window("EXPECTED_NO_FIXTURE", "FIXTURES") is True
    assert is_out_of_coverage_window("EXPECTED_NO_FIXTURE") is True

    # Blank / None guards.
    assert is_resolved_schedule_empty(None, "SOURCE_RETURNED_ZERO") is False
    assert is_resolved_schedule_empty("FIXTURES", None) is False
    assert is_resolved_schedule_empty("FIXTURES", "") is False


# ---------------------------------------------------------------------------
# compute_honest_coverage — out-of-window clip (43c, 2026-06-23)
# ---------------------------------------------------------------------------


def test_compute_honest_coverage_default_out_of_window_is_zero() -> None:
    """Unmigrated callers (no out_of_window) keep the legacy numerator-credit
    behaviour — back-compatible."""
    counts = CaptureStatusCounts(captured=10, empty_confirmed=50, attempted_failed=5)
    assert counts.out_of_window == 0
    assert compute_honest_coverage(counts) == pytest.approx(60 / 65)


def test_compute_honest_coverage_clips_out_of_window_from_both_num_and_denom() -> None:
    """Out-of-life empties are clipped from BOTH numerator and denominator so an
    out-of-window cell reads as a blank, not coverage credit (operator 2026-06-23)."""
    # 49 of the 50 empties are out-of-life (e.g. EXPECTED_INSTRUMENT_NOT_LISTED).
    counts = CaptureStatusCounts(captured=10, empty_confirmed=50, attempted_failed=5, out_of_window=49)
    # within_window_empty = 1; numerator = 10 + 1 = 11; denominator = 11 + 5 = 16.
    assert compute_honest_coverage(counts) == pytest.approx(11 / 16)


def test_compute_honest_coverage_clip_differs_from_credit_when_failures_present() -> None:
    """The clip is materially lower than numerator-credit precisely when there are
    attempted_failed/pending cells — the prediction-POLYMARKET inflation case."""
    credit = compute_honest_coverage(CaptureStatusCounts(captured=10, empty_confirmed=50, attempted_failed=5))
    clip = compute_honest_coverage(
        CaptureStatusCounts(captured=10, empty_confirmed=50, attempted_failed=5, out_of_window=49)
    )
    assert clip < credit


def test_compute_honest_coverage_clip_no_effect_without_failures() -> None:
    """With zero failed/pending cells, clip and credit agree (both 1.0) — the
    docstring's original equivalence holds only in that case."""
    credit = compute_honest_coverage(CaptureStatusCounts(captured=10, empty_confirmed=50))
    clip = compute_honest_coverage(CaptureStatusCounts(captured=10, empty_confirmed=50, out_of_window=49))
    assert credit == pytest.approx(1.0)
    assert clip == pytest.approx(1.0)


def test_out_of_coverage_window_reasons_carry_lifecycle_reasons() -> None:
    """The three out-of-life prediction reasons the operator flagged are in the
    canonical out-of-window set (so producers classify them as clippable)."""
    assert "EXPECTED_INSTRUMENT_NOT_LISTED" in OUT_OF_COVERAGE_WINDOW_REASONS
    assert "EXPECTED_INSTRUMENT_DELISTED" in OUT_OF_COVERAGE_WINDOW_REASONS
    assert "EXPECTED_PRE_VENUE_LAUNCH" in OUT_OF_COVERAGE_WINDOW_REASONS


# ---------------------------------------------------------------------------
# Layered coverage (day_coverage + depth_coverage) — instruments-foundation §2.
# ---------------------------------------------------------------------------


def test_compute_layered_coverage_both_layers_via_ssot() -> None:
    """Both layers are exactly the SSOT formula over their own counts — no
    separate arithmetic, so the deployment-ui can never diverge from one formula."""
    day = CaptureStatusCounts(captured=18, expected_unattempted_pending_fetch=4)  # 4 missing venue-days
    depth = CaptureStatusCounts(captured=1200, expected_unattempted_pending_fetch=300)  # thin days
    layered = compute_layered_coverage(day, depth)
    assert isinstance(layered, LayeredCoverage)
    assert layered.day_coverage == pytest.approx(compute_honest_coverage(day))
    assert layered.depth_coverage == pytest.approx(compute_honest_coverage(depth))
    assert layered.day_coverage == pytest.approx(18 / 22)
    assert layered.depth_coverage == pytest.approx(1200 / 1500)
    # the counts are carried so a consumer renders the breakdown without recompute
    assert layered.day_counts == day
    assert layered.depth_counts == depth


def test_compute_layered_coverage_day_green_depth_low_is_the_thin_day_signal() -> None:
    """The explicit 'every day present, but days under-populated' signal:
    day_coverage high while depth_coverage drags (a venue-day captured with 41
    of thousands)."""
    day = CaptureStatusCounts(captured=2640)  # every expected venue-day answered
    depth = CaptureStatusCounts(captured=41, expected_unattempted_pending_fetch=2599)
    layered = compute_layered_coverage(day, depth)
    assert layered.day_coverage == pytest.approx(1.0)
    assert layered.depth_coverage < 0.05
    assert layered.day_coverage > layered.depth_coverage


def test_compute_layered_coverage_missing_days_drag_day_coverage() -> None:
    """The 2026-06-24 cefi blind-99.9% fix: once the 4 missing venue-days seed as
    expected_unattempted_pending_fetch they DRAG day_coverage below the
    captured-only ratio (instead of being silently absent → falsely ~1.0)."""
    blind = CaptureStatusCounts(captured=62091, attempted_failed=46)  # gaps ABSENT
    honest = CaptureStatusCounts(captured=62091, attempted_failed=46, expected_unattempted_pending_fetch=84)
    assert compute_honest_coverage(blind) > compute_honest_coverage(honest)
    layered = compute_layered_coverage(honest, honest)
    assert layered.day_coverage < compute_honest_coverage(blind)


# ---------------------------------------------------------------------------
# EXPECTED_BOOKMAKER_MARKET_SETS
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_expected_bookmaker_market_sets_has_required_tiers() -> None:
    """The three canonical league tiers must be present."""
    assert "tier_1_domestic" in EXPECTED_BOOKMAKER_MARKET_SETS
    assert "tier_1_international" in EXPECTED_BOOKMAKER_MARKET_SETS
    assert "tier_2_domestic" in EXPECTED_BOOKMAKER_MARKET_SETS


@pytest.mark.unit
def test_expected_bookmaker_market_sets_tier_1_domestic_bookmakers() -> None:
    """Tier-1 domestic must include pinnacle, betfair_ex_uk, williamhill, unibet_uk."""
    tier = EXPECTED_BOOKMAKER_MARKET_SETS["tier_1_domestic"]
    assert "pinnacle" in tier
    assert "betfair_ex_uk" in tier
    assert "williamhill" in tier
    assert "unibet_uk" in tier


@pytest.mark.unit
def test_expected_bookmaker_market_sets_pinnacle_has_asian_handicap_in_tier_1() -> None:
    """Pinnacle carries asian_handicap for tier-1 domestic and international."""
    from unified_api_contracts.canonical.domain.sports.odds import OddsType

    assert OddsType.ASIAN_HANDICAP in EXPECTED_BOOKMAKER_MARKET_SETS["tier_1_domestic"]["pinnacle"]
    assert OddsType.ASIAN_HANDICAP in EXPECTED_BOOKMAKER_MARKET_SETS["tier_1_international"]["pinnacle"]


@pytest.mark.unit
def test_expected_bookmaker_market_sets_all_markets_are_nonempty() -> None:
    """Every (tier, bookmaker) pair must list at least one market type."""
    for tier_key, bookmaker_map in EXPECTED_BOOKMAKER_MARKET_SETS.items():
        assert bookmaker_map, f"tier {tier_key!r} has no bookmakers"
        for bk, markets in bookmaker_map.items():
            assert markets, f"tier {tier_key!r} bookmaker {bk!r} has empty market list"


@pytest.mark.unit
def test_expected_bookmaker_market_sets_tier_2_domestic_is_subset_of_tier_1() -> None:
    """Tier-2 domestic bookmaker set must be a subset of tier-1 domestic."""
    tier1_bks = set(EXPECTED_BOOKMAKER_MARKET_SETS["tier_1_domestic"])
    tier2_bks = set(EXPECTED_BOOKMAKER_MARKET_SETS["tier_2_domestic"])
    assert tier2_bks <= tier1_bks, (
        f"tier_2_domestic bookmakers {tier2_bks - tier1_bks} not in tier_1_domestic"
    )
