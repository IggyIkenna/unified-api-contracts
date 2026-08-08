"""Unit tests for FEATURE_UPSTREAM_REQUIREMENTS + in_coverage helper.

Plan: features_sports_honest_coverage_2026_05_05.md, Phase 1.D.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.canonical.domain.features import FEATURE_REQUIRED_INPUTS
from unified_api_contracts.sports import (
    FEATURE_UPSTREAM_REQUIREMENTS,
    UpstreamReq,
    in_coverage,
    in_coverage_dt,
)


class TestUpstreamReq:
    def test_required_defaults_true(self) -> None:
        req = UpstreamReq(source="api_football", data_type="FIXTURES")
        assert req.required is True
        assert req.notes == ""

    def test_optional_explicit_false(self) -> None:
        req = UpstreamReq(
            source="transfermarkt",
            data_type="PLAYER_VALUES",
            required=False,
            notes="optional fallback",
        )
        assert req.required is False
        assert req.notes == "optional fallback"

    def test_frozen(self) -> None:
        req = UpstreamReq(source="understat", data_type="XG")
        with pytest.raises((AttributeError, Exception)):
            req.required = False  # type: ignore[misc]


class TestFeatureUpstreamRequirements:
    def test_dict_non_empty(self) -> None:
        assert len(FEATURE_UPSTREAM_REQUIREMENTS) > 0

    def test_known_calculators_present(self) -> None:
        # Spot-check the calculators that exist on the daily compute path
        for calc in (
            "team_form",
            "team_goals",
            "season_context",
            "weather_calculator",
            "sfi_progressive",
            "footystats_predictions",
            "odds_calculator",
            "team_xg",
            "halftime_calculator",
        ):
            assert calc in FEATURE_UPSTREAM_REQUIREMENTS, f"missing {calc}"

    def test_every_value_is_list_of_upstreamreq(self) -> None:
        for calc, reqs in FEATURE_UPSTREAM_REQUIREMENTS.items():
            assert isinstance(reqs, list), f"{calc} should be list, got {type(reqs)}"
            assert len(reqs) > 0, f"{calc} has no requirements"
            for req in reqs:
                assert isinstance(req, UpstreamReq), f"{calc} req not UpstreamReq"

    def test_every_calculator_has_at_least_one_required(self) -> None:
        # A calculator with ALL optional upstreams would silently produce all-NaN
        # output for every shard — that's a design smell. Every calculator must
        # have at least one required input.
        for calc, reqs in FEATURE_UPSTREAM_REQUIREMENTS.items():
            assert any(r.required for r in reqs), f"{calc} has no required upstream"

    def test_known_sources_only(self) -> None:
        valid_sources = {
            "api_football",
            "footystats",
            "understat",
            "transfermarkt",
            "soccer_football_info",
            "open_meteo",
            "odds_api",
            "mdps_odds_horizon_bucket",
            "derived",
        }
        for calc, reqs in FEATURE_UPSTREAM_REQUIREMENTS.items():
            for req in reqs:
                assert req.source in valid_sources, (
                    f"{calc}: unknown source '{req.source}' — add to validation set if intentional"
                )


class TestInCoverage:
    def test_pre_launch_date_returns_false(self) -> None:
        # api_football coverage starts 2020-06-06 (canonical sports floor,
        # operator ruling 2026-07-21 — supersedes any earlier per-source value).
        assert in_coverage("api_football", "FIXTURES", "EPL", "2014-01-01") is False

    def test_post_launch_date_in_coverage_league_returns_true(self) -> None:
        # EPL is in api_football's league coverage; 2024 is well past launch
        assert in_coverage("api_football", "FIXTURES", "EPL", "2024-04-13") is True

    def test_understat_xg_out_of_coverage_league_returns_false(self) -> None:
        # Understat XG only covers 6 European leagues. MLS isn't one of them.
        assert in_coverage("understat", "XG", "MLS", "2024-04-13") is False

    def test_understat_xg_in_coverage_league_returns_true(self) -> None:
        # EPL is in understat's coverage
        assert in_coverage("understat", "XG", "EPL", "2024-04-13") is True

    def test_empty_data_type_returns_true(self) -> None:
        # No data_type means no clip-able floor; assume in-coverage
        assert in_coverage("api_football", "", "EPL", "2024-04-13") is True

    def test_empty_league_id_disables_league_check(self) -> None:
        # When the calculator doesn't shard by league (e.g. weather_calculator
        # which is per-fixture), pass league_id="" and only the date floor +
        # known-gap checks apply.
        assert in_coverage("understat", "XG", "", "2024-04-13") is True

    def test_derived_source_always_in_coverage(self) -> None:
        # ``source="derived"`` is the special token for in-pipeline feature
        # dependencies — coverage propagates through the dependent calculator.
        assert in_coverage("derived", "team_form", "EPL", "2024-04-13") is True
        # Even pre-launch dates: derived bypasses date-floor.
        assert in_coverage("derived", "team_form", "EPL", "1999-01-01") is True

    def test_sfi_progressive_stats_pre_2020_06_06_clipped(self) -> None:
        # Per DATA_TYPE_COVERAGE_START override (2020-06-06 canonical sports
        # floor, operator ruling 2026-07-21 — supersedes the old SFI-specific
        # 2020-01-01 value; SFI_PROGRESSIVE_STATS now coincides with the
        # source-wide floor):
        # ("soccer_football_info", "SFI_PROGRESSIVE_STATS") = 2020-06-06
        assert in_coverage("soccer_football_info", "SFI_PROGRESSIVE_STATS", "EPL", "2020-06-05") is False
        assert in_coverage("soccer_football_info", "SFI_PROGRESSIVE_STATS", "EPL", "2020-06-06") is True


class TestOddsCalculatorRegistryConsistency:
    """Guards against registry divergence between required_inputs.py and
    feature_upstream.py for odds_calculator.

    Prior to 2026-08-08 the two registries contradicted each other: the
    2026-06-25 ruling (footystats ODDS removed; MTDS/odds-api owns raw odds)
    was recorded in required_inputs.py but never propagated to
    feature_upstream.py, which still declared footystats ODDS as REQUIRED.
    """

    def test_no_footystats_odds_upstream(self) -> None:
        reqs = FEATURE_UPSTREAM_REQUIREMENTS["odds_calculator"]
        footystats_odds = [r for r in reqs if r.source == "footystats" and r.data_type == "ODDS"]
        assert footystats_odds == [], (
            "footystats ODDS was removed from odds_calculator 2026-06-25 "
            f"(MTDS/odds-api owns raw odds) — still present: {footystats_odds}"
        )

    def test_mdps_horizon_bucket_is_required(self) -> None:
        reqs = FEATURE_UPSTREAM_REQUIREMENTS["odds_calculator"]
        horizon = [r for r in reqs if r.data_type == "ODDS_HORIZON_BUCKET"]
        assert len(horizon) == 1, f"Expected exactly one ODDS_HORIZON_BUCKET req, got {horizon}"
        assert horizon[0].source == "mdps_odds_horizon_bucket"
        assert horizon[0].required is True, "ODDS_HORIZON_BUCKET must be required=True (sole upstream)"

    def test_required_data_types_agree_between_registries(self) -> None:
        """required_inputs.py and feature_upstream.py must declare the same
        required data_types for odds_calculator — divergence guard.

        If this test fails, one registry was updated without updating the other.
        Align them and update the comment in required_inputs.py and/or
        feature_upstream.py to record the ruling date + rationale.
        """
        ri_data_types = {req.data_type for req in FEATURE_REQUIRED_INPUTS["odds_calculator"]}
        fu_required_data_types = {
            req.data_type for req in FEATURE_UPSTREAM_REQUIREMENTS["odds_calculator"] if req.required
        }
        assert ri_data_types == fu_required_data_types, (
            "odds_calculator required data_types diverged between registries — "
            f"required_inputs.py: {ri_data_types!r}, "
            f"feature_upstream.py (required=True): {fu_required_data_types!r}. "
            "Update BOTH registries together when changing odds_calculator inputs."
        )


class TestInCoverageDt:
    def test_accepts_iso_string(self) -> None:
        assert in_coverage_dt("api_football", "FIXTURES", "EPL", "2024-04-13") is True

    def test_accepts_date(self) -> None:
        from datetime import date

        assert in_coverage_dt("api_football", "FIXTURES", "EPL", date(2024, 4, 13)) is True

    def test_accepts_datetime(self) -> None:
        from datetime import datetime

        assert in_coverage_dt("api_football", "FIXTURES", "EPL", datetime(2024, 4, 13, 14, 30)) is True

    def test_pre_launch_via_datetime(self) -> None:
        from datetime import date

        assert in_coverage_dt("api_football", "FIXTURES", "EPL", date(2014, 1, 1)) is False
