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
    is_valid_manifest_source,
    source_required,
    valid_manifest_sources,
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
    """DATABENTO-FIRST (2026-06-24, supersedes the 2026-06-11 massive-first): databento
    is the verified-complete primary for the live MVP universe (Binance tradfi-perp
    basis tickers + CME futures + CFE); massive is the fallback + bulk-backfill path."""
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
# Finding-77 (2026-07-13 operator ruling, option A / narrowed scope) —
# (HYPERLIQUID, liquidations) SOURCE_PRIORITY removal
# (plans/active/issues/fleet_data_acquisition_health_2026_06_21.md)
# ---------------------------------------------------------------------------


def test_cefi_liquidations_excludes_hyperliquid_finding77() -> None:
    """Hyperliquid does not publish a liquidations feed (no S3 prefix, no Tardis
    channel — VENUE_DATA_TYPE_CAPABILITIES["HYPERLIQUID"] has no ``liquidations``
    key), so it was removed from ``("cefi", "liquidations")``. tardis/aster/extended
    (real feeds) stay registered — the pair itself is NOT deregistered, it simply
    resolves without hyperliquid, so consumers get an ordinary (non-empty) source
    list rather than a crash."""
    assert get_source_priority("cefi", "liquidations") == ["tardis", "aster", "extended"]
    assert "hyperliquid" not in get_source_priority("cefi", "liquidations")
    # The pair stays registered (has_source_priority does NOT flip to False) —
    # "no-source" applies only to the hyperliquid vendor, not the whole cell.
    assert has_source_priority("cefi", "liquidations") is True


def test_cefi_book_liq_pairs_kept_by_finding77_narrowed_ruling() -> None:
    """The other three pairs finding-77 originally targeted are REAL, wired,
    tested feeds (uac@3652f99f + the pre-existing HYPERLIQUID book_snapshot_5 S3
    archive) and were explicitly kept by the 2026-07-13 ruling: (ASTER,
    book_snapshot_5), (ASTER, liquidations), (HYPERLIQUID, book_snapshot_5).
    Regression guard against a future over-broad removal sweep."""
    assert "aster" in get_source_priority("cefi", "book_snapshot")
    assert "hyperliquid" in get_source_priority("cefi", "book_snapshot")
    assert "aster" in get_source_priority("cefi", "liquidations")


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
    # (cefi,trades) is multi-source now (hyperliquid/aster); options_chain stays single.
    assert source_required("cefi", "options_chain") is False
    assert source_required("sports", "FIXTURE_EVENTS") is False


def test_source_required_true_for_prediction_multi_source() -> None:
    """Prediction trades/book are multi-source (polymarket_clob + kalshi) since the Kalshi source
    registration — the writer cannot auto-disambiguate, so an explicit source stamp is REQUIRED.
    The single-source MARKET_LIFECYCLE cell (polymarket_gamma_api) stays auto-stampable."""
    assert source_required("prediction", "trades") is True
    assert source_required("prediction", "book_snapshot_5") is True
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
    assert external_sources_for("cefi", "trades") == [
        "tardis",
        "aster",
        "hyperliquid",
        "kalshi_perp",
        "polymarket_perp",
        "extended",
    ]  # HL/ASTER cefi onchain perps + kalshi_perp/polymarket_perp CFTC perp venues + EXTENDED-STARKNET
    # ("pacifica" removed 2026-07-16 — operator ruling: all Solana perp DEXes
    # dropped except Jupiter, not integrated.)
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
    assert default_source("cefi", "options_chain") == "tardis"  # (cefi,trades) multi-source now → no auto-stamp
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


# ---------------------------------------------------------------------------
# bug#14 — manifest WRITE-validation predicate (SOURCE_PRIORITY ∪ live-vendors)
# ---------------------------------------------------------------------------


def test_is_valid_manifest_source_accepts_cefi_cex_live_vendor() -> None:
    # bug#14: a CeFi CEX live capture stamps source=binance; binance is NOT in
    # the batch SOURCE_PRIORITY[("cefi","trades")] list but IS a live vendor.
    assert is_valid_manifest_source("cefi", "trades", "binance") is True
    assert "binance" not in get_source_priority("cefi", "trades")


def test_is_valid_manifest_source_accepts_all_cefi_cex_vendors() -> None:
    for vendor in ("binance", "okx", "bybit", "kraken", "deribit"):
        assert is_valid_manifest_source("cefi", "trades", vendor) is True


def test_is_valid_manifest_source_accepts_batch_priority_source() -> None:
    # tardis is the index-0 batch source — still valid for a write.
    assert is_valid_manifest_source("cefi", "trades", "tardis") is True


