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
    "HYPERLIQUID": ("hyperliquid", None),
    "ASTER": ("aster", None),
    "UNISWAPV2-ETHEREUM": ("uniswap_v2", "ETHEREUM"),
    "UNISWAPV3-ETHEREUM": ("uniswap_v3", "ETHEREUM"),
    "UNISWAPV4-ETHEREUM": ("uniswap_v4", "ETHEREUM"),
    "CURVE-ETHEREUM": ("curve", "ETHEREUM"),
    "AAVEV3-ETHEREUM": ("aave_v3", "ETHEREUM"),
    "ETHERFI": ("etherfi", "ETHEREUM"),
    "LIDO": ("lido", "ETHEREUM"),
    "MORPHO-ETHEREUM": ("morpho", "ETHEREUM"),
    "FLUID-PLASMA": ("fluid_plasma", None),
    "AAVE-PLASMA": ("aave_plasma", None),
    "ETHENA": ("ethena", "ETHEREUM"),
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
]
