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
    "UNISWAPV2-ETHEREUM": {"dex_swaps": "2020-05-06", "dex_pools": "2020-05-06"},
    "UNISWAPV3-ETHEREUM": {"dex_swaps": "2021-05-05", "dex_pools": "2021-05-05"},
    "UNISWAPV3-ARBITRUM": {"dex_swaps": "2021-06-18", "dex_pools": "2021-06-18"},
    "UNISWAPV3-BASE": {"dex_swaps": "2023-09-03", "dex_pools": "2023-09-03"},
    "UNISWAPV3-OPTIMISM": {"dex_swaps": "2021-11-12", "dex_pools": "2021-11-12"},
    "UNISWAPV3-POLYGON": {"dex_swaps": "2021-12-22", "dex_pools": "2021-12-22"},
    "UNISWAPV4-ETHEREUM": {"dex_swaps": "2025-01-30", "dex_pools": "2025-01-30"},
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
    "AAVEV3-ETHEREUM": {
        "lending_indices": "2023-01-27",
        "oracle_prices": "2023-01-27",
        "rewards": "2023-01-27",
        "risk_params": "2023-01-27",
    },
    "AAVEV3-ARBITRUM": {
        "lending_indices": "2022-03-12",
        "oracle_prices": "2022-03-12",
        "rewards": "2022-03-12",
        "risk_params": "2022-03-12",
    },
    "AAVEV3-AVALANCHE": {
        "lending_indices": "2022-03-12",
        "oracle_prices": "2022-03-12",
        "rewards": "2022-03-12",
        "risk_params": "2022-03-12",
    },
    "AAVEV3-BASE": {
        "lending_indices": "2023-08-23",
        "oracle_prices": "2023-08-23",
        "rewards": "2023-08-23",
        "risk_params": "2023-08-23",
    },
    "AAVEV3-BSC": {
        "lending_indices": "2024-01-24",
        "oracle_prices": "2024-01-24",
        "rewards": "2024-01-24",
        "risk_params": "2024-01-24",
    },
    "AAVEV3-LINEA": {
        "lending_indices": "2025-02-12",
        "oracle_prices": "2025-02-12",
        "rewards": "2025-02-12",
        "risk_params": "2025-02-12",
    },
    "AAVEV3-OPTIMISM": {
        "lending_indices": "2022-03-12",
        "oracle_prices": "2022-03-12",
        "rewards": "2022-03-12",
        "risk_params": "2022-03-12",
    },
    "AAVEV3-POLYGON": {
        "lending_indices": "2022-03-12",
        "oracle_prices": "2022-03-12",
        "rewards": "2022-03-12",
        "risk_params": "2022-03-12",
    },
    "AAVEV3-SCROLL": {"lending_indices": "2024-07-22", "oracle_prices": "2024-07-22"},
    "AAVEV3-ZKSYNC": {"lending_indices": "2024-12-12", "oracle_prices": "2024-12-12"},
    "COMPOUNDV3-ETHEREUM": {"lending_indices": "2022-08-14", "oracle_prices": "2022-08-14"},
    "COMPOUNDV3-ARBITRUM": {"lending_indices": "2023-05-05", "oracle_prices": "2023-05-05"},
    "COMPOUNDV3-BASE": {"lending_indices": "2023-08-20", "oracle_prices": "2023-08-20"},
    "COMPOUNDV3-OPTIMISM": {"lending_indices": "2024-04-07", "oracle_prices": "2024-04-07"},
    "COMPOUNDV3-POLYGON": {"lending_indices": "2024-04-07", "oracle_prices": "2024-04-07"},
    "COMPOUNDV3-SCROLL": {"lending_indices": "2024-07-22", "oracle_prices": "2024-07-22"},
    "MORPHO-ETHEREUM": {"lending_indices": "2024-01-08", "oracle_prices": "2024-01-08"},
    "MORPHO-ARBITRUM": {"lending_indices": "2024-06-01", "oracle_prices": "2024-06-01"},
    "MORPHO-BASE": {"lending_indices": "2024-06-01", "oracle_prices": "2024-06-01"},
    "MORPHO-OPTIMISM": {"lending_indices": "2024-06-01", "oracle_prices": "2024-06-01"},
    "MORPHO-POLYGON": {"lending_indices": "2024-06-01", "oracle_prices": "2024-06-01"},
    "FLUID-ETHEREUM": {"lending_indices": "2024-02-27", "oracle_prices": "2024-02-27"},
    "SPARK-ETHEREUM": {"lending_indices": "2024-01-01", "oracle_prices": "2024-01-01"},
    # ── DeFi — Additional DEX protocols (dex_swaps + dex_pools only) ──
    "SUSHISWAPV3-ETHEREUM": {"dex_swaps": "2021-11-01", "dex_pools": "2021-11-01"},
    "SUSHISWAPV3-BASE": {"dex_swaps": "2023-08-15", "dex_pools": "2023-08-15"},
    "SUSHISWAPV3-AVALANCHE": {"dex_swaps": "2023-08-15", "dex_pools": "2023-08-15"},
    "SUSHISWAP-ARBITRUM": {"dex_swaps": "2021-08-31", "dex_pools": "2021-08-31"},
    "PANCAKESWAPV3-ETHEREUM": {"dex_swaps": "2023-04-12", "dex_pools": "2023-04-12"},
    "PANCAKESWAPV3-ARBITRUM": {"dex_swaps": "2023-04-12", "dex_pools": "2023-04-12"},
    "PANCAKESWAPV3-BASE": {"dex_swaps": "2023-08-15", "dex_pools": "2023-08-15"},
    "PANCAKESWAPV3-BSC": {"dex_swaps": "2023-04-12", "dex_pools": "2023-04-12"},
    "PANCAKESWAPV3-ZKSYNC": {"dex_swaps": "2023-08-15", "dex_pools": "2023-08-15"},
    "CAMELOTV3-ARBITRUM": {"dex_swaps": "2023-05-01", "dex_pools": "2023-05-01"},
    "AERODROMEV3-BASE": {"dex_swaps": "2023-08-28", "dex_pools": "2023-08-28"},
    "VELODROMEV2-OPTIMISM": {"dex_swaps": "2022-06-01", "dex_pools": "2022-06-01"},
    "TRADER_JOEV2-AVALANCHE": {"dex_swaps": "2022-01-01", "dex_pools": "2022-01-01"},
    # ── DeFi — Perpetual DEXes (funding + liquidations) ──
    "GMX-ARBITRUM": {"perp_funding": "2021-09-01", "liquidations": "2021-09-01", "oracle_prices": "2021-09-01"},
    "GMX-AVALANCHE": {"perp_funding": "2021-12-31", "liquidations": "2021-12-31", "oracle_prices": "2021-12-31"},
    # ── DeFi — Solana ──
    "KAMINO-SOLANA": {"lending_indices": "2023-06-01", "oracle_prices": "2023-06-01"},
    "MARINADE-SOLANA": {"lst_rates": "2021-08-01", "oracle_prices": "2021-08-01"},
    "ORCA-SOLANA": {"dex_swaps": "2021-03-01", "dex_pools": "2021-03-01"},
    "RAYDIUM-SOLANA": {"dex_swaps": "2021-02-21", "dex_pools": "2021-02-21"},
    # ── DeFi — LST/Yield protocols ──
    "LIDO-ETHEREUM": {"lst_rates": "2020-12-18", "oracle_prices": "2020-12-18"},
    "ETHERFI-ETHEREUM": {"lst_rates": "2023-11-01", "oracle_prices": "2023-11-01"},
    "ETHENA-ETHEREUM": {"lst_rates": "2024-02-19", "oracle_prices": "2024-02-19"},
    "JITO-SOLANA": {"lst_rates": "2021-11-01", "oracle_prices": "2021-11-01"},
}


__all__ = ["DEFI_VENUE_DATA_TYPE_CAPABILITIES"]
