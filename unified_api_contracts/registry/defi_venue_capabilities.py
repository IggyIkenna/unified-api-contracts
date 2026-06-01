"""DeFi portion of VENUE_DATA_TYPE_CAPABILITIES — extracted from market_data_categories.py.

Keeps the main capabilities file under the 900-line QG ceiling as the
multi-chain DEFI venue count grows. Imported and merged into the main
``VENUE_DATA_TYPE_CAPABILITIES`` dict at module-load time.

Per-(venue, data_type) start dates sourced from public protocol launch
records (best-effort floors; adapters gate per-row via
``get_venue_data_type_start_date``).

SSOT: ``codex/02-data/mtds-data-source-coverage-matrix.md`` §4 (DEFI
multi-chain expansion) + §3 (data_type axes).
"""

from __future__ import annotations

DEFI_VENUE_DATA_TYPE_CAPABILITIES: dict[str, dict[str, str]] = {
    # ── DeFi — DEX protocols (dex_swaps + dex_pools) ──
    "UNISWAP_V2-ETHEREUM": {"dex_swaps": "2020-05-06", "dex_pools": "2020-05-06"},
    "UNISWAP_V3-ETHEREUM": {
        "dex_swaps": "2021-05-05",
        "dex_pools": "2021-05-05",
        "position_data": "2021-05-05",  # LP position data (top 1000 by liquidity)
    },
    "UNISWAP_V3-ARBITRUM": {"dex_swaps": "2021-06-18", "dex_pools": "2021-06-18"},
    "UNISWAP_V3-BASE": {"dex_swaps": "2023-09-03", "dex_pools": "2023-09-03"},
    "UNISWAP_V3-OPTIMISM": {"dex_swaps": "2021-11-12", "dex_pools": "2021-11-12"},
    "UNISWAP_V3-POLYGON": {"dex_swaps": "2021-12-22", "dex_pools": "2021-12-22"},
    "UNISWAP_V4-ETHEREUM": {"dex_swaps": "2025-01-30", "dex_pools": "2025-01-30"},
    "CURVE-ETHEREUM": {"dex_swaps": "2020-01-20", "dex_pools": "2020-01-20"},
    "CURVE-AVALANCHE": {"dex_swaps": "2021-11-10", "dex_pools": "2021-11-10"},
    "CURVE-OPTIMISM": {"dex_swaps": "2022-01-13", "dex_pools": "2022-01-13"},
    "BALANCER-ETHEREUM": {"dex_swaps": "2021-04-22", "dex_pools": "2021-04-22"},
    "BALANCER-ARBITRUM": {"dex_swaps": "2021-08-27", "dex_pools": "2021-08-27"},
    "BALANCER-AVALANCHE": {"dex_swaps": "2023-08-17", "dex_pools": "2023-08-17"},
    "BALANCER-BASE": {"dex_swaps": "2023-07-29", "dex_pools": "2023-07-29"},
    "BALANCER-OPTIMISM": {"dex_swaps": "2022-05-20", "dex_pools": "2022-05-20"},
    "BALANCER-POLYGON": {"dex_swaps": "2021-06-24", "dex_pools": "2021-06-24"},
    # ── DeFi — Lending protocols ──
    "AAVE_V3-ETHEREUM": {
        "lending_indices": "2023-01-27",
        "oracle_prices": "2023-01-27",
        "rewards": "2023-01-27",
        "risk_params": "2023-01-27",
        "liquidation_events": "2023-01-27",  # LiquidationCall events via subgraph
        "flash_loan_events": "2023-01-27",  # FlashLoan events via subgraph
        "position_data": "2023-01-27",  # Top-500 user positions by supplied_usd
    },
    "AAVE_V3-ARBITRUM": {
        "lending_indices": "2022-03-12",
        "oracle_prices": "2022-03-12",
        "rewards": "2022-03-12",
        "risk_params": "2022-03-12",
        "liquidation_events": "2022-03-12",
        "flash_loan_events": "2022-03-12",
        "position_data": "2022-03-12",
    },
    "AAVE_V3-AVALANCHE": {
        "lending_indices": "2022-03-12",
        "oracle_prices": "2022-03-12",
        "rewards": "2022-03-12",
        "risk_params": "2022-03-12",
    },
    "AAVE_V3-BASE": {
        "lending_indices": "2023-08-23",
        "oracle_prices": "2023-08-23",
        "rewards": "2023-08-23",
        "risk_params": "2023-08-23",
    },
    "AAVE_V3-BSC": {
        "lending_indices": "2024-01-24",
        "oracle_prices": "2024-01-24",
        "rewards": "2024-01-24",
        "risk_params": "2024-01-24",
    },
    "AAVE_V3-LINEA": {
        "lending_indices": "2025-02-12",
        "oracle_prices": "2025-02-12",
        "rewards": "2025-02-12",
        "risk_params": "2025-02-12",
    },
    "AAVE_V3-OPTIMISM": {
        "lending_indices": "2022-03-12",
        "oracle_prices": "2022-03-12",
        "rewards": "2022-03-12",
        "risk_params": "2022-03-12",
    },
    "AAVE_V3-POLYGON": {
        "lending_indices": "2022-03-12",
        "oracle_prices": "2022-03-12",
        "rewards": "2022-03-12",
        "risk_params": "2022-03-12",
        "liquidation_events": "2022-03-12",
        "flash_loan_events": "2022-03-12",
        "position_data": "2022-03-12",
    },
    "AAVE_V3-SCROLL": {"lending_indices": "2024-07-22", "oracle_prices": "2024-07-22"},
    "AAVE_V3-ZKSYNC": {"lending_indices": "2024-12-12", "oracle_prices": "2024-12-12"},
    "COMPOUND_V3-ETHEREUM": {"lending_indices": "2022-08-14", "oracle_prices": "2022-08-14"},
    "COMPOUND_V3-ARBITRUM": {"lending_indices": "2023-05-05", "oracle_prices": "2023-05-05"},
    "COMPOUND_V3-BASE": {"lending_indices": "2023-08-20", "oracle_prices": "2023-08-20"},
    "COMPOUND_V3-OPTIMISM": {"lending_indices": "2024-04-07", "oracle_prices": "2024-04-07"},
    "COMPOUND_V3-POLYGON": {"lending_indices": "2024-04-07", "oracle_prices": "2024-04-07"},
    "COMPOUND_V3-SCROLL": {"lending_indices": "2024-07-22", "oracle_prices": "2024-07-22"},
    "MORPHO-ETHEREUM": {
        "lending_indices": "2024-01-08",
        "oracle_prices": "2024-01-08",
        "liquidation_events": "2024-01-08",  # LiquidationCall events via subgraph
    },
    "MORPHO-ARBITRUM": {"lending_indices": "2024-06-01", "oracle_prices": "2024-06-01"},
    "MORPHO-BASE": {"lending_indices": "2024-06-01", "oracle_prices": "2024-06-01"},
    "MORPHO-OPTIMISM": {"lending_indices": "2024-06-01", "oracle_prices": "2024-06-01"},
    "MORPHO-POLYGON": {"lending_indices": "2024-06-01", "oracle_prices": "2024-06-01"},
    "FLUID-ETHEREUM": {"lending_indices": "2024-02-27", "oracle_prices": "2024-02-27"},
    "SPARK-ETHEREUM": {"lending_indices": "2024-01-01", "oracle_prices": "2024-01-01"},
    # cross_asset Phase 1B(b) — Radiant UAC back-fill (was orphan adapter, now declared)
    "RADIANT-ARBITRUM": {"lending_indices": "2022-07-25", "oracle_prices": "2022-07-25"},
    "RADIANT-BSC": {"lending_indices": "2022-09-21", "oracle_prices": "2022-09-21"},
    # ── DeFi — Additional DEX protocols (dex_swaps + dex_pools only) ──
    "SUSHISWAP_V3-ETHEREUM": {"dex_swaps": "2021-11-01", "dex_pools": "2021-11-01"},
    "SUSHISWAP_V3-BASE": {"dex_swaps": "2023-08-15", "dex_pools": "2023-08-15"},
    "SUSHISWAP_V3-AVALANCHE": {"dex_swaps": "2023-08-15", "dex_pools": "2023-08-15"},
    "SUSHISWAP-ARBITRUM": {"dex_swaps": "2021-08-31", "dex_pools": "2021-08-31"},
    "PANCAKESWAP_V3-ETHEREUM": {"dex_swaps": "2023-04-12", "dex_pools": "2023-04-12"},
    "PANCAKESWAP_V3-ARBITRUM": {"dex_swaps": "2023-04-12", "dex_pools": "2023-04-12"},
    "PANCAKESWAP_V3-BASE": {"dex_swaps": "2023-08-15", "dex_pools": "2023-08-15"},
    "PANCAKESWAP_V3-BSC": {"dex_swaps": "2023-04-12", "dex_pools": "2023-04-12"},
    "CAMELOT_V3-ARBITRUM": {"dex_swaps": "2023-05-01", "dex_pools": "2023-05-01"},
    "AERODROME_V3-BASE": {"dex_swaps": "2023-08-28", "dex_pools": "2023-08-28"},
    "VELODROME_V2-OPTIMISM": {"dex_swaps": "2022-06-01", "dex_pools": "2022-06-01"},
    "TRADER_JOE_V2-AVALANCHE": {"dex_swaps": "2022-01-01", "dex_pools": "2022-01-01"},
    # ── DeFi — Perpetual DEXes (funding + liquidations) ──
    # axis_override = "cefi" — CLOB-style perp funding captured via MTDS
    # perp_funding_handler. See DEFI_VENUE_AXIS_OVERRIDES in defi_venues.py.
    "GMX-ARBITRUM": {"perp_funding": "2021-09-01", "liquidations": "2021-09-01", "oracle_prices": "2021-09-01"},
    "GMX-AVALANCHE": {"perp_funding": "2021-12-31", "liquidations": "2021-12-31", "oracle_prices": "2021-12-31"},
    # ── DeFi — Solana ──
    # Drift perpetual CLOB: V1 S3 archive 2022-01-01; LST margin (JitoSOL/mSOL accepted).
    "DRIFT-SOLANA": {"perp_funding": "2022-01-01", "dex_swaps": "2022-01-01"},
    "KAMINO-SOLANA": {"lending_indices": "2023-06-01", "oracle_prices": "2023-06-01"},
    "MARINADE-SOLANA": {"lst_rates": "2021-08-01", "oracle_prices": "2021-08-01"},
    "ORCA-SOLANA": {"dex_swaps": "2021-03-01", "dex_pools": "2021-03-01"},
    "RAYDIUM-SOLANA": {"dex_swaps": "2021-02-21", "dex_pools": "2021-02-21"},
    # ── DeFi — LST/Yield protocols ──
    "LIDO-ETHEREUM": {
        "lst_rates": "2020-12-18",
        "oracle_prices": "2020-12-18",
        "staking_yields": "2020-12-18",  # stETH APY daily rate
    },
    "ETHERFI-ETHEREUM": {
        "lst_rates": "2023-11-01",
        "oracle_prices": "2023-11-01",
        "staking_yields": "2023-11-01",  # weETH APY
    },
    "ETHENA-ETHEREUM": {"lst_rates": "2024-02-19", "oracle_prices": "2024-02-19"},
    "JITO-SOLANA": {"lst_rates": "2021-11-01", "oracle_prices": "2021-11-01"},
    # ── DeFi — EigenLayer (restaking rewards + staking yields) ──
    "EIGENLAYER-ETHEREUM": {
        "eigenlayer_rewards": "2024-08-06",  # RewardsClaimed events
        "staking_yields": "2024-08-06",  # Restaking APY per operator
    },
    # ── DeFi — Gas fees (chain-level, via ALCHEMY synthetic venue) ──
    # The gas_fee_handler uses venue="ALCHEMY" (chain-level, not per-protocol).
    # These entries enable data-status completeness metrics for gas fee coverage.
    "ALCHEMY-ETHEREUM": {"gas_fees": "2020-01-01"},
    "ALCHEMY-ARBITRUM": {"gas_fees": "2021-05-28"},
    "ALCHEMY-POLYGON": {"gas_fees": "2020-05-30"},
    "ALCHEMY-OPTIMISM": {"gas_fees": "2021-11-11"},
    "ALCHEMY-BASE": {"gas_fees": "2023-06-15"},
    # ── DeFi — Token transfers (top 20 DeFi tokens, cross-chain) ──
    # token_transfers adapter uses ALCHEMY RPC; synthetic venue per token x chain.
    "ALCHEMY-ONCHAIN": {"token_transfers": "2020-01-01"},
    # ── DeFi — Bridge events ──
    "ACROSS-ETHEREUM": {"bridge_events": "2021-11-08"},
    "STARGATE-ETHEREUM": {"bridge_events": "2022-03-17"},
    # ── DeFi — Governance events (Compound, Aave, Uniswap DAO) ──
    "COMPOUND-ETHEREUM": {"governance_events": "2020-02-26"},
    "AAVE-ETHEREUM": {"governance_events": "2020-07-27"},
    "UNISWAP-ETHEREUM": {"governance_events": "2020-09-17"},
    # ── DeFi — MEV events (MEV-Boost relay stats) ──
    "FLASHBOTS-ETHEREUM": {"mev_events": "2021-01-01"},
    # ── DeFi — Yield vaults (Phase 1A) ──
    # staking_yields = vault APY time-series (daily rate)
    "YEARN_V3-ETHEREUM": {"staking_yields": "2024-03-20"},
    "YEARN_V3-ARBITRUM": {"staking_yields": "2023-11-15"},
    "YEARN_V3-OPTIMISM": {"staking_yields": "2023-11-15"},
    "CONVEX-ETHEREUM": {"staking_yields": "2021-05-17"},
    "BEEFY-ETHEREUM": {"staking_yields": "2021-12-01"},
    "BEEFY-ARBITRUM": {"staking_yields": "2021-09-20"},
    "BEEFY-BASE": {"staking_yields": "2023-08-15"},
    "BEEFY-POLYGON": {"staking_yields": "2021-05-20"},
    "BEEFY-BSC": {"staking_yields": "2020-10-08"},
    "BEEFY-AVALANCHE": {"staking_yields": "2021-03-15"},
    "PENDLE-ETHEREUM": {"staking_yields": "2021-06-15", "oracle_prices": "2021-06-15"},
    "PENDLE-ARBITRUM": {"staking_yields": "2024-01-26", "oracle_prices": "2024-01-26"},
    "IDLE-ETHEREUM": {"staking_yields": "2019-08-13"},
    "IDLE-ARBITRUM": {"staking_yields": "2024-12-01"},
    "IDLE-POLYGON": {"staking_yields": "2021-11-11"},
    # ── DeFi — Additional LSTs (Phase 1A) ──
    "ROCKETPOOL-ETHEREUM": {"lst_rates": "2021-11-08", "oracle_prices": "2021-11-08"},
    "SOLBLAZE-SOLANA": {"lst_rates": "2022-10-15", "oracle_prices": "2022-10-15"},
    # ── DeFi — Restaking / LRTs (Phase 1A) ──
    # staking_yields = restaking APY; oracle_prices = LRT token price (via Chainlink/Pyth)
    "SYMBIOTIC-ETHEREUM": {"staking_yields": "2024-06-11", "oracle_prices": "2024-06-11"},
    "KARAK-ETHEREUM": {"staking_yields": "2024-04-08", "oracle_prices": "2024-04-08"},
    "KARAK-ARBITRUM": {"staking_yields": "2024-04-08", "oracle_prices": "2024-04-08"},
    "RENZO-ETHEREUM": {"staking_yields": "2024-04-29", "oracle_prices": "2024-04-29"},
    "RENZO-ARBITRUM": {"staking_yields": "2024-02-29", "oracle_prices": "2024-02-29"},
    "KELPDAO-ETHEREUM": {"staking_yields": "2023-11-09", "oracle_prices": "2023-11-09"},
    "PUFFER-ETHEREUM": {"staking_yields": "2024-05-09", "oracle_prices": "2024-05-09"},
    "JITORESTAKING-SOLANA": {"staking_yields": "2024-08-01"},
    # ── DeFi — Solana DEX aggregator (Phase 1A) ──
    "JUPITER-SOLANA": {"dex_swaps": "2021-10-13"},
}


