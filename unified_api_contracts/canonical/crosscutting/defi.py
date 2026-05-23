"""DeFi crosscutting protocol and chain enums — shared across MTDS, strategy, execution, risk.

These enums identify DeFi lending protocols and chain identifiers used across
the DeFi pipeline (MTDS adapters, strategy-service archetype configs, execution-service
connectors, risk-and-exposure-service HF calculations).

They live here (not in a service-specific module) because the same enum values
flow through UAC archetype config, strategy-service factory, execution-service
orchestrator, risk-and-exposure-service HF calculation, and MTDS lending-rate
adapter keys — four services, one source of truth.

Plans:
- ``plans/active/defi_recursive_borrow_archetypes_2026_05_10.md`` Phase 2
  (UAC config schema extension — LendingProtocol)
- ``plans/active/defi_master.md`` § "Chain coverage + CLOB-on-chain"
  Phase 1 (ChainKind + CHAIN_BRIDGE_GRAPH)
"""

from __future__ import annotations

from enum import StrEnum


class ChainKind(StrEnum):
    """Canonical chain identifier for strategy archetype configs.

    Used by:

    * Strategy-service archetype configs — ``allowed_chains: list[ChainKind]``
      field gates which chains the archetype is permitted to execute on.
    * Execution-service — connector routing per chain.
    * MTDS adapters — per-chain adapter dispatch keys.

    Covers both EVM chains (where ``CHAIN_CONFIGS`` provides per-chain
    operational settings keyed by EVM chain ID) and non-EVM chains (Solana,
    Hyperliquid L1, Starknet) which have separate RPC template dicts.

    String values are lowercase; canonical string names match the UPPERCASE
    keys in ``CHAIN_GENESIS_DATES`` (lowercased).  E.g.
    ``ChainKind.ARBITRUM == "arbitrum"`` and
    ``CHAIN_GENESIS_DATES["ARBITRUM"] == "2021-08-31"``.
    """

    # ── Tier 1: Core ETH + major L2s ─────────────────────────────────────
    ETHEREUM = "ethereum"
    """Ethereum mainnet (chain ID 1). Primary DeFi chain."""
    ARBITRUM = "arbitrum"
    """Arbitrum One (chain ID 42161). Primary low-gas L2 for DeFi."""
    BASE = "base"
    """Base mainnet (chain ID 8453). Coinbase-backed OP-stack L2."""
    OPTIMISM = "optimism"
    """Optimism mainnet (chain ID 10)."""
    POLYGON = "polygon"
    """Polygon PoS mainnet (chain ID 137)."""
    AVALANCHE = "avalanche"
    """Avalanche C-Chain (chain ID 43114)."""

    # ── Tier 2: Major non-ETH EVM chains ─────────────────────────────────
    BSC = "bsc"
    """Binance Smart Chain / BNB Chain (chain ID 56)."""
    GNOSIS = "gnosis"
    """Gnosis Chain / xDai (chain ID 100)."""

    # ── Tier 3: ETH-native L2s + zkEVMs ──────────────────────────────────
    LINEA = "linea"
    """Linea mainnet (chain ID 59144)."""
    SCROLL = "scroll"
    """Scroll mainnet (chain ID 534352)."""
    ZKSYNC = "zksync"
    """zkSync Era mainnet (chain ID 324)."""
    BLAST = "blast"
    """Blast mainnet (chain ID 81457)."""
    MODE = "mode"
    """Mode mainnet (chain ID 34443)."""

    # ── Tier 4: Alt-L1s ───────────────────────────────────────────────────
    CELO = "celo"
    """Celo mainnet."""
    AURORA = "aurora"
    """Aurora (NEAR-based EVM) mainnet."""
    FANTOM = "fantom"
    """Fantom Opera mainnet."""
    MANTLE = "mantle"
    """Mantle mainnet."""
    METIS = "metis"
    """Metis Andromeda mainnet."""
    MOONBEAM = "moonbeam"
    """Moonbeam (Polkadot-based EVM) mainnet."""

    # ── Non-EVM chains ────────────────────────────────────────────────────
    SOLANA = "solana"
    """Solana mainnet. Primary Solana DeFi chain (Jito/Marinade/Orca/Raydium)."""
    BITCOIN = "bitcoin"
    """Bitcoin mainnet. Wrapped BTC on EVM chains (WBTC, cbBTC, tBTC)."""
    STARKNET = "starknet"
    """Starknet mainnet. ZK-rollup L2 on Ethereum; Extended DEX-perp venue.
    RPC: ``STARKNET_RPC_TEMPLATES``. Bridge: STARKNET ↔ ETHEREUM via STARK proof."""
    HYPERLIQUID_L1 = "hyperliquid_l1"
    """Hyperliquid L1 native chain. CLOB-on-chain perp venue (Lighter/Pacifica sibling).
    RPC: ``HYPERLIQUID_RPC_TEMPLATES``. Bridge: HYPERLIQUID_L1 ↔ ARBITRUM via native bridge."""


