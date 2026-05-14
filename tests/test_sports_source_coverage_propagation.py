"""Sports source coverage propagation tests.

Verifies that ``clip_dates_to_source_coverage`` correctly drops pre-coverage
dates for every (source, data_type) pair in ``SOURCE_COVERAGE_START`` and
``DATA_TYPE_COVERAGE_START``.

Plan: data_status_comprehensive_test_coverage_2026_05_07.md § C sports-half.
"""

from __future__ import annotations

from datetime import date

import pytest

from unified_api_contracts.canonical.domain.sports.league_data import (
    DATA_TYPE_COVERAGE_START,
    SOURCE_COVERAGE_START,
    clip_dates_to_source_coverage,
    get_source_coverage_start,
)


class TestClipDatesToSourceCoverage:
    """Behavioural tests for clip_dates_to_source_coverage."""

    @pytest.mark.unit
    def test_range_entirely_before_coverage_returns_inverted_bounds(self) -> None:
        """Entire range pre-coverage → inverted bounds signal."""
        # footystats starts 2019-01-01; window 2010-2018 is entirely pre-coverage
        start, end = clip_dates_to_source_coverage("footystats", "2010-01-01", "2018-12-31")
        assert end == "" or start > end

    @pytest.mark.unit
    def test_range_straddles_coverage_start_clips_to_coverage(self) -> None:
        """Range that starts before coverage and ends after → clipped to coverage start."""
        # footystats starts 2019-01-01
        start, end = clip_dates_to_source_coverage("footystats", "2018-01-01", "2019-06-01")
        assert start == "2019-01-01"
        assert end == "2019-06-01"

    @pytest.mark.unit
    def test_range_entirely_within_coverage_unchanged(self) -> None:
        """Range entirely within coverage → returned unchanged."""
        start, end = clip_dates_to_source_coverage("footystats", "2021-01-01", "2021-12-31")
        assert start == "2021-01-01"
        assert end == "2021-12-31"

    @pytest.mark.unit
    def test_unknown_source_returns_range_unchanged(self) -> None:
        """Unknown source → no clip applied, range returned as-is."""
        start, end = clip_dates_to_source_coverage("nonexistent_source", "2010-01-01", "2021-12-31")
        assert start == "2010-01-01"
        assert end == "2021-12-31"

    @pytest.mark.unit
    def test_data_type_override_applied_when_specified(self) -> None:
        """Per-(source, data_type) override takes precedence over source-wide value."""
        # soccer_football_info source-wide: 2019-01-01
        # SFI_PROGRESSIVE_STATS override: 2020-01-01
        start, end = clip_dates_to_source_coverage(
            "soccer_football_info",
            "2019-06-01",
            "2020-06-01",
            data_type="SFI_PROGRESSIVE_STATS",
        )
        assert start == "2020-01-01"
        assert end == "2020-06-01"

    @pytest.mark.unit
    def test_data_type_without_override_falls_back_to_source_wide(self) -> None:
        """data_type with no override uses the source-wide coverage start."""
        # soccer_football_info: 2019-01-01 (no override for MATCHES)
        start, end = clip_dates_to_source_coverage(
            "soccer_football_info",
            "2018-01-01",
            "2019-06-01",
            data_type="MATCHES",
        )
        assert start == "2019-01-01"
        assert end == "2019-06-01"

    @pytest.mark.unit
    def test_api_football_fixture_events_override(self) -> None:
        """api_football FIXTURE_EVENTS override is 2020-06-06 (later than source-wide 2018-01-01)."""
        start, end = clip_dates_to_source_coverage(
            "api_football",
            "2019-01-01",
            "2021-01-01",
            data_type="FIXTURE_EVENTS",
        )
        assert start == "2020-06-06"
        assert end == "2021-01-01"

    @pytest.mark.unit
    def test_api_football_fixture_lineups_override(self) -> None:
        """api_football FIXTURE_LINEUPS override is 2020-06-06."""
        start, end = clip_dates_to_source_coverage(
            "api_football",
            "2019-01-01",
            "2021-01-01",
            data_type="FIXTURE_LINEUPS",
        )
        assert start == "2020-06-06"
        assert end == "2021-01-01"

    @pytest.mark.unit
    def test_api_football_fixture_stats_override(self) -> None:
        """api_football FIXTURE_STATS override is 2020-06-06."""
        start, end = clip_dates_to_source_coverage(
            "api_football",
            "2019-01-01",
            "2021-01-01",
            data_type="FIXTURE_STATS",
        )
        assert start == "2020-06-06"

    @pytest.mark.unit
    def test_api_football_player_stats_override(self) -> None:
        """api_football PLAYER_STATS override is 2020-06-06."""
        start, end = clip_dates_to_source_coverage(
            "api_football",
            "2019-01-01",
            "2021-01-01",
            data_type="PLAYER_STATS",
        )
        assert start == "2020-06-06"

    @pytest.mark.unit
    def test_api_football_no_override_uses_source_wide(self) -> None:
        """api_football without data_type override uses source-wide 2018-01-01."""
        start, end = clip_dates_to_source_coverage(
            "api_football",
            "2017-01-01",
            "2018-06-01",
        )
        assert start == "2018-01-01"
        assert end == "2018-06-01"

    @pytest.mark.unit
    def test_range_starting_exactly_at_coverage_is_not_clipped(self) -> None:
        """Range starting exactly at coverage start → no clip needed."""
        start, end = clip_dates_to_source_coverage("footystats", "2019-01-01", "2019-12-31")
        assert start == "2019-01-01"
        assert end == "2019-12-31"


