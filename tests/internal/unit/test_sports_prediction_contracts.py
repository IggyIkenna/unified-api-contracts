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
import pytest

from unified_api_contracts.internal.schemas.contracts import (
    CONTRACT_REGISTRY,
    PREDICTION_PREDICTION_MARKET_TRADES,
    SPORTS_ODDS_HORIZON_BUCKET,
    SPORTS_ODDS_SNAPSHOT,
    SPORTS_ODDS_TRADES,
    SchemaContractNotFoundError,
    lookup_contract,
    validate_dataframe,
)
from unified_api_contracts.registry import derive_sports_instrument_type

# ---------------------------------------------------------------------------
# SPORTS_ODDS_TRADES
# ---------------------------------------------------------------------------


def test_sports_odds_trades_registered_in_contract_registry() -> None:
    contract = CONTRACT_REGISTRY[("sports", "odds", "trades")]
    assert contract is SPORTS_ODDS_TRADES


def test_sports_odds_trades_lookup_returns_contract() -> None:
    contract = lookup_contract(asset_group="sports", instrument_type="odds", data_type="trades")
    assert contract is SPORTS_ODDS_TRADES


def test_sports_odds_trades_symbol_column_is_fixture_id() -> None:
    """Sports contracts key on ``fixture_id`` — not ``symbol``, not ``bookmaker_key``.

    ``bookmaker_key`` (row-level rename of the manifest 'venue' dimension —
    see venue_fetch.py) is the bookmaker (BET365/PINNACLE/BETFAIR) shard
    dimension. ``fixture_id`` is the per-row instrument id anchor.
    """
    assert SPORTS_ODDS_TRADES.symbol_column == "fixture_id"


def test_sports_odds_trades_has_required_v4_shard_columns() -> None:
    """source + bookmaker_key + league_id are all mandatory (v4 manifest shard dims).

    Corrected 2026-07-26 (T2.9 schema-contract-drift fix): the previously
    registered field names (``venue``/``ts_event``/``data_source``/
    ``market_type``/``outcome``/``odds_decimal``) never matched what the
    native live writer actually persists — verified directly against a live
    ``pipeline_mode=batch_odds_api`` canonical object.
    """
    declared = {c.name for c in SPORTS_ODDS_TRADES.columns}
    required = {
        "instrument_id",
        "bookmaker_key",
        "bm_time",
        "source",
        "league_id",
        "fixture_id",
        "market_key",
        "outcome_name",
        "price",
    }
    assert required.issubset(declared)


def test_sports_odds_trades_no_broker_client_columns() -> None:
    """broker/client never existed in the real writer output — removed 2026-07-26.

    The prior contract declared them as nullable row columns, but no sports
    odds ingestion path (checked live) ever emits a ``broker``/``client``
    field — declaring absent columns as "nullable" still fails validation
    (``missing_column``, independent of nullability), so they were dropped
    rather than kept nullable.
    """
    declared = {c.name for c in SPORTS_ODDS_TRADES.columns}
    assert "broker" not in declared
    assert "client" not in declared


def test_sports_odds_trades_bookmaker_key_source_league_are_non_nullable() -> None:
    """bookmaker_key + source + league_id are shard dims — NEVER null."""
    by_name = {c.name: c for c in SPORTS_ODDS_TRADES.columns}
    assert by_name["bookmaker_key"].nullable is False
    assert by_name["source"].nullable is False
    assert by_name["league_id"].nullable is False


