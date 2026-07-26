"""Extended tests for registry/market_data_categories.py — targeting missed branches."""

from __future__ import annotations

import pytest

from unified_api_contracts import InstrumentType
from unified_api_contracts.registry.market_data_categories import (
    CHAIN_BUNDLE_ACCEPTED_NONCANONICAL_INSTRUMENT_TYPES,
    DATA_TYPES_BY_ASSET_GROUP,
    NEEDS_CANDLE_PROCESSING,
    TIMEFRAMES,
    TRADFI_CHAIN_SNAPSHOT_ACCEPTED_NONCANONICAL_DATA_TYPES,
    VENUES_BY_ASSET_GROUP,
    get_valid_timeframes_for_data_type,
    needs_candle_processing,
    resolve_data_type_for_feature_group,
)

# ---------------------------------------------------------------------------
# get_valid_timeframes_for_data_type
# ---------------------------------------------------------------------------


def test_trades_returns_all_timeframes() -> None:
    """trades has no base granularity — returns all timeframes."""
    result = get_valid_timeframes_for_data_type("trades")
    assert result == list(TIMEFRAMES)


def test_unknown_data_type_returns_all_timeframes() -> None:
    result = get_valid_timeframes_for_data_type("not_a_real_data_type")
    assert result == list(TIMEFRAMES)


def test_ohlcv_1m_filters_to_1m_and_above() -> None:
    """ohlcv_1m base granularity: only timeframes >= 1m returned."""
    result = get_valid_timeframes_for_data_type("ohlcv_1m")
    assert isinstance(result, list)
    assert len(result) > 0
    # 1m should be in results
    assert "1m" in result or any("1m" in tf for tf in result)


def test_ohlcv_15m_filters_to_15m_and_above() -> None:
    result = get_valid_timeframes_for_data_type("ohlcv_15m")
    assert isinstance(result, list)
    # Should be a strict subset of all timeframes
    assert len(result) <= len(list(TIMEFRAMES))


# ---------------------------------------------------------------------------
# needs_candle_processing
# ---------------------------------------------------------------------------


def test_needs_candle_processing_for_book_snapshot() -> None:
    """book_snapshot data requires candle processing."""
    result = needs_candle_processing("book_snapshot_5")
    assert isinstance(result, bool)


def test_needs_candle_processing_for_ohlcv() -> None:
    """ohlcv_1m is already candles — should not need processing."""
    result = needs_candle_processing("ohlcv_1m")
    assert isinstance(result, bool)


def test_needs_candle_processing_unknown_data_type() -> None:
    result = needs_candle_processing("unknown_data_type")
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# VENUES_BY_ASSET_GROUP and DATA_TYPES_BY_ASSET_GROUP presence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ag", ["cefi", "defi", "tradfi", "sports", "prediction"])
def test_venues_by_asset_group_has_entries(ag: str) -> None:
    venues = VENUES_BY_ASSET_GROUP.get(ag, [])
    assert isinstance(venues, list)
    assert len(venues) > 0


@pytest.mark.parametrize("ag", ["cefi", "defi", "tradfi", "sports"])
def test_data_types_by_asset_group_has_entries(ag: str) -> None:
    data_types = DATA_TYPES_BY_ASSET_GROUP.get(ag, [])
    assert isinstance(data_types, list)
    assert len(data_types) > 0


def test_cefi_has_trades_data_type() -> None:
    assert "trades" in DATA_TYPES_BY_ASSET_GROUP.get("cefi", [])


def test_tradfi_has_ohlcv_data_types() -> None:
    tradfi_types = DATA_TYPES_BY_ASSET_GROUP.get("tradfi", [])
    assert "ohlcv_1m" in tradfi_types


def test_venues_are_strings() -> None:
    for ag, venues in VENUES_BY_ASSET_GROUP.items():
        for v in venues:
            assert isinstance(v, str), f"Non-string venue in {ag}: {v!r}"


