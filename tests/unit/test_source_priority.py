"""Unit tests for the source_priority SSOT module."""

from __future__ import annotations

import pytest

from unified_api_contracts.canonical.crosscutting.availability_semantics import (
    AVAILABILITY_AT_SEMANTICS,
)
from unified_api_contracts.canonical.crosscutting.source_priority import (
    EMISSION_LATENCY_MS_BY_SOURCE,
    SOURCE_PRIORITY,
    assert_emission_latency_round_trip,
    emission_latency_ms_for_source,
    get_primary_source,
    get_primary_source_with_latency,
    get_source_priority,
    has_source_priority,
)

# ---------------------------------------------------------------------------
# Sports primary sources
# ---------------------------------------------------------------------------


def test_sports_fixtures_primary_is_api_football() -> None:
    assert get_primary_source("sports", "FIXTURES") == "api_football"


def test_sports_understat_xg_primary_is_understat() -> None:
    assert get_primary_source("sports", "UNDERSTAT_XG") == "understat"


def test_sports_sfi_progressive_primary_is_sfi() -> None:
    assert get_primary_source("sports", "SFI_PROGRESSIVE_STATS") == "soccer_football_info"


def test_sports_odds_primary_is_odds_api() -> None:
    assert get_primary_source("sports", "ODDS_SNAPSHOT") == "odds_api"


def test_sports_weather_primary_is_open_meteo() -> None:
    assert get_primary_source("sports", "WEATHER_FORECAST") == "open_meteo"


def test_sports_player_values_primary_is_transfermarkt() -> None:
    assert get_primary_source("sports", "PLAYER_VALUES") == "transfermarkt"


# ---------------------------------------------------------------------------
# Market-data primary sources
# ---------------------------------------------------------------------------


def test_cefi_primary_is_tardis() -> None:
    assert get_primary_source("cefi", "trades") == "tardis"
    assert get_primary_source("cefi", "options_chain") == "tardis"


def test_tradfi_primary_is_databento() -> None:
    assert get_primary_source("tradfi", "trades") == "databento"
    assert get_primary_source("tradfi", "options_chain") == "databento"


def test_prediction_primary_is_polymarket_clob() -> None:
    assert get_primary_source("prediction", "trades") == "polymarket_clob"


def test_defi_primary_is_onchain_subgraph_or_rpc() -> None:
    assert get_primary_source("defi", "swap") == "onchain_subgraph"
    assert get_primary_source("defi", "gas_fees") == "onchain_rpc"


# ---------------------------------------------------------------------------
# Failure mode
# ---------------------------------------------------------------------------


def test_unregistered_pair_raises_keyerror() -> None:
    with pytest.raises(KeyError, match="No source priority registered"):
        get_source_priority("cefi", "totally_made_up_data_type")


def test_get_primary_source_raises_on_unregistered() -> None:
    with pytest.raises(KeyError):
        get_primary_source("alien", "trades")


# ---------------------------------------------------------------------------
# has_source_priority
# ---------------------------------------------------------------------------


def test_has_source_priority_returns_true_for_registered() -> None:
    assert has_source_priority("sports", "FIXTURE_LINEUPS") is True


def test_has_source_priority_returns_false_for_unregistered() -> None:
    assert has_source_priority("cefi", "made_up") is False


# ---------------------------------------------------------------------------
# Returned-list mutation safety
# ---------------------------------------------------------------------------


def test_get_source_priority_returns_copy_not_reference() -> None:
    """Mutating the returned list must NOT mutate the registry."""
    sources = get_source_priority("cefi", "trades")
    sources.append("malicious_injection")
    fresh = get_source_priority("cefi", "trades")
    assert "malicious_injection" not in fresh


# ---------------------------------------------------------------------------
# Registry shape
# ---------------------------------------------------------------------------


