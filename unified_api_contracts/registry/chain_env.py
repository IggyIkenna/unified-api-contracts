"""Chain environment resolution -- maps chain names to chain IDs per environment.

Strategy says "ETHEREUM", system resolves to chain_id=1 (mainnet) or 11155111 (Sepolia)
based on CHAIN_ENV config value.
"""

from __future__ import annotations

# Mainnet chain IDs
MAINNET_CHAIN_IDS: dict[str, int] = {
    "ETHEREUM": 1,
    "ARBITRUM": 42161,
    "OPTIMISM": 10,
    "BASE": 8453,
    "POLYGON": 137,
    "AVALANCHE": 43114,
    "BSC": 56,
    "LINEA": 59144,
    "MANTLE": 5000,
    "BLAST": 81457,
    "MODE": 34443,
    "GNOSIS": 100,
    "FANTOM": 250,
    "CELO": 42220,
    "AURORA": 1313161554,
    "METIS": 1088,
    "MOONBEAM": 1284,
    "SOLANA": 0,  # Not EVM -- handled separately
    "BITCOIN": 0,  # Not EVM -- handled separately
}

# Testnet chain IDs
TESTNET_CHAIN_IDS: dict[str, int] = {
    "ETHEREUM": 11155111,  # Sepolia
    "ARBITRUM": 421614,  # Arbitrum Sepolia
    "OPTIMISM": 11155420,  # Optimism Sepolia
    "BASE": 84532,  # Base Sepolia
    "POLYGON": 80002,  # Polygon Amoy
    "AVALANCHE": 43113,  # Avalanche Fuji
    "BSC": 97,  # BSC Testnet
    "LINEA": 59141,  # Linea Sepolia
    "MANTLE": 5003,  # Mantle Sepolia
    "BLAST": 168587773,  # Blast Sepolia
    "MODE": 919,  # Mode Testnet
    "GNOSIS": 10200,  # Gnosis Chiado
    "FANTOM": 4002,  # Fantom Testnet
    "CELO": 44787,  # Celo Alfajores
    "AURORA": 1313161555,  # Aurora Testnet
    "METIS": 599,  # Metis Goerli
    "MOONBEAM": 1287,  # Moonbase Alpha
    "SOLANA": 0,  # Devnet -- handled separately
    "BITCOIN": 0,  # Testnet -- handled separately
}

# Fork chain IDs (Tenderly forks use mainnet chain ID but different RPC)
FORK_CHAIN_IDS = MAINNET_CHAIN_IDS  # Same chain IDs, different RPC URL

# Gas fee collection start dates per chain (earliest date with archival RPC data).
# Used by gas fee handler to skip dates before chain genesis / EIP-1559 activation.
# SSOT for gas fee backfill date ranges — services read these, never hardcode dates.
GAS_FEE_CHAIN_START_DATES: dict[int, str] = {
    1: "2020-01-01",  # Ethereum — archival nodes have data from genesis
    10: "2021-11-12",  # Optimism — mainnet regenesis (EVM equivalence)
    56: "2020-09-01",  # BSC — mainnet launch
    137: "2020-06-01",  # Polygon — mainnet launch (Matic rebranded)
    8453: "2023-08-09",  # Base — mainnet launch
    42161: "2021-09-01",  # Arbitrum One — public mainnet
    43114: "2020-09-22",  # Avalanche C-Chain — mainnet launch
    59144: "2023-07-12",  # Linea — mainnet alpha launch
    # ── Tier-4 alt-L1s (defi_pipeline_extension_followups Phase 5 expansion) ──
    250: "2019-12-27",  # Fantom Opera — mainnet launch
    1088: "2021-11-19",  # Metis Andromeda — mainnet launch
    1284: "2022-01-11",  # Moonbeam — mainnet launch
    5000: "2023-07-14",  # Mantle — mainnet launch
    42220: "2020-04-22",  # Celo — mainnet launch
    1313161554: "2021-05-18",  # Aurora — mainnet launch
}

# Solana start date for gas fee collection (Alchemy archival RPC coverage)
GAS_FEE_SOLANA_START_DATE: str = "2021-01-01"