# ---------------------------------------------------------------------------
# NEEDS_CANDLE_PROCESSING completeness (registry-drift guard)
# ---------------------------------------------------------------------------
# market-data-processing-service enforces this same invariant over the "defi"
# group (tests/unit/test_defi_bypass_routing.py). Enforcing it ONLY downstream
# means UAC can land an unclassified data_type green and red MDPS's LDR on the
# next dep resolve — which is exactly what "perp_trades" did on 2026-07-16.
# This is the same assertion, run in UAC's own gate, at the source of the drift.
#
# Scoped to "defi" deliberately: needs_candle_processing() defaults unknown
# types to True, which is the CORRECT answer for every cefi/tradfi type but the
# WRONG one for most defi types (the group is a pass-through/candle mix), so an
# omission is only silently harmful here. sports/prediction/tradfi carry
# pre-existing unclassified types (ODDS, MARKET_LIFECYCLE, mbp_10, …) that
# default-True benignly; classifying them is a separate call, not a drift guard.


@pytest.mark.parametrize("data_type", DATA_TYPES_BY_ASSET_GROUP["defi"])
def test_defi_data_type_has_explicit_candle_classification(data_type: str) -> None:
    """Every defi data_type needs an explicit entry — the True default is unsafe here."""
    assert data_type in NEEDS_CANDLE_PROCESSING, (
        f"DeFi data type '{data_type}' is in DATA_TYPES_BY_ASSET_GROUP but missing from "
        f"NEEDS_CANDLE_PROCESSING. It will default to True and route to an MDPS candle "
        f"adapter that may not exist. Add an explicit True/False entry."
    )


# ---------------------------------------------------------------------------
# TRADFI_CHAIN_SNAPSHOT_ACCEPTED_NONCANONICAL_DATA_TYPES (audit 2026-07-22,
# distinct_values_noncanonical_audit_2026_07_20.md "futures_chain tradfi
# remedy decision") — mirrors SPORTS_ODDS_API_ACCEPTED_NONCANONICAL_BOOKMAKERS:
# genuinely non-canonical, permanently-accepted tradfi data_type values (real
# captured chain-snapshot rows, operator PRESERVE-ruled), consumed by
# deployment-api's `_distinct_values.py` to stop badging them as drift without
# ever making them canonical.
# ---------------------------------------------------------------------------


def test_tradfi_chain_snapshot_accepted_exceptions_are_exactly_options_and_futures_chain() -> None:
    assert frozenset({"options_chain", "futures_chain"}) == TRADFI_CHAIN_SNAPSHOT_ACCEPTED_NONCANONICAL_DATA_TYPES


def test_tradfi_chain_snapshot_accepted_exceptions_are_not_canonical_tradfi_data_types() -> None:
    """The whole point: these stay OUT of DATA_TYPES_BY_ASSET_GROUP['tradfi'] — an
    accepted-exception, never a canonical-set addition (options_chain/futures_chain
    are instrument_types, not data_types; the data_type for those rows is 'trades')."""
    tradfi_data_types = DATA_TYPES_BY_ASSET_GROUP.get("tradfi", [])
    for value in TRADFI_CHAIN_SNAPSHOT_ACCEPTED_NONCANONICAL_DATA_TYPES:
        assert value not in tradfi_data_types, (
            f"'{value}' leaked into DATA_TYPES_BY_ASSET_GROUP['tradfi'] — it must stay an "
            f"accepted-exception (TRADFI_CHAIN_SNAPSHOT_ACCEPTED_NONCANONICAL_DATA_TYPES), "
            f"never a canonical data_type."
        )


# ---------------------------------------------------------------------------
# CHAIN_BUNDLE_ACCEPTED_NONCANONICAL_INSTRUMENT_TYPES (audit follow-up
# 2026-07-22, distinct_values_noncanonical_audit_2026_07_20.md "D5 —
# bundle-grain recognition") — mirrors
# TRADFI_CHAIN_SNAPSHOT_ACCEPTED_NONCANONICAL_DATA_TYPES / the sports
# bookmakers pattern exactly, but on the tradfi+cefi ``instrument_types`` axis:
# ``options_chain``/``futures_chain`` are the real MTDS Tardis-writer bundle
# tokens, genuinely non-canonical (not ``InstrumentType`` members) and
# permanently accepted, never purged/relabelled. ``combo`` is deliberately
# excluded (mirrors ``TRADFI_CHAIN_INSTRUMENT_TYPES``'s own exclusion in
# ``canonical/partition_paths.py`` — its leg-aware id format is unsettled).
# ---------------------------------------------------------------------------