def test_sports_odds_trades_validates_sample_dataframe() -> None:
    """Sample mirrors a live ``pipeline_mode=batch_odds_api`` canonical object's
    real column names + dtypes (verified 2026-07-26 against a captured
    ``venue=WILLIAMHILL/league_id=ALLSVENSKAN`` shard) — ``bm_time`` is the
    writer's raw ISO8601 string, not a parsed datetime64 column.
    """
    df = pd.DataFrame(
        {
            "instrument_id": pd.Series(
                ["FOOTBALL:BETFAIR_EX_UK:MATCH_ODDS:EPL:2025-26:ARSENAL-CHELSEA::HOME"],
                dtype="string",
            ),
            "bookmaker_key": pd.Series(["BETFAIR_EX_UK"], dtype="string"),
            "bm_time": pd.Series(["2026-03-22T14:00:00Z"], dtype="string"),
            "source": pd.Series(["ODDS_API"], dtype="string"),
            "league_id": pd.Series(["EPL"], dtype="string"),
            "fixture_id": pd.Series(["EPL:ARSENAL_v_CHELSEA:20260322"], dtype="string"),
            "market_key": pd.Series(["h2h"], dtype="string"),
            "outcome_name": pd.Series(["HOME"], dtype="string"),
            "price": pd.Series([1.85], dtype="float64"),
        }
    )
    violations = validate_dataframe(df, SPORTS_ODDS_TRADES)
    assert violations == [], f"expected no violations, got {violations}"


# ---------------------------------------------------------------------------
# EXCHANGE_ODDS/FIXED_ODDS fork — RETIRED 2026-08-08
# (sports_taxonomy_p1_capture_and_contracts_2026_08_08.md, operator ruling 9).
#
# The 2026-07-25 fork (sports_closeout_exchange_fixed_odds_fork_2026_07_25.md
# todo 3) registered SPORTS_EXCHANGE_ODDS_TRADES/SPORTS_FIXED_ODDS_TRADES as
# their own CONTRACT_REGISTRY entries. Exchange-vs-sportsbook is a property of
# the VENUE, so per-instrument stamping is redundant; neither contract exists
# any more and both instrument_types now resolve entirely via the dual-read
# fallback below, for every data_type including "trades".
# ---------------------------------------------------------------------------


def test_sports_exchange_odds_trades_no_longer_has_own_contract_registry_entry() -> None:
    assert ("sports", "exchange_odds", "trades") not in CONTRACT_REGISTRY
    assert ("sports", "fixed_odds", "trades") not in CONTRACT_REGISTRY


def test_legacy_odds_trades_still_registered_during_dual_read_window() -> None:
    """The (now-retired) fork never removed the legacy odds entry."""
    assert ("sports", "odds", "trades") in CONTRACT_REGISTRY
    assert CONTRACT_REGISTRY[("sports", "odds", "trades")] is SPORTS_ODDS_TRADES


# ---------------------------------------------------------------------------
# derive_sports_instrument_type — the read-time replacement for the retired
# per-instrument stamp: exchange-vs-sportsbook derived from the venue.
# ---------------------------------------------------------------------------


def test_derive_sports_instrument_type_exchange_venue() -> None:
    assert derive_sports_instrument_type("BETFAIR_EX_UK") == "exchange_odds"


def test_derive_sports_instrument_type_bookmaker_venue() -> None:
    assert derive_sports_instrument_type("PINNACLE") == "fixed_odds"


def test_derive_sports_instrument_type_unmapped_venue_falls_back_to_odds() -> None:
    """ODDS_API is an aggregator source, not a bet-placement venue — no
    exchange/sportsbook classification exists for it, so it must fall back to
    the generic token, matching what the live writer stamps unconditionally.
    """
    assert derive_sports_instrument_type("ODDS_API") == "odds"


def test_derive_sports_instrument_type_is_case_insensitive() -> None:
    assert derive_sports_instrument_type("pinnacle") == "fixed_odds"


# ---------------------------------------------------------------------------
# SPORTS_ODDS_HORIZON_BUCKET — first-class ``horizon`` axis
# (sports_taxonomy_p1_capture_and_contracts_2026_08_08.md, operator ruling 5).
# Previously ``data_type=odds_horizon_bucket`` had NO registered
# SchemaContract at all — this formalises it, separate from
# SPORTS_ODDS_TRADES, precisely because ``validate_dataframe`` requires
# every declared column present regardless of ``nullable``/``required``
# (see ``test_sports_odds_trades_no_broker_client_columns`` above).
# ---------------------------------------------------------------------------