# Chain genesis dates per chain (mainnet launch). SSOT for the data-status
# panel's per-chain pre-launch clipping — DEFI dates earlier than a chain's
# genesis can never have data so they're dropped from the missing/expected
# denominator (otherwise the panel renders thousands of "missing" dates
# stretching back to ETHEREUM's 2015 genesis for chains that launched in
# 2021-2023). Distinct from ``GAS_FEE_CHAIN_START_DATES``: that's the date
# Alchemy archival RPC coverage starts (which can lag chain genesis by
# months), this is the chain's mainnet launch (the absolute earliest any
# data can exist on-chain).
#
# Naming conventions (locked here per defi_catalogue Phase 1C verification 2026-05-12):
# - Each chain has ONE canonical key. Rebrands keep the legacy key (no alias keys —
#   that would duplicate the entry + invite drift).
#   - BSC = "Binance Smart Chain" (legacy) / "BNB Chain" (2022 rebrand). Same chain
#     ID 56, same contracts. Callers that receive "BNB_CHAIN" / "BNB" / "BNBCHAIN"
#     must normalise to "BSC" at entry (do not add alias keys here).
#   - POLYGON = "Matic" (legacy) / "Polygon PoS" (rebrand). Same chain ID 137.
# - Polygon zkEVM is a DISTINCT chain from Polygon PoS (chain ID 1101, different
#   contracts, different bridge). It is currently NOT in defi_catalogue Phase 1A
#   scope; add as "POLYGON_ZKEVM": "2023-03-27" only when a protocol on that chain
#   enters Phase 1A.
CHAIN_GENESIS_DATES: dict[str, str] = {
    "ETHEREUM": "2015-07-30",  # Frontier mainnet
    "ARBITRUM": "2021-08-31",  # Arbitrum One public mainnet
    "BASE": "2023-08-09",  # Base mainnet
    "OPTIMISM": "2021-12-16",  # OP mainnet (post-regenesis)
    "POLYGON": "2020-05-30",  # Matic mainnet (rebranded to Polygon)
    "AVALANCHE": "2020-09-22",  # C-Chain launch
    "BSC": "2020-08-29",  # Binance Smart Chain (rebranded to BNB Chain 2022; same chain ID 56)
    "LINEA": "2023-07-11",  # Linea mainnet alpha
    "SCROLL": "2023-10-17",  # Scroll mainnet
    "ZKSYNC": "2023-03-24",  # zkSync Era mainnet
    "CELO": "2020-04-22",  # Celo mainnet
    "AURORA": "2021-05-12",  # Aurora mainnet
    "FANTOM": "2019-12-28",  # Fantom Opera mainnet
    "MANTLE": "2023-07-14",  # Mantle mainnet
    "GNOSIS": "2018-10-08",  # xDai chain (rebranded to Gnosis)
    "METIS": "2021-11-19",  # Metis Andromeda mainnet
    "MOONBEAM": "2022-01-11",  # Moonbeam mainnet
    "BLAST": "2024-02-29",  # Blast mainnet
    "MODE": "2024-01-12",  # Mode mainnet
    "SOLANA": "2020-03-16",  # Solana mainnet beta
    "BITCOIN": "2009-01-03",  # Bitcoin genesis
}


def get_chain_genesis_date(chain_name: str) -> str | None:
    """Return the chain's mainnet genesis date (ISO YYYY-MM-DD) or None.

    Case-insensitive on ``chain_name``. Returns ``None`` for unknown
    chains so callers can fall back to a category-wide start date when
    the chain isn't yet declared in the SSOT.
    """
    return CHAIN_GENESIS_DATES.get(chain_name.upper()) if chain_name else None


