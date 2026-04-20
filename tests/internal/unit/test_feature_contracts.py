"""Unit tests for features SchemaContracts (Phase 5c.1).

Data plan: ``data_pipeline_completion_2026_04_18`` §Phase 5c. Verifies
contracts are registered for every feature_group the eight feature services
emit, and that core shard columns (instrument_id, venue, ts_event,
ts_event_out, feature_group, timeframe) are present on every one.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.internal.schemas._feature_contracts import (
    CALENDAR_FEATURE_GROUPS,
    COMMODITY_FEATURE_GROUPS,
    CROSS_INSTRUMENT_FEATURE_GROUPS,
    DELTA_ONE_FEATURE_GROUPS,
    MULTI_TIMEFRAME_FEATURE_GROUPS,
    ONCHAIN_FEATURE_GROUPS,
    SPORTS_FEATURE_GROUPS,
    VOLATILITY_FEATURE_GROUPS,
)
from unified_api_contracts.internal.schemas.contracts import (
    CONTRACT_REGISTRY,
    lookup_contract,
)

# Columns every feature contract must declare.
_REQUIRED_CORE = {
    "instrument_id",
    "venue",
    "ts_event",
    "ts_event_out",
    "feature_group",
    "timeframe",
}


def _has_core(contract_cols: list[str]) -> bool:
    return _REQUIRED_CORE.issubset(set(contract_cols))


# ---------------------------------------------------------------------------
# Per-service coverage
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fg", DELTA_ONE_FEATURE_GROUPS)
def test_delta_one_registered_for_cefi_perpetual(fg: str) -> None:
    contract = lookup_contract(category="cefi", instrument_type="perpetual", data_type=fg)
    assert contract.symbol_column == "symbol"
    assert _has_core([c.name for c in contract.columns])


@pytest.mark.parametrize("fg", DELTA_ONE_FEATURE_GROUPS)
def test_delta_one_registered_for_tradfi_future(fg: str) -> None:
    contract = lookup_contract(category="tradfi", instrument_type="future", data_type=fg)
    assert contract.symbol_column == "symbol"


@pytest.mark.parametrize("fg", VOLATILITY_FEATURE_GROUPS)
def test_volatility_registered_for_cefi_options(fg: str) -> None:
    contract = lookup_contract(category="cefi", instrument_type="options_chain", data_type=fg)
    assert contract.symbol_column == "underlying"


@pytest.mark.parametrize("fg", VOLATILITY_FEATURE_GROUPS)
def test_volatility_registered_for_tradfi_options(fg: str) -> None:
    contract = lookup_contract(category="tradfi", instrument_type="options_chain", data_type=fg)
    assert contract.symbol_column == "underlying"


@pytest.mark.parametrize(
    "fg",
    [
        "aave_lending_rates",
        "aave_utilization",
        "aave_risk_params",
        "aave_rate_impact",
        "flash_loan_availability",
    ],
)
def test_onchain_aave_registered_for_a_token(fg: str) -> None:
    contract = lookup_contract(category="defi", instrument_type="a_token", data_type=fg)
    assert contract.symbol_column == "token"
    assert "chain" in {c.name for c in contract.columns}


def test_onchain_lst_staking_yields_registered_for_lst() -> None:
    contract = lookup_contract(category="defi", instrument_type="lst", data_type="lst_staking_yields")
    assert "chain" in {c.name for c in contract.columns}


def test_onchain_fear_greed_registered_for_spot_asset() -> None:
    contract = lookup_contract(category="defi", instrument_type="spot_asset", data_type="fear_greed")
    assert contract.symbol_column == "symbol"


@pytest.mark.parametrize("fg", SPORTS_FEATURE_GROUPS)
def test_sports_registered(fg: str) -> None:
    contract = lookup_contract(category="sports", instrument_type="odds", data_type=fg)
    assert contract.symbol_column == "fixture_id"
    assert _has_core([c.name for c in contract.columns])


@pytest.mark.parametrize("fg", CALENDAR_FEATURE_GROUPS)
def test_calendar_registered_for_tradfi_index(fg: str) -> None:
    contract = lookup_contract(category="tradfi", instrument_type="index", data_type=fg)
    assert contract.symbol_column == "symbol"


@pytest.mark.parametrize("fg", MULTI_TIMEFRAME_FEATURE_GROUPS)
def test_multi_timeframe_registered_for_cefi_perpetual(fg: str) -> None:
    contract = lookup_contract(category="cefi", instrument_type="perpetual", data_type=fg)
    assert _has_core([c.name for c in contract.columns])


@pytest.mark.parametrize("fg", CROSS_INSTRUMENT_FEATURE_GROUPS)
def test_cross_instrument_registered_for_cefi_perpetual(fg: str) -> None:
    contract = lookup_contract(category="cefi", instrument_type="perpetual", data_type=fg)
    assert _has_core([c.name for c in contract.columns])


def test_cross_instrument_polymarket_scoped_to_prediction() -> None:
    contract = lookup_contract(
        category="prediction",
        instrument_type="prediction_market",
        data_type="polymarket_crowd_sentiment",
    )
    assert contract.symbol_column == "condition_id"
    assert "chain" in {c.name for c in contract.columns}


@pytest.mark.parametrize("fg", COMMODITY_FEATURE_GROUPS)
def test_commodity_registered_for_tradfi_future(fg: str) -> None:
    contract = lookup_contract(category="tradfi", instrument_type="future", data_type=fg)
    assert contract.symbol_column == "symbol"


# ---------------------------------------------------------------------------
# Invariant — every feature contract carries the shared core
# ---------------------------------------------------------------------------


def test_every_feature_contract_has_core_columns() -> None:
    """A feature contract has the core column set; market-tick/MDPS contracts
    that happen to share a ``data_type`` name with a feature group (e.g.
    ``liquidations``) are distinguished by missing the ``feature_group`` +
    ``ts_event_out`` core columns — we detect them by column membership and
    skip them."""
    all_feature_groups = (
        set(DELTA_ONE_FEATURE_GROUPS)
        | set(VOLATILITY_FEATURE_GROUPS)
        | set(ONCHAIN_FEATURE_GROUPS)
        | set(SPORTS_FEATURE_GROUPS)
        | set(CALENDAR_FEATURE_GROUPS)
        | set(MULTI_TIMEFRAME_FEATURE_GROUPS)
        | set(CROSS_INSTRUMENT_FEATURE_GROUPS)
        | set(COMMODITY_FEATURE_GROUPS)
    )
    for (category, itype, dt), contract in CONTRACT_REGISTRY.items():
        if dt not in all_feature_groups:
            continue
        names = [c.name for c in contract.columns]
        # Non-feature contracts may share a data_type name — they lack
        # ``feature_group`` / ``ts_event_out`` so we treat them as non-feature.
        if "feature_group" not in names and "ts_event_out" not in names:
            continue
        assert _has_core(names), f"feature contract {(category, itype, dt)} missing core column(s): {names}"


def test_total_feature_contract_count_reasonable() -> None:
    """Sanity: >=300 feature contracts registered (8 services x avg 40 (category x instrument_type x feature_group))."""
    all_feature_groups = (
        set(DELTA_ONE_FEATURE_GROUPS)
        | set(VOLATILITY_FEATURE_GROUPS)
        | set(ONCHAIN_FEATURE_GROUPS)
        | set(SPORTS_FEATURE_GROUPS)
        | set(CALENDAR_FEATURE_GROUPS)
        | set(MULTI_TIMEFRAME_FEATURE_GROUPS)
        | set(CROSS_INSTRUMENT_FEATURE_GROUPS)
        | set(COMMODITY_FEATURE_GROUPS)
    )
    registered = [
        k
        for k, contract in CONTRACT_REGISTRY.items()
        if k[2] in all_feature_groups and any(c.name == "feature_group" for c in contract.columns)
    ]
    assert len(registered) >= 300, f"only {len(registered)} feature contracts registered"