def test_sports_odds_horizon_bucket_registered_in_contract_registry() -> None:
    contract = CONTRACT_REGISTRY[("sports", "odds", "odds_horizon_bucket")]
    assert contract is SPORTS_ODDS_HORIZON_BUCKET


def test_sports_odds_horizon_bucket_lookup_returns_contract() -> None:
    contract = lookup_contract(asset_group="sports", instrument_type="odds", data_type="odds_horizon_bucket")
    assert contract is SPORTS_ODDS_HORIZON_BUCKET


def test_sports_odds_horizon_bucket_has_required_horizon_column() -> None:
    by_name = {c.name: c for c in SPORTS_ODDS_HORIZON_BUCKET.columns}
    assert "horizon" in by_name
    assert by_name["horizon"].nullable is False


def test_sports_odds_horizon_bucket_shares_raw_odds_columns_plus_horizon() -> None:
    """The bucketed shape is the raw odds row shape plus one new axis column."""
    raw_names = {c.name for c in SPORTS_ODDS_TRADES.columns}
    bucketed_names = {c.name for c in SPORTS_ODDS_HORIZON_BUCKET.columns}
    assert bucketed_names == raw_names | {"horizon"}


def test_sports_odds_horizon_bucket_validates_sample_dataframe() -> None:
    df = pd.DataFrame(
        {
            "instrument_id": pd.Series(
                ["FOOTBALL:PINNACLE:MATCH_ODDS:EPL:2025-26:ARSENAL-CHELSEA::HOME"],
                dtype="string",
            ),
            "bookmaker_key": pd.Series(["PINNACLE"], dtype="string"),
            "bm_time": pd.Series(["2026-03-22T14:00:00Z"], dtype="string"),
            "source": pd.Series(["ODDS_API"], dtype="string"),
            "league_id": pd.Series(["EPL"], dtype="string"),
            "fixture_id": pd.Series(["EPL:ARSENAL_v_CHELSEA:20260322"], dtype="string"),
            "market_key": pd.Series(["h2h"], dtype="string"),
            "outcome_name": pd.Series(["HOME"], dtype="string"),
            "price": pd.Series([1.85], dtype="float64"),
            "horizon": pd.Series(["T-24h"], dtype="string"),
        }
    )
    violations = validate_dataframe(df, SPORTS_ODDS_HORIZON_BUCKET)
    assert violations == [], f"expected no violations, got {violations}"


# ---------------------------------------------------------------------------
# lookup_contract dual-read: legacy "odds" + EXCHANGE_ODDS/FIXED_ODDS.
# The 2026-08-08 retirement (operator ruling 9) removed BOTH instrument_types'
# CONTRACT_REGISTRY entries entirely (not just the non-"trades" ones) -- every
# sports lookup for "exchange_odds"/"fixed_odds", any data_type including
# "trades", now falls back to the legacy "odds" contract unconditionally.
# ---------------------------------------------------------------------------


def test_lookup_contract_legacy_odds_path_still_resolves_directly() -> None:
    """The legacy path is untouched by the dual-read fallback."""
    contract = lookup_contract(asset_group="sports", instrument_type="odds", data_type="trades")
    assert contract is SPORTS_ODDS_TRADES


def test_lookup_contract_retired_instrument_types_resolve_via_odds_fallback() -> None:
    """No forked entry exists any more -- "trades" now falls back too, same as
    every other sports odds data_type.
    """
    exchange = lookup_contract(asset_group="sports", instrument_type="exchange_odds", data_type="trades")
    fixed = lookup_contract(asset_group="sports", instrument_type="fixed_odds", data_type="trades")
    assert exchange is SPORTS_ODDS_TRADES
    assert fixed is SPORTS_ODDS_TRADES


