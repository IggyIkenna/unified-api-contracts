"""Unit tests for the windowed shard-coverage classifier contract.

Tests the pure-logic core of
``unified_api_contracts.canonical.crosscutting.shard_coverage_classification``
— the decision table that the honest-coverage smoke-test harness relies on
to keep RUNNABLE / INSUFFICIENT_HISTORY / HONEST_EMPTY from collapsing.

The manifest-walking wrapper (``classify_shard_coverage``) is gated behind
``NotImplementedError`` today — its body lands in the e2e-testing IMPLEMENT
P1 todo of ``plans/active/honest_coverage_smoke_harness_2026_06_28.md``. The
tests cover the IO-free half (``classify_from_capture_counts`` +
``bucket_capture_status_cell``) so the IMPLEMENT worker only composes the
IO around a verified core.
"""

from __future__ import annotations

from datetime import date

import pytest

from unified_api_contracts.canonical.crosscutting.honest_coverage import (
    EmptyConfirmedReason,
)
from unified_api_contracts.canonical.crosscutting.shard_coverage_classification import (
    MAX_HOLES_IN_REPORT,
    RequiredWindow,
    ShardCoverageClass,
    WindowCaptureCounts,
    bucket_capture_status_cell,
    classify_from_capture_counts,
    classify_shard_coverage,
)


class TestShardCoverageClassEnum:
    """ShardCoverageClass — closed-set verdict enum, three members."""

    def test_three_member_closed_set(self) -> None:
        # The trichotomy is total — three classes, no more, no less. Adding
        # a fourth state without updating the decision table + the codex
        # SSOT is review-blocking.
        members = {m.value for m in ShardCoverageClass}
        assert members == {"RUNNABLE", "INSUFFICIENT_HISTORY", "HONEST_EMPTY"}

    def test_string_valued(self) -> None:
        # StrEnum members serialise straight to JSON / parquet without
        # an explicit ``.value`` lookup at every call site.
        assert ShardCoverageClass.RUNNABLE == "RUNNABLE"
        assert ShardCoverageClass.INSUFFICIENT_HISTORY == "INSUFFICIENT_HISTORY"
        assert ShardCoverageClass.HONEST_EMPTY == "HONEST_EMPTY"


class TestRequiredWindow:
    """RequiredWindow — inclusive date range with a product-shaped kind."""

    def test_calendar_days_inclusive(self) -> None:
        w = RequiredWindow(start=date(2026, 6, 1), end=date(2026, 6, 1), kind="max_daily_aggregation")
        assert w.calendar_days == 1
        w2 = RequiredWindow(start=date(2025, 9, 1), end=date(2025, 11, 30), kind="seasonal_continuous")
        assert w2.calendar_days == 91

    def test_reverse_range_rejected(self) -> None:
        # An empty / reverse window is a programmer error — fail loudly at
        # construction so the harness can't silently classify "no days at
        # all" as HONEST_EMPTY.
        with pytest.raises(ValueError, match="before start"):
            _ = RequiredWindow(start=date(2026, 6, 5), end=date(2026, 6, 1), kind="lookback_n")


