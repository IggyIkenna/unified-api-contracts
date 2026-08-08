"""Unit tests for the canonical persist envelope + SINK_MATRIX.

Covers:
* CanonicalPersistEnvelope round-trip (serialize/deserialize, all RetentionClass values).
* payload_inline / payload_pointer XOR invariant.
* SINK_MATRIX resolver: exact match, wildcard fallback, raise on unknown.
* Matrix completeness gate: every entry is resolvable (no silent default).

Plan: ``live_data_persistence_central_event_log_2026_06_25.md`` Plan 01.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from unified_api_contracts.events.persist import (
    CanonicalPersistEnvelope,
    RetentionClass,
)
from unified_api_contracts.events.sink_matrix import (
    SINK_MATRIX,
    SinkConfig,
    retention_class_for,
    sinks_for,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc(year: int, month: int, day: int, h: int = 0, m: int = 0, s: int = 0) -> datetime:
    return datetime(year, month, day, h, m, s, tzinfo=UTC)


def _inline_envelope(**kwargs: object) -> CanonicalPersistEnvelope:
    defaults: dict[str, object] = {
        "asset_group": "cefi",
        "data_type": "candle",
        "period_start": _utc(2026, 6, 26, 10, 0, 0),
        "period_end": _utc(2026, 6, 26, 10, 1, 0),
        "source": "MDPS",
        "available_at": _utc(2026, 6, 26, 10, 1, 2),
        "retention_class": RetentionClass.REPRODUCIBLE,
        "payload_inline": json.dumps({"open": 100.0, "high": 101.0, "low": 99.5, "close": 100.5, "volume": 42.0}),
        "correlation_id": "corr-abc123",
        "vm_name": "test-vm",
    }
    defaults.update(kwargs)
    return CanonicalPersistEnvelope.model_validate(defaults)


# ---------------------------------------------------------------------------
# CanonicalPersistEnvelope round-trip tests
# ---------------------------------------------------------------------------


class TestCanonicalPersistEnvelopeRoundTrip:
    def test_inline_payload_round_trip_reproducible(self) -> None:
        env = _inline_envelope(retention_class=RetentionClass.REPRODUCIBLE)
        dumped = env.model_dump_json()
        restored = CanonicalPersistEnvelope.model_validate_json(dumped)
        assert restored.retention_class == RetentionClass.REPRODUCIBLE
        assert restored.payload_inline is not None
        assert restored.payload_pointer is None
        assert restored.schema_version == "1"

    def test_inline_payload_round_trip_stream_only(self) -> None:
        env = _inline_envelope(
            retention_class=RetentionClass.STREAM_ONLY,
            data_type="execution_fills",
            source="execution",
        )
        dumped = env.model_dump_json()
        restored = CanonicalPersistEnvelope.model_validate_json(dumped)
        assert restored.retention_class == RetentionClass.STREAM_ONLY

    def test_pointer_payload_round_trip(self) -> None:
        env = CanonicalPersistEnvelope.model_validate(
            {
                "asset_group": "defi",
                "data_type": "trades",
                "period_start": _utc(2026, 6, 26, 9, 0, 0),
                "period_end": _utc(2026, 6, 26, 9, 1, 0),
                "source": "MTDS",
                "available_at": _utc(2026, 6, 26, 9, 1, 1),
                "retention_class": RetentionClass.REPRODUCIBLE,
                "payload_pointer": "gs://live-data-bucket/defi/trades/2026-06-26/chunk.parquet",
                "correlation_id": "corr-xyz",
                "vm_name": "vm-1",
            }
        )
        dumped = env.model_dump_json()
        restored = CanonicalPersistEnvelope.model_validate_json(dumped)
        assert restored.payload_pointer is not None
        assert restored.payload_inline is None

    def test_all_optional_shard_fields_null(self) -> None:
        env = _inline_envelope(venue=None, chain=None, instrument_id=None, instrument_type=None)
        assert env.venue is None
        assert env.chain is None
        assert env.instrument_id is None

    def test_shard_fields_populated(self) -> None:
        env = _inline_envelope(venue="binance", chain="ethereum", instrument_id="ETH-USDT", instrument_type="spot")
        dumped = env.model_dump_json()
        restored = CanonicalPersistEnvelope.model_validate_json(dumped)
        assert restored.venue == "binance"
        assert restored.chain == "ethereum"
        assert restored.instrument_id == "ETH-USDT"


# ---------------------------------------------------------------------------
# Payload XOR invariant
# ---------------------------------------------------------------------------


class TestPayloadXorInvariant:
    def test_neither_inline_nor_pointer_raises(self) -> None:
        with pytest.raises(Exception):
            CanonicalPersistEnvelope.model_validate(
                {
                    "asset_group": "cefi",
                    "data_type": "candle",
                    "period_start": _utc(2026, 6, 26),
                    "period_end": _utc(2026, 6, 26, 0, 1),
                    "source": "MDPS",
                    "available_at": _utc(2026, 6, 26, 0, 1, 2),
                    "retention_class": RetentionClass.REPRODUCIBLE,
                    # neither payload_inline nor payload_pointer set
                    "correlation_id": "corr",
                    "vm_name": "vm",
                }
            )

    def test_both_inline_and_pointer_raises(self) -> None:
        with pytest.raises(Exception):
            CanonicalPersistEnvelope.model_validate(
                {
                    "asset_group": "cefi",
                    "data_type": "candle",
                    "period_start": _utc(2026, 6, 26),
                    "period_end": _utc(2026, 6, 26, 0, 1),
                    "source": "MDPS",
                    "available_at": _utc(2026, 6, 26, 0, 1, 2),
                    "retention_class": RetentionClass.REPRODUCIBLE,
                    "payload_inline": '{"close": 100}',
                    "payload_pointer": "gs://bucket/path.parquet",
                    "correlation_id": "corr",
                    "vm_name": "vm",
                }
            )


# ---------------------------------------------------------------------------
# SINK_MATRIX resolver tests
# ---------------------------------------------------------------------------


class TestSinkMatrixResolver:
    def test_exact_match_cefi_trades(self) -> None:
        cfg = sinks_for("cefi", "trades")
        assert isinstance(cfg, SinkConfig)
        assert cfg.retention_class == RetentionClass.REPRODUCIBLE
        assert cfg.table is True
        assert cfg.hot is True
        assert cfg.gcs_warm is True

    def test_exact_match_stream_only_execution_fills(self) -> None:
        cfg = sinks_for("cefi", "execution_fills")
        assert cfg.retention_class == RetentionClass.STREAM_ONLY
        assert cfg.cold_ttl_days is None

    def test_wildcard_fallback_candle_cefi(self) -> None:
        # ("*", "candle") covers all asset_groups
        cfg = sinks_for("cefi", "candle")
        assert cfg.retention_class == RetentionClass.REPRODUCIBLE
        assert cfg.cold_ttl_days == 365

    def test_wildcard_fallback_candle_defi(self) -> None:
        cfg = sinks_for("defi", "candle")
        assert cfg.retention_class == RetentionClass.REPRODUCIBLE

    def test_wildcard_fallback_candle_tradfi(self) -> None:
        cfg = sinks_for("tradfi", "candle")
        assert cfg.retention_class == RetentionClass.REPRODUCIBLE

    def test_wildcard_fallback_execution_fills_defi(self) -> None:
        cfg = sinks_for("defi", "execution_fills")
        assert cfg.retention_class == RetentionClass.STREAM_ONLY
        assert cfg.cold_ttl_days is None

    def test_retention_class_for_helper_reproducible(self) -> None:
        rc = retention_class_for("cefi", "trades")
        assert rc == RetentionClass.REPRODUCIBLE

    def test_retention_class_for_helper_stream_only(self) -> None:
        rc = retention_class_for("defi", "execution_pnl")
        assert rc == RetentionClass.STREAM_ONLY

    def test_unknown_shard_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="No SINK_MATRIX entry"):
            sinks_for("cefi", "totally_unknown_data_type_xyz")

    def test_unknown_asset_group_raises_key_error(self) -> None:
        # "totally_unknown_ag" + no wildcard entry for "trades" specific to it;
        # ("cefi","trades") exists but not ("totally_unknown_ag","trades"),
        # and wildcard ("*","trades") does not exist either.
        with pytest.raises(KeyError, match="No SINK_MATRIX entry"):
            sinks_for("totally_unknown_ag", "trades")

    def test_keep_flag_on_ml_predictions(self) -> None:
        cfg = sinks_for("cefi", "per_strategy_signal")
        assert cfg.keep_flag is True

    def test_stream_only_has_no_ttl(self) -> None:
        for data_type in ("execution_fills", "execution_positions", "execution_pnl", "paper_ledger"):
            cfg = sinks_for("cefi", data_type)
            assert cfg.cold_ttl_days is None, f"{data_type} must have no cold TTL (STREAM_ONLY)"


# ---------------------------------------------------------------------------
# Matrix completeness gate (Plan 01 §P1 gate requirement)
#
# Asserts:
# 1. The matrix is non-empty.
# 2. Every explicit entry resolves (exact > wildcard).
# 3. Spot-check: all six execution data_types across two asset_groups.
# ---------------------------------------------------------------------------


class TestSinkMatrixCompleteness:
    def test_matrix_is_non_empty(self) -> None:
        assert len(SINK_MATRIX) > 0, "SINK_MATRIX must have at least one entry"

    def test_all_explicit_entries_resolve(self) -> None:
        failed: list[tuple[str, str]] = []
        for ag, dt in SINK_MATRIX:
            if ag == "*":
                continue
            try:
                sinks_for(ag, dt)
            except KeyError:
                failed.append((ag, dt))
        assert not failed, f"These explicit entries failed to resolve: {failed}"

    def test_wildcard_entries_resolve_for_sample_asset_groups(self) -> None:
        sample_asset_groups = ["cefi", "defi", "tradfi", "sports", "prediction", "commodity"]
        wildcard_data_types = [ag_dt[1] for ag_dt in SINK_MATRIX if ag_dt[0] == "*"]
        failed: list[tuple[str, str]] = []
        for ag in sample_asset_groups:
            for dt in wildcard_data_types:
                try:
                    sinks_for(ag, dt)
                except KeyError:
                    failed.append((ag, dt))
        assert not failed, f"Wildcard entries failed for these (ag, dt): {failed}"

    def test_execution_shards_stream_only_all_variants(self) -> None:
        for ag in ("cefi", "defi"):
            for dt in ("execution_fills", "execution_positions", "execution_pnl", "paper_ledger"):
                cfg = sinks_for(ag, dt)
                assert cfg.retention_class == RetentionClass.STREAM_ONLY
                assert cfg.cold_ttl_days is None

    def test_mtds_shards_all_reproducible(self) -> None:
        mtds_shards = [
            ("cefi", "trades"),
            ("cefi", "book_snapshot_5"),
            ("cefi", "derivative_ticker"),
            ("cefi", "liquidations"),
            ("defi", "trades"),
            ("defi", "book_snapshot_5"),
            ("defi", "liquidations"),
            ("tradfi", "trades"),
            ("sports", "odds"),  # renamed from trades 2026-08-08 (P1)
            ("prediction", "trades"),
        ]
        for ag, dt in mtds_shards:
            cfg = sinks_for(ag, dt)
            assert cfg.retention_class == RetentionClass.REPRODUCIBLE, f"({ag}, {dt}) must be REPRODUCIBLE"
