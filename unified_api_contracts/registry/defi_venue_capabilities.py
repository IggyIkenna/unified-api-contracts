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
    # ── DeFi — DEX protocols (dex_pool_swaps + dex_pool_state) ──
    "UNISWAP_V2-ETHEREUM": {"dex_pool_swaps": "2020-05-06", "dex_pool_state": "2020-05-06"},
    "UNISWAP_V3-ETHEREUM": {
        "dex_pool_swaps": "2021-05-05",
        "dex_pool_state": "2021-05-05",
        "position_data": "2021-05-05",  # LP position data (top 1000 by liquidity)
    },
    "UNISWAP_V3-ARBITRUM": {"dex_pool_swaps": "2021-06-18", "dex_pool_state": "2021-06-18"},
    "UNISWAP_V3-BASE": {"dex_pool_swaps": "2023-09-03", "dex_pool_state": "2023-09-03"},
    "UNISWAP_V3-OPTIMISM": {"dex_pool_swaps": "2021-11-12", "dex_pool_state": "2021-11-12"},
    "UNISWAP_V3-POLYGON": {"dex_pool_swaps": "2021-12-22", "dex_pool_state": "2021-12-22"},
    "UNISWAP_V4-ETHEREUM": {"dex_pool_swaps": "2025-01-30", "dex_pool_state": "2025-01-30"},
    "CURVE-ETHEREUM": {"dex_pool_swaps": "2020-01-20", "dex_pool_state": "2020-01-20"},
    "CURVE-AVALANCHE": {"dex_pool_swaps": "2021-11-10", "dex_pool_state": "2021-11-10"},
    "CURVE-OPTIMISM": {"dex_pool_swaps": "2022-01-13", "dex_pool_state": "2022-01-13"},
    "BALANCER-ETHEREUM": {"dex_pool_swaps": "2021-04-22", "dex_pool_state": "2021-04-22"},
    "BALANCER-ARBITRUM": {"dex_pool_swaps": "2021-08-27", "dex_pool_state": "2021-08-27"},
    "BALANCER-AVALANCHE": {"dex_pool_swaps": "2023-08-17", "dex_pool_state": "2023-08-17"},
    "BALANCER-BASE": {"dex_pool_swaps": "2023-07-29", "dex_pool_state": "2023-07-29"},
    "BALANCER-OPTIMISM": {"dex_pool_swaps": "2022-05-20", "dex_pool_state": "2022-05-20"},
    "BALANCER-POLYGON": {"dex_pool_swaps": "2021-06-24", "dex_pool_state": "2021-06-24"},
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
    # RADIANT-ETHEREUM + EULER_V2/VENUS/BENQI (operator 2026-07-10, decision #9 —
    # defi_code_codex_drift_2026_05_27.md D10). These 4 protocols already have
    # real PROTOCOL_CAPABILITIES + SUBGRAPH_IDS entries (unified-api-contracts
    # @cd65ff76, 2026-06-02) and MTDS collector wiring
    # (market-tick-data-service@d98f5726) — the ORIGINAL D10 "no capability"
    # premise (filed 2026-05-27, before cd65ff76 landed) is stale for those two
    # registries. What was GENUINELY still missing is exactly this dict — this
    # module is the honest-coverage denominator's per-(venue,data_type)
    # capability gate (the DeFi analog of cefi/tradfi's
    # VENUE_DATA_TYPE_CAPABILITIES), and these 4 venues had ZERO entries here.
    # Start dates from the researched PROTOCOL_LAUNCH_DATES SSOT (chain_env.py)
    # — the same source that already drives these venues' pre-genesis
    # empty_confirmed boundary in the enumerator (verified against the prod
    # availability manifest: RADIANT-ETHEREUM's empty_confirmed max_date=
    # 2023-07-17, one day before this 2023-07-18 floor; same 1-day-offset
    # pattern for BENQI/VENUS-BSC). data_types kept to the MINIMAL real capture
    # surface (lending_indices only, NOT the full aspirational LENDING_DATA set
    # used by _ProtocolCapability) — matching the SOLEND-SOLANA/MARGINFI-SOLANA
    # convention above ("declared the data_type ACTUALLY captured... declaring
    # more would inflate the could-exist denominator with cells that have no
    # data") — the prod manifest shows ZERO real captured/attempted_failed rows
    # for ANY data_type on ANY of these 4 venues, ever (only pre-genesis
    # empty_confirmed stamps); the capture orchestrator-wiring is a separate,
    # already-tracked gap (mtds_is_full_adapter_smoketest_findings_2026_07_07.md
    # P1: "Wire VENUS/BENQI/RADIANT/EULER_V2's already-functional adapters into
    # the production orchestrator — code works, it's just never invoked").
    # DEFI_VENUE_PHASE for all 4 stays "pipeline" (re-phasing to "live" is
    # deliberately NOT part of this change — VENUES_BY_ASSET_GROUP["defi"] only
    # admits phase=="live" venues, so this entry is inert until the
    # orchestrator-wiring item lands and phase flips for real) — it exists so
    # the declaration is honest + ready the moment a real capture path lands.
    # Live-network-probe verification (2026-07-10): the EULER_V2 Goldsky
    # subgraph IS reachable but its indexed HEAD is ~271K blocks (~38 days)
    # behind current Ethereum mainnet — a dead/stalled upstream that should be
    # re-verified before any future phase flip to "live".
    "RADIANT-ETHEREUM": {"lending_indices": "2023-07-18", "oracle_prices": "2023-07-18"},
    "EULER_V2-ETHEREUM": {"lending_indices": "2024-08-01"},
    "EULER_V2-ARBITRUM": {"lending_indices": "2024-08-01"},
    "VENUS-BSC": {"lending_indices": "2020-10-08"},
    "VENUS-ETHEREUM": {"lending_indices": "2023-06-01"},
    "BENQI-AVALANCHE": {"lending_indices": "2021-08-19"},
    # ── DeFi — Additional DEX protocols (dex_pool_swaps + dex_pool_state only) ──
    "SUSHISWAP_V3-ETHEREUM": {"dex_pool_swaps": "2021-11-01", "dex_pool_state": "2021-11-01"},
    "SUSHISWAP_V3-BASE": {"dex_pool_swaps": "2023-08-15", "dex_pool_state": "2023-08-15"},
    "SUSHISWAP_V3-AVALANCHE": {"dex_pool_swaps": "2023-08-15", "dex_pool_state": "2023-08-15"},
    "SUSHISWAP-ARBITRUM": {"dex_pool_swaps": "2021-08-31", "dex_pool_state": "2021-08-31"},
    "PANCAKESWAP_V3-ETHEREUM": {"dex_pool_swaps": "2023-04-12", "dex_pool_state": "2023-04-12"},
    "PANCAKESWAP_V3-ARBITRUM": {"dex_pool_swaps": "2023-04-12", "dex_pool_state": "2023-04-12"},
    "PANCAKESWAP_V3-BASE": {"dex_pool_swaps": "2023-08-15", "dex_pool_state": "2023-08-15"},
    "PANCAKESWAP_V3-BSC": {"dex_pool_swaps": "2023-04-12", "dex_pool_state": "2023-04-12"},
    "CAMELOT_V3-ARBITRUM": {"dex_pool_swaps": "2023-05-01", "dex_pool_state": "2023-05-01"},
    "AERODROME_V3-BASE": {"dex_pool_swaps": "2023-08-28", "dex_pool_state": "2023-08-28"},
    "VELODROME_V2-OPTIMISM": {"dex_pool_swaps": "2022-06-01", "dex_pool_state": "2022-06-01"},
    "TRADER_JOE_V2-AVALANCHE": {"dex_pool_swaps": "2022-01-01", "dex_pool_state": "2022-01-01"},
    # ── DeFi — Perpetual DEXes (funding + liquidations) ──
    # axis_override = "cefi" — CLOB-style perp funding captured via MTDS
    # perp_funding_handler. See DEFI_VENUE_AXIS_OVERRIDES in defi_venues.py.
    # derivative_ticker (2026-07-15, defi_perp_funding_canonicalisation_derivative_ticker_all_perps issue,
    # operator ruling "highest-resolution derivative_ticker for ALL perps, even without OI at source"):
    # GMX's fundingRateChangedEvents subgraph query has no OI field on the entity at all (verified against
    # market-tick-data-service/cli/handlers/_perp_funding_gmx.py:115-130 — the Messari financialsDailySnapshots
    # fallback has a daily-aggregate OI proxy but that's a degraded fallback path, not additive to the primary
    # query). Same start date as perp_funding — it's the SAME underlying event feed, now dual-written under both
    # data_types (mtds@<sha to be filled by shipping commit>).
    "GMX-ARBITRUM": {
        "perp_funding": "2021-09-01",
        "liquidations": "2021-09-01",
        "oracle_prices": "2021-09-01",
        "derivative_ticker": "2021-09-01",
    },
    "GMX-AVALANCHE": {
        "perp_funding": "2021-12-31",
        "liquidations": "2021-12-31",
        "oracle_prices": "2021-12-31",
        "derivative_ticker": "2021-12-31",
    },
    # ── DeFi — Solana ──
    # Drift perpetual CLOB: V1 S3 archive 2022-01-01; LST margin (JitoSOL/mSOL accepted).
    # derivative_ticker (2026-07-15, same issue as above): drift_adapter.py's fetch_drift_data already produces
    # real derivative_ticker rows (funding_rate/mark_price via the Drift Data API /fundingRates endpoint,
    # adapters/drift_adapter.py:141-167) but ONLY for date >= 2025-01-01 (_DRIFT_API_START gate at
    # adapters/drift_adapter.py:315-341) — there is no S3-archive funding fetch in this adapter for the
    # 2022-01-01..2024-12-31 window (that window's funding is captured under a DIFFERENT data_type,
    # perp_funding, via a separate S3-CSV backfill path in solana_defi_drift.py). Declaring 2022-01-01 here would
    # be dishonest (nothing serves derivative_ticker before 2025-01-01) — floor matches the adapter's real gate.
    "DRIFT-SOLANA": {"perp_funding": "2022-01-01", "dex_pool_swaps": "2022-01-01", "derivative_ticker": "2025-01-01"},
    "KAMINO-SOLANA": {"lending_indices": "2023-06-01", "oracle_prices": "2023-06-01"},
    "MARINADE-SOLANA": {"lst_rates": "2021-08-01", "oracle_prices": "2021-08-01"},
    "ORCA-SOLANA": {"dex_pool_swaps": "2021-03-01", "dex_pool_state": "2021-03-01"},
    "RAYDIUM-SOLANA": {"dex_pool_swaps": "2021-02-21", "dex_pool_state": "2021-02-21"},
    # Solana lending — DATA-001 capability backfill (2026-06-16): declared the
    # data_type ACTUALLY captured in the prod availability index (lending_indices
    # only; no oracle_prices captured yet — declaring it would inflate the
    # could-exist denominator with cells that have no data). Floor = earliest
    # captured date in projected_index_defi.parquet (best-effort; adapter gates
    # per-row via get_venue_data_type_start_date).
    "SOLEND-SOLANA": {"lending_indices": "2022-11-01"},
    "MARGINFI-SOLANA": {"lending_indices": "2025-01-01"},
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
    # ── DeFi — ERC-4626 share-price vaults (vault_share_price) ──
    # DATA-001 capability backfill (2026-06-16): these venues had captured
    # vault_share_price shards in the prod availability index but no
    # VENUE_DATA_TYPE_CAPABILITIES entry → their shards were uncredited in the
    # could-exist denominator (the universe builder reads this dict directly).
    # data_type = the one observed in projected_index_defi.parquet; floor =
    # earliest captured date there (best-effort; adapter gates per-row).
    "MAKER-ETHEREUM": {"vault_share_price": "2023-01-18"},  # sDAI / DSR share price
    "FRAX-ETHEREUM": {"vault_share_price": "2023-10-19"},  # sfrxETH / Frax vault share price
    "MORPHOVAULTS-ETHEREUM": {"vault_share_price": "2024-01-04"},  # MetaMorpho ERC-4626 vaults
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
    # 2026-07-10 DeFi turbo-API read-path bug fix (defi_turbo_api_hides_real_captured_data_2026_07_07.md):
    # these 5 venues were in ALL_DEFI_VENUES (declared "pipeline" phase) with real
    # captured ``lst_rates`` shards in the prod availability index but NO
    # VENUE_DATA_TYPE_CAPABILITIES entry at all -> get_expected_data_types_for_venue
    # returned [] -> the MTDS honest-coverage override short-circuited to
    # expected_shards=0 -> the turbo API either showed 0/0 or silently dropped the
    # UAC-driven annotations, masking real data. data_type + earliest-captured floor
    # verified directly against the live GCS manifest (market-data-tick-defi bucket,
    # capture_status=='captured' rows only; empty_confirmed/expected_unattempted
    # excluded) -- no oracle_prices/staking_yields captured for any of these 5, so
    # only lst_rates is declared (mirrors the DATA-001 precedent: declaring an
    # uncaptured dt would inflate the could-exist denominator with empty cells).
    "MANTLE-ETHEREUM": {"lst_rates": "2023-10-06"},  # 990 captured rows through 2026-06-21
    "STADER-ETHEREUM": {"lst_rates": "2023-07-10"},  # 1,078 captured rows through 2026-06-21
    "STAKEWISE-ETHEREUM": {"lst_rates": "2023-11-28"},  # 937 captured rows through 2026-06-21
    "SWELL-ETHEREUM": {"lst_rates": "2023-04-17"},  # 1,162 captured rows through 2026-06-21
    "ANKR-ETHEREUM": {
        "lst_rates": "2020-12-30"
    },  # 2,000 captured rows through 2026-06-21 (same gap, not previously flagged)
    "SOLBLAZE-SOLANA": {"lst_rates": "2022-10-15", "oracle_prices": "2022-10-15"},
    # ── DeFi — Restaking / LRTs (Phase 1A) ──
    # staking_yields = restaking APY; oracle_prices = LRT token price (via Chainlink/Pyth)
    "SYMBIOTIC-ETHEREUM": {"staking_yields": "2024-06-11", "oracle_prices": "2024-06-11"},
    "KARAK-ETHEREUM": {"staking_yields": "2024-04-08", "oracle_prices": "2024-04-08"},
    "KARAK-ARBITRUM": {"staking_yields": "2024-04-08", "oracle_prices": "2024-04-08"},
    "RENZO-ETHEREUM": {"staking_yields": "2024-04-29", "oracle_prices": "2024-04-29"},
    "RENZO-ARBITRUM": {"staking_yields": "2024-02-29", "oracle_prices": "2024-02-29"},
    "KELPDAO-ETHEREUM": {"staking_yields": "2023-11-09", "oracle_prices": "2023-11-09"},
    # PUFFER's declared staking_yields/oracle_prices are roadmap dts (0 captured
    # rows as of 2026-07-10 verification) -- kept as-is. lst_rates added 2026-07-10
    # (defi_turbo_api_hides_real_captured_data_2026_07_07.md): 871 real captured
    # rows through 2026-06-21 under this data_type were previously undeclared,
    # so honest-coverage always matched against the wrong column and reported 0%.
    "PUFFER-ETHEREUM": {"staking_yields": "2024-05-09", "oracle_prices": "2024-05-09", "lst_rates": "2024-02-01"},
    "JITORESTAKING-SOLANA": {"staking_yields": "2024-08-01"},
    # ── DeFi — Solana DEX aggregator (Phase 1A) ──
    "JUPITER-SOLANA": {"dex_pool_swaps": "2021-10-13"},
}


# ── Canonical underscore-name aliases ──
# Ghost no-underscore keys (UNISWAP_V3, AAVE_V3, etc.) are legacy-name aliases for
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
