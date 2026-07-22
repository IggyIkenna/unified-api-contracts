"""Sports source coverage propagation tests.

Verifies that ``clip_dates_to_source_coverage`` correctly drops pre-coverage
dates for every (source, data_type) pair in ``SOURCE_COVERAGE_START`` and
``DATA_TYPE_COVERAGE_START``.

FLOOR = 2020-06-06 for ALL sports sources (operator ruling 2026-07-21,
CANONICAL). Odds tick data starts 2020-06-06 (measured: ZERO odds before it);
without odds nothing downstream is legitimately computable, so 2020-06-06 is
the floor for every source/coverage/expectation, superseding the per-source
"evidence-derived" floors (the 2026-07-15 amendment's api_football/footystats/
understat/transfermarkt/soccer_football_info/open_meteo values, and the
api_football per-fixture overrides it deleted). All pre-2020-06-06 sports data
is out-of-scope and is being wiped — a window entirely before the floor is no
longer "real data that must survive the clip", it is expected-empty.

Plan: data_status_comprehensive_test_coverage_2026_05_07.md § C sports-half.
"""

from __future__ import annotations

from datetime import date

import pytest

from unified_api_contracts.canonical.domain.sports.league_data import (
    DATA_TYPE_COVERAGE_START,
    SOURCE_COVERAGE_START,
    SPORTS_DATA_TYPE_TO_SOURCE,
    clip_dates_to_source_coverage,
    get_source_coverage_start,
    is_pre_launch_date,
)
from unified_api_contracts.registry.venue_mapping import VenueMapping


