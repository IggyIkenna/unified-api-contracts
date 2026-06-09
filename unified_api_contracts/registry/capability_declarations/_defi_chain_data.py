"""Chain-specific data: RPC templates, token addresses, gas tokens, contract addresses.

Extracted from _defi.py to keep individual modules under the 900-line limit.
All public symbols are re-exported by _defi.py so the external API is unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

# ---------------------------------------------------------------------------
# ChainConfig — typed per-chain operational settings (SSOT)
#
# Lifted out of the bare ``CHAIN_RPC_TEMPLATES`` dict 2026-05-03 (defi
# pipeline extension follow-ups Phase 5) so downstream services can reach
# for ``reorg_depth`` / ``avg_block_time_s`` / ``native_gas_token``
# without re-implementing per-chain heuristics. ``CHAIN_RPC_TEMPLATES``
# is kept as a derived view of ``CHAIN_CONFIGS[].rpc_url_template`` for
# back-compat — every existing caller keeps working unchanged.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChainConfig:
    """Per-chain operational settings for backfill / live / execution.

    Attributes:
        rpc_url_template: Provider URL with ``{api_key}`` placeholder.
            Public RPCs (Tier-4 chains) leave the placeholder unrendered;
            ``str.format(api_key="")`` is a no-op for them.
        reorg_depth: Conservative confirmations-to-finality. L1s use deep
            (≥30) values; high-finality L2s + sequencer-only chains use
            shallower (1-30) values. The execution-service +
            instruments-service reference these to gate event ingestion.
        avg_block_time_s: Mean block-time, used by data-status to compute
            expected per-day block ranges + by execution-service to
            estimate inclusion latency.
        native_gas_token: ETH/BNB/MATIC/AVAX/etc — symbol of the asset
            paid as gas. Sourced from CHAIN_NATIVE_GAS_TOKEN.
    """

    rpc_url_template: str
    reorg_depth: int
    avg_block_time_s: float
    native_gas_token: str


# ---------------------------------------------------------------------------
# Chain-specific Alchemy RPC URL templates (SSOT)
#
# Used by execution-service to resolve a fully-qualified RPC URL before
# injecting it into UDEI connector config.  Interfaces never touch these
# directly — they receive a pre-resolved ``rpc_url`` from the service layer.
# ---------------------------------------------------------------------------
# Per-chain typed config — SSOT. ``CHAIN_RPC_TEMPLATES`` below is a derived
# ``dict[int, str]`` view kept for back-compat.
CHAIN_CONFIGS: dict[int, ChainConfig] = {
    # ── Tier 1: Core ETH + L2s (strategy-critical) ───────────────
    1: ChainConfig(
        rpc_url_template="https://eth-mainnet.g.alchemy.com/v2/{api_key}",
        reorg_depth=64,
        avg_block_time_s=12.0,
        native_gas_token="ETH",
    ),
    10: ChainConfig(
        rpc_url_template="https://opt-mainnet.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=2.0,
        native_gas_token="ETH",
    ),
    8453: ChainConfig(
        rpc_url_template="https://base-mainnet.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=2.0,
        native_gas_token="ETH",
    ),
    42161: ChainConfig(
        rpc_url_template="https://arb-mainnet.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=0.25,
        native_gas_token="ETH",
    ),
    # ── Tier 2: Major non-ETH EVM chains ─────────────────────────
    56: ChainConfig(
        rpc_url_template="https://bnb-mainnet.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=3.0,
        native_gas_token="BNB",
    ),
    137: ChainConfig(
        rpc_url_template="https://polygon-mainnet.g.alchemy.com/v2/{api_key}",
        reorg_depth=128,
        avg_block_time_s=2.0,
        native_gas_token="MATIC",
    ),
    43114: ChainConfig(
        rpc_url_template="https://avax-mainnet.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=2.0,
        native_gas_token="AVAX",
    ),
    100: ChainConfig(
        rpc_url_template="https://gnosis-mainnet.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=5.0,
        native_gas_token="XDAI",
    ),
    # ── Tier 3: ETH-native L2s + zkEVMs ──────────────────────────
    130: ChainConfig(
        rpc_url_template="https://unichain-mainnet.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=1.0,
        native_gas_token="ETH",
    ),
    324: ChainConfig(
        rpc_url_template="https://zksync-mainnet.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=1.0,
        native_gas_token="ETH",
    ),
    480: ChainConfig(
        rpc_url_template="https://worldchain-mainnet.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=2.0,
        native_gas_token="ETH",
    ),
    1101: ChainConfig(
        rpc_url_template="https://polygonzkevm-mainnet.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=5.0,
        native_gas_token="ETH",
    ),
    2741: ChainConfig(
        rpc_url_template="https://abstract-mainnet.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=1.0,
        native_gas_token="ETH",
    ),
    34443: ChainConfig(
        rpc_url_template="https://mode-mainnet.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=2.0,
        native_gas_token="ETH",
    ),
    57073: ChainConfig(
        rpc_url_template="https://ink-mainnet.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=1.0,
        native_gas_token="ETH",
    ),
    59144: ChainConfig(
        rpc_url_template="https://linea-mainnet.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=12.0,
        native_gas_token="ETH",
    ),
    81457: ChainConfig(
        rpc_url_template="https://blast-mainnet.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=2.0,
        native_gas_token="ETH",
    ),
    534352: ChainConfig(
        rpc_url_template="https://scroll-mainnet.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=3.0,
        native_gas_token="ETH",
    ),
    7777777: ChainConfig(
        rpc_url_template="https://zora-mainnet.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=2.0,
        native_gas_token="ETH",
    ),
    # ── Tier 4: Alt-L1 / non-Alchemy chains (public RPC; api_key is no-op) ────
    # DeFi pipeline extension Phase 6.1: backfill chains the analysis silently
    # treated as unsupported. Public RPCs work for read-only / instruments-
    # service ingest; for production execution-service calls, switch to a
    # dedicated provider (QuickNode, Infura) via Secret Manager.
    250: ChainConfig(
        # 2026-05-04: switched from rpc.ftm.tools (returns 401 Unauthorized
        # without an API key) to the official Fantom Foundation RPC
        # which exposes eth_feeHistory on a free public endpoint.
        rpc_url_template="https://rpcapi.fantom.network",
        reorg_depth=30,
        avg_block_time_s=1.0,
        native_gas_token="FTM",
    ),
    1088: ChainConfig(
        # METIS: all public RPCs reject eth_feeHistory with -32601 method-
        # not-found (probed andromeda.metis.io, metis-rpc.publicnode.com,
        # metis.api.onfinality.io 2026-05-04). The instruments-service
        # path uses different RPCs that work; gas-fee collection requires
        # a paid endpoint (excluded from DEFAULT_GAS_FEE_CHAINS until then).
        rpc_url_template="https://andromeda.metis.io/?owner=1088",
        reorg_depth=30,
        avg_block_time_s=2.0,
        native_gas_token="METIS",
    ),
    1284: ChainConfig(
        # MOONBEAM: all public RPCs return -32603 "Block range out of
        # bounds" on eth_feeHistory, even at tip (probed
        # rpc.api.moonbeam.network, moonbeam.publicnode.com,
        # moonbeam.api.onfinality.io 2026-05-04). instruments-service
        # paths work via the same URL. Gas-fee collection requires a
        # paid endpoint (excluded from DEFAULT_GAS_FEE_CHAINS).
        rpc_url_template="https://rpc.api.moonbeam.network",
        reorg_depth=30,
        avg_block_time_s=12.0,
        native_gas_token="GLMR",
    ),
    5000: ChainConfig(
        rpc_url_template="https://rpc.mantle.xyz",
        reorg_depth=30,
        avg_block_time_s=2.0,
        native_gas_token="MNT",
    ),
    42220: ChainConfig(
        rpc_url_template="https://forno.celo.org",
        reorg_depth=30,
        avg_block_time_s=5.0,
        native_gas_token="CELO",
    ),
    1313161554: ChainConfig(
        rpc_url_template="https://mainnet.aurora.dev",
        reorg_depth=30,
        avg_block_time_s=1.0,
        native_gas_token="ETH",
    ),
    # ── Testnets (EVM) — same key, different endpoints ───────────
    11155111: ChainConfig(
        rpc_url_template="https://eth-sepolia.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=12.0,
        native_gas_token="ETH",
    ),
    11155420: ChainConfig(
        rpc_url_template="https://opt-sepolia.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=2.0,
        native_gas_token="ETH",
    ),
    84532: ChainConfig(
        rpc_url_template="https://base-sepolia.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=2.0,
        native_gas_token="ETH",
    ),
    421614: ChainConfig(
        rpc_url_template="https://arb-sepolia.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=0.25,
        native_gas_token="ETH",
    ),
    80002: ChainConfig(
        rpc_url_template="https://polygon-amoy.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=2.0,
        native_gas_token="MATIC",
    ),
    43113: ChainConfig(
        rpc_url_template="https://avax-fuji.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=2.0,
        native_gas_token="AVAX",
    ),
    300: ChainConfig(
        rpc_url_template="https://zksync-sepolia.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=1.0,
        native_gas_token="ETH",
    ),
    168587773: ChainConfig(
        rpc_url_template="https://blast-sepolia.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=2.0,
        native_gas_token="ETH",
    ),
    534351: ChainConfig(
        rpc_url_template="https://scroll-sepolia.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=3.0,
        native_gas_token="ETH",
    ),
    59141: ChainConfig(
        rpc_url_template="https://linea-sepolia.g.alchemy.com/v2/{api_key}",
        reorg_depth=30,
        avg_block_time_s=12.0,
        native_gas_token="ETH",
    ),
}


# Back-compat view: ``dict[int, str]`` mapping chain_id → rpc_url_template.
# Existing callers keep working; new callers should pull
# ``CHAIN_CONFIGS[chain_id]`` directly to access reorg_depth /
# avg_block_time_s / native_gas_token.
CHAIN_RPC_TEMPLATES: dict[int, str] = {chain_id: cfg.rpc_url_template for chain_id, cfg in CHAIN_CONFIGS.items()}


def get_chain_config(chain_id: int) -> ChainConfig | None:
    """Return the typed ChainConfig for a given chain_id, or None."""
    return CHAIN_CONFIGS.get(chain_id)


def is_block_finalized(chain_id: int, confirmations: int) -> bool:
    """Return True iff ``confirmations`` clears the chain's reorg depth.

    Consumers (event ingestion, transfer confirmation, flash-loan receipt
    polling) call this to decide whether a block is safe to treat as
    canonical. Falls open (returns True) for chains not in CHAIN_CONFIGS
    so the predicate is conservative against missing configs.

    Example:
        confirmations = web3.eth.block_number - tx_receipt.block_number
        if is_block_finalized(chain_id=1, confirmations=confirmations):
            mark_canonical(tx)
    """
    cfg = CHAIN_CONFIGS.get(chain_id)
    if cfg is None:
        return True
    return confirmations >= cfg.reorg_depth


def time_budget_to_block_offset(chain_id: int, seconds: float) -> int:
    """Convert a wall-clock time budget into a block-count offset for a chain.

    Used by execution-service MEV protection (max_block_number =
    current_block + offset) and by manifest-pre-flight to size
    expected-block windows. Returns 1 minimum (never zero — even a 0.25s
    Arbitrum chain advances at least one block in any meaningful budget).

    Falls open with a 12s assumption (Ethereum-equivalent) for chains
    not in CHAIN_CONFIGS.

    Example:
        # Block range that covers 90 seconds of wall time.
        offset = time_budget_to_block_offset(chain_id=42161, seconds=90.0)
        # → 360 (Arbitrum at 0.25s/block)
    """
    cfg = CHAIN_CONFIGS.get(chain_id)
    avg_s = cfg.avg_block_time_s if cfg is not None else 12.0
    if avg_s <= 0:
        return 1
    return max(1, int(seconds / avg_s))


# ---------------------------------------------------------------------------
# Solana RPC templates — same pattern as EVM, keyed by network name.
# Uses the same alchemy-api-key from Secret Manager (one key covers all chains).
# SSOT for all Solana RPC URLs — services import from here, never hardcode.
# ---------------------------------------------------------------------------
SOLANA_RPC_TEMPLATES: dict[str, str] = {
    # ── Mainnet ──────────────────────────────────────────────────
    "alchemy": "https://solana-mainnet.g.alchemy.com/v2/{api_key}",
    "helius": "https://mainnet.helius-rpc.com/?api-key={api_key}",
    # ── Devnet (Solana testnet equivalent) ────────────────────────
    "alchemy_devnet": "https://solana-devnet.g.alchemy.com/v2/{api_key}",
    "helius_devnet": "https://devnet.helius-rpc.com/?api-key={api_key}",
    "public_devnet": "https://api.devnet.solana.com",
}

# All RPC templates use secret: alchemy-api-key (DATA_SOURCE_TO_SECRET in canonical_mappings)
# Same key works for EVM + Solana on Alchemy.

# ---------------------------------------------------------------------------
# Protected RPC URLs for MEV-resistant transaction submission (SSOT)
#
# Used by execution-service MEV protection layer (mev/protection.py).
# Connectors must NOT hardcode these — import from here.
# ETHEREUM: Flashbots Protect (free, no auth needed, blocks sandwich attacks)
# ETHEREUM_BUNDLE: Flashbots Bundle relay (requires ethers signing for bundles)
# MEV_BLOCKER: CoW Protocol MEV Blocker (aggregates multiple builders)
# ---------------------------------------------------------------------------
PROTECTED_RPC_URLS: dict[str, str] = {
    "ETHEREUM": "https://rpc.flashbots.net",  # Flashbots Protect (MEV Blocker)
    "ETHEREUM_BUNDLE": "https://relay.flashbots.net",  # Flashbots Bundle relay
    "MEV_BLOCKER": "https://rpc.mevblocker.io",  # CoW Protocol MEV Blocker
}

# ---------------------------------------------------------------------------
# Chain native gas tokens (SSOT)
# Gas is paid in the native token — ETH on L2s, BNB/MATIC/AVAX on alt-L1s
# ---------------------------------------------------------------------------
CHAIN_NATIVE_GAS_TOKEN: dict[int, str] = {
    1: "ETH",
    10: "ETH",
    56: "BNB",
    130: "ETH",
    137: "MATIC",
    324: "ETH",
    480: "ETH",
    1101: "ETH",
    2741: "ETH",
    8453: "ETH",
    34443: "ETH",
    42161: "ETH",
    43114: "AVAX",
    57073: "ETH",
    59144: "ETH",
    81457: "ETH",
    534352: "ETH",
    7777777: "ETH",
    11155111: "ETH",
    # Tier 4 (Phase 6.1 extension)
    100: "XDAI",  # GNOSIS — was already in RPC table
    250: "FTM",  # FANTOM
    1088: "METIS",  # METIS
    1284: "GLMR",  # MOONBEAM
    5000: "MNT",  # MANTLE
    42220: "CELO",  # CELO
    1313161554: "ETH",  # AURORA — Ethereum-compatible
}

# ---------------------------------------------------------------------------
# WETH addresses per chain (SSOT for wrap/unwrap)
# DeFi protocols require WETH (ERC20); gas is paid in native ETH.
# On non-ETH chains, this is the wrapped native token (WBNB, WMATIC, WAVAX).
# ---------------------------------------------------------------------------
WETH_ADDRESSES: dict[int, str] = {
    1: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    10: "0x4200000000000000000000000000000000000006",
    56: "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
    130: "0x4200000000000000000000000000000000000006",
    137: "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
    324: "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91",
    480: "0x4200000000000000000000000000000000000006",
    1101: "0x4F9A0e7FD2Bf6067db6994CF12E4495Df938E6e9",
    2741: "0x4200000000000000000000000000000000000006",
    8453: "0x4200000000000000000000000000000000000006",
    34443: "0x4200000000000000000000000000000000000006",
    42161: "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
    43114: "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",  # WAVAX
    57073: "0x4200000000000000000000000000000000000006",
    59144: "0xe5D7C2a44FfDDf6b295A15c148167daaAf5Cf34f",
    81457: "0x4300000000000000000000000000000000000004",
    534352: "0x5300000000000000000000000000000000000004",
    7777777: "0x4200000000000000000000000000000000000006",
    11155111: "0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14",
}

# ---------------------------------------------------------------------------
# WBTC / cbBTC addresses per chain (BTC on EVM — first-class instruments)
# ---------------------------------------------------------------------------
WBTC_ADDRESSES: dict[int, str] = {
    1: "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
    10: "0x68f180fcCe6836688e9084f035309E29Bf0A2095",
    137: "0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6",
    42161: "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f",
    43114: "0x50b7545627a5162F82A992c33b87aDc75187B218",
}

CBBTC_ADDRESSES: dict[int, str] = {
    1: "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf",
    8453: "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf",
    42161: "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf",
}


def get_native_gas_token(chain_id: int) -> str:
    """Get the native gas token symbol for a chain."""
    return CHAIN_NATIVE_GAS_TOKEN.get(chain_id, "ETH")


def get_weth_address(chain_id: int) -> str | None:
    """Get the WETH (wrapped native) contract address for a chain."""
    return WETH_ADDRESSES.get(chain_id)


# ---------------------------------------------------------------------------
# Non-EVM chains (SSOT)
#
# Solana and Bitcoin are fundamentally different from EVM chains:
# - Different RPC protocols, transaction models, token standards
# - Separate adapter stacks required (not The Graph subgraphs)
# - Chain IDs are conventional strings, not EVM uint256
# ---------------------------------------------------------------------------


class NonEvmChain(StrEnum):
    """Non-EVM chain identifiers."""

    SOLANA = "SOLANA"
    BITCOIN = "BITCOIN"


# Solana key program/token addresses (symbol -> mint)
SOLANA_TOKEN_ADDRESSES: dict[str, str] = {
    # Native + wrapped
    "WSOL": "So11111111111111111111111111111111111111112",
    "SOL": "So11111111111111111111111111111111111111112",
    # Stablecoins
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "PYUSD": "2b1kV6DkPAnxd5ixfnExCx2PdhTtQER4hSsd53Ky7Adr",
    "USDE": "DEkqHyPN7GMRJ5cAU54aqYySacfiMkNy3asF1JEvp2up",
    "SUSDE": "Eh6XEPhSwoLv5kaAtbuvv6EaVHm11Yjhed2BNSHBBBiA",
    "USDH": "USDH1SM1ojwWUga67PBrgQe7PYQMjdiBJKgnGFmsDs7F",
    "EURC": "HzwqbKZw8HxMN6bF2yFZNrht3c2iXXzpKcFu7uBEDKtr",
    # BTC wrapped
    "WETH": "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",
    "WBTC": "3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh",
    "WBTC_PORTAL": "3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh",
    "CBBTC": "cbbtcn3Keb2DW3ZsmLmrsPGsRRhQ3HmFsRJhKqLm1bq",
    "TBTC": "6DNSN2BJsaPFdFFc1zP37kkeNe4Usc1Sqkzr9C9vPWcU",
    # Liquid staking
    "MSOL": "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",
    "JITOSOL": "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",
    "BSOL": "bSo13r4TkiE4KumL71LsHTPpL2euBYLFx6h9HP3piy1",
    "STSOL": "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj",
    "JSOL": "7Q2afV64in6N6SeZsAAB81TJzwpeLmhBf8u3mE2ip1Fh",
    "BNSOL": "BNso1VUJnh4zcfpZa6986Ea66P6TCp59hvtNJ8b1X85",
    # Top ecosystem tokens
    "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
    "JTO": "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL",
    "RAY": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
    "ORCA": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "PYTH": "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3",
    "HNT": "hntyVP6YFm1Hg25TN9WGLqM12b8TQv3TXsxg8HBatYS",
    "WIF": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
    "MNDE": "MNDEFzGvMt87ueuHvVU9VcTqsAP5b3fTGPsHuuPA5ey",
    "KMNO": "KMNo3nJsBXfcpJTVhZcXLW7RmTwTt4GVFE7suUBo9sS",
    "RNDR": "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof",
    # Bridged
    "AVAX": "AUrMpCDYYcPuGMvN8P8PQkpHf3AqiL54ziiPPWQr3XXR",
    "WSTETH": "ZScHuTtqZukUrtZS43teTKGs2VqkKL8k4QCouR2n6Uo",
    "BNB": "9gP2kCy3wA1ctvYWQk75guqXuHfrEomqydHLtcTCqiLa",
}

# Reverse mapping: mint -> symbol (for parsing on-chain / API responses)
SOLANA_MINT_TO_SYMBOL: dict[str, str] = {v: k for k, v in SOLANA_TOKEN_ADDRESSES.items()}
# Fix WSOL/SOL collision — prefer SOL
SOLANA_MINT_TO_SYMBOL["So11111111111111111111111111111111111111112"] = "SOL"

# Solana DeFi protocol metadata — SSOT for all API endpoints.
# Services import these URLs; never hardcode them.
SOLANA_DEFI_PROTOCOLS: dict[str, dict[str, str]] = {
    "drift": {
        "name": "Drift Protocol",
        "type": "perps_dex",
        "program_id": "dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH",
        "api_url": "https://data.api.drift.trade",
        "dlob_url": "https://dlob.drift.trade",
        "ws_url": "wss://dlob.drift.trade/ws",
        "s3_historical_url": (
            "https://drift-historical-data-v2.s3.eu-west-1.amazonaws.com"
            "/program/dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH"
        ),
        "data_source": "drift_api",
    },
    "mango": {
        "name": "Mango Markets V4",
        "type": "perps_dex",
        "program_id": "4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg",
        "api_url": "https://api.mngo.cloud/data/v4",
        "data_source": "mango_api",
    },
    "zeta": {
        "name": "Zeta Markets",
        "type": "perps_dex",
        "program_id": "ZETAxsqBRek56DhiGXrn75yj2NHU3aYUnxvHXpkf3aD",
        "api_url": "https://dex.zeta.markets/api",
        "data_source": "zeta_api",
    },
    "flash_trade": {
        "name": "Flash Trade",
        "type": "perps_dex",
        "program_id": "FLASH6Lo6h3iasJKWDs2F8TkW2UKf3s15C8PMGuVfgBn",
        "api_url": "https://api.flash.trade/api/v1",
        "data_source": "flash_api",
    },
    "raydium": {
        "name": "Raydium",
        "type": "dex",
        "program_id": "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
        "api_url": "https://api-v3.raydium.io",
        "data_source": "raydium_api",
    },
    "orca": {
        "name": "Orca (Whirlpool)",
        "type": "dex",
        "program_id": "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",
        "api_url": "https://api.mainnet.orca.so",
        "data_source": "orca_api",
    },
    "marinade": {
        "name": "Marinade Finance",
        "type": "liquid_staking",
        "program_id": "MarBmsSgKXdrN1egZf5sqe1TMai9K1rChYNDJgjq7aD",
        "api_url": "https://api.marinade.finance",
        "data_source": "marinade_api",
    },
    "kamino": {
        "name": "Kamino Finance",
        "type": "lending",
        "program_id": "KLend2g3cP87ber41GXWsSZQhDqc7juFGkhGJk2HRFUj",
        "api_url": "https://api.kamino.finance",
        "data_source": "kamino_api",
    },
    "jupiter": {
        "name": "Jupiter",
        "type": "aggregator",
        "api_url": "https://lite-api.jup.ag/swap/v1",
        "data_source": "jupiter_api",
    },
    "jito": {
        "name": "Jito",
        "type": "liquid_staking",
        "api_url": "https://kobe.mainnet.jito.network",
        "program_id": "Jito4APyf642JPZPx3hGc6WWJ8zPKtRbRs4P3eg9gB",
        "data_source": "helius",
    },
    "marginfi": {
        "name": "Marginfi",
        "type": "lending",
        "program_id": "MFv2hWf31Z9kbCa1snEPYctwafyhdvnV7FZnsebVacA",
        "data_source": "defillama",
    },
    "solend": {
        "name": "Solend",
        "type": "lending",
        "program_id": "So1endDq2YkqhipRh3WViPa8hFb54GdNFfmLqErtPqNo",
        "data_source": "defillama",
    },
    # ── Plan C: Solana AMM coverage expansion (2026-05-13) ──────────────
    "meteora": {
        "name": "Meteora Dynamic Liquidity",
        "type": "amm_dex",
        "program_id": "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo",
        "api_url": "https://app.meteora.ag/api",
        "data_source": "meteora_api",
    },
    "phoenix": {
        "name": "Phoenix CLOB DEX",
        "type": "clob_dex",
        "program_id": "PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY",
        "api_url": "https://api.phoenix.trade",
        "data_source": "phoenix_api",
    },
    "lifinity": {
        "name": "Lifinity Protocol",
        "type": "amm_dex",
        "program_id": "LFNTYraetVioAPnGJht4yNg2aUZFXR776cMeN9VMjXp",
        "api_url": "https://api.lifinity.io",
        "data_source": "lifinity_api",
    },
    "pyth": {
        "name": "Pyth Network Oracle",
        "type": "oracle",
        "program_id": "rec5EKMGg6MxZYaMdyBfgwp4d5rB9T1VQH5pJv5LtFJ",
        "api_url": "https://hermes.pyth.network/v2",
        "pythnet_url": "https://pythnet.rpcpool.com",
        "data_source": "pyth_hermes",
    },
    # solayer + picasso + cambrian removed 2026-06-02 (operator decision): no usable/decodable
    # DeFi data source. Solayer = sSOL is a custom LRT vault with no decodable exchange-rate
    # layout / no IDL (program_id here was a "best-guess" placeholder). Picasso ~3 tx/month,
    # no yield API; Cambrian is a dev SDK, not a venue. Excluded from the registry. SSOT:
    # plans/active/issues/issue_docs_remediation_sweep_2026_06_02.md.
}


def get_solana_protocol_url(protocol: str, url_type: str = "api_url") -> str | None:
    """Get a Solana DeFi protocol URL by protocol name and URL type.

    Args:
        protocol: Protocol key (drift, raydium, orca, kamino, marinade, jupiter).
        url_type: URL type key (api_url, dlob_url, ws_url, s3_historical_url).
    """
    proto = SOLANA_DEFI_PROTOCOLS.get(protocol)
    if proto is None:
        return None
    return proto.get(url_type)


def resolve_solana_mint(mint: str) -> str:
    """Resolve a Solana token mint address to its symbol.

    Returns empty string for unknown mints — callers should reject instruments
    where either token can't be resolved to a known symbol.
    """
    return SOLANA_MINT_TO_SYMBOL.get(mint, "")


# Bitcoin metadata — native BTC DeFi is minimal; we focus on wrapped BTC on EVM.
# Stacks (STX) has some Bitcoin DeFi but is too small for our system.
BITCOIN_RPC_TEMPLATES: dict[str, str] = {
    "blockstream": "https://blockstream.info/api",
    "mempool": "https://mempool.space/api",
}

# ---------------------------------------------------------------------------
# Hyperliquid L1 RPC templates
# Native CLOB-on-chain perp venue; bridges to/from Arbitrum via native bridge.
# Uses Hyperliquid's own API endpoints — no Alchemy key required.
# ---------------------------------------------------------------------------
HYPERLIQUID_RPC_TEMPLATES: dict[str, str] = {
    "mainnet": "https://api.hyperliquid.xyz",
    "testnet": "https://api.hyperliquid-testnet.xyz",
}

# ---------------------------------------------------------------------------
# Starknet RPC templates
# ZK-rollup L2 on Ethereum; bridges via StarkGate (~8h withdrawal delay).
# Uses alchemy-api-key from Secret Manager (Alchemy supports Starknet).
# ---------------------------------------------------------------------------
STARKNET_RPC_TEMPLATES: dict[str, str] = {
    "alchemy": "https://starknet-mainnet.g.alchemy.com/starknet/version/rpc/v0_7/{api_key}",
    "public": "https://free-rpc.nethermind.io/mainnet-juno",
    "testnet_alchemy": "https://starknet-sepolia.g.alchemy.com/starknet/version/rpc/v0_7/{api_key}",
    "testnet_public": "https://free-rpc.nethermind.io/sepolia-juno",
}

# Wrapped BTC tokens on EVM chains (already in WBTC_ADDRESSES / CBBTC_ADDRESSES above)
# tBTC is another wrapped BTC option on Ethereum
TBTC_ADDRESSES: dict[int, str] = {
    1: "0x18084fbA666a33d37592fA2633fD49a74DD93a88",
    42161: "0x6c84a8f1c29108F47a79964b5Fe888D4f4D0dE40",
    137: "0x236aa50979D5f3De3Bd1Eeb40E81137F22ab794b",
    10: "0x6c84a8f1c29108F47a79964b5Fe888D4f4D0dE40",
    8453: "0x236aa50979D5f3De3Bd1Eeb40E81137F22ab794b",
}


def get_solana_rpc_url(provider: str = "alchemy", api_key: str = "") -> str | None:
    """Get a Solana RPC URL for the given provider."""
    template = SOLANA_RPC_TEMPLATES.get(provider)
    if template is None:
        return None
    return template.format(api_key=api_key)


def get_solana_token_address(symbol: str) -> str | None:
    """Get a Solana SPL token address by symbol."""
    return SOLANA_TOKEN_ADDRESSES.get(symbol.upper())
