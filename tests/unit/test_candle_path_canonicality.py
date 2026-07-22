"""Unit tests for the ``processed_candles/`` extension to the machine oracle.

candle_feature_canonical_path_divergence_2026_07_20.md todo 10 /
data_pipeline_reconciliation_skill_2026_07_20.md todo 39: the oracle used to
hardcode ``raw_tick_data/by_date/`` and false-flag every candle path as
``structural`` (both the canonical-ish and the orphan shape identically). This
extends it to validate the LOCKED candle template (CORRECTED RULING
2026-07-21) with a ``require_candle_migration_complete`` suppression toggle
(default False — mirrors taxonomy exception AE-6) so the pre-migration corpus
does not manufacture fresh false positives.
"""

from __future__ import annotations

from unified_api_contracts import canonical_path_violations, is_canonical
from unified_api_contracts.canonical.partition_paths import PROCESSED_CANDLES_PREFIX

# Measured 2026-07-20 real prod object (cefi, canonical-ish — has pipeline_mode,
# no instrument_type=).
_CEFI_OLD_SHAPE = (
    "processed_candles/by_date/day=2019-03-30/pipeline_mode=batch_tardis/timeframe=15m/"
    "data_type=derivative_ticker/venue=DERIBIT/DERIBIT:PERPETUAL:BTC-PERPETUAL.parquet"
)

# Measured 2026-07-20 real prod object (cefi, ADDENDUM iii-a orphan — no
# pipeline_mode= segment at all).
_CEFI_ORPHAN_SHAPE = (
    "processed_candles/by_date/day=2026-05-23/timeframe=15m/data_type=ohlcv_15m/"
    "venue=COINBASE-SPOT/COINBASE-SPOT:spot_pair:BTC-USDT.parquet"
)

# LOCKED shape (ratified 2026-07-21) — the post-migration target.
_CEFI_LOCKED_SHAPE = (
    "processed_candles/by_date/day=2019-03-30/pipeline_mode=batch_tardis/timeframe=15m/"
    "data_type=derivative_ticker/instrument_type=perpetual/venue=DERIBIT/"
    "DERIBIT:PERPETUAL:BTC-PERPETUAL.parquet"
)

# Prediction shape — instrument_type= is the TERMINAL axis, no venue= ever
# (unchanged by the migration; per-asset-group-bucket-layouts.md).
_PREDICTION_SHAPE = (
    "processed_candles/by_date/day=2026-04-17/timeframe=1h/data_type=trades/"
    "instrument_type=binary_option/0xabc123.parquet"
)

# Measured 2026-07-20 real defect: an empty instrument stem (a chain-bundle
# write that never got its bundled ``ticks.parquet`` name).
_EMPTY_STEM_SHAPE = (
    "processed_candles/by_date/day=2019-05-08/pipeline_mode=batch_tardis/timeframe=15m/"
    "data_type=trades/venue=DERIBIT/underlying=BTC/.parquet"
)


# ---------------------------------------------------------------------------
# migration_pending window (default require_candle_migration_complete=False):
# the pre-migration corpus must NOT manufacture false positives.
# ---------------------------------------------------------------------------


def test_old_shape_canonical_by_default_during_migration_window() -> None:
    assert is_canonical(_CEFI_OLD_SHAPE), canonical_path_violations(_CEFI_OLD_SHAPE)


def test_orphan_split_brain_shape_canonical_by_default_during_migration_window() -> None:
    """ADDENDUM iii-a: the pipeline_mode-less orphan must ALSO be suppressed."""
    assert is_canonical(_CEFI_ORPHAN_SHAPE), canonical_path_violations(_CEFI_ORPHAN_SHAPE)


def test_locked_shape_is_canonical_during_migration_window_too() -> None:
    """The NEW shape must round-trip clean regardless of the suppression flag."""
    assert is_canonical(_CEFI_LOCKED_SHAPE), canonical_path_violations(_CEFI_LOCKED_SHAPE)


def test_prediction_shape_is_canonical() -> None:
    assert is_canonical(_PREDICTION_SHAPE), canonical_path_violations(_PREDICTION_SHAPE)


# ---------------------------------------------------------------------------
# require_candle_migration_complete=True — enforce the LOCKED shape.
# ---------------------------------------------------------------------------