# Per-(chain, protocol) launch dates for DeFi protocols. Mirrors the role
# ``CHAIN_GENESIS_DATES`` plays for chains: clips pre-protocol-launch days
# from the data-status panel's expected denominator. Without this clip,
# AAVEV3-ARBITRUM's "expected dates" stretch back to ARBITRUM genesis
# (2021-08-31) even though Aave V3 didn't deploy on Arbitrum until
# 2022-03-16, inflating the leaf-shard denominator by ~6 months of
# always-empty days.
#
# Callers compose this with ``CHAIN_GENESIS_DATES`` via
# ``max(chain_genesis, protocol_launch)`` to get the effective earliest
# date a (chain, protocol) shard could exist.
#
# Date sources are public mainnet announcements / The Graph subgraph
# deploy timestamps / DefiLlama protocol-launch metadata. Pairs whose
# launch date is not yet researched live in
# ``_PROTOCOL_LAUNCH_PENDING_INVESTIGATION`` and the sanity test allows
# their absence; new entries to ``ALL_DEFI_VENUES`` not present in
# either set fail the test loudly.
PROTOCOL_LAUNCH_DATES: dict[tuple[str, str], str] = {
    # ── Aave V3 (per-chain mainnet deploy dates) ──
    # ETHEREUM deployed Jan 27 2023 (much later than the Mar 2022 multi-L2
    # rollout) — verified 2026-05-08 via AAVE V3 ETH subgraph
    # ``Cd2gEDVeqnjBn1hSeqFMitw8Q1iiyV9FYUZkLNRcL87g``: earliest
    # ``reserveParamsHistoryItems`` event is 2023-01-27 08:00:11 UTC
    # (WETH reserve); 2022-03-14, 2022-12-08, 2023-01-26 all return 0
    # rows. Pre-fix entry was 2022-03-14 (mis-aligned with the L2 cohort)
    # which caused 11 months of pre-deployment dates to be backfill-attempted
    # and recorded as ``empty_confirmed[SOURCE_RETURNED_ZERO]``, framed as
    # "Bug 1 silent zero" in
    # ``plans/active/issues/lending_indices_handler_bugs_2026_05_07.md``
    # — actually a UAC SSOT misdiagnosis, not a code bug.
    ("ETHEREUM", "AAVEV3"): "2023-01-27",
    ("ARBITRUM", "AAVEV3"): "2022-03-16",
    # OPTIMISM AAVE V3 actually deployed 2022-03-15 (subgraph indexes
    # ``reserveParamsHistoryItems`` from 2022-03-15 21:48:18 UTC) — not
    # 2022-08-04 as the pre-2026-05-08 entry claimed. Tab 14 audit
    # 2026-05-08 found 142 days of legitimate post-deploy OPT data
    # was being silently clipped as ``EXPECTED_PRE_GENESIS_CHAIN`` because
    # the 2022-08-04 floor pre-skipped the 2022-03-15 → 2022-08-03 window.
    # See plans/archive/issues/defi_fork1_prep_audit_2026_05_08.md.
    ("OPTIMISM", "AAVEV3"): "2022-03-15",
    # POLYGON earliest event 2022-03-12 (Tab 14 audit 2026-05-08); pre-fix
    # entry 2022-03-16 was 4 days late.
    ("POLYGON", "AAVEV3"): "2022-03-12",
    # AVALANCHE earliest event 2022-03-12 (Tab 14 audit 2026-05-08);
    # pre-fix entry 2022-03-16 was 4 days late.
    ("AVALANCHE", "AAVEV3"): "2022-03-12",
    # BASE earliest event 2023-08-22 (Tab 14 audit 2026-05-08); pre-fix
    # 2023-08-09 (BASE chain genesis) was 13 days early — caused 13d of
    # ``SOURCE_RETURNED_ZERO`` rows that should have been
    # ``EXPECTED_PRE_PROTOCOL_LAUNCH``.
    ("BASE", "AAVEV3"): "2023-08-22",
    # BSC earliest event 2024-01-23 (Tab 14 audit 2026-05-08); pre-fix
    # 2023-04-06 was 293 days early — caused ~293d of ``SOURCE_RETURNED_ZERO``
    # false-empty rows.
    ("BSC", "AAVEV3"): "2024-01-23",
    # LINEA earliest event 2025-02-11 (Tab 14 audit 2026-05-08); pre-fix
    # 2024-09-26 was 138 days early — caused ~138d of false-empty rows.
    ("LINEA", "AAVEV3"): "2025-02-11",
    ("SCROLL", "AAVEV3"): "2024-04-29",
    ("ZKSYNC", "AAVEV3"): "2024-04-09",
    # ── Compound V3 (Comet) ──
    # ETHEREUM earliest ``dailyMarketAccountings`` event 2022-08-13 04:18:30
    # UTC (Tab 14 audit 2026-05-08); pre-fix 2022-08-25 was 12 days late —
    # caused 12d of legitimate post-deploy ETH Compound V3 data to be
    # silently clipped as pre-launch.
    ("ETHEREUM", "COMPOUNDV3"): "2022-08-13",
    # ARBITRUM earliest event 2023-05-04 22:00:26 UTC (Tab 14 audit
    # 2026-05-08); pre-fix 2023-04-13 was 21 days early — caused 21d of
    # ``SOURCE_RETURNED_ZERO`` false-empty rows.
    ("ARBITRUM", "COMPOUNDV3"): "2023-05-04",
    # BASE earliest event 2023-08-04 23:29:21 UTC (subgraph indexes
    # pre-mainnet-open BASE blocks); pre-fix 2023-08-26 was 22 days late —
    # caused 22d of legitimate post-deploy BASE data to be silently clipped.
    ("BASE", "COMPOUNDV3"): "2023-08-04",
    # OPTIMISM earliest event 2024-04-06 17:09:21 UTC (Tab 14 audit
    # 2026-05-08); pre-fix 2024-02-15 was 51 days early — caused 51d of
    # false-empty rows.
    ("OPTIMISM", "COMPOUNDV3"): "2024-04-06",
    # POLYGON entry removed 2026-05-08 — Tab 14 audit confirmed
    # ``SUBGRAPH_IDS["compound_v3"]`` has no POLYGON entry (subgraph returned
    # 0 markets, Compound V3 not active on Polygon). The lingering UAC entry
    # was inflating the data-status denominator with always-empty days.
    ("SCROLL", "COMPOUNDV3"): "2024-04-22",
    # ── Uniswap (V2 / V3 / V4) ──
    ("ETHEREUM", "UNISWAPV2"): "2020-05-04",
    ("ETHEREUM", "UNISWAPV3"): "2021-05-04",
    # ARBITRUM earliest ``poolDayDatas`` event 2021-06-01 (subgraph
    # indexes pre-mainnet-open Arbitrum blocks); pre-fix 2021-08-31
    # (chain genesis) was 91 days late — caused 91d of legitimate
    # pre-public-launch indexed data to be silently clipped. Tab 14
    # audit 2026-05-08.
    ("ARBITRUM", "UNISWAPV3"): "2021-06-01",
    # OPTIMISM earliest event 2021-11-11 (subgraph indexes pre-mainnet-open
    # Optimism blocks); pre-fix 2021-12-16 (OP chain-genesis) was 35d late.
    ("OPTIMISM", "UNISWAPV3"): "2021-11-11",
    ("POLYGON", "UNISWAPV3"): "2021-12-21",
    # BASE earliest event 2023-07-31 (subgraph indexes pre-mainnet-open
    # BASE blocks); pre-fix 2023-08-09 (BASE chain genesis) was 9d late.
    ("BASE", "UNISWAPV3"): "2023-07-31",
    ("ETHEREUM", "UNISWAPV4"): "2025-01-31",
    # ── Curve / Balancer / SushiSwap ──
    ("ETHEREUM", "CURVE"): "2020-01-19",
    ("ETHEREUM", "BALANCER"): "2020-03-31",
    ("ETHEREUM", "SUSHISWAPV3"): "2023-04-04",
    # ── Liquid Staking / yield protocols (Ethereum) ──
    ("ETHEREUM", "LIDO"): "2020-12-19",
    ("ETHEREUM", "ROCKETPOOL"): "2021-11-08",
    ("ETHEREUM", "ETHERFI"): "2023-04-25",
    ("ETHEREUM", "ETHENA"): "2024-02-19",
    ("ETHEREUM", "MAKER"): "2017-12-19",
    ("ETHEREUM", "FRAX"): "2020-12-21",
    # Spark earliest Messari ``marketDailySnapshots`` event 2023-03-07
    # 04:31:11 UTC (Tab 14 audit 2026-05-08). Local
    # ``LENDING_PROTOCOL_DEPLOY_DATES`` fallback in instruments-service
    # had 2023-05-09, over-clipping 63 days of legitimate Spark data;
    # adding the UAC SSOT entry tightens the floor to subgraph reality.
    # See plans/archive/issues/defi_fork1_prep_audit_2026_05_08.md.
    ("ETHEREUM", "SPARK"): "2023-03-07",
    # ── Solana ──
    ("SOLANA", "JITO"): "2022-08-15",
    ("SOLANA", "MARINADE"): "2021-08-02",
    ("SOLANA", "RAYDIUM"): "2021-02-21",
    ("SOLANA", "ORCA"): "2021-02-09",
    ("SOLANA", "KAMINO"): "2022-08-23",
    ("SOLANA", "DRIFT"): "2021-11-18",
    # ── Perp DEXes / aggregators ──
    ("ARBITRUM", "GMX"): "2021-09-01",
    ("AVALANCHE", "GMX"): "2022-01-05",
    # ASTER perp DEX on BNB Chain — operator decision 2026-05-11 (defi_master Q1 #4 approved).
    # Conservative date: Aster DEX launched on BSC ~Q3 2024 per public news; first on-chain event
    # verifiable via BscScan. Eliminates ~759 false-flagged missing rows from defi_988 audit.
    ("BSC", "ASTER"): "2024-09-01",
    # ── Catalogue Phase 1A new launch dates (slot 5 2026-05-11 per
    #    defi_catalogue_chain_primitives_2026_05_10.md Phase 1A). Dates
    #    sourced from public mainnet announcements + DefiLlama protocol-
    #    launch metadata. Subgraph-truth refinement deferred to catalogue
    #    Phase 3 owner (Tab 14-style audit per the prior 2026-05-08 pass
    #    that tightened Aave/Compound dates). Less-confident pairs (Beefy
    #    multi-chain rollouts, Yearn-V3 L2 rollouts, etc.) sit in
    #    ``_PROTOCOL_LAUNCH_PENDING_INVESTIGATION`` until subgraph probes
    #    land — they fall back to ``CHAIN_GENESIS_DATES`` (safe over-clip)
    #    in the meantime.
    ("ETHEREUM", "CONVEX"): "2021-05-17",  # Convex Finance public launch
    ("ETHEREUM", "PENDLE"): "2021-06-15",  # Pendle V1 mainnet
    ("ETHEREUM", "IDLE"): "2019-08-13",  # Idle Finance launch
    ("ETHEREUM", "SYMBIOTIC"): "2024-06-11",  # Symbiotic mainnet launch
    ("ETHEREUM", "KARAK"): "2024-04-08",  # Karak Network mainnet
    ("ETHEREUM", "RENZO"): "2024-04-29",  # Renzo Protocol (ezETH) mainnet
    ("ETHEREUM", "KELPDAO"): "2023-11-09",  # KelpDAO (rsETH) mainnet
    ("ARBITRUM", "PENDLE"): "2024-01-26",  # Pendle V2 Arbitrum expansion
    ("ARBITRUM", "RADIANT"): "2022-07-25",  # Radiant Capital V1 Arbitrum launch
    ("BSC", "RADIANT"): "2022-09-21",  # Radiant V2 BSC expansion
    ("SOLANA", "JUPITER"): "2021-10-13",  # Jupiter aggregator launch
    ("SOLANA", "JITORESTAKING"): "2024-08-01",  # Jito Restaking mainnet
    # ── PROTOCOL_LAUNCH_DATES catalogue Phase 1B research (slot 5 2026-05-12
    #    5-sub-agent fan-out — Ethereum lending/vault + LST/restaking + Balancer
    #    rollouts + DEX/AMM rollouts + Beefy/Yearn/Idle multi-chain). 45 new
    #    pairs sourced from official protocol blogs, Etherscan/Snowtrace/Polygonscan
    #    contract-creation timestamps, DefiLlama protocol-launch metadata, +
    #    CoinDesk / TheDefiant coverage. Confidence tier flagged per pair:
    #    high = primary-source verified day-of; medium = announcement-anchored;
    #    low = relative-age estimate. Conservative principle applied (date is
    #    ≤ first verifiable on-chain event). SolBlaze on Solana kept in pending
    #    (medium-low confidence; pool-creation-tx audit deferred).
    # ── Ethereum lending/vault + restaking (Sub-agent A) ──
    (
        "ETHEREUM",
        "MORPHO",
    ): "2023-12-28",  # Morpho Blue contract 0xBBBB...EEFFCb deployed via Etherscan internal-tx block 18883124; high
    (
        "ETHEREUM",
        "FLUID",
    ): "2024-02-15",  # Fluid Liquidity proxy 0x52aa899454998be5b000ad077a46bbe360f4e497 ~2024-02-17 per Etherscan relative-age; conservative -2d; medium
    (
        "ETHEREUM",
        "MORPHOVAULTS",
    ): "2024-01-04",  # MetaMorpho factory 0xA9c3D3a366466Fa809d1Ae982Fb2c46E5fC41101 ~2024-01-04 per Etherscan; first Steakhouse USDC vault Jan 2024; medium
    ("ETHEREUM", "YEARNV3"): "2024-03-20",  # Yearn V3 mainnet launch per Yearn / Binance Square + Token Terminal; high
    (
        "ETHEREUM",
        "ANKR",
    ): "2020-12-01",  # ankrETH ERC20 0xe95a203b1a91a908f9b9ce46459d101078c2c3cb verified 2020-10-09; Ankr docs Dec 2020 first-LST month; conservative; medium
    (
        "ETHEREUM",
        "STADER",
    ): "2023-07-10",  # Stader ETHx mainnet public launch per Stader blog (launch incentives Jul 10 - Aug 9); high
    (
        "ETHEREUM",
        "STAKEWISE",
    ): "2023-11-28",  # StakeWise V3 + osETH ERC20 launch per StakeWise Medium (osETH = V3-era token; V2 deprecated 2025-06-01); high
    (
        "ETHEREUM",
        "EIGENLAYER",
    ): "2023-06-14",  # EigenLayer Stage 1 mainnet (LST deposits, $17M cap) per EigenLayer blog + TheBlock/Coinacademy coverage; high
    # ── LST + restaking + PancakeSwap ETH (Sub-agent B) ──
    ("ETHEREUM", "SWELL"): "2023-04-25",  # swETH mainnet "Seawolf unleashed" per Swell post; high
    ("ETHEREUM", "PUFFER"): "2024-05-09",  # Puffer mainnet "pufETH deposits live" per Puffer Medium; high
    ("ETHEREUM", "MANTLE"): "2023-12-04",  # Mantle mETH LSP Permissionless Mode launch per CoinDesk + Mantle Docs; high
    ("ETHEREUM", "ALCHEMY"): "2021-02-27",  # Alchemix alUSD mainnet + ALCX token launch (alETH followed Jun 2021); high
    (
        "ETHEREUM",
        "PANCAKESWAPV3",
    ): "2023-04-01",  # PancakeSwap V3 Factory 0x0BFb...91865 deployed 2023-04-01 00:20 UTC per Etherscan; public announce 2023-04-03; high
    # ── Solana lending/LST (Sub-agent B) ── SolBlaze deferred (low confidence)
    (
        "SOLANA",
        "MARGINFI",
    ): "2023-02-23",  # mrgnlend lending protocol launch on Solana mainnet (Squads + multiple sources); high
    ("SOLANA", "SOLEND"): "2021-08-13",  # Solend mainnet launch announcement (Smart Liquidity 2021-08-13); high
    # ── Balancer multi-chain rollout (Sub-agent C) ──
    (
        "ARBITRUM",
        "BALANCER",
    ): "2021-08-31",  # Arbitrum One mainnet day; Balancer joined per Fernando Martinelli Medium + Coindesk; high
    (
        "BASE",
        "BALANCER",
    ): "2023-08-09",  # Balancer Base announced Aug 1 2023 per Avalanche blog (bundled w/ Avalanche launch); CLAMPED to BASE chain genesis 2023-08-09 (no on-chain events possible pre-genesis); medium
    (
        "OPTIMISM",
        "BALANCER",
    ): "2022-06-01",  # Balancer Optimism launch June 2 2022 per Balancer Labs Medium "Balancer is Now on Optimism!"; conservative -1d; high
    (
        "POLYGON",
        "BALANCER",
    ): "2021-07-01",  # Balancer Polygon launch per Polygon Technology blog (incentives began June 28); high
    (
        "AVALANCHE",
        "BALANCER",
    ): "2023-08-01",  # Balancer Avalanche deploy per Avax.network blog "Balancer Deploys on Avalanche"; high
    # ── PancakeSwap V3 multi-chain rollout (Sub-agent C) ──
    (
        "ARBITRUM",
        "PANCAKESWAPV3",
    ): "2023-08-09",  # PancakeSwap V3 Arbitrum deploy Aug 10 per Coindesk + BSC News + DL News; conservative -1d; high
    (
        "BASE",
        "PANCAKESWAPV3",
    ): "2023-08-30",  # PancakeSwap V3 Base launch Aug 31 per PancakeSwap blog + Galxe "Traverse"; conservative -1d; medium
    (
        "BSC",
        "PANCAKESWAPV3",
    ): "2023-04-03",  # PancakeSwap V3 BNB Chain Apr 3 per CoinCarp + BSC News "Chef's Special" + Crypto Times; high
    # ── SushiSwap multi-chain (Sub-agent C + D) ──
    ("ARBITRUM", "SUSHISWAP"): "2021-08-31",  # Arbitrum One full public mainnet (Sushi among earliest); high
    ("AVALANCHE", "SUSHISWAPV3"): "2023-05-04",  # SushiSwap V3 13-chain rollout per CoinDesk 2023-05-04; high
    (
        "BASE",
        "SUSHISWAPV3",
    ): "2023-08-09",  # SushiSwap on Base announced Aug 4 2023; CLAMPED to BASE chain genesis 2023-08-09 (sub-agent D flagged); medium
    # ── DEX/AMM multi-chain rollouts (Sub-agent D) ──
    (
        "ARBITRUM",
        "CAMELOTV3",
    ): "2023-04-08",  # Camelot V2 (Algebra concentrated-liq) stage-1 launch; V3 codebase same Algebra fork per CoinDesk + Camelot docs; medium
    ("OPTIMISM", "VELODROMEV2"): "2023-06-22",  # Velodrome V2 launch Medium post + Velodrome Finance blog; high
    ("OPTIMISM", "CURVE"): "2022-01-18",  # Curve Optimism deployment announcement tweet (TheDefiant, TheBlock); high
    (
        "AVALANCHE",
        "CURVE",
    ): "2021-08-18",  # Curve Avalanche deployment via Avalanche Rush program (TheDefiant + Avalanche Medium); high
    (
        "AVALANCHE",
        "TRADER_JOEV2",
    ): "2022-11-17",  # Trader Joe Liquidity Book V2 live per TokenInsight + TheDefiant; high
    (
        "BASE",
        "AERODROMEV3",
    ): "2024-04-22",  # Aerodrome Slipstream (concentrated-liq V3) launch per Aerodrome official X + CCN; high
    (
        "BASE",
        "MORPHO",
    ): "2024-06-18",  # Morpho Blue on Base — first L2 deployment per Paul Frambot X + Morpho blog + CryptoTimes; high
    # ── Beefy multi-chain (Sub-agent E) ──
    (
        "ETHEREUM",
        "BEEFY",
    ): "2021-12-01",  # Beefy multichain expansion era; Convex ETH vaults active late-2021 (Coinbase: BEEFY ERC20 created 2021-06-22); BIP-71 ETH migration Sept 2023; low (conservative)
    ("ARBITRUM", "BEEFY"): "2021-09-20",  # Beefy Learn Medium "Beefy Finance deploys on Arbitrum"; high
    (
        "BASE",
        "BEEFY",
    ): "2023-08-15",  # Coinbase Base mainnet GA 2023-08-09; Beefy x Lido Base article 2023-11-08 + DefiLlama TVL ~2023-08; medium (conservative pre-Lido article)
    (
        "POLYGON",
        "BEEFY",
    ): "2021-05-20",  # Beefy Polygon partnership Medium 2021-05-26 + Iron Finance vaults live 2021-06-03; conservative pre-partnership; high
    ("BSC", "BEEFY"): "2020-10-08",  # Official Beefy founding launch on BSC; first BNB Chain yield optimizer; high
    (
        "AVALANCHE",
        "BEEFY",
    ): "2021-03-15",  # TokenPost "Yield optimizer Beefy Finance now is launched on Avalanche" 2021-03-16; high
    # ── Yearn V3 + Idle + Karak + Renzo on L2s (Sub-agent E) ──
    (
        "ARBITRUM",
        "YEARNV3",
    ): "2023-11-15",  # Yearn V3 v3.0.0 cross-chain deploy per Yearn docs; Polygon first focus Nov 2023; ETH mainnet GA Mar 2024; low (conservative pre-GA)
    (
        "OPTIMISM",
        "YEARNV3",
    ): "2023-11-15",  # Yearn V3 v3.0.0 deployed cross-chain incl. Optimism per Yearn docs Nov 2023; low
    (
        "ARBITRUM",
        "IDLE",
    ): "2024-12-01",  # Idle Medium "Credit Vaults are coming to Arbitrum" 2024-12-04; conservative pre-announce; medium
    (
        "POLYGON",
        "IDLE",
    ): "2021-11-11",  # Idle Medium "Idle is officially live on Polygon!" (Smart Liquidity repost 2021-11-11); high
    (
        "ARBITRUM",
        "KARAK",
    ): "2024-04-08",  # Karak private mainnet 2024-04-08; public 2024-04-09; Arbitrum included multi-chain day-1 per DLNews; high
    (
        "ARBITRUM",
        "RENZO",
    ): "2024-02-29",  # Renzo + Connext native restaking on Arbitrum launch per official X (tweet 1763237166459527250) + Metaverse Post; high
}