def test_lookup_contract_dual_reads_unforked_odds_data_type_via_exchange_odds() -> None:
    """sports_odds_snapshot has no ("sports","exchange_odds",...) entry --
    the dual-read fallback must resolve it to the legacy odds contract.
    """
    contract = lookup_contract(asset_group="sports", instrument_type="exchange_odds", data_type="sports_odds_snapshot")
    assert contract is SPORTS_ODDS_SNAPSHOT
    assert contract is CONTRACT_REGISTRY[("sports", "odds", "sports_odds_snapshot")]


def test_lookup_contract_dual_reads_unforked_odds_data_type_via_fixed_odds() -> None:
    contract = lookup_contract(asset_group="sports", instrument_type="fixed_odds", data_type="sports_odds_snapshot")
    assert contract is SPORTS_ODDS_SNAPSHOT


def test_lookup_contract_dual_read_fallback_is_sports_only() -> None:
    """The exchange_odds/fixed_odds fallback must not leak to other asset_groups
    -- an unregistered (asset_group, instrument_type, data_type) combo must
    still raise, not silently resolve to an unrelated contract.
    """
    with pytest.raises(SchemaContractNotFoundError):
        lookup_contract(asset_group="cefi", instrument_type="exchange_odds", data_type="sports_odds_snapshot")


# ---------------------------------------------------------------------------
# PREDICTION_PREDICTION_MARKET_TRADES
# ---------------------------------------------------------------------------


def test_prediction_market_trades_registered_in_contract_registry() -> None:
    contract = CONTRACT_REGISTRY[("prediction", "prediction_market", "trades")]
    assert contract is PREDICTION_PREDICTION_MARKET_TRADES


def test_prediction_market_trades_lookup_returns_contract() -> None:
    contract = lookup_contract(
        asset_group="prediction",
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
        "asset_group",
        "market_type",
        "resolution_period",
    }
    assert required == declared


def test_prediction_market_trades_outcome_index_is_int64() -> None:
    by_name = {c.name: c for c in PREDICTION_PREDICTION_MARKET_TRADES.columns}
    assert by_name["outcome_index"].dtype == "int64"
    assert by_name["outcome_index"].nullable is False


def test_prediction_market_trades_underlying_is_required() -> None:
    """``underlying`` tags the real-world asset (BNB/SPX/TRUMP/EPL/…).

    Promoted from nullable to required in the 6-dimension resharding —
    the canonical classifier (``classify_polymarket_market``) always
    produces a value (``UNKNOWN`` for MISC markets).
    """
    by_name = {c.name: c for c in PREDICTION_PREDICTION_MARKET_TRADES.columns}
    assert by_name["underlying"].nullable is False


def test_prediction_market_trades_new_shard_columns_required() -> None:
    """The 6-dimension resharding adds three non-null shard columns:
    ``asset_group`` / ``market_type`` / ``resolution_period``.
    """
    by_name = {c.name: c for c in PREDICTION_PREDICTION_MARKET_TRADES.columns}
    for col_name in ("asset_group", "market_type", "resolution_period"):
        assert col_name in by_name, f"missing {col_name}"
        assert by_name[col_name].nullable is False
        assert by_name[col_name].dtype == "string"


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
            "asset_group": pd.Series(["CRYPTO_PRICE"], dtype="string"),
            "market_type": pd.Series(["range_bracket"], dtype="string"),
            "resolution_period": pd.Series(["monthly"], dtype="string"),
        }
    )
    violations = validate_dataframe(df, PREDICTION_PREDICTION_MARKET_TRADES)
    assert violations == [], f"expected no violations, got {violations}"


# ---------------------------------------------------------------------------
# Sanity: new contracts meet existing global invariants
# ---------------------------------------------------------------------------