# ── Canonical underscore-name aliases ──
# Ghost no-underscore keys (UNISWAP_V3, AAVE_V3, etc.) kept for backward-compat with
# historical GCS paths. New MTDS writes use canonical underscore names. These aliases
# ensure downstream consumers resolve both forms to identical capability dicts.
_CANONICAL_ALIASES: dict[str, str] = {
    "UNISWAP_V2-ETHEREUM": "UNISWAP_V2-ETHEREUM",
    "UNISWAP_V3-ETHEREUM": "UNISWAP_V3-ETHEREUM",
    "UNISWAP_V3-ARBITRUM": "UNISWAP_V3-ARBITRUM",
    "UNISWAP_V3-BASE": "UNISWAP_V3-BASE",
    "UNISWAP_V3-OPTIMISM": "UNISWAP_V3-OPTIMISM",
    "UNISWAP_V3-POLYGON": "UNISWAP_V3-POLYGON",
    "UNISWAP_V4-ETHEREUM": "UNISWAP_V4-ETHEREUM",
    "AAVE_V3-ETHEREUM": "AAVE_V3-ETHEREUM",
    "AAVE_V3-ARBITRUM": "AAVE_V3-ARBITRUM",
    "AAVE_V3-AVALANCHE": "AAVE_V3-AVALANCHE",
    "AAVE_V3-BASE": "AAVE_V3-BASE",
    "AAVE_V3-BSC": "AAVE_V3-BSC",
    "AAVE_V3-LINEA": "AAVE_V3-LINEA",
    "AAVE_V3-OPTIMISM": "AAVE_V3-OPTIMISM",
    "AAVE_V3-POLYGON": "AAVE_V3-POLYGON",
    "AAVE_V3-SCROLL": "AAVE_V3-SCROLL",
    "AAVE_V3-ZKSYNC": "AAVE_V3-ZKSYNC",
    "COMPOUND_V3-ETHEREUM": "COMPOUND_V3-ETHEREUM",
    "COMPOUND_V3-ARBITRUM": "COMPOUND_V3-ARBITRUM",
    "COMPOUND_V3-BASE": "COMPOUND_V3-BASE",
    "COMPOUND_V3-OPTIMISM": "COMPOUND_V3-OPTIMISM",
    "COMPOUND_V3-POLYGON": "COMPOUND_V3-POLYGON",
    "COMPOUND_V3-SCROLL": "COMPOUND_V3-SCROLL",
    "SUSHISWAP_V3-ETHEREUM": "SUSHISWAP_V3-ETHEREUM",
    "SUSHISWAP_V3-BASE": "SUSHISWAP_V3-BASE",
    "SUSHISWAP_V3-AVALANCHE": "SUSHISWAP_V3-AVALANCHE",
    "PANCAKESWAP_V3-ETHEREUM": "PANCAKESWAP_V3-ETHEREUM",
    "PANCAKESWAP_V3-ARBITRUM": "PANCAKESWAP_V3-ARBITRUM",
    "PANCAKESWAP_V3-BASE": "PANCAKESWAP_V3-BASE",
    "PANCAKESWAP_V3-BSC": "PANCAKESWAP_V3-BSC",
    "CAMELOT_V3-ARBITRUM": "CAMELOT_V3-ARBITRUM",
    "AERODROME_V3-BASE": "AERODROME_V3-BASE",
    "YEARN_V3-ETHEREUM": "YEARN_V3-ETHEREUM",
    "YEARN_V3-ARBITRUM": "YEARN_V3-ARBITRUM",
    "YEARN_V3-OPTIMISM": "YEARN_V3-OPTIMISM",
}
DEFI_VENUE_DATA_TYPE_CAPABILITIES.update(
    {canonical: DEFI_VENUE_DATA_TYPE_CAPABILITIES[ghost] for canonical, ghost in _CANONICAL_ALIASES.items()}
)

__all__ = ["DEFI_VENUE_DATA_TYPE_CAPABILITIES"]
