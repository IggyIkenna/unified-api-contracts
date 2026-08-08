"""Unit tests for the per-(AG, data_type) required-window registry.

Locks the IMPLEMENT P1 gate of the honest-coverage smoke harness plan:
``registry covers all 5 AGs' MVP data_types; sports entries reference real
season windows`` — adding a new MVP data_type without a registry entry is
review-blocking (the harness fails-loudly via
:class:`UnknownRequiredWindowError`, but this test catches the omission at
contract-test time).
"""

from __future__ import annotations

from datetime import date

import pytest

from unified_api_contracts.canonical.crosscutting.required_window_registry import (
    MVP_ASSET_GROUPS,
    MVP_REQUIRED_WINDOW_REGISTRY,
    RequiredWindowSpec,
    UnknownRequiredWindowError,
    registered_data_types_for_asset_group,
    resolve_required_window,
)


class TestRegistryShape:
    """RequiredWindowSpec construction invariants + coverage of 5 AGs."""

    def test_all_five_asset_groups_covered(self) -> None:
        # The harness iterates every AG; an AG with zero entries is a
        # silent skip in disguise.
        present = {ag for (ag, _dt) in MVP_REQUIRED_WINDOW_REGISTRY}
        assert present == set(MVP_ASSET_GROUPS)

    @pytest.mark.parametrize("ag", MVP_ASSET_GROUPS)
    def test_each_ag_has_at_least_one_data_type(self, ag: str) -> None:
        # Per-AG harness fanout depends on a non-empty set; an empty AG
        # means the harness doesn't smoke-test anything for it.
        assert len(registered_data_types_for_asset_group(ag)) >= 1, ag

    def test_lookback_n_specs_carry_provenance(self) -> None:
        # Every lookback_n entry MUST name the driver feature family +
        # periods + coarsest timeframe — the audit trail for the integer.
        for (ag, dt), spec in MVP_REQUIRED_WINDOW_REGISTRY.items():
            if spec.kind == "lookback_n":
                assert spec.lookback_calendar_days >= 1, (ag, dt)
                assert spec.driver_feature_family, (ag, dt)
                assert spec.driver_lookback_periods >= 1, (ag, dt)
                assert spec.driver_coarsest_timeframe, (ag, dt)

    def test_non_lookback_specs_have_zero_lookback(self) -> None:
        # Carrying a lookback value on a seasonal / max-daily spec is a
        # mis-configured entry — __post_init__ rejects it.
        for (ag, dt), spec in MVP_REQUIRED_WINDOW_REGISTRY.items():
            if spec.kind != "lookback_n":
                assert spec.lookback_calendar_days == 0, (ag, dt)


class TestRequiredWindowSpecValidation:
    """RequiredWindowSpec.__post_init__ rejects internally-inconsistent entries."""

    def test_lookback_n_requires_positive_days(self) -> None:
        with pytest.raises(ValueError, match="lookback_calendar_days"):
            RequiredWindowSpec(kind="lookback_n", lookback_calendar_days=0)

    def test_non_lookback_must_not_carry_lookback_days(self) -> None:
        with pytest.raises(ValueError, match="must NOT carry"):
            RequiredWindowSpec(kind="max_daily_aggregation", lookback_calendar_days=5)
        with pytest.raises(ValueError, match="must NOT carry"):
            RequiredWindowSpec(kind="seasonal_continuous", lookback_calendar_days=91)


