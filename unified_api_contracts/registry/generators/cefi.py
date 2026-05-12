"""CeFi synthetic-generator seeds — :class:`SyntheticGeneratorSpec` instances for the ``leveraged_funding_arb`` / ``ARBITRAGE_PRICE_DISPERSION`` cutover archetype.

Phase 1.B of ``mock_data_pipeline_benchmarking_2026_05_10.md``. Six
generators covering the CeFi data_types the cutover hedge + arb legs read:
``trades`` / ``ohlcv_1m`` / ``ohlcv_15m`` / ``funding_rate`` /
``open_interest`` / ``liquidations`` across the 6 cutover perp venues.

Per-day row counts are realism-axis-1 defaults; calibrate against real
backfill samples per plan § Audit findings 0.B before the Phase 5 VM runs.
Shard-key axes match the per-asset_group shard-atom matrix in
``plans/epics/infrastructure_master_2026_05_07.md`` (CeFi tick/bar/derivative
data sharded ``(venue, instrument)``).
"""

from __future__ import annotations

from typing import Final

from ...canonical.crosscutting.synthetic_generator import (
    SyntheticDataDomain,
    SyntheticGeneratorId,
    SyntheticGeneratorSpec,
    register_generator,
)

# Cutover CeFi perp venues (lowercase short-names per CLAUDE.md vocab).
CUTOVER_CEFI_VENUES: Final[tuple[str, ...]] = ("bybit", "deribit", "binance", "okx", "hyperliquid", "aster")

# Representative cutover instrument set (the arb/hedge legs trade these).
CUTOVER_CEFI_INSTRUMENTS: Final[tuple[str, ...]] = ("BTCUSDT", "ETHUSDT", "SOLUSDT")

_CEFI_TICK_PARTITION: Final = "asset_group={asset_group}/data_type={data_type}/venue={venue}/instrument={instrument}/dt={dt}"
_CEFI_DERIV_PARTITION: Final = _CEFI_TICK_PARTITION

# n_shards default = len(venues) * len(instruments) = 6 * 3 = 18 cells.

CEFI_TRADES_SPEC = SyntheticGeneratorSpec(
    generator_id=SyntheticGeneratorId.CEFI_TRADES,
    domain=SyntheticDataDomain.CEFI_TICK,
    asset_group="cefi",
    data_type="trades",
    schema_version="trades.v3",
    default_row_count_per_day=1_800_000,  # ~100k trades/day/cell * 18 cells (axis-1 estimate)
    default_shard_key_axes=("venue", "instrument"),
    default_partition_template=_CEFI_TICK_PARTITION,
    archetypes_consuming=frozenset({"ARBITRAGE_PRICE_DISPERSION", "leveraged_funding_arb"}),
    pipeline_stages_touching=("mtds_read", "mdps_compute", "features", "strategy", "matching_engine"),
    description="Per-venue per-instrument trade ticks for the CeFi arb/hedge legs; highest-cardinality CeFi data_type.",
)

CEFI_OHLCV_1M_SPEC = SyntheticGeneratorSpec(
    generator_id=SyntheticGeneratorId.CEFI_OHLCV_1M,
    domain=SyntheticDataDomain.CEFI_OHLCV,
    asset_group="cefi",
    data_type="ohlcv_1m",
    schema_version="ohlcv.v2",
    default_row_count_per_day=25_920,  # 1440 bars/day * 18 cells
    default_shard_key_axes=("venue", "instrument"),
    default_partition_template=_CEFI_TICK_PARTITION,
    archetypes_consuming=frozenset({"ARBITRAGE_PRICE_DISPERSION", "leveraged_funding_arb"}),
    pipeline_stages_touching=("mtds_read", "mdps_compute", "features", "ml_inference", "strategy"),
    description="1-minute OHLCV bars per (venue, instrument); MDPS-computed but also a direct features-* input.",
)