def test_new_contracts_require_instrument_id_non_nullable_string() -> None:
    for contract in (
        SPORTS_ODDS_TRADES,
        PREDICTION_PREDICTION_MARKET_TRADES,
    ):
        id_specs = [c for c in contract.columns if c.name == "instrument_id"]
        assert len(id_specs) == 1
        assert id_specs[0].dtype == "string"
        assert id_specs[0].nullable is False


def test_new_contracts_declared_symbol_columns_are_present_in_schema() -> None:
    for contract in (
        SPORTS_ODDS_TRADES,
        PREDICTION_PREDICTION_MARKET_TRADES,
    ):
        names = {c.name for c in contract.columns}
        assert contract.symbol_column in names


# ---------------------------------------------------------------------------
# PREDICTION market — Gap 1 of cross-category audit (2026-04-25):
#   book_snapshot + market_metadata + fills contracts.
# ---------------------------------------------------------------------------


def test_prediction_book_snapshot_registered() -> None:
    from unified_api_contracts.internal.schemas._sports_prediction_contracts import (
        PREDICTION_PREDICTION_MARKET_BOOK_SNAPSHOT,
    )

    key = ("prediction", "prediction_market", "book_snapshot_5")
    assert key in CONTRACT_REGISTRY
    assert CONTRACT_REGISTRY[key] is PREDICTION_PREDICTION_MARKET_BOOK_SNAPSHOT
    resolved = lookup_contract(
        asset_group="prediction", instrument_type="prediction_market", data_type="book_snapshot_5"
    )
    assert resolved is PREDICTION_PREDICTION_MARKET_BOOK_SNAPSHOT
    # condition_id is the canonical identifier (matches trades contract).
    assert resolved.symbol_column == "condition_id"
    names = {c.name for c in resolved.columns}
    # bids + asks ladder are JSON-serialised (not flattened) per docstring.
    assert "bids" in names and "asks" in names
    # asset_id is mandatory — outcome-token-scoped book.
    asset_col = next(c for c in resolved.columns if c.name == "asset_id")
    assert asset_col.nullable is False


def test_prediction_market_metadata_registered() -> None:
    from unified_api_contracts.internal.schemas._sports_prediction_contracts import (
        PREDICTION_PREDICTION_MARKET_METADATA,
    )

    key = ("prediction", "prediction_market", "market_metadata")
    assert key in CONTRACT_REGISTRY
    resolved = lookup_contract(
        asset_group="prediction",
        instrument_type="prediction_market",
        data_type="market_metadata",
    )
    assert resolved is PREDICTION_PREDICTION_MARKET_METADATA
    assert resolved.symbol_column == "condition_id"
    names = {c.name for c in resolved.columns}
    # Gamma API core fields.
    assert {"question", "active", "closed", "tokens"} <= names
    # active / closed are non-nullable booleans.
    active_col = next(c for c in resolved.columns if c.name == "active")
    assert active_col.dtype == "bool" and active_col.nullable is False


def test_prediction_market_fills_registered() -> None:
    from unified_api_contracts.internal.schemas._sports_prediction_contracts import (
        PREDICTION_PREDICTION_MARKET_FILLS,
    )

    key = ("prediction", "prediction_market", "fills")
    assert key in CONTRACT_REGISTRY
    resolved = lookup_contract(asset_group="prediction", instrument_type="prediction_market", data_type="fills")
    assert resolved is PREDICTION_PREDICTION_MARKET_FILLS
    assert resolved.symbol_column == "condition_id"
    names = {c.name for c in resolved.columns}
    # Fill identity + linkage to parent order.
    assert {"fill_id", "order_id", "condition_id", "asset_id"} <= names
    # fee/maker/taker are nullable (legacy fills + redacted addresses).
    for nullable_col in ("fee", "maker", "taker"):
        spec = next(c for c in resolved.columns if c.name == nullable_col)
        assert spec.nullable is True, f"{nullable_col} must be nullable"