# (chain, protocol) pairs declared in ``ALL_DEFI_VENUES`` whose launch
# date has not yet been researched. The sanity test allows their
# absence from ``PROTOCOL_LAUNCH_DATES``; callers without an entry
# fall back to ``CHAIN_GENESIS_DATES`` (over-clipping toward chain
# genesis is fine — under-clipping inflates the missing-shards
# denominator). Add a launch date and remove the pair from this set
# to tighten the clip.
_PROTOCOL_LAUNCH_PENDING_INVESTIGATION: frozenset[tuple[str, str]] = frozenset(
    {
        # SPARK / ETHEREUM moved to ``PROTOCOL_LAUNCH_DATES`` 2026-05-08
        # (Tab 14 audit verified 2023-03-07 earliest subgraph event).
        # ── Catalogue Phase 1B research (slot 5 2026-05-12 5-sub-agent fan-out)
        # moved 45 pairs to ``PROTOCOL_LAUNCH_DATES``. The remaining pending
        # entries are below + (SOLANA, SOLBLAZE) flagged for follow-up.
        # POLYGON / COMPOUNDV3 — UAC ``ALL_DEFI_VENUES`` declares it but
        # ``SUBGRAPH_IDS["compound_v3"]`` has no POLYGON entry (Compound V3
        # is not active on Polygon — subgraph returned 0 markets). Removed
        # from ``PROTOCOL_LAUNCH_DATES`` 2026-05-08 (Tab 14 audit) to stop
        # inflating the data-status denominator with always-empty days.
        ("POLYGON", "COMPOUNDV3"),
        # (SOLANA, SOLBLAZE) — slot 5 2026-05-12 Sub-agent B research returned
        # only medium-low confidence (date 2022-10-15 anchored to Solanacompass
        # stake-pool Epoch 345 + Nov 2022 X promo; no primary-source pool-
        # creation-tx audit done). Operator follow-up via Solscan stake-pool
        # creation tx for pool address `stk9ApL5HeVAwPLr3TLhDXdZS8ptVu7zp6ov8HFDuMi`
        # before tightening the floor.
        ("SOLANA", "SOLBLAZE"),
    }
)


