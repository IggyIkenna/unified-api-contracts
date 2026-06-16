"""Unit tests for the availability_semantics SSOT module."""

from __future__ import annotations

import pytest

from unified_api_contracts.canonical.crosscutting.availability_semantics import (
    ANNOUNCEMENT_FLOOR_HOURS,
    AVAILABILITY_AT_SEMANTICS,
    DEFAULT_ANNOUNCEMENT_FLOOR_HOURS,
    get_announcement_floor_hours,
    get_availability_semantic,
    has_availability_semantic,
)

# ---------------------------------------------------------------------------
# Sports semantics
# ---------------------------------------------------------------------------


def test_sports_lineups_uses_kickoff_minus_60min() -> None:
    assert get_availability_semantic("sports", "FIXTURE_LINEUPS") == "kickoff_minus_60min"


def test_sports_post_match_uses_match_end_time() -> None:
    assert get_availability_semantic("sports", "FIXTURE_STATS") == "match_end_time"
    assert get_availability_semantic("sports", "FIXTURE_PLAYER_STATS") == "match_end_time"
    assert get_availability_semantic("sports", "RESULTS") == "match_end_time"
    assert get_availability_semantic("sports", "UNDERSTAT_XG") == "match_end_time"
    assert get_availability_semantic("sports", "SFI_PROGRESSIVE_STATS") == "match_end_time"


def test_sports_events_uses_event_time() -> None:
    assert get_availability_semantic("sports", "FIXTURE_EVENTS") == "event_time"


def test_sports_injuries_uses_report_time() -> None:
    assert get_availability_semantic("sports", "INJURIES") == "report_time"


def test_sports_fixtures_uses_announced_at() -> None:
    assert get_availability_semantic("sports", "FIXTURES") == "announced_at"


def test_sports_weather_uses_forecast_issue_time() -> None:
    assert get_availability_semantic("sports", "WEATHER_FORECAST") == "forecast_issue_time"


def test_sports_odds_uses_publication_time() -> None:
    assert get_availability_semantic("sports", "ODDS_SNAPSHOT") == "publication_time"
    assert get_availability_semantic("sports", "ODDS_MOVEMENT") == "publication_time"
    assert get_availability_semantic("sports", "ARBITRAGE") == "publication_time"


def test_sports_reference_tables_use_fetch_completed_at() -> None:
    for data_type in ("TEAMS", "PLAYERS", "VENUES", "LEAGUES", "PLAYER_VALUES"):
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
        ("prediction", "book_snapshot"),
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
# ANNOUNCEMENT_FLOOR_HOURS — fixture publication floor registry
# ---------------------------------------------------------------------------


def test_default_announcement_floor_is_14_days() -> None:
    """DEFAULT_ANNOUNCEMENT_FLOOR_HOURS == 336 (14d × 24h)."""
    assert DEFAULT_ANNOUNCEMENT_FLOOR_HOURS == 14 * 24


def test_top5_eu_leagues_seeded_at_14d() -> None:
    """Top-5 EU leagues are pre-seeded (initial conservative observation seed)."""
    for league_id in ("EPL", "LA_LIGA", "BUNDESLIGA", "SERIE_A", "LIGUE_1"):
        assert league_id in ANNOUNCEMENT_FLOOR_HOURS
        assert ANNOUNCEMENT_FLOOR_HOURS[league_id] == DEFAULT_ANNOUNCEMENT_FLOOR_HOURS


def test_all_floor_values_are_positive_hours() -> None:
    """Every per-league floor must be a positive integer (hours)."""
    for league_id, hours in ANNOUNCEMENT_FLOOR_HOURS.items():
        assert isinstance(hours, int) and hours > 0, league_id


def test_get_announcement_floor_hours_known_league() -> None:
    """Known league returns the seeded value."""
    assert get_announcement_floor_hours("EPL") == ANNOUNCEMENT_FLOOR_HOURS["EPL"]


def test_get_announcement_floor_hours_unknown_league_returns_default() -> None:
    """Unknown league falls back to DEFAULT_ANNOUNCEMENT_FLOOR_HOURS."""
    assert get_announcement_floor_hours("UNKNOWN_LEAGUE_XYZ") == DEFAULT_ANNOUNCEMENT_FLOOR_HOURS


def test_floor_replaces_7d_heuristic() -> None:
    """The default (14d = 336h) is MORE conservative than the old kickoff−7d (168h) heuristic."""
    OLD_HEURISTIC_HOURS = 7 * 24
    assert DEFAULT_ANNOUNCEMENT_FLOOR_HOURS > OLD_HEURISTIC_HOURS


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