class TestBucketCaptureStatusCell:
    """bucket_capture_status_cell — single-row mapping into the per-day vocabulary."""

    def test_captured_bucket(self) -> None:
        assert bucket_capture_status_cell(capture_status="captured", error_reason=None) == "C"
        # error_reason is ignored for "captured" (it's blank on a captured row).
        assert bucket_capture_status_cell(capture_status="captured", error_reason="") == "C"

    def test_within_window_empty_bucket(self) -> None:
        # Within-window reasons (weekend / holiday / paused / postponed / source-returned-zero).
        for reason in (
            EmptyConfirmedReason.EXPECTED_HOLIDAY.value,
            EmptyConfirmedReason.EXPECTED_WEEKEND.value,
            EmptyConfirmedReason.EXPECTED_PAUSED_LEAGUE.value,
            EmptyConfirmedReason.EXPECTED_FIXTURE_POSTPONED.value,
            EmptyConfirmedReason.SOURCE_RETURNED_ZERO.value,
        ):
            assert (
                bucket_capture_status_cell(capture_status="empty_confirmed", error_reason=reason) == "WE"
            ), f"{reason} should bucket as within-window (WE)"

    def test_out_of_coverage_window_empty_bucket(self) -> None:
        # Out-of-coverage-window reasons (pre-launch / pre-genesis / not-listed / delisted /
        # source-doesn't-cover / no-fixture / not-enough-tvl / chain-aggregate / …).
        for reason in (
            EmptyConfirmedReason.EXPECTED_PRE_GENESIS_CHAIN.value,
            EmptyConfirmedReason.EXPECTED_PRE_VENUE_LAUNCH.value,
            EmptyConfirmedReason.EXPECTED_INSTRUMENT_NOT_LISTED.value,
            EmptyConfirmedReason.EXPECTED_INSTRUMENT_DELISTED.value,
            EmptyConfirmedReason.EXPECTED_SOURCE_DOES_NOT_COVER_LEAGUE.value,
            EmptyConfirmedReason.EXPECTED_NO_FIXTURE.value,
            EmptyConfirmedReason.EXPECTED_NOT_ENOUGH_TVL.value,
        ):
            assert (
                bucket_capture_status_cell(capture_status="empty_confirmed", error_reason=reason) == "OOW"
            ), f"{reason} should bucket as out-of-coverage-window (OOW)"

    def test_attempted_failed_bucket(self) -> None:
        # error_reason on attempted_failed carries the RecordFailedReason value;
        # for window classification the F bucket is taken regardless.
        assert bucket_capture_status_cell(capture_status="attempted_failed", error_reason=None) == "F"
        assert (
            bucket_capture_status_cell(capture_status="attempted_failed", error_reason="CLASSIFIED_VENUE_ERROR")
            == "F"
        )

    def test_expected_unattempted_with_expected_prefix_bucket(self) -> None:
        # Tier-3 sentinel pre-resolved → no-fetch-needed → known-empty.
        assert (
            bucket_capture_status_cell(
                capture_status="expected_unattempted",
                error_reason=EmptyConfirmedReason.EXPECTED_HOLIDAY.value,
            )
            == "UK"
        )

    def test_expected_unattempted_without_expected_prefix_bucket(self) -> None:
        # Pending fetch — the gap a backfill is expected to close.
        for reason in (None, "", "PENDING_BACKFILL"):
            assert (
                bucket_capture_status_cell(capture_status="expected_unattempted", error_reason=reason) == "U"
            ), f"reason={reason!r} should bucket as pending unattempted (U)"

    def test_unknown_capture_status_rejected(self) -> None:
        with pytest.raises(ValueError, match="Unknown capture_status"):
            bucket_capture_status_cell(capture_status="not_a_state", error_reason=None)

    def test_schedule_defining_fixtures_zero_routes_to_oow(self) -> None:
        # Operator direction 2026-06-23: a schedule-DEFINING FIXTURES no-match-day
        # SOURCE_RETURNED_ZERO routes through is_out_of_coverage_window when
        # data_type is supplied. This is the data-type-aware path that
        # bucket_capture_status_cell MUST honour.
        assert (
            bucket_capture_status_cell(
                capture_status="empty_confirmed",
                error_reason=EmptyConfirmedReason.SOURCE_RETURNED_ZERO.value,
                data_type="FIXTURES",
            )
            == "OOW"
        )
        # ...but a SOURCE_RETURNED_ZERO on an enrichment data_type stays WE.
        assert (
            bucket_capture_status_cell(
                capture_status="empty_confirmed",
                error_reason=EmptyConfirmedReason.SOURCE_RETURNED_ZERO.value,
                data_type="ohlcv_1m",
            )
            == "WE"
        )