class TestSourceCoverageStartCompleteness:
    """Verify SOURCE_COVERAGE_START and DATA_TYPE_COVERAGE_START completeness."""

    @pytest.mark.unit
    def test_all_source_coverage_starts_are_dates(self) -> None:
        """Every value in SOURCE_COVERAGE_START is a date (not a string)."""
        for source, coverage_date in SOURCE_COVERAGE_START.items():
            assert isinstance(coverage_date, date), f"{source!r} has non-date value {coverage_date!r}"

    @pytest.mark.unit
    def test_all_data_type_coverage_starts_are_dates(self) -> None:
        """Every value in DATA_TYPE_COVERAGE_START is a date (not a string)."""
        for key, coverage_date in DATA_TYPE_COVERAGE_START.items():
            assert isinstance(coverage_date, date), f"{key!r} has non-date value {coverage_date!r}"

    @pytest.mark.unit
    def test_data_type_overrides_are_not_earlier_than_source_wide(self) -> None:
        """Per-(source, data_type) overrides must be >= the source-wide coverage start.

        An earlier override would be semantically incorrect — it would claim the
        source had data before it actually launched.
        """
        for (source_key, data_type), override_date in DATA_TYPE_COVERAGE_START.items():
            source_wide = SOURCE_COVERAGE_START.get(source_key)
            if source_wide is not None:
                assert override_date >= source_wide, (
                    f"DATA_TYPE_COVERAGE_START[({source_key!r}, {data_type!r})] = {override_date} "
                    f"is earlier than SOURCE_COVERAGE_START[{source_key!r}] = {source_wide}. "
                    "Override must be >= source-wide start."
                )

    @pytest.mark.unit
    def test_data_type_overrides_source_keys_are_known_sources(self) -> None:
        """Every source_key in DATA_TYPE_COVERAGE_START must be a known source."""
        for (source_key, _data_type), _coverage_date in DATA_TYPE_COVERAGE_START.items():
            assert source_key in SOURCE_COVERAGE_START, (
                f"DATA_TYPE_COVERAGE_START references unknown source {source_key!r}. "
                "Add it to SOURCE_COVERAGE_START first."
            )

    @pytest.mark.unit
    def test_all_sports_sources_have_reasonable_cutoff(self) -> None:
        """All sports source coverage starts are in [2010-01-01, today]."""
        min_date = date(2010, 1, 1)
        today = date.today()
        for source, coverage_date in SOURCE_COVERAGE_START.items():
            assert min_date <= coverage_date <= today, (
                f"{source!r} has unreasonable coverage start {coverage_date} (must be in [{min_date}, {today}])"
            )

    @pytest.mark.unit
    def test_get_source_coverage_start_returns_override_when_data_type_given(self) -> None:
        """get_source_coverage_start returns override when data_type specified."""
        result = get_source_coverage_start("soccer_football_info", "SFI_PROGRESSIVE_STATS")
        assert result == date(2020, 1, 1)

    @pytest.mark.unit
    def test_get_source_coverage_start_returns_source_wide_without_data_type(self) -> None:
        """get_source_coverage_start returns source-wide without data_type."""
        result = get_source_coverage_start("soccer_football_info")
        assert result == date(2019, 1, 1)

    @pytest.mark.unit
    def test_get_source_coverage_start_returns_none_for_unknown(self) -> None:
        """get_source_coverage_start returns None for unknown sources."""
        result = get_source_coverage_start("nonexistent_source")
        assert result is None
