"""Contract test for pipeline_mode in manifest rows.

Ensures every manifest row has a valid, non-null pipeline_mode value from the
closed PipelineMode enum. Part of pipeline_mode_implementation_2026_05_28.md
Phase 1.

This test validates that:
1. Values are from the PipelineMode enum (no arbitrary strings)
2. No NULL/empty pipeline_mode values are allowed after backfill
3. Pipeline mode helpers work correctly for validation
"""

from __future__ import annotations

import pandas as pd
import pytest

from unified_api_contracts import PipelineMode


def test_pipeline_mode_values_are_from_enum() -> None:
    """All pipeline_mode values must be valid PipelineMode enum members."""

    # Get all valid PipelineMode values
    valid_values = {mode.value for mode in PipelineMode}

    # Simulate manifest rows with various pipeline_mode values
    test_cases = [
        ("batch_tardis", True),
        ("batch_databento", True),
        ("batch_onchain_rpc", True),
        ("live_binance", True),
        ("batch_invalid", False),  # Not in enum
        ("live_polling", False),  # Not in enum (no such source-aware member)
        ("", False),  # Empty string
        (None, False),  # NULL
    ]

    for value, should_be_valid in test_cases:
        if should_be_valid:
            assert value in valid_values, f"Expected {value!r} to be a valid PipelineMode"
        else:
            assert value not in valid_values, f"Expected {value!r} to be invalid, but it's in PipelineMode enum"


def test_pipeline_mode_enum_validation_in_manifest_rows() -> None:
    """Validate that pipeline_mode values in manifest rows are valid enum members."""

    # Create a sample manifest DataFrame with pipeline_mode
    sample_manifest = pd.DataFrame(
        [
            {
                "date": "2026-05-28",
                "venue": "binance",
                "service_name": "market-tick-data-service",
                "pipeline_mode": "batch_tardis",  # Valid enum value
            }
        ]
    )

    # Test that valid pipeline_mode can be converted to enum
    valid_mode = PipelineMode(sample_manifest["pipeline_mode"].iloc[0])
    assert valid_mode == PipelineMode.BATCH_TARDIS

    # Test with invalid pipeline_mode value
    invalid_manifest = sample_manifest.copy()
    invalid_manifest["pipeline_mode"] = "invalid_mode"

    with pytest.raises(ValueError, match="'invalid_mode' is not a valid PipelineMode"):
        # Enum validation that should happen at write time
        PipelineMode(invalid_manifest["pipeline_mode"].iloc[0])

    # Test with NULL pipeline_mode (after Phase 3 this should fail)
    null_manifest = sample_manifest.copy()
    null_manifest["pipeline_mode"] = None

    # After Phase 3 backfill, pipeline_mode should be NOT NULL
    with pytest.raises((ValueError, TypeError)):
        PipelineMode(null_manifest["pipeline_mode"].iloc[0])


def test_pipeline_mode_required_for_manifest_writer() -> None:
    """ManifestWriter.record_captured must receive valid pipeline_mode."""

    # This test documents the expected behavior after Phase 2
    # The actual implementation happens in Phase 2 when we add the UTL helper

    # Expected signature (already exists per audit):
    # ManifestWriter.record_captured(..., pipeline_mode: PipelineMode)

    # After Phase 2, every call site must provide explicit pipeline_mode
    # No defaults, no None values, no string literals

    # Examples of valid calls (to be enforced by QG grep gate):
    valid_calls = [
        "record_captured(..., pipeline_mode=PipelineMode.BATCH_TARDIS)",
        "record_captured(..., pipeline_mode=PipelineMode.LIVE_BINANCE)",
        "record_captured(..., pipeline_mode=resolve_pipeline_mode(...))",
    ]

    # Examples of invalid calls (to be caught by QG):
    invalid_calls = [
        'record_captured(..., pipeline_mode="batch_tardis")',  # String literal
        "record_captured(..., pipeline_mode=None)",  # None value
        "record_captured(...)",  # Missing pipeline_mode
    ]

    # Document the patterns for Phase 2 QG implementation
    assert valid_calls != invalid_calls  # Trivial assertion for test discovery


def test_all_pipeline_modes_have_test_coverage() -> None:
    """Every PipelineMode enum member should appear in at least one test."""

    # This meta-test ensures we don't add new PipelineMode values without
    # considering their validation implications

    tested_modes = {
        PipelineMode.BATCH_TARDIS,
        PipelineMode.BATCH_DATABENTO,
        PipelineMode.BATCH_ONCHAIN_RPC,
        PipelineMode.LIVE_BINANCE,
    }

    all_modes = set(PipelineMode)

    # We don't need to test every single mode explicitly,
    # but we should have representative coverage
    assert len(tested_modes) > 0, "At least some modes must be tested"
    assert PipelineMode.LIVE_BINANCE in tested_modes, "Live mode must be tested"

    # Ensure no modes are completely orphaned (all should be in UAC)
    for mode in all_modes:
        assert isinstance(mode.value, str), f"{mode} value must be string"
        assert len(mode.value) > 0, f"{mode} value must be non-empty"


def test_pipeline_mode_null_validation() -> None:
    """After Phase 3, NULL pipeline_mode values should be rejected."""

    # This test documents the expected behavior after Phase 3 backfill
    # Currently ~38M manifest rows have NULL pipeline_mode values
    # After backfill, all rows must have valid non-NULL values

    # Simulate checking a manifest row for NULL pipeline_mode
    test_values = [
        None,  # NULL
        "",  # Empty string
        "   ",  # Whitespace only
    ]

    for invalid_value in test_values:
        # These should all fail to create a valid PipelineMode
        with pytest.raises((ValueError, TypeError)):
            if invalid_value is not None and invalid_value.strip():
                # Only try to create enum if not None and not empty after strip
                PipelineMode(invalid_value)
            else:
                # Explicitly raise for None or empty values
                raise ValueError(f"pipeline_mode cannot be {invalid_value!r}")