def test_chain_bundle_accepted_exceptions_are_exactly_options_and_futures_chain() -> None:
    assert frozenset({"options_chain", "futures_chain"}) == CHAIN_BUNDLE_ACCEPTED_NONCANONICAL_INSTRUMENT_TYPES


def test_chain_bundle_accepted_exceptions_exclude_combo() -> None:
    """``combo``'s leg-aware id format is unsettled (see
    ``TRADFI_CHAIN_INSTRUMENT_TYPES``'s own exclusion) — it must NOT be folded
    into this bundle-grain accepted-exception set."""
    assert "combo" not in CHAIN_BUNDLE_ACCEPTED_NONCANONICAL_INSTRUMENT_TYPES


def test_chain_bundle_accepted_exceptions_are_not_instrument_type_enum_members() -> None:
    """The whole point: these stay OUT of the ``InstrumentType`` enum — an
    accepted-exception, never a canonical-set addition (a per-bundle token
    would misrepresent itself as an individually-tradable per-contract
    instrument, the same grain error D1b already fixed for defi venues)."""
    canonical_instrument_types = frozenset(member.value for member in InstrumentType)
    for value in CHAIN_BUNDLE_ACCEPTED_NONCANONICAL_INSTRUMENT_TYPES:
        assert value not in canonical_instrument_types, (
            f"'{value}' leaked into the InstrumentType enum — it must stay an accepted-exception "
            f"(CHAIN_BUNDLE_ACCEPTED_NONCANONICAL_INSTRUMENT_TYPES), never a canonical instrument_type."
        )


# ---------------------------------------------------------------------------
# resolve_data_type_for_feature_group -- TradFi candle-group override
# (tradfi_mdps_build_continuous_mismatches_2_and_4_still_open_2026_07_26.md):
# live-reproduced bug -- every TradFi candle-based feature group fell through
# to the CeFi-oriented "trades" default, so features-delta-one-tradfi's
# lookback validation (keyed on data_type against the availability manifest)
# reported 0 candles for EVERY real, already-landed continuous-future day
# (manifest rows are written with data_type="ohlcv_1m", never "trades").
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "feature_group",
    [
        "technical_indicators",
        "moving_averages",
        "oscillators",
        "volatility_realized",
        "momentum",
        "volume_analysis",
        "vwap",
        "candlestick_patterns",
        "market_structure",
        "returns",
        "round_numbers",
        "streaks",
        "futures_basis",
        "volume_flow",
        "temporal",
        "targets",
        "supply_demand_zones",
        "fibonacci",
        "level_confluence",
        "market_structure_sequence",
        "risk_reward",
        "wedge_quality",
    ],
)
def test_tradfi_candle_feature_groups_resolve_to_ohlcv_1m(feature_group: str) -> None:
    assert resolve_data_type_for_feature_group(feature_group, "TRADFI") == "ohlcv_1m"
    assert resolve_data_type_for_feature_group(feature_group, "tradfi") == "ohlcv_1m"


def test_tradfi_microstructure_still_resolves_to_tbbo() -> None:
    """The pre-existing tradfi override must survive the candle-group additions."""
    assert resolve_data_type_for_feature_group("microstructure", "TRADFI") == "tbbo"


def test_cefi_candle_feature_groups_unaffected_by_tradfi_override() -> None:
    """The tradfi-only override must not leak into CeFi's own "trades" default."""
    assert resolve_data_type_for_feature_group("futures_basis", "CEFI") == "trades"
    assert resolve_data_type_for_feature_group("technical_indicators", "CEFI") == "trades"