class TestClassifyFromCaptureCounts:
    """classify_from_capture_counts — the decision table itself."""

    def test_runnable_pure_captured(self) -> None:
        # Continuous captured coverage with no holes → RUNNABLE.
        counts = WindowCaptureCounts(captured=91)
        assert classify_from_capture_counts(counts) == ShardCoverageClass.RUNNABLE

    def test_runnable_captured_with_within_window_empty(self) -> None:
        # 91-day sports window with weekend / holiday gaps → still RUNNABLE
        # (within-window empties are legitimate distribution, not holes).
        counts = WindowCaptureCounts(captured=60, within_window_empty=31)
        assert classify_from_capture_counts(counts) == ShardCoverageClass.RUNNABLE

    def test_runnable_captured_with_oow_and_uk(self) -> None:
        # A window that straddles a pre-listing day (OOW) + a Tier-3-known-empty
        # day (UK) but has captured data on the active days → RUNNABLE.
        counts = WindowCaptureCounts(captured=85, out_of_coverage_window_empty=4, known_empty_unattempted=2)
        assert classify_from_capture_counts(counts) == ShardCoverageClass.RUNNABLE

    def test_insufficient_history_one_attempted_failed(self) -> None:
        # Just ONE attempted_failed day in 200 days of captured → INSUFFICIENT_HISTORY.
        # This is the half-window safety property; the harness MUST fail
        # smoke even though 199/200 days are real data.
        counts = WindowCaptureCounts(captured=199, attempted_failed=1)
        assert classify_from_capture_counts(counts) == ShardCoverageClass.INSUFFICIENT_HISTORY

    def test_insufficient_history_one_pending_unattempted(self) -> None:
        # A pending-`expected_unattempted` day is also a hole (the backfill
        # hasn't run yet).
        counts = WindowCaptureCounts(captured=199, pending_unattempted=1)
        assert classify_from_capture_counts(counts) == ShardCoverageClass.INSUFFICIENT_HISTORY

    def test_insufficient_history_one_missing_row(self) -> None:
        # A date in the window with no manifest row at all is a writer-bug
        # signal — "never silent placeholders" hard rule — also INSUFFICIENT.
        counts = WindowCaptureCounts(captured=199, missing_rows=1)
        assert classify_from_capture_counts(counts) == ShardCoverageClass.INSUFFICIENT_HISTORY

    def test_insufficient_history_no_captured_with_holes(self) -> None:
        # Some empty_confirmed days + a failed day → still INSUFFICIENT, NOT
        # honest-empty. The crux: a failed day prevents the HONEST_EMPTY verdict.
        counts = WindowCaptureCounts(within_window_empty=89, attempted_failed=2)
        assert classify_from_capture_counts(counts) == ShardCoverageClass.INSUFFICIENT_HISTORY

    def test_honest_empty_all_oow(self) -> None:
        # Whole window pre-launch (e.g. trying to smoke-test 2018 BINANCE-FUTURES
        # ETH-PERP, which launched 2019-09) → HONEST_EMPTY.
        counts = WindowCaptureCounts(out_of_coverage_window_empty=91)
        assert classify_from_capture_counts(counts) == ShardCoverageClass.HONEST_EMPTY

    def test_honest_empty_all_within_window(self) -> None:
        # Edge case: a 1-day max-daily-aggregation window that lands on a
        # weekend for an equity instrument — single WE day, no captured, no
        # holes → HONEST_EMPTY (consumer must tolerate).
        counts = WindowCaptureCounts(within_window_empty=1)
        assert classify_from_capture_counts(counts) == ShardCoverageClass.HONEST_EMPTY

    def test_honest_empty_mixed_oow_uk_we(self) -> None:
        # Sports off-season: every day in the window is either UK (Tier-3
        # known-empty pre-season) or OOW (source-doesn't-cover-league) →
        # HONEST_EMPTY.
        counts = WindowCaptureCounts(out_of_coverage_window_empty=80, known_empty_unattempted=11)
        assert classify_from_capture_counts(counts) == ShardCoverageClass.HONEST_EMPTY

    def test_honest_empty_does_not_collapse_into_insufficient(self) -> None:
        # The crux test: HONEST_EMPTY (typed absence) is DIFFERENT from
        # INSUFFICIENT_HISTORY (untyped / failed absence). A window of
        # `empty_confirmed[EXPECTED_PRE_VENUE_LAUNCH]` is honest-empty, not
        # insufficient — even though both produce zero captured rows.
        honest_empty_counts = WindowCaptureCounts(out_of_coverage_window_empty=91)
        insufficient_counts = WindowCaptureCounts(attempted_failed=91)
        assert (
            classify_from_capture_counts(honest_empty_counts) == ShardCoverageClass.HONEST_EMPTY
        )
        assert (
            classify_from_capture_counts(insufficient_counts) == ShardCoverageClass.INSUFFICIENT_HISTORY
        )

    def test_priority_insufficient_dominates_runnable(self) -> None:
        # Even when most of the window is captured, a single hole forces
        # INSUFFICIENT — this is the safety direction. The harness exists
        # to fail loudly on partial windows.
        counts = WindowCaptureCounts(captured=190, attempted_failed=10)
        assert classify_from_capture_counts(counts) == ShardCoverageClass.INSUFFICIENT_HISTORY