def test_is_valid_manifest_source_case_insensitive() -> None:
    assert is_valid_manifest_source("cefi", "trades", "BINANCE") is True
    assert is_valid_manifest_source("CEFI", "trades", "binance") is True


def test_is_valid_manifest_source_rejects_unknown_source() -> None:
    # An unregistered/unknown source still raises downstream (mis-stamp guard).
    assert is_valid_manifest_source("cefi", "trades", "madeup") is False


def test_is_valid_manifest_source_rejects_batch_only_non_member() -> None:
    # yahoo is batch-only and not a cefi source → not a valid cefi write source.
    assert is_valid_manifest_source("cefi", "trades", "yahoo") is False


def test_get_source_priority_cefi_trades_unchanged() -> None:
    # The batch read-priority list — 5 original sources + EXTENDED-STARKNET (2026-06-24).
    # (PACIFICA (Solana) was added 2026-07-12 and removed entirely 2026-07-16
    # — operator ruling: all Solana perp DEXes dropped except Jupiter, not
    # integrated.)
    assert get_source_priority("cefi", "trades") == [
        "tardis",
        "aster",
        "hyperliquid",
        "kalshi_perp",
        "polymarket_perp",
        "extended",
    ]


def test_valid_manifest_sources_is_superset_of_priority() -> None:
    batch = set(get_source_priority("cefi", "trades"))
    valid = valid_manifest_sources("cefi", "trades")
    assert batch <= valid
    # binance (live vendor) is in the valid write set but not the batch list.
    assert "binance" in valid and "binance" not in batch


def test_valid_manifest_sources_excludes_batch_only_live_vendor() -> None:
    # polymarket_gamma_api is batch-only → never added as a prediction live vendor.
    valid = valid_manifest_sources("prediction", "trades")
    assert "polymarket_gamma_api" not in valid
    # kalshi / polymarket_clob (the real prediction vendors) are valid.
    assert "kalshi" in valid and "polymarket_clob" in valid


def test_is_valid_manifest_source_tradfi_unaffected() -> None:
    # tradfi has no per-venue live-vendor override map → only batch sources valid.
    assert is_valid_manifest_source("tradfi", "trades", "databento") is True
    assert is_valid_manifest_source("tradfi", "trades", "massive") is True
    assert is_valid_manifest_source("tradfi", "trades", "binance") is False


# ---------------------------------------------------------------------------
# Cross-registry drift guard: SPORTS_DATA_TYPE_TO_SOURCE ↔ SOURCE_PRIORITY
#
# Regression guard for the 2026-06-25→07-15 ODDS split-brain: decision #6
# ("odds are MTDS-owned") stripped ("sports","ODDS") from SOURCE_PRIORITY +
# AVAILABILITY_AT_SEMANTICS + SPORTS_DATA_TYPE_TO_SOURCE as a "coherent unit"
# (8fb1f54f), the operator REVERSED it 2026-06-27, but the revert (c75101be)
# only restored SPORTS_DATA_TYPE_TO_SOURCE. The two registries then disagreed
# for 20 days: league_data said footystats owns ODDS, SOURCE_PRIORITY said the
# pair did not exist — silently disabling the UTL write-time mis-stamp guard
# (_writer_ingest.py gates it on has_source_priority) and making the IS
# expected-universe enumerator fall through to a non-canonical source.
# This class has recurred (TEAMS/STANDINGS drifted the same way 2026-06-25,
# ~137k mis-sourced/phantom rows). SSOT: codex/02-data/sports-data-types-catalog.md.
# ---------------------------------------------------------------------------


#: KNOWN split-brain pairs, quarantined so the guard can ship green while the
#: underlying naming question is ruled on. **This baseline only goes DOWN** — never
#: add to it to make a new drift pass (same convention as the DTZ/TID251 baselines).
#:
#: EMPTY as of 2026-07-15 — the one entry (PLAYER_STATS) was RECONCILED, not waived.
#: The naming question it was parked on is answered: PLAYER_STATS is canonical and
#: FIXTURE_PLAYER_STATS was a phantom (the GCS *entity* folder name, seeded into these
#: crosscutting registries at 106430c9 by analogy with its FIXTURE_* neighbours while
#: PLAYER_STATS already existed in SPORTS_DATA_TYPE_TO_SOURCE). Not a distinct grain:
#: the live IS sports index holds 219,508 PLAYER_STATS rows and ZERO
#: FIXTURE_PLAYER_STATS rows. The mis-stamp guard is now ON for IS PLAYER_STATS writes
#: and accepts what the enrichment path actually stamps (api_football). See
#: _source_priority_data.py ("sports","PLAYER_STATS") for the full diagnosis.
_KNOWN_SPORTS_REGISTRY_DRIFT: frozenset[str] = frozenset()