def test_old_shape_rejected_once_migration_required() -> None:
    violations = canonical_path_violations(_CEFI_OLD_SHAPE, require_candle_migration_complete=True)
    assert any("instrument_type=" in v for v in violations), violations
    assert not is_canonical(_CEFI_OLD_SHAPE, require_candle_migration_complete=True)


def test_orphan_shape_rejected_on_missing_pipeline_mode_once_migration_required() -> None:
    violations = canonical_path_violations(_CEFI_ORPHAN_SHAPE, require_candle_migration_complete=True)
    assert any("pipeline_mode=" in v for v in violations), violations
    assert any("instrument_type=" in v for v in violations), violations


def test_locked_shape_stays_canonical_once_migration_required() -> None:
    assert is_canonical(_CEFI_LOCKED_SHAPE, require_candle_migration_complete=True), canonical_path_violations(
        _CEFI_LOCKED_SHAPE, require_candle_migration_complete=True
    )


def test_prediction_shape_stays_canonical_once_migration_required() -> None:
    """Prediction already carries instrument_type= — the migration doesn't touch it."""
    assert is_canonical(_PREDICTION_SHAPE, require_candle_migration_complete=True)


# ---------------------------------------------------------------------------
# Genuine defects — NEVER suppressed by migration_pending.
# ---------------------------------------------------------------------------


def test_empty_stem_is_always_flagged() -> None:
    for require_complete in (False, True):
        violations = canonical_path_violations(_EMPTY_STEM_SHAPE, require_candle_migration_complete=require_complete)
        assert any("empty instrument stem" in v for v in violations), violations


# ---------------------------------------------------------------------------
# Baseline structural checks (day=, pipeline_mode value format, missing axes).
# ---------------------------------------------------------------------------


def test_missing_timeframe_always_flagged() -> None:
    bad = _CEFI_LOCKED_SHAPE.replace("timeframe=15m/", "")
    violations = canonical_path_violations(bad)
    assert any("timeframe=" in v for v in violations), violations


def test_missing_data_type_always_flagged() -> None:
    bad = _CEFI_LOCKED_SHAPE.replace("data_type=derivative_ticker/", "")
    violations = canonical_path_violations(bad)
    assert any("data_type=" in v for v in violations), violations


def test_malformed_pipeline_mode_value_flagged_even_during_migration_window() -> None:
    bad = _CEFI_OLD_SHAPE.replace("pipeline_mode=batch_tardis", "pipeline_mode=batch")
    violations = canonical_path_violations(bad)
    assert any("pipeline_mode value" in v for v in violations), violations


def test_hyphen_day_segment_rejected() -> None:
    bad = _CEFI_LOCKED_SHAPE.replace("day=2019-03-30", "day-2019-03-30")
    violations = canonical_path_violations(bad)
    assert any("hyphen day" in v for v in violations), violations


def test_no_partition_segments_after_prefix() -> None:
    violations = canonical_path_violations(PROCESSED_CANDLES_PREFIX + "onlyfile.parquet")
    assert any("no partition segments" in v for v in violations), violations


# ---------------------------------------------------------------------------
# Sports stays out of scope (different root, ``processed/`` not
# ``processed_candles/``) — falls through to the unrecognized-prefix branch,
# same as any other unknown path family.
# ---------------------------------------------------------------------------


def test_sports_processed_root_is_out_of_scope_unrecognized_prefix() -> None:
    sports_path = "processed/by_date/day=2026-04-17/data_type=odds_horizon_bucket/bucketed.parquet"
    violations = canonical_path_violations(sports_path)
    assert any("does not start with a recognized canonical prefix" in v for v in violations), violations


def test_raw_tick_data_namespace_is_unaffected_by_the_candle_extension() -> None:
    """Regression: extending the dispatcher must not perturb the raw_tick_data branch."""
    good = (
        "raw_tick_data/by_date/day=2026-04-17/asset_group=defi/venue=AAVE_V3/chain=ETHEREUM/"
        "instrument_type=a_token/data_type=lending_indices/AAVE_V3-ETHEREUM:A_TOKEN:aUSDC.parquet"
    )
    assert is_canonical(good), canonical_path_violations(good)