class TestClipDatesToSourceCoverage:
    """Behavioural tests for clip_dates_to_source_coverage."""

    @pytest.mark.unit
    def test_range_entirely_before_coverage_returns_inverted_bounds(self) -> None:
        """Entire range pre-coverage → inverted bounds signal."""
        # footystats floor is 2020-06-06 (canonical, 2026-07-21); window
        # 2010-2017 is entirely pre-coverage either way.
        start, end = clip_dates_to_source_coverage("footystats", "2010-01-01", "2017-12-31")
        assert end == "" or start > end

    @pytest.mark.unit
    def test_range_straddles_coverage_start_clips_to_coverage(self) -> None:
        """Range that starts before coverage and ends after → clipped to coverage start."""
        # footystats floor is 2020-06-06 (canonical sports floor, operator
        # ruling 2026-07-21 — supersedes the old 2018-01-01 evidence-derived
        # value). Window opens in 2019 and closes in 2021, straddling it.
        start, end = clip_dates_to_source_coverage("footystats", "2019-01-01", "2021-06-01")
        assert start == "2020-06-06"
        assert end == "2021-06-01"

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
        """Per-(source, data_type) override takes precedence over source-wide value.

        soccer_football_info source-wide AND the SFI_PROGRESSIVE_STATS override
        are BOTH 2020-06-06 post-ruling (2026-07-21 canonical sports floor) — the
        old SFI-specific 2020-01-01 override no longer sits later than the
        source-wide value, so the two coincide here. That means this case alone
        can't distinguish "override wins" from "source-wide wins"; see
        ``test_data_type_override_precedence_over_distinct_source_wide`` below
        for the falsifying case that proves the override branch is genuinely
        read.
        """
        start, end = clip_dates_to_source_coverage(
            "soccer_football_info",
            "2020-01-01",
            "2020-12-31",
            data_type="SFI_PROGRESSIVE_STATS",
        )
        assert start == "2020-06-06"
        assert end == "2020-12-31"

    @pytest.mark.unit
    def test_data_type_override_precedence_over_distinct_source_wide(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Falsifier: inject a distinct, later override and confirm it — not source-wide — wins.

        Since the 2026-07-21 ruling collapsed SFI_PROGRESSIVE_STATS onto the
        same 2020-06-06 value as the source-wide floor, a same-value assertion
        can't prove precedence. This monkeypatches a later override onto
        ``DATA_TYPE_COVERAGE_START`` and proves the clip reads the override, not
        ``SOURCE_COVERAGE_START["soccer_football_info"]``.
        """
        monkeypatch.setitem(
            DATA_TYPE_COVERAGE_START,
            ("soccer_football_info", "SFI_PROGRESSIVE_STATS"),
            date(2020, 8, 1),
        )
        start, end = clip_dates_to_source_coverage(
            "soccer_football_info",
            "2020-06-06",
            "2020-12-31",
            data_type="SFI_PROGRESSIVE_STATS",
        )
        assert start == "2020-08-01"
        assert end == "2020-12-31"

    @pytest.mark.unit
    def test_data_type_without_override_falls_back_to_source_wide(self) -> None:
        """data_type with no override uses the source-wide coverage start."""
        # soccer_football_info: 2020-06-06 (canonical sports floor,
        # 2026-07-21 — no override exists for MATCHES).
        start, end = clip_dates_to_source_coverage(
            "soccer_football_info",
            "2020-01-01",
            "2020-12-31",
            data_type="MATCHES",
        )
        assert start == "2020-06-06"
        assert end == "2020-12-31"

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "data_type",
        ["FIXTURE_EVENTS", "FIXTURE_LINEUPS", "FIXTURE_STATS", "PLAYER_STATS"],
    )
    def test_api_football_per_fixture_entities_clip_to_2020_06_06_canonical_floor(self, data_type: str) -> None:
        """api_football per-fixture entities carry NO override — they use the 2020-06-06 canonical floor.

        RENAMED from ``test_api_football_per_fixture_entities_use_source_wide_floor``
        (was pinned to the 2026-07-15 "amend floors to reality" value of
        2018-01-01). The 2026-07-21 operator ruling — odds tick data starts
        2020-06-06 and nothing downstream is legitimately computable without
        it — SUPERSEDES that evidence-derived floor for ALL sports sources,
        api_football included. A range opening before the source-wide floor
        must now clip to 2020-06-06, NOT 2018-01-01.
        """
        start, end = clip_dates_to_source_coverage(
            "api_football",
            "2016-01-01",
            "2021-01-01",
            data_type=data_type,
        )
        assert start == "2020-06-06"
        assert end == "2021-01-01"

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "data_type",
        ["FIXTURE_EVENTS", "FIXTURE_LINEUPS", "FIXTURE_STATS", "PLAYER_STATS"],
    )
    def test_api_football_per_fixture_2018_dates_now_clip_to_empty(self, data_type: str) -> None:
        """2018-01-01 per-fixture data is OUT-OF-SCOPE and clips to empty under the 2020-06-06 floor.

        RENAMED + INVERTED from ``test_api_football_per_fixture_2018_dates_are_not_clipped``
        (which asserted "2018 per-fixture data is REAL and must survive the
        clip" under the 2026-07-15 amendment). The 2026-07-21 operator ruling
        SUPERSEDES that amendment: the sports floor is 2020-06-06 for every
        source because odds tick data — the thing everything downstream needs —
        measures ZERO before that date. Pre-floor sports data (including this
        2018 per-fixture data) is being wiped; a window entirely inside 2018 is
        now expected-empty, not "real data to protect".
        """
        start, end = clip_dates_to_source_coverage(
            "api_football",
            "2018-01-01",
            "2018-12-31",
            data_type=data_type,
        )
        assert start == "2020-06-06"
        assert end == ""

    @pytest.mark.unit
    def test_api_football_no_override_uses_source_wide(self) -> None:
        """api_football without data_type override uses source-wide 2020-06-06."""
        start, end = clip_dates_to_source_coverage(
            "api_football",
            "2014-01-01",
            "2021-01-01",
        )
        assert start == "2020-06-06"
        assert end == "2021-01-01"

    @pytest.mark.unit
    def test_range_starting_exactly_at_coverage_is_not_clipped(self) -> None:
        """Range starting exactly at coverage start → no clip needed."""
        start, end = clip_dates_to_source_coverage("footystats", "2020-06-06", "2021-12-31")
        assert start == "2020-06-06"
        assert end == "2021-12-31"

    @pytest.mark.unit
    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            ("api_football", "2020-06-06"),
            ("footystats", "2020-06-06"),
            ("transfermarkt", "2020-06-06"),
            ("open_meteo", "2020-06-06"),
            ("understat", "2020-06-06"),
            ("soccer_football_info", "2020-06-06"),
        ],
    )
    def test_measured_floors_are_pinned(self, source: str, expected: str) -> None:
        """Pin every sports floor to the 2020-06-06 canonical value (operator ruling 2026-07-21).

        Odds tick data starts 2020-06-06 (measured: ZERO odds before it), and
        without odds nothing downstream is legitimately computable — so
        2020-06-06 is the floor for ALL sports sources, superseding the old
        per-source "evidence-derived" floors (each source's raw data may begin
        earlier, but pre-floor sports data is out-of-scope and is being wiped).
        Moving any of these back down requires a fresh operator ruling, not a
        per-source object probe; see SOURCE_COVERAGE_START for the rationale.
        """
        start, _ = clip_dates_to_source_coverage(source, "2010-01-01", "2026-01-01")
        assert start == expected


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
        assert result == date(2020, 6, 6)

    @pytest.mark.unit
    def test_get_source_coverage_start_returns_source_wide_without_data_type(self) -> None:
        """get_source_coverage_start returns source-wide without data_type."""
        result = get_source_coverage_start("soccer_football_info")
        assert result == date(2020, 6, 6)

    @pytest.mark.unit
    def test_get_source_coverage_start_returns_none_for_unknown(self) -> None:
        """get_source_coverage_start returns None for unknown sources."""
        result = get_source_coverage_start("nonexistent_source")
        assert result is None

    @pytest.mark.unit
    def test_fixtures_schedule_and_outcomes_are_registered(self) -> None:
        """Regression: FIXTURES_SCHEDULE/FIXTURES_OUTCOMES (the live post-2026-07-14
        split of FIXTURES, fixture_lifecycle.py) must resolve a source so
        is_pre_launch_date() can classify them.

        Found 2026-07-22: these two data_types were missing from
        SPORTS_DATA_TYPE_TO_SOURCE, so is_pre_launch_date() silently returned False
        for every row regardless of date — the orphan-sweep's C3 pre-launch-window
        guard could never fire for them, and ~83,541 real pre-2020-06-06 objects
        misclassified as legitimate E_orphan_real instead of floor violations.
        """
        assert SPORTS_DATA_TYPE_TO_SOURCE.get("FIXTURES_SCHEDULE") == "api_football"
        assert SPORTS_DATA_TYPE_TO_SOURCE.get("FIXTURES_OUTCOMES") == "api_football"
        assert is_pre_launch_date("FIXTURES_SCHEDULE", "2019-01-01") is True
        assert is_pre_launch_date("FIXTURES_OUTCOMES", "2019-01-01") is True
        assert is_pre_launch_date("FIXTURES_SCHEDULE", "2021-01-01") is False
        assert is_pre_launch_date("FIXTURES_OUTCOMES", "2021-01-01") is False


class TestOddsApiFloorDerivesFromSportsSsot:
    """The MTDS fetch pre-skip floor must DERIVE from the sports coverage SSOT.

    ``venue_mapping.source_data_start_dates['ODDS_API']`` and
    ``SOURCE_COVERAGE_START['odds_api']`` are the SAME FACT (the odds-api vendor
    floor) consumed by two different surfaces — the MTDS ``is_venue_available``
    FETCH pre-skip vs the coverage oracle / IS fetch guards / ManifestWriter
    ``is_pre_launch_date`` WRITE guard.

    Typed independently they drift, and the drift is SILENT in the dangerous
    direction: lower the sports SSOT on new evidence and a hand-typed fetch floor
    would keep pre-skipping the very dates the oracle now expects, so the backfill
    no-ops while coverage reports the days as missing. That is the failure class
    UAC@c280e1ff exposed for the OTHER sports sources (floors asserted 2018-2020
    uncapturable while ~22,327 real objects were held for those dates). odds_api
    itself is UNCHANGED by the 2026-07-21 ruling — it was already the 2020-06-06
    canonical floor (odds tick data IS the evidence the ruling generalized from).
    """

    @pytest.mark.unit
    def test_fetch_preskip_floor_equals_sports_ssot(self) -> None:
        """Today's values agree — the two surfaces name one floor."""
        venue_mapping = VenueMapping()
        assert venue_mapping.get_venue_start_date("ODDS_API") == SOURCE_COVERAGE_START["odds_api"].isoformat()

    @pytest.mark.unit
    def test_amending_the_sports_ssot_moves_the_fetch_preskip(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The falsifier: amend the SSOT → the FETCH gate must follow, unedited.

        A snapshot assertion would pass against two hand-typed constants that merely
        happen to match. This fails unless the fetch floor genuinely derives: it
        amends only the sports SSOT and requires the MTDS pre-skip to open up.
        """
        monkeypatch.setitem(SOURCE_COVERAGE_START, "odds_api", date(2018, 1, 1))

        venue_mapping = VenueMapping()

        assert venue_mapping.get_venue_start_date("ODDS_API") == "2018-01-01"
        # The pre-skip (MTDS _build_active_venues_for_date) must now admit the date.
        assert venue_mapping.is_venue_available_on_date("ODDS_API", "2018-06-15") is True
