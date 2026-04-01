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
    "SCROLL": 534352,
    "ZKSYNC": 324,
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
    "SCROLL": 534351,  # Scroll Sepolia
    "ZKSYNC": 300,  # zkSync Sepolia
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
    env_urls = BLOCK_EXPLORER_URLS.get(env, BLOCK_EXPLORER_URLS.get("mainnet", {}))
    return env_urls.get(chain_name.upper(), "")
