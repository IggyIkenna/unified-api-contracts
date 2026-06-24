"""Synthetic generator enums and constants."""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class SyntheticDataDomain(StrEnum):
    """High-level shape family for a synthetic generator.

    Closed-set 8. Lets UTL ``synthetic/generator.py`` dispatch a
    shape-family writer (each family shares a parquet column skeleton +
    cardinality model) without re-deriving from the id.
    """

    CEFI_TICK = "CEFI_TICK"
    """CeFi trade / orderbook tick rows (per-event grain)."""
    CEFI_OHLCV = "CEFI_OHLCV"
    """CeFi bar rows (ohlcv_1m / ohlcv_15m / ohlcv_1h / ohlcv_24h)."""
    CEFI_DERIVATIVES = "CEFI_DERIVATIVES"
    """CeFi funding-rate / open-interest / liquidation rows."""
    DEFI_ONCHAIN = "DEFI_ONCHAIN"
    """On-chain primitives — block gas / priority fee / base fee per chain-slot."""
    DEFI_RATES = "DEFI_RATES"
    """LST exchange rates + lending-protocol supply/borrow indices."""
    DEFI_DEX = "DEFI_DEX"
    """DEX pool-state snapshots (reserves, sqrtPriceX96, tick, liquidity)."""
    DEFI_ORACLE = "DEFI_ORACLE"
    """Oracle-feed rows (Pyth Hermes batches, Chainlink aggregator rounds)."""
    TRADFI_OHLCV = "TRADFI_OHLCV"
    """TradFi bar rows (Databento equities + futures + index)."""


class SyntheticGeneratorId(StrEnum):
    """Closed-set generator identifier — one per ``(asset_group, data_type)`` a cutover archetype consumes.

    Naming: ``<asset_group>_<data_type>`` (snake_case ASCII). Reviewers
    reject a :class:`SyntheticGeneratorSpec` whose ``generator_id`` is not a
    member here. Extending the set requires the 4-step "Adding a new
    generator" workflow in the module docstring.

    Pre-cutover members cover the 2 cutover archetypes only (DeFi
    ``carry_staked_basis`` lead + CeFi ``leveraged_funding_arb`` /
    ``ARBITRAGE_PRICE_DISPERSION``) plus a minimal TradFi-OHLCV path for
    the cross-asset hedge overlay.
    """

    # ----- CeFi (leveraged_funding_arb / ARBITRAGE_PRICE_DISPERSION) ---------
    CEFI_TRADES = "cefi_trades"
    CEFI_OHLCV_1M = "cefi_ohlcv_1m"
    CEFI_OHLCV_15M = "cefi_ohlcv_15m"
    CEFI_FUNDING_RATE = "cefi_funding_rate"
    CEFI_OPEN_INTEREST = "cefi_open_interest"
    CEFI_LIQUIDATIONS = "cefi_liquidations"

    # ----- DeFi (carry_staked_basis) ----------------------------------------
    DEFI_GAS = "defi_gas"
    DEFI_LST_RATES = "defi_lst_rates"
    DEFI_LENDING_INDICES = "defi_lending_indices"
    DEFI_DEX_POOL_STATE = "defi_dex_pool_state"
    DEFI_ORACLE_FEEDS = "defi_oracle_feeds"

    # ----- TradFi (cross-asset hedge overlay) -------------------------------
    TRADFI_OHLCV_1M = "tradfi_ohlcv_1m"
    TRADFI_OHLCV_1D = "tradfi_ohlcv_1d"


class SyntheticRealismAxis(StrEnum):
    """How faithful the synthetic rows are to real data.

    Closed-set 4 (ordered). The benchmark harness only needs axes 1-3 —
    bottleneck measurement is driven by *data shape* (row count, byte size,
    shard count), not *data value*. Axis 4 (calibrated dynamics for value
    correctness) is DEFERRED post-cutover; the cutover pipelines are
    shape-driven not value-driven.
    """

    CARDINALITY = "CARDINALITY"
    """Axis 1: correct row count per ``(generator, day, shard)``; values are
    cheap RNG fills with the right dtypes + monotone timestamps."""
    PARQUET_SIZE = "PARQUET_SIZE"
    """Axis 2: axis-1 + per-shard byte size within +/-20% of a real
    backfill sample (string-column width, dictionary-encoding ratio)."""
    SHARD_COUNT = "SHARD_COUNT"
    """Axis 3: axis-2 + correct shard fan-out (per-venue / per-instrument /
    per-chain) so GCS / S3 listing depth matches prod."""
    CALIBRATED_DYNAMICS = "CALIBRATED_DYNAMICS"
    """Axis 4 (DEFERRED post-cutover): axis-3 + calibrated GBM / SDE value
    paths for correctness benchmarking. Not shipped pre-cutover."""


SHARD_AXIS_PATTERN: Final = frozenset(
    {"venue", "instrument", "chain", "protocol", "pool", "oracle_feed", "data_type", "day"},
)
"""The closed set of shard-key axes a synthetic generator may fan out on.

Must be a subset of the per-asset_group shard-atom matrix in
``plans/epics/infrastructure_master.md`` — drift between this
list and that matrix is a silent correctness bug per CLAUDE.md
"Shard-granularity SSOT (CRITICAL)".
"""


__all__ = [
    "SHARD_AXIS_PATTERN",
    "SyntheticDataDomain",
    "SyntheticGeneratorId",
    "SyntheticRealismAxis",
]