def get_protocol_launch_date(chain: str, protocol: str) -> str | None:
    """Return the (chain, protocol) mainnet launch date or ``None``.

    Case-insensitive on both args. Used by the data-status panel's
    expected-universe builder to clip pre-protocol-launch days from
    the leaf-shard denominator. Callers should compose with
    ``get_chain_genesis_date(chain)`` via:

        effective = max(get_chain_genesis_date(chain) or "",
                        get_protocol_launch_date(chain, protocol) or "")

    so the result respects whichever clip is tighter (pre-1.0 the
    chain genesis is a safe fallback when a protocol pair is not yet
    declared).
    """
    if not chain or not protocol:
        return None
    return PROTOCOL_LAUNCH_DATES.get((chain.upper(), protocol.upper()))


# Environment names
CHAIN_ENVS = ("mainnet", "testnet", "fork")

# Block explorer base URLs per chain per env
BLOCK_EXPLORER_URLS: dict[str, dict[str, str]] = {
    "mainnet": {
        "ETHEREUM": "https://etherscan.io",
        "ARBITRUM": "https://arbiscan.io",
        "BASE": "https://basescan.org",
        "OPTIMISM": "https://optimistic.etherscan.io",
        "POLYGON": "https://polygonscan.com",
    },
    "testnet": {
        "ETHEREUM": "https://sepolia.etherscan.io",
        "ARBITRUM": "https://sepolia.arbiscan.io",
        "BASE": "https://sepolia.basescan.org",
        "OPTIMISM": "https://sepolia-optimism.etherscan.io",
        "POLYGON": "https://amoy.polygonscan.com",
    },
}