def test_every_sports_data_type_to_source_key_has_source_priority() -> None:
    """Every data_type the sports domain map claims a source for must be registered
    in SOURCE_PRIORITY — otherwise has_source_priority() is False and every gate
    keyed on it treats the pair as unowned/source-exempt.
    """
    from unified_api_contracts import SPORTS_DATA_TYPE_TO_SOURCE

    missing = [
        dt
        for dt in SPORTS_DATA_TYPE_TO_SOURCE
        if ("sports", dt) not in SOURCE_PRIORITY and dt not in _KNOWN_SPORTS_REGISTRY_DRIFT
    ]
    assert not missing, (
        f"{len(missing)} sports data_type(s) in SPORTS_DATA_TYPE_TO_SOURCE have NO "
        f"SOURCE_PRIORITY entry (registry split-brain): {sorted(missing)}"
    )


def test_known_sports_registry_drift_baseline_only_shrinks() -> None:
    """The quarantine list must not outlive the defect it documents.

    If a pair in _KNOWN_SPORTS_REGISTRY_DRIFT has been reconciled, delete it from the
    baseline (that is the only legal edit). This test fails when the baseline is stale,
    so the allowlist cannot silently become permanent.
    """
    from unified_api_contracts import SPORTS_DATA_TYPE_TO_SOURCE

    stale = [
        dt
        for dt in _KNOWN_SPORTS_REGISTRY_DRIFT
        if dt not in SPORTS_DATA_TYPE_TO_SOURCE or ("sports", dt) in SOURCE_PRIORITY
    ]
    assert not stale, f"reconciled — remove from _KNOWN_SPORTS_REGISTRY_DRIFT: {sorted(stale)}"


def test_sports_registries_agree_on_owning_source() -> None:
    """The domain map's source must be the SOURCE_PRIORITY primary for the pair.

    A disagreement (not just an absence) is how TEAMS/STANDINGS produced ~137k
    mis-sourced manifest rows: the writer raised MissingSourceError on the domain
    map's source because SOURCE_PRIORITY named a different one.
    """
    from unified_api_contracts import SPORTS_DATA_TYPE_TO_SOURCE

    disagreements: list[str] = []
    for dt, domain_source in SPORTS_DATA_TYPE_TO_SOURCE.items():
        key = ("sports", dt)
        if key not in SOURCE_PRIORITY:
            continue  # covered by the split-brain test above
        priority = SOURCE_PRIORITY[key]
        if domain_source not in priority:
            disagreements.append(
                f"{dt}: SPORTS_DATA_TYPE_TO_SOURCE={domain_source!r} not in SOURCE_PRIORITY={priority!r}"
            )
        elif priority[0] != domain_source:
            disagreements.append(
                f"{dt}: domain map says {domain_source!r} but SOURCE_PRIORITY primary is {priority[0]!r}"
            )
    assert not disagreements, "sports registry drift:\n  " + "\n  ".join(disagreements)


def test_sports_odds_is_footystats_owned_in_both_registries() -> None:
    """Pin the operator's 2026-06-27 ruling (#6 REVERSED) at the registry level.

    footystats' PREDICTIVE pre-match ODDS snapshot = instruments-service reference
    data. RAW bookmaker tick odds = odds_api/MTDS (ODDS_SNAPSHOT/ODDS_MOVEMENT/
    ARBITRAGE). They legitimately coexist — do NOT "unify" them.
    """
    from unified_api_contracts import SPORTS_DATA_TYPE_TO_SOURCE

    assert has_source_priority("sports", "ODDS") is True
    assert get_primary_source("sports", "ODDS") == "footystats"
    assert SPORTS_DATA_TYPE_TO_SOURCE["ODDS"] == "footystats"
    assert ("sports", "ODDS") in AVAILABILITY_AT_SEMANTICS
    # The MTDS raw-tick odds types stay odds_api-owned — the coexistence rule.
    assert get_primary_source("sports", "ODDS_SNAPSHOT") == "odds_api"
    assert get_primary_source("sports", "ODDS_MOVEMENT") == "odds_api"


def test_sports_odds_api_football_is_not_a_valid_odds_source() -> None:
    """api_football has no odds path in IS (get_odds() is a deprecated stub), so an
    api_football×ODDS manifest row is impossible by construction. With ODDS
    registered, the UTL write-time mis-stamp guard rejects it again.
    SSOT: codex/02-data/sports-data-source-coverage-matrix.md §4.
    """
    assert is_valid_manifest_source("sports", "ODDS", "footystats") is True
    assert is_valid_manifest_source("sports", "ODDS", "api_football") is False
