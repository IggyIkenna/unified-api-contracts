"""Unit tests for the source_priority SSOT module."""

from __future__ import annotations

import pytest

from unified_api_contracts.canonical.crosscutting.availability_semantics import (
    AVAILABILITY_AT_SEMANTICS,
)
from unified_api_contracts.canonical.crosscutting.source_priority import (
    COMPUTED_SOURCES,
    EMISSION_LATENCY_MS_BY_SOURCE,
    SOURCE_PRIORITY,
    assert_emission_latency_round_trip,
    default_source,
    emission_latency_ms_for_source,
    external_sources_for,
    get_primary_source,
    get_primary_source_with_latency,
    get_source_priority,
    has_source_priority,
    source_required,
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


def test_tradfi_primary_is_massive() -> None:
    """MASSIVE-FIRST per operator ratification 2026-06-11 (MVP catalogue
    completion); databento is the secondary/resilience source."""
    assert get_primary_source("tradfi", "trades") == "massive"
    assert get_primary_source("tradfi", "options_chain") == "massive"


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
# source_required — registry-driven multi-source gate
# (data_source_provenance_all_asset_groups_2026_06_01.md Phase 1)
# ---------------------------------------------------------------------------


def test_source_required_true_for_tradfi_multi_source() -> None:
    """TradFi trades has databento + massive → source required."""
    assert source_required("tradfi", "trades") is True
    assert source_required("tradfi", "ohlcv_15m") is True


def test_source_required_true_for_defi_multi_source() -> None:
    """DeFi oracle_prices / native_staking_rates are multi-source → required."""
    assert source_required("defi", "oracle_prices") is True
    assert source_required("defi", "native_staking_rates") is True


def test_source_required_true_for_sports_multi_source() -> None:
    """Sports FIXTURES has api_football + footystats → source required."""
    assert source_required("sports", "FIXTURES") is True


def test_source_required_false_for_single_source_cells() -> None:
    """Single-entry SOURCE_PRIORITY lists → no source required."""
    assert source_required("defi", "swap") is False
    assert source_required("cefi", "trades") is False
    assert source_required("sports", "FIXTURE_EVENTS") is False


def test_source_required_true_for_prediction_multi_source() -> None:
    """Prediction trades/book are multi-source (polymarket_clob + kalshi) since the Kalshi source
    registration — the writer cannot auto-disambiguate, so an explicit source stamp is REQUIRED.
    The single-source MARKET_LIFECYCLE cell (polymarket_gamma_api) stays auto-stampable."""
    assert source_required("prediction", "trades") is True
    assert source_required("prediction", "book_snapshot") is True
    assert source_required("prediction", "MARKET_LIFECYCLE") is False


def test_source_required_false_for_unregistered_pair() -> None:
    """Unregistered pairs are not gated by source_required (non-raising)."""
    assert source_required("defi", "made_up_data_type") is False
    assert source_required("cefi", "made_up") is False


def test_source_required_matches_external_cardinality() -> None:
    """source_required True iff the cell has >1 *external* source — exhaustive."""
    for asset_group, data_type in SOURCE_PRIORITY:
        external = external_sources_for(asset_group, data_type)
        assert source_required(asset_group, data_type) is (len(external) > 1)


# ---------------------------------------------------------------------------
# COMPUTED_SOURCES exemption + external_sources_for
# ---------------------------------------------------------------------------


def test_computed_sources_are_exempt_from_external() -> None:
    """Computed/service emitters are filtered out of external_sources_for."""
    # execution_fills / hedge_ratio_snapshot etc. have a computed source only.
    assert external_sources_for("defi", "execution_fills") == []
    assert external_sources_for("defi", "hedge_ratio_snapshot") == []
    assert external_sources_for("defi", "feature_observation_snapshot") == []
    assert external_sources_for("defi", "cross_instrument_signal") == []


def test_external_sources_for_external_vendors() -> None:
    """External-vendor cells return their full source list."""
    assert external_sources_for("cefi", "trades") == ["tardis"]
    assert external_sources_for("defi", "oracle_prices") == ["pyth_hermes", "chainlink"]
    assert external_sources_for("prediction", "trades") == ["polymarket_clob", "kalshi"]


def test_computed_cells_not_source_required() -> None:
    """Computed/service-only cells are exempt from the source gate."""
    assert source_required("defi", "execution_fills") is False
    assert source_required("defi", "hedge_ratio_snapshot") is False
    assert source_required("cefi", "execution_fills") is False


# ---------------------------------------------------------------------------
# default_source — universal-stamping auto-fill for single external-source cells
# ---------------------------------------------------------------------------


def test_default_source_single_external_returns_that_source() -> None:
    assert default_source("cefi", "trades") == "tardis"
    assert default_source("defi", "swap") == "onchain_subgraph"
    # Prediction MARKET_LIFECYCLE stays single-source (Gamma metadata); trades/cqg are now multi-source.
    assert default_source("prediction", "MARKET_LIFECYCLE") == "polymarket_gamma_api"


def test_default_source_multi_external_returns_none() -> None:
    """Multi external-source cells cannot be auto-stamped (ambiguous)."""
    assert default_source("tradfi", "trades") is None
    assert default_source("defi", "oracle_prices") is None
    assert default_source("prediction", "trades") is None  # polymarket_clob + kalshi
    assert default_source("sports", "FIXTURES") is None


def test_default_source_computed_and_unregistered_return_none() -> None:
    assert default_source("defi", "execution_fills") is None  # computed → exempt
    assert default_source("defi", "made_up_data_type") is None  # unregistered


def test_computed_sources_membership() -> None:
    """The exempt set names the internal service emitters (not external vendors)."""
    assert "execution_service" in COMPUTED_SOURCES
    assert "strategy_service" in COMPUTED_SOURCES
    assert "tardis" not in COMPUTED_SOURCES
    assert "databento" not in COMPUTED_SOURCES


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