class TestResolveRequiredWindow:
    """resolve_required_window — registry + context → concrete RequiredWindow."""

    def test_max_daily_aggregation_returns_single_day_window(self) -> None:
        today = date(2026, 6, 28)
        window = resolve_required_window(asset_group="tradfi", data_type="ohlcv_24h", today=today)
        assert window.start == today
        assert window.end == today
        assert window.kind == "max_daily_aggregation"
        assert window.calendar_days == 1

    def test_lookback_n_returns_n_day_window(self) -> None:
        today = date(2026, 6, 28)
        window = resolve_required_window(asset_group="cefi", data_type="trades", today=today)
        assert window.kind == "lookback_n"
        # cefi/trades = 200 calendar days
        assert window.calendar_days == 200
        assert window.end == today
        assert (today - window.start).days == 199

    def test_tradfi_ohlcv_1m_envelops_200_trading_days(self) -> None:
        # ~290 calendar days per the audit table envelops 200 trading days
        # on M-F venues — the EXPECTED_HOLIDAY / EXPECTED_WEEKEND cells
        # inside the window are within-window absences (RUNNABLE-compatible).
        today = date(2026, 6, 28)
        window = resolve_required_window(asset_group="tradfi", data_type="ohlcv_1m", today=today)
        assert window.kind == "lookback_n"
        assert window.calendar_days >= 200  # at minimum 200 trading days

    def test_seasonal_continuous_requires_league_and_season(self) -> None:
        today = date(2026, 6, 28)
        with pytest.raises(ValueError, match="league_id"):
            resolve_required_window(asset_group="sports", data_type="fixtures", today=today)
        with pytest.raises(ValueError, match="season_year"):
            resolve_required_window(
                asset_group="sports",
                data_type="fixtures",
                today=today,
                league_id="EPL",
            )

    def test_seasonal_continuous_pulls_real_season_boundary(self) -> None:
        # The window comes from the UAC sports league registry — NEVER
        # magic numbers in the caller. The harness gate "sports entries
        # reference real season windows" is met here.
        # today=2026-06-28 is post-season (EPL 2025-26 ends 2026-05-31),
        # so min(season_end, today) == season_end — boundary unchanged.
        today = date(2026, 6, 28)
        window = resolve_required_window(
            asset_group="sports",
            data_type="fixtures",
            today=today,
            league_id="EPL",
            season_year=2025,
        )
        assert window.kind == "seasonal_continuous"
        # EPL season runs Aug-May (cross-year). The 2025-26 season starts
        # in Aug 2025 and ends in May 2026 per the league registry.
        assert window.start.year == 2025
        assert window.start.month == 8
        assert window.end.year == 2026
        assert window.end >= window.start

    def test_seasonal_continuous_during_season_clips_end_to_today(self) -> None:
        # Regression: during-season today < season_end. Before the fix,
        # end=season_end caused all future-date rows to be counted as
        # M(missing) → INSUFFICIENT_HISTORY. After the fix, end=today.
        today = date(2025, 12, 1)
        window = resolve_required_window(
            asset_group="sports",
            data_type="fixtures",
            today=today,
            league_id="EPL",
            season_year=2025,
        )
        assert window.kind == "seasonal_continuous"
        assert window.end == today  # clipped to today, not season_end=2026-05-31
        assert window.start == date(2025, 8, 1)
        assert window.calendar_days == (today - date(2025, 8, 1)).days + 1

    def test_seasonal_continuous_post_season_end_unchanged(self) -> None:
        # Post-season today > season_end: min(season_end, today) == season_end.
        # Behaviour is identical to pre-fix — end stays at the season close.
        today = date(2026, 7, 1)
        window = resolve_required_window(
            asset_group="sports",
            data_type="fixtures",
            today=today,
            league_id="EPL",
            season_year=2025,
        )
        assert window.kind == "seasonal_continuous"
        assert window.end == date(2026, 5, 31)  # season_end, not today
        assert window.end < today

    def test_seasonal_continuous_early_in_season_clips_to_today(self) -> None:
        # Tiny window near season start — verifies clipping works on early dates.
        today = date(2025, 8, 15)
        window = resolve_required_window(
            asset_group="sports",
            data_type="fixtures",
            today=today,
            league_id="EPL",
            season_year=2025,
        )
        assert window.kind == "seasonal_continuous"
        assert window.end == today
        assert window.start == date(2025, 8, 1)
        assert window.calendar_days == 15  # Aug 1..Aug 15 inclusive

    def test_unknown_combo_raises_loudly(self) -> None:
        # The plan's IMPLEMENT P1 gate: "no combo silently skipped
        # (un-classified = hard error)". UnknownRequiredWindowError IS
        # that hard error.
        today = date(2026, 6, 28)
        with pytest.raises(UnknownRequiredWindowError, match="No required-window spec"):
            resolve_required_window(
                asset_group="cefi",
                data_type="not_a_real_data_type",
                today=today,
            )


class TestRegisteredDataTypesFor:
    def test_returns_data_types_for_known_ag(self) -> None:
        cefi_dts = registered_data_types_for_asset_group("cefi")
        assert "trades" in cefi_dts
        assert "book_snapshot_5" in cefi_dts
        assert "derivative_ticker" in cefi_dts
        assert "options_chain" in cefi_dts
        assert "futures_chain" in cefi_dts

    def test_returns_empty_for_unknown_ag(self) -> None:
        # An AG with no entries returns empty — the harness then sees
        # nothing to iterate (and a separate AG-coverage assertion
        # upstream catches the missing-AG case).
        assert registered_data_types_for_asset_group("not_an_ag") == frozenset()

    def test_sports_entries_are_all_seasonal_continuous(self) -> None:
        # Sports MVP data_types MUST be seasonal_continuous per the plan
        # ("sports / seasonal — a long continuous instrument-and-market
        # pipeline across seasons").
        for dt in registered_data_types_for_asset_group("sports"):
            spec = MVP_REQUIRED_WINDOW_REGISTRY[("sports", dt)]
            assert spec.kind == "seasonal_continuous", dt
