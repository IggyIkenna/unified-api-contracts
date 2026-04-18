"""Unit tests for SPORTS_ODDS_TRADES + PREDICTION_PREDICTION_MARKET_TRADES SchemaContracts.

Phase 1.1 + 1.2 of data_pipeline_completion_2026_04_18. Verifies
``lookup_contract`` returns the expected contract, that the declared column
list + ``symbol_column`` match the plan spec, and that the
``CONTRACT_REGISTRY`` entry is populated by the side-effect import from
``_sports_prediction_contracts``.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from unified_api_contracts.internal.schemas.contracts import (
    CONTRACT_REGISTRY,
    PREDICTION_PREDICTION_MARKET_TRADES,
    SPORTS_ODDS_TRADES,
    lookup_contract,
    validate_dataframe,
)

# ---------------------------------------------------------------------------
# SPORTS_ODDS_TRADES
# ---------------------------------------------------------------------------


def test_sports_odds_trades_registered_in_contract_registry() -> None:
    contract = CONTRACT_REGISTRY[("sports", "odds", "trades")]
    assert contract is SPORTS_ODDS_TRADES


def test_sports_odds_trades_lookup_returns_contract() -> None:
    contract = lookup_contract(category="sports", instrument_type="odds", data_type="trades")
    assert contract is SPORTS_ODDS_TRADES


def test_sports_odds_trades_symbol_column_is_fixture_id() -> None:
    """Sports contracts key on ``fixture_id`` — not ``symbol``, not ``venue``.

    ``venue`` is the bookmaker (BET365/PINNACLE/BETFAIR) and is a shard
    dimension. ``fixture_id`` is the per-row instrument id anchor.
    """
    assert SPORTS_ODDS_TRADES.symbol_column == "fixture_id"


def test_sports_odds_trades_has_required_v4_shard_columns() -> None:
    """data_source + venue + league_id are all mandatory (v4 manifest shard dims)."""
    declared = {c.name for c in SPORTS_ODDS_TRADES.columns}
    required = {
        "instrument_id",
        "venue",
        "ts_event",
        "data_source",
        "league_id",
        "fixture_id",
        "market_type",
        "outcome",
        "odds_decimal",
    }
    assert required.issubset(declared)


def test_sports_odds_trades_broker_and_client_are_nullable_row_columns() -> None:
    """broker + client are execution-side row columns, not shard dims — nullable."""
    by_name = {c.name: c for c in SPORTS_ODDS_TRADES.columns}
    assert by_name["broker"].nullable is True
    assert by_name["client"].nullable is True


def test_sports_odds_trades_venue_data_source_league_are_non_nullable() -> None:
    """venue + data_source + league_id are shard dims — NEVER null."""
    by_name = {c.name: c for c in SPORTS_ODDS_TRADES.columns}
    assert by_name["venue"].nullable is False
    assert by_name["data_source"].nullable is False
    assert by_name["league_id"].nullable is False


def test_sports_odds_trades_validates_sample_dataframe() -> None:
    df = pd.DataFrame(
        {
            "instrument_id": pd.Series(
                ["FOOTBALL:BETFAIR_EX_UK:MATCH_ODDS:EPL:2025-26:ARSENAL-CHELSEA::HOME"],
                dtype="string",
            ),
            "venue": pd.Series(["BETFAIR_EX_UK"], dtype="string"),
            "ts_event": pd.Series(
                [datetime(2026, 3, 22, 14, 0, tzinfo=UTC)],
                dtype="datetime64[ns, UTC]",
            ),
            "data_source": pd.Series(["ODDS_API"], dtype="string"),
            "league_id": pd.Series(["EPL"], dtype="string"),
            "fixture_id": pd.Series(["EPL:ARSENAL_v_CHELSEA:20260322"], dtype="string"),
            "market_type": pd.Series(["H2H"], dtype="string"),
            "outcome": pd.Series(["HOME"], dtype="string"),
            "odds_decimal": pd.Series([1.85], dtype="float64"),
            "broker": pd.Series([pd.NA], dtype="string"),
            "client": pd.Series([pd.NA], dtype="string"),
        }
    )
    violations = validate_dataframe(df, SPORTS_ODDS_TRADES)
    assert violations == [], f"expected no violations, got {violations}"


# ---------------------------------------------------------------------------
# PREDICTION_PREDICTION_MARKET_TRADES
# ---------------------------------------------------------------------------


def test_prediction_market_trades_registered_in_contract_registry() -> None:
    contract = CONTRACT_REGISTRY[("prediction", "prediction_market", "trades")]
    assert contract is PREDICTION_PREDICTION_MARKET_TRADES


def test_prediction_market_trades_lookup_returns_contract() -> None:
    contract = lookup_contract(
        category="prediction",
        instrument_type="prediction_market",
        data_type="trades",
    )
    assert contract is PREDICTION_PREDICTION_MARKET_TRADES


def test_prediction_market_trades_symbol_column_is_condition_id() -> None:
    """Polymarket rows anchor on ``condition_id`` — the on-chain market id."""
    assert PREDICTION_PREDICTION_MARKET_TRADES.symbol_column == "condition_id"


def test_prediction_market_trades_has_all_required_columns() -> None:
    declared = {c.name for c in PREDICTION_PREDICTION_MARKET_TRADES.columns}
    required = {
        "instrument_id",
        "venue",
        "chain",
        "ts_event",
        "price",
        "size",
        "side",
        "outcome",
        "outcome_index",
        "condition_id",
        "asset_id",
        "underlying",
    }
    assert required == declared


def test_prediction_market_trades_outcome_index_is_int64() -> None:
    by_name = {c.name: c for c in PREDICTION_PREDICTION_MARKET_TRADES.columns}
    assert by_name["outcome_index"].dtype == "int64"
    assert by_name["outcome_index"].nullable is False


def test_prediction_market_trades_underlying_is_nullable() -> None:
    """``underlying`` tags the real-world asset (BNB/ETH/…); nullable for
    rows without a canonical mapping yet."""
    by_name = {c.name: c for c in PREDICTION_PREDICTION_MARKET_TRADES.columns}
    assert by_name["underlying"].nullable is True


def test_prediction_market_trades_validates_sample_dataframe() -> None:
    df = pd.DataFrame(
        {
            "instrument_id": pd.Series(
                ["POLYMARKET:PREDICTION_MARKET:0xabc123:0"],
                dtype="string",
            ),
            "venue": pd.Series(["POLYMARKET"], dtype="string"),
            "chain": pd.Series(["POLYGON"], dtype="string"),
            "ts_event": pd.Series(
                [datetime(2026, 3, 22, 14, 0, tzinfo=UTC)],
                dtype="datetime64[ns, UTC]",
            ),
            "price": pd.Series([0.65], dtype="float64"),
            "size": pd.Series([100.0], dtype="float64"),
            "side": pd.Series(["BUY"], dtype="string"),
            "outcome": pd.Series(["YES"], dtype="string"),
            "outcome_index": pd.Series([0], dtype="int64"),
            "condition_id": pd.Series(["0xabc123"], dtype="string"),
            "asset_id": pd.Series(["789"], dtype="string"),
            "underlying": pd.Series(["BNB"], dtype="string"),
        }
    )
    violations = validate_dataframe(df, PREDICTION_PREDICTION_MARKET_TRADES)
    assert violations == [], f"expected no violations, got {violations}"


# ---------------------------------------------------------------------------
# Sanity: new contracts meet existing global invariants
# ---------------------------------------------------------------------------


def test_new_contracts_require_instrument_id_non_nullable_string() -> None:
    for contract in (SPORTS_ODDS_TRADES, PREDICTION_PREDICTION_MARKET_TRADES):
        id_specs = [c for c in contract.columns if c.name == "instrument_id"]
        assert len(id_specs) == 1
        assert id_specs[0].dtype == "string"
        assert id_specs[0].nullable is False


def test_new_contracts_declared_symbol_columns_are_present_in_schema() -> None:
    for contract in (SPORTS_ODDS_TRADES, PREDICTION_PREDICTION_MARKET_TRADES):
        names = {c.name for c in contract.columns}
        assert contract.symbol_column in names
