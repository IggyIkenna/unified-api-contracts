"""Tests for InstrumentRecord canonical-identity fields.

Covers the additive, optional ``canonical_instrument_id`` + ``product_root``
fields populated by the TradFi/Databento adapter from the UAC exchange-code
registry (EXCHANGE_CODE_TO_NAME / DatabentoInstrumentDef.base_asset).

- default-None (backward-compatible / non-breaking added-optional-field)
- Pydantic construction + model_dump/model_validate round-trip preserves them
- 1:1 alignment with the parquet serialisation schema column names
"""

from __future__ import annotations

from datetime import UTC, datetime

from unified_api_contracts.internal.domain.instruments import INSTRUMENTS_PARQUET_SCHEMA
from unified_api_contracts.internal.reference.instrument import InstrumentRecord, InstrumentType


def _cme_future_record(**overrides: object) -> InstrumentRecord:
    """Minimal TradFi FUTURE record (CME ES front-month)."""
    kwargs: dict[str, object] = {
        "instrument_key": "CME:FUTURE:ESM0",
        "venue": "CME",
        "instrument_type": InstrumentType.FUTURE,
        "raw_symbol": "ESM0",
        "base_asset": "ESM0",
        "expiry": datetime(2030, 6, 21, tzinfo=UTC),
    }
    kwargs.update(overrides)
    return InstrumentRecord(**kwargs)  # type: ignore[arg-type]


def test_canonical_identity_fields_default_none() -> None:
    rec = _cme_future_record()
    assert rec.canonical_instrument_id is None
    assert rec.product_root is None


def test_canonical_identity_roundtrip() -> None:
    rec = _cme_future_record(
        canonical_instrument_id="CME:FUTURE:SP500:2030-06",
        product_root="SP500",
    )
    assert rec.canonical_instrument_id == "CME:FUTURE:SP500:2030-06"
    assert rec.product_root == "SP500"
    # raw_symbol unchanged — canonicals are additive.
    assert rec.raw_symbol == "ESM0"


def test_canonical_identity_pydantic_serialise_deserialise() -> None:
    rec = _cme_future_record(
        canonical_instrument_id="CME:FUTURE:SP500:2030-06",
        product_root="SP500",
    )
    dumped = rec.model_dump()
    restored = InstrumentRecord.model_validate(dumped)
    assert restored.canonical_instrument_id == rec.canonical_instrument_id
    assert restored.product_root == rec.product_root
    assert restored.raw_symbol == rec.raw_symbol


def test_canonical_identity_columns_in_parquet_schema() -> None:
    """New fields are aligned 1:1 with INSTRUMENTS_PARQUET_SCHEMA columns."""
    column_names = {col["name"] for col in INSTRUMENTS_PARQUET_SCHEMA}
    assert "canonical_instrument_id" in column_names
    assert "product_root" in column_names