CEFI_OHLCV_15M_SPEC = SyntheticGeneratorSpec(
    generator_id=SyntheticGeneratorId.CEFI_OHLCV_15M,
    domain=SyntheticDataDomain.CEFI_OHLCV,
    asset_group="cefi",
    data_type="ohlcv_15m",
    schema_version="ohlcv.v2",
    default_row_count_per_day=1_728,  # 96 bars/day * 18 cells
    default_shard_key_axes=("venue", "instrument"),
    default_partition_template=_CEFI_TICK_PARTITION,
    archetypes_consuming=frozenset({"ARBITRAGE_PRICE_DISPERSION", "leveraged_funding_arb"}),
    pipeline_stages_touching=("mtds_read", "mdps_compute", "features", "ml_inference", "strategy"),
    description="15-minute OHLCV bars per (venue, instrument); volatility-feature window input.",
)

CEFI_FUNDING_RATE_SPEC = SyntheticGeneratorSpec(
    generator_id=SyntheticGeneratorId.CEFI_FUNDING_RATE,
    domain=SyntheticDataDomain.CEFI_DERIVATIVES,
    asset_group="cefi",
    data_type="funding_rate",
    schema_version="funding_rate.v2",
    default_row_count_per_day=432,  # up to 24 settlements/day (hourly venues) * 18 cells
    default_shard_key_axes=("venue", "instrument"),
    default_partition_template=_CEFI_DERIV_PARTITION,
    archetypes_consuming=frozenset({"ARBITRAGE_PRICE_DISPERSION", "leveraged_funding_arb"}),
    pipeline_stages_touching=("mtds_read", "features", "strategy"),
    description="Per-venue per-instrument funding-rate settlements; THE carry signal for leveraged_funding_arb.",
)

CEFI_OPEN_INTEREST_SPEC = SyntheticGeneratorSpec(
    generator_id=SyntheticGeneratorId.CEFI_OPEN_INTEREST,
    domain=SyntheticDataDomain.CEFI_DERIVATIVES,
    asset_group="cefi",
    data_type="open_interest",
    schema_version="open_interest.v1",
    default_row_count_per_day=25_920,  # 1440 1-min OI snapshots/day * 18 cells
    default_shard_key_axes=("venue", "instrument"),
    default_partition_template=_CEFI_DERIV_PARTITION,
    archetypes_consuming=frozenset({"ARBITRAGE_PRICE_DISPERSION", "leveraged_funding_arb"}),
    pipeline_stages_touching=("mtds_read", "features", "strategy"),
    description="Per-venue per-instrument open-interest snapshots; crowding/positioning feature input.",
)

CEFI_LIQUIDATIONS_SPEC = SyntheticGeneratorSpec(
    generator_id=SyntheticGeneratorId.CEFI_LIQUIDATIONS,
    domain=SyntheticDataDomain.CEFI_DERIVATIVES,
    asset_group="cefi",
    data_type="liquidations",
    schema_version="liquidations.v1",
    default_row_count_per_day=90_000,  # ~5k events/day/cell on a volatile day * 18 cells
    default_shard_key_axes=("venue", "instrument"),
    default_partition_template=_CEFI_DERIV_PARTITION,
    archetypes_consuming=frozenset({"ARBITRAGE_PRICE_DISPERSION", "leveraged_funding_arb"}),
    pipeline_stages_touching=("mtds_read", "features", "strategy"),
    description="Per-venue per-instrument liquidation events; cascade/stress feature input (bursty cardinality).",
)

SPECS: Final[tuple[SyntheticGeneratorSpec, ...]] = (
    CEFI_TRADES_SPEC,
    CEFI_OHLCV_1M_SPEC,
    CEFI_OHLCV_15M_SPEC,
    CEFI_FUNDING_RATE_SPEC,
    CEFI_OPEN_INTEREST_SPEC,
    CEFI_LIQUIDATIONS_SPEC,
)

for _spec in SPECS:
    register_generator(_spec)

__all__ = [
    "CEFI_FUNDING_RATE_SPEC",
    "CEFI_LIQUIDATIONS_SPEC",
    "CEFI_OHLCV_15M_SPEC",
    "CEFI_OHLCV_1M_SPEC",
    "CEFI_OPEN_INTEREST_SPEC",
    "CEFI_TRADES_SPEC",
    "CUTOVER_CEFI_INSTRUMENTS",
    "CUTOVER_CEFI_VENUES",
    "SPECS",
]
