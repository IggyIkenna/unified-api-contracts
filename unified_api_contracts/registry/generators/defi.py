"""DeFi synthetic-generator seeds — :class:`SyntheticGeneratorSpec` instances for the ``carry_staked_basis`` cutover archetype (lead).

Phase 1.B of ``mock_data_pipeline_benchmarking_2026_05_10.md``. Five
generators covering the on-chain data_types ``carry_staked_basis`` reads:
``gas`` (per chain-slot) / ``lst_rates`` (LST exchange-rate snapshots) /
``lending_indices`` (Aave + Morpho supply/borrow indices) /
``dex_pool_state`` (Uniswap-V3 + Curve-V2 pool snapshots) /
``oracle_feeds`` (Pyth Hermes batches + Chainlink aggregator rounds).

Shard atoms per the per-asset_group matrix in
``plans/epics/infrastructure_master_2026_05_07.md``: gas is ``(chain,)``;
LST rates / lending indices are ``(chain, protocol)``; DEX pool state is
``(chain, pool)`` (pool == protocol-instance here); oracle feeds are
``(chain, oracle_feed)``.

Per-day row counts are realism-axis-1 estimates — chain block/slot rates
differ ~50x (Ethereum ~7.2k blocks/day vs Solana ~216k slots/day vs
Arbitrum ~350k blocks/day at 250ms); the UTL generator distributes
``row_count_per_day`` across shards weighted by a per-chain block-rate
table, NOT uniformly. Calibrate against real backfill samples per plan
§ Audit findings 0.B.
"""

from __future__ import annotations

from typing import Final

from ...canonical.crosscutting.synthetic_generator import (
    SyntheticDataDomain,
    SyntheticGeneratorId,
    SyntheticGeneratorSpec,
    register_generator,
)

# Cutover chains carry_staked_basis touches (lowercase keys per CLAUDE.md vocab).
CUTOVER_DEFI_EVM_CHAINS: Final[tuple[str, ...]] = ("ethereum", "arbitrum", "optimism", "base")
CUTOVER_DEFI_CHAINS: Final[tuple[str, ...]] = (*CUTOVER_DEFI_EVM_CHAINS, "solana")

# LST assets — Solana (jitoSOL/mSOL/bSOL via Marinade/Jito/BlazeStake) + EVM (wstETH/rETH/cbETH via Lido/Rocket/Coinbase).
CUTOVER_LST_PROTOCOLS: Final[tuple[str, ...]] = (
    "marinade",
    "jito",
    "blazestake",
    "lido",
    "rocket_pool",
    "coinbase_cbeth",
)

# Lending protocols for the recursive-staked / yield-rotation legs.
CUTOVER_LENDING_PROTOCOLS: Final[tuple[str, ...]] = ("aave_v3", "morpho")

# DEX pools for the basis hedge swap legs (protocol-instance granularity).
CUTOVER_DEX_POOLS: Final[tuple[str, ...]] = (
    "uniswap_v3_wsteth_eth",
    "uniswap_v3_reth_eth",
    "curve_v2_steth_eth",
    "uniswap_v3_jitosol_sol",
)

# Oracle feeds — Pyth (Solana) + Chainlink (EVM) price feeds the archetype's mark uses.
CUTOVER_ORACLE_FEEDS: Final[tuple[str, ...]] = (
    "pyth_sol_usd",
    "pyth_jitosol_sol",
    "chainlink_eth_usd",
    "chainlink_wsteth_eth",
    "chainlink_reth_eth",
)

_CHAIN_PARTITION: Final = "asset_group={asset_group}/data_type={data_type}/chain={chain}/dt={dt}"
_CHAIN_PROTOCOL_PARTITION: Final = (
    "asset_group={asset_group}/data_type={data_type}/chain={chain}/protocol={protocol}/dt={dt}"
)
_CHAIN_POOL_PARTITION: Final = "asset_group={asset_group}/data_type={data_type}/chain={chain}/pool={pool}/dt={dt}"
_CHAIN_ORACLE_PARTITION: Final = (
    "asset_group={asset_group}/data_type={data_type}/chain={chain}/oracle_feed={oracle_feed}/dt={dt}"
)

DEFI_GAS_SPEC = SyntheticGeneratorSpec(
    generator_id=SyntheticGeneratorId.DEFI_GAS,
    domain=SyntheticDataDomain.DEFI_ONCHAIN,
    asset_group="defi",
    data_type="gas",
    schema_version="gas.v2",
    # ETH ~7.2k + ARB ~350k + OP ~43.2k + BASE ~43.2k + SOL ~216k = ~660k blocks/day total.
    default_row_count_per_day=660_000,
    default_shard_key_axes=("chain",),
    default_partition_template=_CHAIN_PARTITION,
    archetypes_consuming=frozenset({"carry_staked_basis", "leveraged_funding_arb"}),
    pipeline_stages_touching=("mtds_read", "features", "strategy", "matching_engine"),
    description="Per-chain per-block base-fee / priority-fee rows; tx-cost input for the on-chain hedge legs.",
)

