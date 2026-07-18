"""Tests for the InstrumentRecord prediction fixture-match fields (A4).

Covers the six additive, optional fixture-match fields (``af_league_id``,
``home_team_canonical_id``, ``away_team_canonical_id``, ``fixture_date``,
``af_fixture_id``, ``af_fixture_match_status``) that materialise the
instruments-service prediction fixture-match side-table onto the shared
InstrumentRecord schema.

- default-None (backward-compatible / non-breaking added-optional-field)
- Pydantic construction + model_dump/model_validate round-trip preserves them
- 1:1 alignment with the parquet serialisation schema column names

Plan: prediction_consolidated_closeout_2026_07_18 A4.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from unified_api_contracts.internal.domain.instruments import INSTRUMENTS_PARQUET_SCHEMA
from unified_api_contracts.internal.reference.instrument import InstrumentRecord, InstrumentType

_FIXTURE_MATCH_FIELDS = (
    "af_league_id",
    "home_team_canonical_id",
    "away_team_canonical_id",
    "fixture_date",
    "af_fixture_id",
    "af_fixture_match_status",
)


def _prediction_event_record(**overrides: object) -> InstrumentRecord:
    """Minimal valid prediction market record (Kalshi soccer EVENT_CONTRACT).

    EVENT_CONTRACT requires a non-null ``expiry`` (resolution_date axis); the
    fixture-match fields are additive on top and default None.
    """
    kwargs: dict[str, object] = {
        "instrument_key": "KALSHI:EVENT_CONTRACT:KXEPLGAME-25JUL18LFCBRE",
        "venue": "KALSHI",
        "instrument_type": InstrumentType.EVENT_CONTRACT,
        "expiry": datetime(2025, 7, 18, tzinfo=UTC),
    }
    kwargs.update(overrides)
    return InstrumentRecord(**kwargs)  # type: ignore[arg-type]


def test_fixture_match_fields_default_none() -> None:
    rec = _prediction_event_record()
    for field in _FIXTURE_MATCH_FIELDS:
        assert getattr(rec, field) is None, f"{field} must default to None"


def test_non_prediction_record_unaffected() -> None:
    # Adding the fields must not perturb an existing CeFi record — the model_validator
    # never references them and they stay None.
    rec = InstrumentRecord(
        instrument_key="BINANCE:SPOT_PAIR:BTCUSDT",
        venue="BINANCE",
        instrument_type=InstrumentType.SPOT_PAIR,
        base_asset="BTC",
        quote_asset="USDT",
    )
    for field in _FIXTURE_MATCH_FIELDS:
        assert getattr(rec, field) is None


def test_fixture_match_populated_roundtrip() -> None:
    rec = _prediction_event_record(
        af_league_id="EPL",
        home_team_canonical_id="LIVERPOOL",
        away_team_canonical_id="BRENTFORD",
        fixture_date=date(2025, 7, 18),
        af_fixture_id=1234567,
        af_fixture_match_status="MATCHED",
    )
    assert rec.af_league_id == "EPL"
    assert rec.home_team_canonical_id == "LIVERPOOL"
    assert rec.away_team_canonical_id == "BRENTFORD"
    assert rec.fixture_date == date(2025, 7, 18)
    assert rec.af_fixture_id == 1234567
    assert rec.af_fixture_match_status == "MATCHED"


def test_fixture_match_pydantic_serialise_deserialise() -> None:
    rec = _prediction_event_record(
        af_league_id="EPL",
        home_team_canonical_id="LIVERPOOL",
        away_team_canonical_id="BRENTFORD",
        fixture_date=date(2025, 7, 18),
        af_fixture_id=1234567,
        af_fixture_match_status="MATCHED",
    )
    restored = InstrumentRecord.model_validate(rec.model_dump())
    for field in _FIXTURE_MATCH_FIELDS:
        assert getattr(restored, field) == getattr(rec, field)


def test_unresolved_team_name_status_is_honest_absence() -> None:
    # An attempt-with-no-match keeps af_fixture_id None while carrying the closed-set
    # UNRESOLVED_TEAM_NAME status — distinguishable from a genuine null.
    rec = _prediction_event_record(
        af_league_id="EPL",
        fixture_date=date(2025, 7, 18),
        af_fixture_match_status="UNRESOLVED_TEAM_NAME",
    )
    assert rec.af_fixture_id is None
    assert rec.af_fixture_match_status == "UNRESOLVED_TEAM_NAME"


def test_fixture_match_columns_in_parquet_schema() -> None:
    """New fields are aligned 1:1 with INSTRUMENTS_PARQUET_SCHEMA columns."""
    column_names = {col["name"] for col in INSTRUMENTS_PARQUET_SCHEMA}
    for field in _FIXTURE_MATCH_FIELDS:
        assert field in column_names, f"{field} must be in INSTRUMENTS_PARQUET_SCHEMA (model↔schema 1:1)"
