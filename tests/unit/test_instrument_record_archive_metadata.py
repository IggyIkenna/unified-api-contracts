"""Tests for InstrumentRecord archive-metadata fields (is_mtds_contract_audit_2026_05_20 Phase 1).

Covers:
- Round-trip Pydantic construction + field access for new archive-metadata fields
- EXPECTED_PAST_SOURCE_COVERAGE_END is a valid EmptyConfirmedReason
- All 6 new fields default to None (backward-compatible)
- Fields accept correct types and are accessible
"""

from __future__ import annotations

from datetime import date

import pytest

from unified_api_contracts.canonical.crosscutting.honest_coverage import (
    EMPTY_CONFIRMED_REASONS,
    EmptyConfirmedReason,
)
from unified_api_contracts.internal.reference.instrument import InstrumentRecord, InstrumentType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DUMMY_ADDR = "0xBcca60bB61934080951369a648Fb03DF4F96263C"


def _drift_defi_record(**overrides: object) -> InstrumentRecord:
    """Minimal DeFi STAKING record representing a Drift market."""
    kwargs: dict[str, object] = {
        "instrument_key": "DRIFT:STAKING:SOL-PERP",
        "venue": "DRIFT",
        "instrument_type": InstrumentType.STAKING,
        "pool_address": _DUMMY_ADDR,
        "base_asset_decimals": 9,
    }
    kwargs.update(overrides)
    return InstrumentRecord(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# EXPECTED_PAST_SOURCE_COVERAGE_END enum tests
# ---------------------------------------------------------------------------


def test_expected_past_source_coverage_end_in_enum() -> None:
    assert EmptyConfirmedReason.EXPECTED_PAST_SOURCE_COVERAGE_END == "EXPECTED_PAST_SOURCE_COVERAGE_END"


def test_expected_past_source_coverage_end_in_closed_set() -> None:
    assert "EXPECTED_PAST_SOURCE_COVERAGE_END" in EMPTY_CONFIRMED_REASONS


# ---------------------------------------------------------------------------
# InstrumentRecord archive-metadata field default-None tests
# ---------------------------------------------------------------------------


def test_archive_fields_default_none() -> None:
    rec = _drift_defi_record()
    assert rec.source_archive_url_template is None
    assert rec.source_record_types is None
    assert rec.source_coverage_start is None
    assert rec.source_coverage_end is None
    assert rec.listed_at is None
    assert rec.delisted_at is None


# ---------------------------------------------------------------------------
# Round-trip: set all 6 new fields, verify
# ---------------------------------------------------------------------------


def test_archive_metadata_roundtrip() -> None:
    url_template = (
        "https://drift-historical-data-v2.s3.eu-west-1.amazonaws.com/program/{program_id}/"
        "market/{market}/{record_type}/{year}/{day}"
    )
    record_types = {"trades": "tradeRecords", "funding_rate": "fundingRateRecords"}
    coverage_start = {"trades": date(2020, 9, 14), "funding_rate": date(2021, 5, 1)}
    coverage_end = {"trades": date(2025, 1, 8), "funding_rate": date(2025, 1, 8)}
    listed = date(2020, 9, 14)
    delisted = date(2025, 1, 8)

    rec = _drift_defi_record(
        source_archive_url_template=url_template,
        source_record_types=record_types,
        source_coverage_start=coverage_start,
        source_coverage_end=coverage_end,
        listed_at=listed,
        delisted_at=delisted,
    )

    assert rec.source_archive_url_template == url_template
    assert rec.source_record_types == record_types
    assert rec.source_coverage_start == coverage_start
    assert rec.source_coverage_end == coverage_end
    assert rec.listed_at == listed
    assert rec.delisted_at == delisted


def test_archive_metadata_pydantic_serialise_deserialise() -> None:
    """model_dump + model_validate roundtrip preserves all archive-metadata fields."""
    rec = _drift_defi_record(
        source_archive_url_template="https://example.com/{market}/{year}/{day}",
        source_record_types={"trades": "tradeRecords"},
        source_coverage_start={"trades": date(2020, 9, 14)},
        source_coverage_end={"trades": date(2025, 1, 8)},
        listed_at=date(2020, 9, 14),
        delisted_at=date(2025, 1, 8),
    )
    dumped = rec.model_dump()
    restored = InstrumentRecord.model_validate(dumped)

    assert restored.source_archive_url_template == rec.source_archive_url_template
    assert restored.source_record_types == rec.source_record_types
    assert restored.source_coverage_start == rec.source_coverage_start
    assert restored.source_coverage_end == rec.source_coverage_end
    assert restored.listed_at == rec.listed_at
    assert restored.delisted_at == rec.delisted_at


# ---------------------------------------------------------------------------
# Coverage-end logic helpers (not in model — just verify field semantics)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query_date,coverage_end,expected_past_end",
    [
        (date(2025, 1, 7), date(2025, 1, 8), False),  # day before end — still in coverage
        (date(2025, 1, 8), date(2025, 1, 8), False),  # last day of coverage — still in coverage
        (date(2025, 1, 9), date(2025, 1, 8), True),  # first day after end — past coverage
        (date(2026, 5, 20), date(2025, 1, 8), True),  # today vs Drift archive end
    ],
)
def test_coverage_end_logic(query_date: date, coverage_end: date, expected_past_end: bool) -> None:
    """Callers should emit EXPECTED_PAST_SOURCE_COVERAGE_END when query_date > coverage_end."""
    rec = _drift_defi_record(
        source_coverage_end={"trades": coverage_end},
    )
    assert rec.source_coverage_end is not None
    is_past = query_date > rec.source_coverage_end["trades"]
    assert is_past == expected_past_end
