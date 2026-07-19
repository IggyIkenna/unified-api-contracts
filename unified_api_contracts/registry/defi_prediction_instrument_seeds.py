"""MVP seed instrument tables for DEFI + PREDICTION per-instrument data_types.

Wave 8G of the MTDS per-instrument sentinel rollout. The Wave 8B
``get_expected_instruments_for_venue`` accessor in
``market_data_categories.py`` returns non-empty lists for CEFI / TRADFI
via ``_SPOT_MVP_SEED_INSTRUMENTS`` / ``_PERP_MVP_SEED_INSTRUMENTS`` /
``_OPTION_FUTURE_MVP_SEED_UNDERLYINGS``. DEFI + PREDICTION per-instrument
dts (``dex_pool_state``, ``dex_pool_swaps``, ``lending_indices``, ``oracle_prices``,
``lst_rates``, ``rewards``, ``risk_params``, ``trades`` on POLYMARKET /
KALSHI) historically fell through to ``()`` — meaning the Phase 8
honest-coverage aggregator degraded those categories to the Tier-2
(venue x data_type) denominator and silently under-counted expected
shards.

This module holds the Wave 8G MVP seed tables. Values sourced from the
live GCS availability manifests on ``central-element-323112`` on
2026-04-20:

    * DEX pools — ``gs://dex-pools-central-element-323112/dex_pool_state/
      uniswap_v3/ETHEREUM/date=2026-04-14/*.parquet`` (top 20 by TVL).
    * Aave reserves — ``gs://lending-indices-central-element-323112/
      lending_indices/aave_v3/ETHEREUM/date=2026-04-14/*.parquet``
      (21 reserves observed; top 10 by liquidity + canonical usage).
    * LST rates — ``gs://lst-rates-central-element-323112/lst_rates/
      date=2026-04-09/*.parquet`` (6 tokens: stETH, wstETH, rETH, cbETH,
      sUSDe, sDAI mapped to their emitting protocol).
    * Prediction markets —
      ``gs://instruments-store-prediction-central-element-323112/
      instrument_availability/by_date/day=2026-04-14/market=BTC/
      venue=POLYMARKET/instruments.parquet`` (700 active conditionIds;
      MVP caps at top 10).

Scope is deliberately narrow (MVP discipline — matches the 21/10/2
SPOT/PERP/option-underlying pattern from Wave 8B): the seed list gives
the aggregator a realistic Tier-3 denominator while keeping manifest row
counts bounded. Operators dial into Expanded / Full tiers via the
``--per-instrument-sentinel-cap`` CLI flag and via runtime
``instruments_provider`` injection once the live instruments-service
snapshot is routed into the orchestrator.

SSOT: ``unified-trading-pm/codex/02-data/mtds-data-source-coverage-matrix.md``
§ 8 (Wave 8G).
"""

from __future__ import annotations

# ── DEFI seeds ──────────────────────────────────────────────────────────

# UniswapV3 Ethereum — top 20 pools by TVL on 2026-04-14. Lowercase pool
# addresses (canonical form used by the dex-pools bucket + SwapRouter).
# Data source: ``uniswap_v3_ETHEREUM_20260415_221716.parquet`` (1000 pools
# daily, sorted by tvl_usd descending, top 20 taken). Top 5 are the
# USDC/WETH 0.05%, USDC/WETH 0.3%, WETH/USDT 0.3%, WBTC/WETH 0.3%, and
# WBTC/USDC 0.3% pools — aggregate ~$1.2B TVL.
_UNISWAP_V3_ETHEREUM_TOP_POOLS: tuple[str, ...] = (
    "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",  # USDC/WETH 0.05%  # QG-allow: defi-citation
    "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8",  # USDC/WETH 0.3%  # QG-allow: defi-citation
    "0x4e68ccd3e89f51c3074ca5072bbac773960dfa36",  # WETH/USDT 0.3%  # QG-allow: defi-citation
    "0xcbcdf9626bc03e24f779434178a73a0b4bad62ed",  # WBTC/WETH 0.3%  # QG-allow: defi-citation
    "0x99ac8ca7087fa4a2a1fb6357269965a2014abc35",  # WBTC/USDC 0.3%  # QG-allow: defi-citation
    "0x4585fe77225b41b697c938b018e2ac67ac5a20c0",  # WBTC/WETH 0.05%  # QG-allow: defi-citation
    "0x11b815efb8f581194ae79006d24e0d814b7697f6",  # WETH/USDT 0.05%  # QG-allow: defi-citation
    "0xa6cc3c2531fdaa6ae1a3ca84c2855806728693e8",  # LINK/WETH 0.3%  # QG-allow: defi-citation
    "0x9db9e0e53058c89e5b94e29621a205198648425b",  # WBTC/USDT 0.3%  # QG-allow: defi-citation
    "0xc2e9f25be6257c210d7adf0d4cd6e3e881ba25f8",  # DAI/WETH 0.3%  # QG-allow: defi-citation
    "0x5796d7ad51583ae2c7297652edb7006bcd90519d",  # HKDM/USDM 0.01%  # QG-allow: defi-citation
    "0x3416cf6c708da44db2624d63ea0aaef7113527c6",  # USDC/USDT 0.01%  # QG-allow: defi-citation
    "0xe8f7c89c5efa061e340f2d2f206ec78fd8f7e124",  # WBTC/cbBTC 0.01%  # QG-allow: defi-citation
    "0x1d42064fc4beb5f8aaf85f4617ae8b3b5b8bd801",  # UNI/WETH 0.3%  # QG-allow: defi-citation
    "0x11950d141ecb863f01007add7d1a342041227b58",  # PEPE/WETH 0.3%  # QG-allow: defi-citation
    "0xbafead7c60ea473758ed6c6021505e8bbd7e8e5d",  # AUSD/USDC 0.01%  # QG-allow: defi-citation
    "0x56534741cd8b152df6d48adf7ac51f75169a83b2",  # WBTC/USDT 0.05%  # QG-allow: defi-citation
    "0x4a25dbdf9629b1782c3e2c7de3bdce41f1c7f801",  # USDM/USDT 0.05%  # QG-allow: defi-citation
    "0x970a7749ecaa4394c8b2bf5f2471f41fd6b79288",  # wM/USDC 0.01%  # QG-allow: defi-citation
    "0x6546055f46e866a4b9a4a13e81273e3152bae5da",  # XAUt/USDT 0.05%  # QG-allow: defi-citation
)