def resolve_chain_id(chain_name: str, env: str = "mainnet") -> int:
    """Resolve a chain name to its numeric chain ID for the given environment.

    Args:
        chain_name: Canonical chain name (e.g. "ETHEREUM", "ARBITRUM").
        env: Environment -- "mainnet", "testnet", or "fork".

    Returns:
        Chain ID as integer.

    Raises:
        ValueError: If chain_name is not recognized.
    """
    chain_upper = chain_name.upper()
    chain_ids = TESTNET_CHAIN_IDS if env == "testnet" else MAINNET_CHAIN_IDS

    if chain_upper not in chain_ids:
        msg = f"Unknown chain: {chain_name!r}. Known chains: {sorted(chain_ids.keys())}"
        raise ValueError(msg)
    return chain_ids[chain_upper]


def resolve_rpc_url(chain_name: str, env: str = "mainnet", alchemy_api_key: str = "") -> str:
    """Resolve chain name + env to an RPC URL using CHAIN_RPC_TEMPLATES.

    For fork env, returns empty string -- caller must use Tenderly fork URL.

    Args:
        chain_name: Canonical chain name.
        env: "mainnet", "testnet", or "fork".
        alchemy_api_key: Alchemy API key for template substitution.

    Returns:
        RPC URL string. Empty string if fork env (caller provides fork URL).
    """
    if env == "fork":
        return ""  # Caller provides Tenderly fork URL

    from unified_api_contracts.registry.capability_declarations._defi import (
        CHAIN_RPC_TEMPLATES,
    )

    chain_id = resolve_chain_id(chain_name, env)
    if chain_id == 0:
        return ""  # Non-EVM chains (Solana, Bitcoin) -- use dedicated RPC templates

    template = CHAIN_RPC_TEMPLATES.get(chain_id, "")
    if not template:
        return ""
    return template.replace("{api_key}", alchemy_api_key)


def get_block_explorer_url(chain_name: str, env: str = "mainnet") -> str:
    """Get block explorer base URL for a chain and environment."""
    mainnet_urls = BLOCK_EXPLORER_URLS.get("mainnet")
    if mainnet_urls is None:
        return ""
    env_urls = BLOCK_EXPLORER_URLS.get(env, mainnet_urls)
    return env_urls.get(chain_name.upper(), "")