class TestWindowCaptureCountsTotal:
    """WindowCaptureCounts.total — sanity that the buckets sum to the day count."""

    def test_total_sums_all_buckets(self) -> None:
        counts = WindowCaptureCounts(
            captured=10,
            within_window_empty=20,
            out_of_coverage_window_empty=30,
            known_empty_unattempted=5,
            attempted_failed=3,
            pending_unattempted=2,
            missing_rows=1,
        )
        assert counts.total() == 71

    def test_total_zero_default(self) -> None:
        assert WindowCaptureCounts().total() == 0


class _Cell:
    """Tiny ShardManifestCell-compatible row used by the wrapper tests."""

    def __init__(self, d: date, status: str, reason: str | None = None) -> None:
        self._date = d
        self._status = status
        self._reason = reason

    @property
    def date(self) -> date:
        return self._date

    @property
    def capture_status(self) -> str:
        return self._status

    @property
    def error_reason(self) -> str | None:
        return self._reason


class TestClassifyShardCoverageWrapper:
    """Integration tests for the manifest-walking wrapper.

    The wrapper composes the per-day bucketer with missing-row detection
    and the verdict decision table — see the module docstring's decision
    table for the property tested here.
    """

    def test_empty_cells_over_full_window_is_insufficient_history(self) -> None:
        # Zero rows over a 3-day window → all 3 days are missing-row → the
        # half-window safety property fires (writer-bug class, never silent
        # placeholders per data-pipeline-correctness HARD RULE).
        window = RequiredWindow(start=date(2026, 6, 1), end=date(2026, 6, 3), kind="lookback_n")
        report = classify_shard_coverage(
            asset_group="cefi",
            venue="BINANCE-FUTURES",
            data_type="trades",
            instrument_id="BTCUSDT",
            required_window=window,
            manifest_cells=(),
        )
        assert report.classification == ShardCoverageClass.INSUFFICIENT_HISTORY
        assert report.counts.missing_rows == 3
        assert report.holes == (date(2026, 6, 1), date(2026, 6, 2), date(2026, 6, 3))
        assert "INSUFFICIENT_HISTORY" in report.rationale

    def test_continuous_captured_window_is_runnable(self) -> None:
        window = RequiredWindow(start=date(2026, 6, 1), end=date(2026, 6, 3), kind="lookback_n")
        cells = [
            _Cell(date(2026, 6, 1), "captured"),
            _Cell(date(2026, 6, 2), "captured"),
            _Cell(date(2026, 6, 3), "captured"),
        ]
        report = classify_shard_coverage(
            asset_group="cefi",
            venue="BINANCE-FUTURES",
            data_type="trades",
            instrument_id="BTCUSDT",
            required_window=window,
            manifest_cells=cells,
        )
        assert report.classification == ShardCoverageClass.RUNNABLE
        assert report.counts.captured == 3
        assert report.holes == ()
        assert report.bundle_key == ()

    def test_full_window_honest_empty_does_not_collapse_to_insufficient(self) -> None:
        # The adversarial property the harness exists to enforce: a fully
        # OOW/UK/WE window with zero F+U+M is HONEST_EMPTY, NOT
        # INSUFFICIENT_HISTORY (codex/02-data/shard-coverage-classification.md).
        window = RequiredWindow(start=date(2026, 6, 1), end=date(2026, 6, 3), kind="lookback_n")
        cells = [
            _Cell(date(2026, 6, 1), "empty_confirmed", "EXPECTED_PRE_VENUE_LAUNCH"),
            _Cell(date(2026, 6, 2), "empty_confirmed", "EXPECTED_PRE_VENUE_LAUNCH"),
            _Cell(date(2026, 6, 3), "expected_unattempted", "EXPECTED_NOT_LISTED"),
        ]
        report = classify_shard_coverage(
            asset_group="cefi",
            venue="HYPERLIQUID",
            data_type="trades",
            instrument_id="OBSCURE-PERP",
            required_window=window,
            manifest_cells=cells,
        )
        assert report.classification == ShardCoverageClass.HONEST_EMPTY
        assert report.counts.missing_rows == 0
        assert report.counts.captured == 0

    def test_one_attempted_failed_in_runnable_window_flips_to_insufficient(self) -> None:
        # The safety property: one F day inside a window that is otherwise
        # full of captured days flips the verdict to INSUFFICIENT_HISTORY.
        window = RequiredWindow(start=date(2026, 6, 1), end=date(2026, 6, 4), kind="lookback_n")
        cells = [
            _Cell(date(2026, 6, 1), "captured"),
            _Cell(date(2026, 6, 2), "captured"),
            _Cell(date(2026, 6, 3), "attempted_failed", "HTTP_429"),
            _Cell(date(2026, 6, 4), "captured"),
        ]
        report = classify_shard_coverage(
            asset_group="cefi",
            venue="BINANCE-FUTURES",
            data_type="trades",
            instrument_id="BTCUSDT",
            required_window=window,
            manifest_cells=cells,
        )
        assert report.classification == ShardCoverageClass.INSUFFICIENT_HISTORY
        assert report.counts.attempted_failed == 1
        assert report.holes == (date(2026, 6, 3),)

    def test_cells_outside_window_are_ignored(self) -> None:
        window = RequiredWindow(start=date(2026, 6, 1), end=date(2026, 6, 2), kind="lookback_n")
        cells = [
            _Cell(date(2026, 5, 31), "attempted_failed", "HTTP_500"),
            _Cell(date(2026, 6, 1), "captured"),
            _Cell(date(2026, 6, 2), "captured"),
            _Cell(date(2026, 6, 3), "captured"),
        ]
        report = classify_shard_coverage(
            asset_group="cefi",
            venue="BINANCE-FUTURES",
            data_type="trades",
            instrument_id="BTCUSDT",
            required_window=window,
            manifest_cells=cells,
        )
        assert report.classification == ShardCoverageClass.RUNNABLE
        assert report.counts.total() == 2
        assert report.counts.captured == 2

    def test_duplicate_date_in_window_is_writer_invariant_violation(self) -> None:
        window = RequiredWindow(start=date(2026, 6, 1), end=date(2026, 6, 1), kind="max_daily_aggregation")
        cells = [
            _Cell(date(2026, 6, 1), "captured"),
            _Cell(date(2026, 6, 1), "attempted_failed", "HTTP_500"),
        ]
        with pytest.raises(ValueError, match="duplicate manifest row"):
            classify_shard_coverage(
                asset_group="cefi",
                venue="BINANCE-FUTURES",
                data_type="trades",
                instrument_id="BTCUSDT",
                required_window=window,
                manifest_cells=cells,
            )

    def test_holes_bounded_to_max_holes_in_report(self) -> None:
        # A fully-failed long window emits at most MAX_HOLES_IN_REPORT hole
        # dates so the report stays serialisable; the truth-counts live on
        # counts.missing_rows.
        span = MAX_HOLES_IN_REPORT + 3
        window = RequiredWindow(
            start=date(2026, 6, 1),
            end=date(2026, 6, 1) + (date(2026, 6, span) - date(2026, 6, 1)),
            kind="lookback_n",
        )
        report = classify_shard_coverage(
            asset_group="cefi",
            venue="BINANCE-FUTURES",
            data_type="trades",
            instrument_id="BTCUSDT",
            required_window=window,
            manifest_cells=(),
        )
        assert report.classification == ShardCoverageClass.INSUFFICIENT_HISTORY
        assert len(report.holes) == MAX_HOLES_IN_REPORT
        assert report.counts.missing_rows == window.calendar_days

    def test_bundle_key_preserved_for_bundled_shards(self) -> None:
        window = RequiredWindow(start=date(2026, 6, 1), end=date(2026, 6, 1), kind="max_daily_aggregation")
        report = classify_shard_coverage(
            asset_group="cefi",
            venue="DERIBIT",
            data_type="options_chain",
            instrument_id=None,
            required_window=window,
            manifest_cells=(_Cell(date(2026, 6, 1), "captured"),),
            bundle_key=("BTC",),
        )
        assert report.bundle_key == ("BTC",)
        assert report.instrument_id is None
        assert report.classification == ShardCoverageClass.RUNNABLE


class TestModuleConstants:
    def test_max_holes_in_report_bounded(self) -> None:
        # The hole-set on a report is bounded so a fully-failed window
        # can't bloat memory; truth-counts live on WindowCaptureCounts.
        assert MAX_HOLES_IN_REPORT >= 1
        assert MAX_HOLES_IN_REPORT <= 50