# Aave V3 Ethereum — top 10 reserves by canonical usage + observed
# liquidity on 2026-04-14. Data source: ``aave_v3_ETHEREUM_20260415_
# 191702.parquet`` (21 reserves observed). Symbol form (not underlying
# address) — Aave's per-reserve parquets are keyed on ``symbol``.
_AAVE_V3_ETHEREUM_TOP_RESERVES: tuple[str, ...] = (
    "USDC",
    "USDT",
    "DAI",
    "WETH",
    "WBTC",
    "AAVE",
    "LINK",
    "USDe",
    "wstETH",
    "weETH",
)

# LST/staking protocols — one seed token per protocol (the token the
# protocol's exchange-rate oracle emits). Data source:
# ``lst_rates_1775736000.parquet`` (2026-04-09, 6 rows). Lido emits both
# stETH and wstETH (rebase + wrapped); Ether.fi emits eETH + weETH;
# Ethena emits USDe + sUSDe.
_LIDO_ETHEREUM_LST_TOKENS: tuple[str, ...] = ("stETH", "wstETH")
_ETHERFI_ETHEREUM_LST_TOKENS: tuple[str, ...] = ("eETH", "weETH")
_ETHENA_ETHEREUM_LST_TOKENS: tuple[str, ...] = ("USDe", "sUSDe")


# ── PREDICTION seeds ────────────────────────────────────────────────────

# Polymarket — top 10 conditionIds from the BTC market on 2026-04-14
# (700 active conditionIds total). The Polymarket bucket partitions by
# market underlying (BTC / ETH / SOL / SPX / NDX / ...), so BTC is the
# single-highest-volume partition; seeding with its top 10 gives the
# aggregator a realistic non-empty denominator for POLYMARKET trades.
# Data source:
# ``instruments-store-prediction-central-element-323112/
# instrument_availability/by_date/day=2026-04-14/market=BTC/
# venue=POLYMARKET/instruments.parquet``.
_POLYMARKET_TOP_CONDITION_IDS: tuple[str, ...] = (
    "0xaeb90563cfa2b094efccc44658f991a39e0687082f1882d7d51c5d709821ba5b",  # QG-allow: defi-citation
    "0xdd1101f985c5649c070c0acc370e72d48a1117a2d4775fd060526771c4c38e41",  # QG-allow: defi-citation
    "0x5778bf2998b76e62ea6a2cfa9dcb070265f2a0b3d37da9736a90f765d04abe52",  # QG-allow: defi-citation
    "0xb4edd1ceca7ae170d1ed632677a8671797b3d47374d38ffac7d410cfb9e9f5c7",  # QG-allow: defi-citation
    "0xedc2c7b97fd9475880d65d875b74ac709093cb9ef50b31245a0f9df73b9f53e7",  # QG-allow: defi-citation
    "0xcaf9ab651cb192c756ce23d15692041d9397cb9983bb55022dc1e3f5525a8a32",  # QG-allow: defi-citation
    "0x53506e5fd3f980c20e9b6683962a1bc72aaa18ad01dcc2b8416b5c606aff9fb9",  # QG-allow: defi-citation
    "0x0047decf5a127be6ec0ba4eee78c9b224eb2d5445aff6241377272eacd42114f",  # QG-allow: defi-citation
    "0x1c2f06de72ad9ecd9a25babc2a908302261686659d642c9d369946ce0d1bfdd3",  # QG-allow: defi-citation
    "0x3c18e248b91adf9f665a07747f0e2ff6727913bdc910f99e93861572b4eb3651",  # QG-allow: defi-citation
)

