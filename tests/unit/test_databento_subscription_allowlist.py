"""Unit tests for unified_api_contracts.registry.databento_subscription_allowlist.

Covers:
1. allowed/blocked dataset (assert_dataset_allowed)
2. banned OHLCV schemas (ohlcv-1h / ohlcv-1d) and allowed ones (ohlcv-1s / ohlcv-1m)
3. per-level lookback-floor boundaries (L0 / L1 / L2 / L3)
4. batch API ban (assert_batch_api_allowed) and break-glass override
5. break-glass (covered in #4)
6. enum-repr normalisation (_normalize_schema)
"""

from __future__ import annotations

from datetime import UTC, timedelta
from datetime import datetime as dt

import pytest

from unified_api_contracts.registry.databento_subscription_allowlist import (
    ALLOWED_DATABENTO_DATASETS,
    LEVEL_MAX_LOOKBACK_DAYS,
    DatabentoBatchApiBannedError,
    DatabentoDatasetNotAllowedError,
    DatabentoLookbackExceededError,
    DatabentoSchemaNotAllowedError,
    _normalize_schema,
    assert_batch_api_allowed,
    assert_dataset_allowed,
    assert_lookback_allowed,
    assert_schema_allowed,
    earliest_allowed_start,
)

# ---------------------------------------------------------------------------
# 1. Dataset allowlist
# ---------------------------------------------------------------------------


class TestAssertDatasetAllowed:
    """assert_dataset_allowed passes for subscribed datasets, raises for everything else."""

    def test_glbx_mdp3_passes(self) -> None:
        assert_dataset_allowed("GLBX.MDP3")  # CME Globex

    def test_dbeq_basic_passes(self) -> None:
        assert_dataset_allowed("DBEQ.BASIC")  # US Equities

    def test_xcbf_pitch_passes(self) -> None:
        assert_dataset_allowed("XCBF.PITCH")  # Cboe Futures / VIX

    def test_all_allowed_datasets_pass(self) -> None:
        for ds in ALLOWED_DATABENTO_DATASETS:
            assert_dataset_allowed(ds)  # must not raise

    def test_unknown_dataset_raises(self) -> None:
        with pytest.raises(DatabentoDatasetNotAllowedError):
            assert_dataset_allowed("XNAS.ITCH")

    def test_empty_string_raises(self) -> None:
        with pytest.raises(DatabentoDatasetNotAllowedError):
            assert_dataset_allowed("")

    def test_cfe_bare_raises(self) -> None:
        # Operator notes that bare 'CFE' is rejected by the API — our gate is stricter.
        with pytest.raises(DatabentoDatasetNotAllowedError):
            assert_dataset_allowed("CFE")

    def test_lowercase_variant_raises(self) -> None:
        # Dataset names are case-sensitive on the wire.
        with pytest.raises(DatabentoDatasetNotAllowedError):
            assert_dataset_allowed("glbx.mdp3")


# ---------------------------------------------------------------------------
# 2. Schema allowlist — banned OHLCV + allowed schemas
# ---------------------------------------------------------------------------


class TestAssertSchemaAllowed:
    """assert_schema_allowed enforces the fetch policy: 1s/1m OK, 1h/1d banned."""

    # Banned OHLCV schemas
    def test_ohlcv_1h_raises(self) -> None:
        with pytest.raises(DatabentoSchemaNotAllowedError):
            assert_schema_allowed("ohlcv-1h")

    def test_ohlcv_1d_raises(self) -> None:
        with pytest.raises(DatabentoSchemaNotAllowedError):
            assert_schema_allowed("ohlcv-1d")

    # Allowed OHLCV schemas
    def test_ohlcv_1s_passes(self) -> None:
        assert_schema_allowed("ohlcv-1s")

    def test_ohlcv_1m_passes(self) -> None:
        assert_schema_allowed("ohlcv-1m")

    # Other allowed schemas
    def test_trades_passes(self) -> None:
        assert_schema_allowed("trades")

    def test_mbp_10_passes(self) -> None:
        assert_schema_allowed("mbp-10")

    def test_mbo_passes(self) -> None:
        assert_schema_allowed("mbo")

    def test_definition_passes(self) -> None:
        assert_schema_allowed("definition")

    # Completely unknown schema
    def test_unknown_schema_raises(self) -> None:
        with pytest.raises(DatabentoSchemaNotAllowedError):
            assert_schema_allowed("orderbook-depth-5")


# ---------------------------------------------------------------------------
# 3. Per-level lookback-floor boundaries
# ---------------------------------------------------------------------------


