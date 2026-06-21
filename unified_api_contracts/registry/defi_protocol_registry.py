"""DeFi protocol registry (SSOT).

Maps canonical venue keys to protocol identifiers and chain context.
Extends VenueMapping.venue_to_data_provider with protocol-level detail.

Previously duplicated across instruments-service config files
(instrument_definitions.py and defi_definitions.py).
Centralized here as the system SSOT per UAC registry pattern.
"""

from __future__ import annotations

# Maps canonical venue keys to (protocol_adapter_key, chain) for adapter dispatch.
# protocol_adapter_key matches the key used by UMI factory.py get_adapter().
# chain is the L1/L2 network or None for chain-agnostic protocols.
DEFI_VENUE_TO_PROTOCOL: dict[str, tuple[str, str | None]] = {
    "UNISWAP_V2-ETHEREUM": ("uniswap_v2", "ETHEREUM"),
    "UNISWAP_V3-ETHEREUM": ("uniswap_v3", "ETHEREUM"),
    "UNISWAP_V4-ETHEREUM": ("uniswap_v4", "ETHEREUM"),
    "CURVE-ETHEREUM": ("curve", "ETHEREUM"),
    "AAVE_V3-ETHEREUM": ("aave_v3", "ETHEREUM"),
    "ETHERFI-ETHEREUM": ("etherfi", "ETHEREUM"),
    "LIDO-ETHEREUM": ("lido", "ETHEREUM"),
    "MORPHO-ETHEREUM": ("morpho", "ETHEREUM"),
    "FLUID-PLASMA": ("fluid_plasma", None),
    "AAVE-PLASMA": ("aave_plasma", None),
    "ETHENA-ETHEREUM": ("ethena", "ETHEREUM"),
    # ── Chain-dominant DEXes ──────────────────────────────────────
    "PANCAKESWAP_V3-BSC": ("pancakeswap_v3", "BSC"),
    "PANCAKESWAP_V3-ETHEREUM": ("pancakeswap_v3", "ETHEREUM"),
    "PANCAKESWAP_V3-BASE": ("pancakeswap_v3", "BASE"),
    "SUSHISWAP_V3-ETHEREUM": ("sushiswap_v3", "ETHEREUM"),
    "SUSHISWAP_V3-AVALANCHE": ("sushiswap_v3", "AVALANCHE"),
    "SUSHISWAP-ARBITRUM": ("sushiswap", "ARBITRUM"),
    "AERODROME_V3-BASE": ("aerodrome_v3", "BASE"),
    "VELODROME_V2-OPTIMISM": ("velodrome_v2", "OPTIMISM"),
    "CAMELOT_V3-ARBITRUM": ("camelot_v3", "ARBITRUM"),
    "TRADER_JOE_V2-AVALANCHE": ("trader_joe_v2", "AVALANCHE"),
    # ── Additional perps / lending ────────────────────────────────
    "GMX-ARBITRUM": ("gmx", "ARBITRUM"),
    "GMX-AVALANCHE": ("gmx", "AVALANCHE"),
    "SPARK-ETHEREUM": ("spark", "ETHEREUM"),
}

# All DeFi protocols to process when no venue filter is specified.
# Order matches processing priority (DEX → Lending → LST/Yield).
DEFI_PROTOCOLS: list[tuple[str, str | None]] = [
    ("uniswap_v2", "ETHEREUM"),
    ("uniswap_v3", "ETHEREUM"),
    ("uniswap_v4", "ETHEREUM"),
    ("curve", "ETHEREUM"),
    ("balancer", "ETHEREUM"),
    ("aave_v3", "ETHEREUM"),
    ("etherfi", "ETHEREUM"),
    ("lido", "ETHEREUM"),
    ("morpho", "ETHEREUM"),
    ("fluid_plasma", None),
    ("aave_plasma", None),
    ("hyperliquid", None),
    ("aster", None),
    ("ethena", "ETHEREUM"),
    # Chain-dominant DEXes
    ("pancakeswap_v3", "BSC"),
    ("sushiswap_v3", "ETHEREUM"),
    ("aerodrome_v3", "BASE"),
    ("velodrome_v2", "OPTIMISM"),
    ("camelot_v3", "ARBITRUM"),
    ("trader_joe_v2", "AVALANCHE"),
    # Additional perps / lending
    ("gmx", "ARBITRUM"),
    ("spark", "ETHEREUM"),
]
