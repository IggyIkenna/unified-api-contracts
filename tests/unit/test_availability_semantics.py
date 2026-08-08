"""Unit tests for the availability_semantics SSOT module."""

from __future__ import annotations

import pytest

from unified_api_contracts.canonical.crosscutting.availability_semantics import (
    AVAILABILITY_AT_SEMANTICS,
    FIXTURE_ANNOUNCEMENT_FLOOR_DAYS,
    FIXTURE_ANNOUNCEMENT_FLOOR_DAYS_DEFAULT,
    get_availability_semantic,
    get_fixture_announcement_floor_days,
    has_availability_semantic,
)

# ---------------------------------------------------------------------------
# Sports semantics
# ---------------------------------------------------------------------------


def test_sports_lineups_uses_kickoff_minus_60min() -> None:
    assert get_availability_semantic("sports", "fixture_lineups") == "kickoff_minus_60min"


def test_sports_post_match_uses_match_end_time() -> None:
    assert get_availability_semantic("sports", "fixture_stats") == "match_end_time"
    # player_stats (was the phantom FIXTURE_PLAYER_STATS until 2026-07-15 — the entity
    # folder name; the canonical data_type is player_stats, which is what IS writes).
    assert get_availability_semantic("sports", "player_stats") == "match_end_time"
    assert get_availability_semantic("sports", "RESULTS") == "match_end_time"
    assert get_availability_semantic("sports", "UNDERSTAT_XG") == "match_end_time"
    assert get_availability_semantic("sports", "sfi_progressive_stats") == "match_end_time"


def test_sports_events_uses_event_time() -> None:
    assert get_availability_semantic("sports", "fixture_events") == "event_time"


def test_sports_injuries_uses_report_time() -> None:
    assert get_availability_semantic("sports", "injuries") == "report_time"


def test_sports_fixtures_uses_announced_at() -> None:
    assert get_availability_semantic("sports", "fixtures") == "announced_at"


def test_sports_weather_uses_forecast_issue_time() -> None:
    assert get_availability_semantic("sports", "WEATHER_FORECAST") == "forecast_issue_time"


def test_sports_odds_uses_publication_time() -> None:
    assert get_availability_semantic("sports", "ODDS_SNAPSHOT") == "publication_time"
    assert get_availability_semantic("sports", "ODDS_MOVEMENT") == "publication_time"
    assert get_availability_semantic("sports", "ARBITRAGE") == "publication_time"


def test_sports_reference_tables_use_fetch_completed_at() -> None:
    # P1 2026-08-08: IS reference types now lowercase; PLAYERS/VENUES/LEAGUES kept uppercase (not in 19-token vocab).
    for data_type in ("teams", "PLAYERS", "VENUES", "LEAGUES", "player_values"):
        assert get_availability_semantic("sports", data_type) == "fetch_completed_at"


# ---------------------------------------------------------------------------
# Market-data asset_groups (CeFi / DeFi / TradFi / prediction)
# ---------------------------------------------------------------------------


def test_market_data_asset_groups_use_tick_timestamp() -> None:
    for asset_group, data_type in [
        ("cefi", "trades"),
        ("cefi", "ohlcv_1m"),
        ("cefi", "options_chain"),
        ("defi", "swap"),
        ("defi", "liquidity"),
        ("tradfi", "trades"),
        ("tradfi", "options_chain"),
        ("prediction", "trades"),
        ("prediction", "book_snapshot_5"),
    ]:
        assert get_availability_semantic(asset_group, data_type) == "tick_timestamp"


def test_defi_phase_1a_seed_gap_data_types_use_tick_timestamp() -> None:
    """The 5 DeFi data_types added 2026-05-07 to close the feature_dag seed gap.

    Per the Phase 1A audit (parallel-agent pass over 87 unchecked todos),
    10 of 12 onchain feature_groups were blocked from completing the DAG
    seed because these 5 data_types — declared in
    ``unified_api_contracts.registry.market_data_categories.DEFI_DATA_TYPES``
    and consumed by features-onchain calculators — were missing from the
    availability_semantics registry. All 5 are per-event on-chain reads
    where the row's own timestamp IS the available_at.
    """
    for data_type in (
        "lending_indices",
        "risk_params",
        "rewards",
        "flash_loan_events",
        "eigenlayer_rewards",
    ):
        assert get_availability_semantic("defi", data_type) == "tick_timestamp", (
            f"defi/{data_type} expected tick_timestamp; got {get_availability_semantic('defi', data_type)}"
        )
        assert has_availability_semantic("defi", data_type)


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------


