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
CHAIN_GENESIS_DATES: dict[str, str] = {
    "ETHEREUM": "2015-07-30",  # Frontier mainnet
    "ARBITRUM": "2021-08-31",  # Arbitrum One public mainnet
    "BASE": "2023-08-09",  # Base mainnet
    "OPTIMISM": "2021-12-16",  # OP mainnet (post-regenesis)
    "POLYGON": "2020-05-30",  # Matic mainnet (rebranded to Polygon)
    "AVALANCHE": "2020-09-22",  # C-Chain launch
    "BSC": "2020-08-29",  # Binance Smart Chain (rebranded to BNB Chain)
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