def test_registry_keys_are_two_string_tuples() -> None:
    for key in SOURCE_PRIORITY:
        assert isinstance(key, tuple)
        assert len(key) == 2
        assert isinstance(key[0], str)
        assert isinstance(key[1], str)


def test_every_value_is_non_empty_list_of_strings() -> None:
    for key, sources in SOURCE_PRIORITY.items():
        assert isinstance(sources, list), f"{key} value is not a list"
        assert len(sources) > 0, f"{key} has empty source list"
        for src in sources:
            assert isinstance(src, str)
            assert src, f"{key} has empty source string"


def test_registry_has_minimum_seed_size() -> None:
    assert len(SOURCE_PRIORITY) >= 30


# ---------------------------------------------------------------------------
# Cross-module consistency: availability_semantics + source_priority
# ---------------------------------------------------------------------------


def test_every_availability_semantic_pair_has_source_priority() -> None:
    """If a (asset_group, data_type) pair is in AVAILABILITY_AT_SEMANTICS, it
    must also be in SOURCE_PRIORITY — the pipeline can't stamp ``available_at``
    without knowing which source's emission time defines it.
    """
    missing: list[tuple[str, str]] = []
    for key in AVAILABILITY_AT_SEMANTICS:
        if key not in SOURCE_PRIORITY:
            missing.append(key)
    assert not missing, f"{len(missing)} pairs have availability semantic but no source priority: {missing[:10]}"


def test_every_source_priority_pair_has_availability_semantic() -> None:
    """Inverse: every source-priority pair must have a stamping semantic."""
    missing: list[tuple[str, str]] = []
    for key in SOURCE_PRIORITY:
        if key not in AVAILABILITY_AT_SEMANTICS:
            missing.append(key)
    assert not missing, f"{len(missing)} pairs have source priority but no availability semantic: {missing[:10]}"


# ---------------------------------------------------------------------------
# Emission-latency registry — F2-v2 prerequisite for available_at stamping
# ---------------------------------------------------------------------------


def test_emission_latency_round_trip() -> None:
    """Closed-set: every source in SOURCE_PRIORITY has a latency entry, and vice versa."""
    assert_emission_latency_round_trip()


def test_emission_latency_ms_for_known_source() -> None:
    assert emission_latency_ms_for_source("tardis") == 50
    assert emission_latency_ms_for_source("databento") == 10
    assert emission_latency_ms_for_source("api_football") == 1_000


def test_emission_latency_ms_for_unknown_source_raises() -> None:
    with pytest.raises(KeyError, match="No emission latency registered"):
        emission_latency_ms_for_source("nonexistent_source")


def test_emission_latency_values_are_positive_int_under_one_day() -> None:
    """Sanity bounds: latencies are non-negative ints under 24h (86_400_000ms)."""
    one_day_ms = 86_400_000
    for source, latency in EMISSION_LATENCY_MS_BY_SOURCE.items():
        assert isinstance(latency, int), f"{source} latency is not an int: {type(latency)}"
        assert latency >= 0, f"{source} latency is negative: {latency}"
        assert latency <= one_day_ms, f"{source} latency exceeds 24h: {latency}"


def test_get_primary_source_with_latency_for_cefi_trades() -> None:
    source, latency_ms = get_primary_source_with_latency("cefi", "trades")
    assert source == "tardis"
    assert latency_ms == 50


def test_get_primary_source_with_latency_for_sports_fixtures() -> None:
    source, latency_ms = get_primary_source_with_latency("sports", "FIXTURES")
    assert source == "api_football"
    assert latency_ms == 1_000


def test_get_primary_source_with_latency_for_prediction_trades() -> None:
    source, latency_ms = get_primary_source_with_latency("prediction", "trades")
    assert source == "polymarket_clob"
    assert latency_ms == 200


def test_get_primary_source_with_latency_unknown_pair_raises() -> None:
    with pytest.raises(KeyError, match="No source priority registered"):
        get_primary_source_with_latency("nonexistent_asset_group", "nonexistent_data_type")