def test_reference_uses_fetch_completed_at() -> None:
    assert get_availability_semantic("reference", "instruments") == "fetch_completed_at"
    assert get_availability_semantic("reference", "venue_trading_calendar") == "fetch_completed_at"


# ---------------------------------------------------------------------------
# Failure mode (KeyError on unregistered)
# ---------------------------------------------------------------------------


def test_unregistered_pair_raises_keyerror() -> None:
    with pytest.raises(KeyError, match="No availability_at semantic registered"):
        get_availability_semantic("cefi", "totally_made_up_data_type")


def test_unregistered_asset_group_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        get_availability_semantic("alien_asset_group", "trades")


# ---------------------------------------------------------------------------
# has_availability_semantic
# ---------------------------------------------------------------------------


def test_has_availability_semantic_returns_true_for_registered() -> None:
    assert has_availability_semantic("sports", "FIXTURE_LINEUPS") is True


def test_has_availability_semantic_returns_false_for_unregistered() -> None:
    assert has_availability_semantic("cefi", "made_up") is False


# ---------------------------------------------------------------------------
# Registry shape
# ---------------------------------------------------------------------------


def test_registry_keys_are_two_string_tuples() -> None:
    for key in AVAILABILITY_AT_SEMANTICS:
        assert isinstance(key, tuple)
        assert len(key) == 2
        assert isinstance(key[0], str)
        assert isinstance(key[1], str)


def test_registry_values_are_known_semantics() -> None:
    valid_semantics = {
        "fetch_completed_at",
        "kickoff_minus_60min",
        "match_end_time",
        "event_time",
        "report_time",
        "announced_at",
        "forecast_issue_time",
        "publication_time",
        "tick_timestamp",
        "market_created_at",
    }
    for value in AVAILABILITY_AT_SEMANTICS.values():
        assert value in valid_semantics


def test_registry_has_minimum_seed_size() -> None:
    # Smoke: catch accidental wipe.
    assert len(AVAILABILITY_AT_SEMANTICS) >= 30


# ---------------------------------------------------------------------------
# Per-league fixture announcement floor
# ---------------------------------------------------------------------------


def test_default_floor_is_14_days() -> None:
    assert FIXTURE_ANNOUNCEMENT_FLOOR_DAYS_DEFAULT == 14


def test_big5_leagues_have_known_floors() -> None:
    # EPL, La Liga, Serie A, Ligue 1 all 21; Bundesliga 28
    assert FIXTURE_ANNOUNCEMENT_FLOOR_DAYS[39] == 21  # EPL
    assert FIXTURE_ANNOUNCEMENT_FLOOR_DAYS[140] == 21  # La Liga
    assert FIXTURE_ANNOUNCEMENT_FLOOR_DAYS[78] == 28  # Bundesliga
    assert FIXTURE_ANNOUNCEMENT_FLOOR_DAYS[135] == 21  # Serie A
    assert FIXTURE_ANNOUNCEMENT_FLOOR_DAYS[61] == 21  # Ligue 1


def test_get_fixture_announcement_floor_days_returns_per_league_value() -> None:
    assert get_fixture_announcement_floor_days(39) == 21  # EPL
    assert get_fixture_announcement_floor_days(78) == 28  # Bundesliga


def test_get_fixture_announcement_floor_days_returns_default_for_unknown() -> None:
    assert get_fixture_announcement_floor_days(99999) == FIXTURE_ANNOUNCEMENT_FLOOR_DAYS_DEFAULT


def test_all_floor_values_are_positive_integers() -> None:
    for league_id, days in FIXTURE_ANNOUNCEMENT_FLOOR_DAYS.items():
        assert isinstance(league_id, int), f"key {league_id!r} is not int"
        assert isinstance(days, int) and days > 0, f"league {league_id}: days={days} invalid"


def test_no_duplicate_keys_with_different_semantics() -> None:
    # Defensive: dict keys are unique by definition, but verify no
    # asset_group + data_type pair maps to two semantics via casing drift.
    seen_lowercase: dict[tuple[str, str], str] = {}
    for (ag, dt), semantic in AVAILABILITY_AT_SEMANTICS.items():
        normalised = (ag.lower(), dt.lower())
        if normalised in seen_lowercase:
            assert seen_lowercase[normalised] == semantic, (
                f"Casing drift: {(ag, dt)} maps to {semantic} but a "
                f"differently-cased duplicate maps to {seen_lowercase[normalised]}"
            )
        seen_lowercase[normalised] = semantic
