"""Unit tests for the availability_semantics SSOT module."""

from __future__ import annotations

import pytest

from unified_api_contracts.canonical.crosscutting.availability_semantics import (
    AVAILABILITY_AT_SEMANTICS,
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
