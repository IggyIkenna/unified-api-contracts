"""TradFi synthetic-generator seeds — minimal :class:`SyntheticGeneratorSpec` set for the cross-asset hedge overlay.

Phase 1.B of ``mock_data_pipeline_benchmarking_2026_05_10.md``. The
cutover archetypes are CeFi + DeFi; TradFi is only touched by the
cross-asset hedge-overlay path the work-split scope names ("DeFi + CeFi +
TradFi simulation paths"). So this module ships only two low-cardinality
OHLCV generators (1-minute + daily bars) sharded ``(venue, instrument)``
where ``venue`` is the data source (``databento`` / ``barchart``) — enough
to exercise the TradFi reader path in the benchmark harness without
re-deriving the full TradFi universe.

Full TradFi generator coverage (tick / order-book / corporate-actions /
index-constituents) is DEFERRED post-cutover per the plan's "Deferred
work" table.
"""

from __future__ import annotations

from typing import Final

from ...canonical.crosscutting.synthetic_generator import (
    SyntheticDataDomain,
    SyntheticGeneratorId,
    SyntheticGeneratorSpec,
    register_generator,
)

# Representative TradFi instruments the cross-asset hedge overlay references (equity index + rates + FX proxies).
CUTOVER_TRADFI_INSTRUMENTS: Final[tuple[str, ...]] = ("ES", "NQ", "ZN", "GC", "DXY")
CUTOVER_TRADFI_SOURCES: Final[tuple[str, ...]] = ("databento",)

_TRADFI_PARTITION: Final = "asset_group={asset_group}/data_type={data_type}/venue={venue}/instrument={instrument}/dt={dt}"

TRADFI_OHLCV_1M_SPEC = SyntheticGeneratorSpec(
    generator_id=SyntheticGeneratorId.TRADFI_OHLCV_1M,
    domain=SyntheticDataDomain.TRADFI_OHLCV,
    asset_group="tradfi",
    data_type="ohlcv_1m",
    schema_version="ohlcv.v2",
    # ~390 RTH minutes/day (equities) up to ~1380 (futures near-24h) per cell; model 1380 * 5 cells.
    default_row_count_per_day=6_900,
    default_shard_key_axes=("venue", "instrument"),
    default_partition_template=_TRADFI_PARTITION,
    archetypes_consuming=frozenset({"carry_staked_basis", "leveraged_funding_arb"}),
    pipeline_stages_touching=("mtds_read", "mdps_compute", "features", "strategy"),
    description="1-minute TradFi OHLCV bars (index futures + rates + FX proxy); cross-asset hedge-overlay regime input.",
)

TRADFI_OHLCV_1D_SPEC = SyntheticGeneratorSpec(
    generator_id=SyntheticGeneratorId.TRADFI_OHLCV_1D,
    domain=SyntheticDataDomain.TRADFI_OHLCV,
    asset_group="tradfi",
    data_type="ohlcv_1d",
    schema_version="ohlcv.v2",
    default_row_count_per_day=5,  # 1 bar/day * 5 cells
    default_shard_key_axes=("venue", "instrument"),
    default_partition_template=_TRADFI_PARTITION,
    archetypes_consuming=frozenset({"carry_staked_basis", "leveraged_funding_arb"}),
    pipeline_stages_touching=("mtds_read", "features", "strategy"),
    description="Daily TradFi OHLCV bars; long-window cross-asset correlation feature input.",
)

SPECS: Final[tuple[SyntheticGeneratorSpec, ...]] = (
    TRADFI_OHLCV_1M_SPEC,
    TRADFI_OHLCV_1D_SPEC,
)

for _spec in SPECS:
    register_generator(_spec)

__all__ = [
    "CUTOVER_TRADFI_INSTRUMENTS",
    "CUTOVER_TRADFI_SOURCES",
    "SPECS",
    "TRADFI_OHLCV_1D_SPEC",
    "TRADFI_OHLCV_1M_SPEC",
]