# Kalshi — no observable bucket in
# ``instruments-store-prediction-central-element-323112`` as of
# 2026-04-20 (only POLYMARKET partitions exist). Seed is intentionally
# empty; the honest-coverage aggregator will report
# ``attempted_failed`` / ``empty_confirmed`` until the Kalshi adapter
# lands. Wave 8G honours "no live data → empty seed".
_KALSHI_TOP_CONDITION_IDS: tuple[str, ...] = ()


# ── (venue, data_type) → seed map ───────────────────────────────────────

# Keyed on ``(venue, data_type)`` to match the exact per-shard fan-out
# the aggregator runs. Consumers call into these via
# ``get_expected_instruments_for_venue`` in ``market_data_categories.py``
# which already handles the ``cap`` + ``instruments_provider`` paths.

DEFI_MVP_SEED_INSTRUMENTS: dict[tuple[str, str], tuple[str, ...]] = {
    # UNISWAP_V3-ETHEREUM — dex_pool_state + dex_pool_swaps share the pool set.
    ("UNISWAP_V3-ETHEREUM", "dex_pool_state"): _UNISWAP_V3_ETHEREUM_TOP_POOLS,
    ("UNISWAP_V3-ETHEREUM", "dex_pool_swaps"): _UNISWAP_V3_ETHEREUM_TOP_POOLS,
    # AAVE_V3-ETHEREUM — every per-reserve dt expands to the same reserve
    # universe (lending_indices / oracle_prices / rewards / risk_params).
    ("AAVE_V3-ETHEREUM", "lending_indices"): _AAVE_V3_ETHEREUM_TOP_RESERVES,
    ("AAVE_V3-ETHEREUM", "oracle_prices"): _AAVE_V3_ETHEREUM_TOP_RESERVES,
    ("AAVE_V3-ETHEREUM", "rewards"): _AAVE_V3_ETHEREUM_TOP_RESERVES,
    ("AAVE_V3-ETHEREUM", "risk_params"): _AAVE_V3_ETHEREUM_TOP_RESERVES,
    # LST protocols — lst_rates + oracle_prices share the token set.
    ("LIDO-ETHEREUM", "lst_rates"): _LIDO_ETHEREUM_LST_TOKENS,
    ("LIDO-ETHEREUM", "oracle_prices"): _LIDO_ETHEREUM_LST_TOKENS,
    ("ETHERFI-ETHEREUM", "lst_rates"): _ETHERFI_ETHEREUM_LST_TOKENS,
    ("ETHERFI-ETHEREUM", "oracle_prices"): _ETHERFI_ETHEREUM_LST_TOKENS,
    ("ETHENA-ETHEREUM", "lst_rates"): _ETHENA_ETHEREUM_LST_TOKENS,
    ("ETHENA-ETHEREUM", "oracle_prices"): _ETHENA_ETHEREUM_LST_TOKENS,
}

PREDICTION_MVP_SEED_INSTRUMENTS: dict[tuple[str, str], tuple[str, ...]] = {
    # Polymarket + Kalshi emit canonical ``trades`` (the legacy
    # ``prediction_trades`` data_type was retired 2026-04-19 for cross-category
    # alignment — see ``VENUE_DATA_TYPE_CAPABILITIES``). The rollout-window dual
    # seed on ``("VENUE", "prediction_trades")`` was dropped 2026-07-19 once the
    # prod manifest migration folded every ``prediction_trades`` row into
    # ``trades`` (0 captured cells lost) — the captured reality is now
    # ``trades``-only, so seeding only ``trades`` keeps the expected denominator
    # aligned with what is actually captured.
    ("POLYMARKET", "trades"): _POLYMARKET_TOP_CONDITION_IDS,
    ("KALSHI", "trades"): _KALSHI_TOP_CONDITION_IDS,
}


def seed_for_venue_and_data_type(venue: str, data_type: str) -> tuple[str, ...]:
    """Return the Wave 8G MVP seed for ``(venue, data_type)`` or ``()``.

    Pure helper — no runtime I/O, no date churn tracking. Consumed by
    ``get_expected_instruments_for_venue`` in ``market_data_categories.py``
    to cover the DEFI + PREDICTION path. Callers branch on truthiness:
    truthy → Tier-3 per-instrument fan-out; falsy → Tier-2 fall-back.
    """
    seed = DEFI_MVP_SEED_INSTRUMENTS.get((venue, data_type))
    if seed is not None:
        return seed
    return PREDICTION_MVP_SEED_INSTRUMENTS.get((venue, data_type), ())


__all__ = [
    "DEFI_MVP_SEED_INSTRUMENTS",
    "PREDICTION_MVP_SEED_INSTRUMENTS",
    "seed_for_venue_and_data_type",
]