# ---------------------------------------------------------------------------
# Chain bridge graph — which chains can transfer assets to which
#
# This is the *direct* (1-hop) bridge graph: ``CHAIN_BRIDGE_GRAPH[A]`` lists
# chains directly bridgeable from A.  Multi-hop paths (A → B → C) are not
# enumerated here.
#
# Sources:
# - Hyperliquid L1 ↔ Arbitrum: Hyperliquid native bridge (USDC-based)
# - Starknet ↔ Ethereum: StarkGate (STARK proof bridge, ~8h withdrawal delay)
#
# Extended with all EVM L2 ↔ Ethereum bridges (used by transfer-rebalance
# service to enumerate valid rebalance paths).
#
# Plan: defi_master.md § "Chain coverage + CLOB-on-chain" Phase 1.
# ---------------------------------------------------------------------------
CHAIN_BRIDGE_GRAPH: dict[str, list[str]] = {
    # New non-EVM chain bridges (2026-05-18)
    ChainKind.HYPERLIQUID_L1: [ChainKind.ARBITRUM],
    ChainKind.STARKNET: [ChainKind.ETHEREUM],
    # EVM L2 ↔ Ethereum bridges (symmetric — added for completeness)
    ChainKind.ARBITRUM: [ChainKind.ETHEREUM, ChainKind.HYPERLIQUID_L1],
    ChainKind.BASE: [ChainKind.ETHEREUM],
    ChainKind.OPTIMISM: [ChainKind.ETHEREUM],
    ChainKind.LINEA: [ChainKind.ETHEREUM],
    ChainKind.SCROLL: [ChainKind.ETHEREUM],
    ChainKind.ZKSYNC: [ChainKind.ETHEREUM],
    ChainKind.BLAST: [ChainKind.ETHEREUM],
    ChainKind.MODE: [ChainKind.ETHEREUM],
    ChainKind.ETHEREUM: [
        ChainKind.ARBITRUM,
        ChainKind.BASE,
        ChainKind.OPTIMISM,
        ChainKind.LINEA,
        ChainKind.SCROLL,
        ChainKind.ZKSYNC,
        ChainKind.BLAST,
        ChainKind.MODE,
        ChainKind.STARKNET,
    ],
}


class LendingProtocol(StrEnum):
    """Canonical DeFi lending protocol identifier.

    Used by:

    * :mod:`unified_api_contracts.internal.architecture_v2.archetype_config` —
      ``lending_protocol`` field on :class:`~archetype_config.ArchetypeConfig`
      to declare which protocol the recursive-borrow strategy targets.
    * MTDS lending-rate adapters — ``aave_v3_lending_rates.py`` /
      ``compound_v3_lending_rates.py`` / etc. as their canonical protocol key.
    * Strategy-service factory — to route lending-leg execution to the
      correct on-chain integration.
    * Risk-and-exposure-service — to look up
      ``defi_reserve_params.get_reserve_params(asset, protocol=...)`` for HF
      calculation.

    Members ``SPARK``, ``MORPHO_BLUE``, and ``MAKER_DSR`` are included for
    completeness; they are P1/P2 for May-23 (AAVE_V3 + COMPOUND_V3 are P0).
    """

    AAVE_V3 = "aave_v3"
    """Aave V3 (multi-chain: Ethereum, Arbitrum, Base, Optimism, Polygon, …)."""

    COMPOUND_V3 = "compound_v3"
    """Compound V3 / Comet (multi-chain: Ethereum, Arbitrum, Base, Polygon)."""

    SPARK = "spark"
    """Spark Protocol (Aave V3 fork on Ethereum, operated by MakerDAO/Sky)."""

    MORPHO_BLUE = "morpho_blue"
    """Morpho Blue — isolated per-market lending with configurable LLTV."""

    MAKER_DSR = "maker_dsr"
    """MakerDAO DAI Savings Rate — single yield stream, no borrow leg."""