DEFI_LST_RATES_SPEC = SyntheticGeneratorSpec(
    generator_id=SyntheticGeneratorId.DEFI_LST_RATES,
    domain=SyntheticDataDomain.DEFI_RATES,
    asset_group="defi",
    data_type="lst_rates",
    schema_version="lst_rates.v1",
    # ~1 snapshot/epoch on Solana (~2-day epoch -> sub-daily) + per-block-ish on EVM; model ~96 (15-min) snapshots/day/cell.
    default_row_count_per_day=576,  # 96 * 6 LST protocol cells
    default_shard_key_axes=("chain", "protocol"),
    default_partition_template=_CHAIN_PROTOCOL_PARTITION,
    archetypes_consuming=frozenset({"carry_staked_basis"}),
    pipeline_stages_touching=("mtds_read", "features", "strategy"),
    description="LST exchange-rate snapshots (jitoSOL/mSOL/bSOL/wstETH/rETH/cbETH); THE staking-yield signal.",
)

DEFI_LENDING_INDICES_SPEC = SyntheticGeneratorSpec(
    generator_id=SyntheticGeneratorId.DEFI_LENDING_INDICES,
    domain=SyntheticDataDomain.DEFI_RATES,
    asset_group="defi",
    data_type="lending_indices",
    schema_version="lending_indices.v2",
    # Per-reserve supply/borrow index ~hourly snapshots; ~24/day/cell, ~5 reserves * 2 protocols * 5 chains -> model 24 * 50 cells.
    default_row_count_per_day=1_200,
    default_shard_key_axes=("chain", "protocol"),
    default_partition_template=_CHAIN_PROTOCOL_PARTITION,
    archetypes_consuming=frozenset({"carry_staked_basis"}),
    pipeline_stages_touching=("mtds_read", "features", "strategy"),
    description="Aave-V3 + Morpho supply/borrow index snapshots; borrow-cost input for the recursive-staked leg.",
)

DEFI_DEX_POOL_STATE_SPEC = SyntheticGeneratorSpec(
    generator_id=SyntheticGeneratorId.DEFI_DEX_POOL_STATE,
    domain=SyntheticDataDomain.DEFI_DEX,
    asset_group="defi",
    data_type="dex_pool_state",
    schema_version="dex_pool_state.v1",
    # Per-pool reserves/sqrtPrice/tick/liquidity snapshot ~per block on the pool's chain; model ~1440 (1-min) snapshots/day/cell.
    default_row_count_per_day=5_760,  # 1440 * 4 pool cells
    default_shard_key_axes=("chain", "pool"),
    default_partition_template=_CHAIN_POOL_PARTITION,
    archetypes_consuming=frozenset({"carry_staked_basis"}),
    pipeline_stages_touching=("mtds_read", "features", "strategy", "matching_engine"),
    description="Uniswap-V3 + Curve-V2 pool-state snapshots (reserves, sqrtPriceX96, tick, liquidity); hedge-swap slippage input.",
)

DEFI_ORACLE_FEEDS_SPEC = SyntheticGeneratorSpec(
    generator_id=SyntheticGeneratorId.DEFI_ORACLE_FEEDS,
    domain=SyntheticDataDomain.DEFI_ORACLE,
    asset_group="defi",
    data_type="oracle_feeds",
    schema_version="oracle_feeds.v1",
    # Pyth Hermes ~per slot (~400ms) on Solana; Chainlink aggregator rounds ~heartbeat (1h) + deviation; model ~1440 (1-min) rows/day/cell.
    default_row_count_per_day=7_200,  # 1440 * 5 oracle-feed cells
    default_shard_key_axes=("chain", "oracle_feed"),
    default_partition_template=_CHAIN_ORACLE_PARTITION,
    archetypes_consuming=frozenset({"carry_staked_basis"}),
    pipeline_stages_touching=("mtds_read", "features", "strategy"),
    description="Pyth Hermes batches + Chainlink aggregator rounds; the mark-price oracle input for carry_staked_basis.",
)

SPECS: Final[tuple[SyntheticGeneratorSpec, ...]] = (
    DEFI_GAS_SPEC,
    DEFI_LST_RATES_SPEC,
    DEFI_LENDING_INDICES_SPEC,
    DEFI_DEX_POOL_STATE_SPEC,
    DEFI_ORACLE_FEEDS_SPEC,
)

for _spec in SPECS:
    register_generator(_spec)

__all__ = [
    "CUTOVER_DEFI_CHAINS",
    "CUTOVER_DEFI_EVM_CHAINS",
    "CUTOVER_DEX_POOLS",
    "CUTOVER_LENDING_PROTOCOLS",
    "CUTOVER_LST_PROTOCOLS",
    "CUTOVER_ORACLE_FEEDS",
    "DEFI_DEX_POOL_STATE_SPEC",
    "DEFI_GAS_SPEC",
    "DEFI_LENDING_INDICES_SPEC",
    "DEFI_LST_RATES_SPEC",
    "DEFI_ORACLE_FEEDS_SPEC",
    "SPECS",
]