class TestLookbackFloorBoundaries:
    """assert_lookback_allowed fails closed at the level's free-window edge."""

    # ---- L0 (ohlcv-1s) — 16 years free -----------------------------------

    def test_l0_within_16y_passes(self) -> None:
        now = dt.now(UTC)
        # 1 day inside the 16-year window
        start = now - timedelta(days=LEVEL_MAX_LOOKBACK_DAYS["L0"] - 1)
        assert_lookback_allowed("ohlcv-1s", start, now=now)

    def test_l0_at_boundary_passes(self) -> None:
        # Exactly at the floor (same day) — must pass.
        now = dt.now(UTC)
        floor = earliest_allowed_start("ohlcv-1s", now=now)
        # floor itself: allowed (start >= floor)
        assert_lookback_allowed("ohlcv-1s", floor, now=now)

    def test_l0_beyond_16y_raises(self) -> None:
        now = dt.now(UTC)
        start = now - timedelta(days=LEVEL_MAX_LOOKBACK_DAYS["L0"] + 1)
        with pytest.raises(DatabentoLookbackExceededError):
            assert_lookback_allowed("ohlcv-1s", start, now=now)

    # ---- L1 (trades) — 365 days free -------------------------------------

    def test_l1_within_365d_passes(self) -> None:
        now = dt.now(UTC)
        start = now - timedelta(days=365)
        assert_lookback_allowed("trades", start, now=now)

    def test_l1_at_366d_raises(self) -> None:
        now = dt.now(UTC)
        start = now - timedelta(days=366)
        with pytest.raises(DatabentoLookbackExceededError):
            assert_lookback_allowed("trades", start, now=now)

    # ---- L2 (mbp-10) — 30 days free --------------------------------------

    def test_l2_within_30d_passes(self) -> None:
        now = dt.now(UTC)
        start = now - timedelta(days=30)
        assert_lookback_allowed("mbp-10", start, now=now)

    def test_l2_at_31d_raises(self) -> None:
        now = dt.now(UTC)
        start = now - timedelta(days=31)
        with pytest.raises(DatabentoLookbackExceededError):
            assert_lookback_allowed("mbp-10", start, now=now)

    # ---- L3 (mbo) — 30 days free -----------------------------------------

    def test_l3_within_30d_passes(self) -> None:
        now = dt.now(UTC)
        start = now - timedelta(days=30)
        assert_lookback_allowed("mbo", start, now=now)

    def test_l3_at_31d_raises(self) -> None:
        now = dt.now(UTC)
        start = now - timedelta(days=31)
        with pytest.raises(DatabentoLookbackExceededError):
            assert_lookback_allowed("mbo", start, now=now)


# ---------------------------------------------------------------------------
# 4 + 5. Batch API ban and break-glass
# ---------------------------------------------------------------------------


class TestBatchApiBan:
    """assert_batch_api_allowed blocks batch.submit_job by default; break_glass=True overrides."""

    def test_batch_submit_job_raises_by_default(self) -> None:
        with pytest.raises(DatabentoBatchApiBannedError):
            assert_batch_api_allowed("batch.submit_job")

    def test_batch_submit_job_break_glass_passes(self) -> None:
        # break_glass=True is the explicit audited override — must not raise.
        assert_batch_api_allowed("batch.submit_job", break_glass=True)

    def test_non_banned_api_passes(self) -> None:
        # A non-banned name such as timeseries.get_range is always allowed.
        assert_batch_api_allowed("timeseries.get_range")

    def test_non_banned_api_with_break_glass_passes(self) -> None:
        assert_batch_api_allowed("timeseries.get_range", break_glass=True)

    def test_unrelated_name_passes(self) -> None:
        assert_batch_api_allowed("metadata.get_cost")


# ---------------------------------------------------------------------------
# 6. Enum-repr normalisation
# ---------------------------------------------------------------------------


class TestNormalizeSchema:
    """_normalize_schema converts enum reprs and underscore forms to hyphenated wire form."""

    def test_underscore_ohlcv_1m_to_hyphen(self) -> None:
        assert _normalize_schema("ohlcv_1m") == "ohlcv-1m"

    def test_schema_enum_repr_ohlcv_1s(self) -> None:
        # Simulates the str() output of databento.Schema.OHLCV_1S → "Schema.OHLCV_1S"
        assert _normalize_schema("Schema.OHLCV_1S") == "ohlcv-1s"

    def test_already_hyphenated_unchanged(self) -> None:
        assert _normalize_schema("ohlcv-1m") == "ohlcv-1m"

    def test_uppercase_lowercased(self) -> None:
        assert _normalize_schema("TRADES") == "trades"

    def test_underscore_trades(self) -> None:
        assert _normalize_schema("trades") == "trades"

    def test_schema_enum_repr_mbp_10(self) -> None:
        assert _normalize_schema("Schema.MBP_10") == "mbp-10"

    def test_schema_enum_repr_mbo(self) -> None:
        assert _normalize_schema("Schema.MBO") == "mbo"

    def test_leading_trailing_whitespace_stripped(self) -> None:
        assert _normalize_schema("  ohlcv_1m  ") == "ohlcv-1m"