def test_all_three_new_prediction_contracts_use_condition_id() -> None:
    """All three new contracts pivot on condition_id for cross-endpoint joins.

    This is the institutional invariant: book / metadata / fills / trades must
    all join on the same canonical key (Polymarket's on-chain market id) so
    cross-API stitching works without column mapping.
    """
    keys = [
        ("prediction", "prediction_market", "book_snapshot_5"),
        ("prediction", "prediction_market", "market_metadata"),
        ("prediction", "prediction_market", "fills"),
        ("prediction", "prediction_market", "trades"),  # incumbent
    ]
    for key in keys:
        contract = CONTRACT_REGISTRY[key]
        assert contract.symbol_column == "condition_id", (
            f"{key} must pivot on condition_id (got {contract.symbol_column!r})"
        )


# ---------------------------------------------------------------------------
# G1-ENUM validity-matrix reachability (sports_shard_enumeration_cartesian_
# blowup_2026_07_20.md Part 2 item 2.3): CONTRACT_REGISTRY's sports "odds"
# family must be reachable from VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE.
# The matrix had NO ("sports","odds") entry at all despite
# CONTRACT_REGISTRY[("sports","odds","trades")] backing 1,806,527 real prod
# rows (instrument_type=odds/data_type=trades).
# ---------------------------------------------------------------------------


def test_sports_odds_instrument_type_has_a_validity_matrix_entry() -> None:
    """Regression lock for the ("sports","odds") matrix hole.

    Before this fix, ``VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE`` had no
    ``("sports","odds")`` key at all, so every real
    (instrument_type=odds, data_type=trades) manifest row -- 1,806,527 of them
    in prod -- silently fell through the "unmapped instrument_type" path
    instead of an audited, confirmed matrix entry.
    """
    from unified_api_contracts.registry.market_data_categories import (
        VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE,
    )

    assert ("sports", "odds") in VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE
    assert "trades" in VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("sports", "odds")]


def test_every_sports_odds_family_contract_registry_entry_is_matrix_reachable() -> None:
    """Every CONTRACT_REGISTRY key sharing a sports market-data "odds" family
    instrument_type -- and whose data_type is a genuine
    ``DATA_TYPES_BY_ASSET_GROUP["sports"]`` member (not a schema-internal name
    like ``SPORTS_ODDS_SNAPSHOT``'s ``sports_odds_snapshot``, a separate,
    out-of-scope naming mismatch between CONTRACT_REGISTRY's schema keys and
    the wire data_type vocabulary) -- must have its data_type present in the
    ``VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE`` entry for that
    instrument_type.

    Scoped to the odds-shape family the matrix already declares
    (fixture/exchange_odds/fixed_odds/prop/odds) rather than the whole
    CONTRACT_REGISTRY -- most of the registry (ml_training manifests, sports
    reference/derived/feature contracts, MDPS candle-feature families, ...)
    is outside what this market-data validity matrix models at all.
    """
    from unified_api_contracts.registry.market_data_categories import (
        DATA_TYPES_BY_ASSET_GROUP,
        VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE,
    )

    odds_family_instrument_types = {"fixture", "exchange_odds", "fixed_odds", "prop", "odds"}
    sports_data_types = set(DATA_TYPES_BY_ASSET_GROUP["sports"])

    violations: list[tuple[str, str, str]] = []
    for asset_group, instrument_type, data_type in CONTRACT_REGISTRY:
        if asset_group != "sports" or instrument_type not in odds_family_instrument_types:
            continue
        if data_type not in sports_data_types:
            continue  # out of scope: schema-internal name, not a wire data_type
        matrix_entry = VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE.get((asset_group, instrument_type))
        if matrix_entry is None or data_type not in matrix_entry:
            violations.append((asset_group, instrument_type, data_type))

    assert not violations, (
        f"sports odds-family CONTRACT_REGISTRY entries with no validity-matrix coverage: {violations}"
    )
