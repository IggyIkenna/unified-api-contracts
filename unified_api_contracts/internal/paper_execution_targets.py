"""Paper execution target registry — maps chain/venue to paper execution target.

When OperationalMode=PAPER, execution-service routes instructions to the paper
target for each chain or venue. This registry is the single source of truth for
that routing decision.

Target types (ExecutionTarget):
  FORK       — Tenderly fork (EVM chains) or local Hardhat/Anvil replay
  TESTNET    — Exchange/network testnet (Solana devnet, Deribit testnet, etc.)
  SIMULATION — Matching-engine simulation only (no external execution API)

Venue identifiers are uppercase canonical keys matching UAC venue registry.
Chain identifiers use lowercase canonical names matching CHAIN_RPC_TEMPLATES.
"""

from __future__ import annotations

from unified_api_contracts.internal.modes import ExecutionTarget

# ---------------------------------------------------------------------------
# EVM chains → Tenderly fork
# ---------------------------------------------------------------------------
_EVM_CHAIN_KEYS = (
    "ethereum",
    "arbitrum",
    "arbitrum_one",
    "optimism",
    "base",
    "polygon",
    "avalanche",
    "bnb",
    "bsc",
)

# ---------------------------------------------------------------------------
# Solana ecosystem → devnet
# ---------------------------------------------------------------------------
_SOLANA_CHAIN_KEYS = (
    "solana",
    "solana_mainnet",
)

# ---------------------------------------------------------------------------
# CeFi perp venues → testnet endpoints
# ---------------------------------------------------------------------------
_CEFI_PERP_VENUES = (
    "DERIBIT",
    "BINANCE",
    "BINANCE-FUTURES",
    "BYBIT",
    "OKX",
    "HYPERLIQUID",
    "KRAKEN",
    "KRAKEN-FUTURES",
)

# ---------------------------------------------------------------------------
# Sports betting venues → simulation (PaperBettingAdapter)
# ---------------------------------------------------------------------------
_SPORTS_VENUES = (
    "BETFAIR",
    "BETFAIR_EX_UK",
    "BETFAIR_EX_EU",
    "BETFAIR_EX_AU",
    "BETFAIR_SB_UK",
    "MATCHBOOK",
    "SMARKETS",
    "BETSSON",
)

# ---------------------------------------------------------------------------
# Prediction markets → simulation
# ---------------------------------------------------------------------------
_PREDICTION_VENUES = (
    "POLYMARKET",
    "KALSHI",
    "MANIFOLD",
)

# ---------------------------------------------------------------------------
# Canonical registry
# ---------------------------------------------------------------------------
PAPER_EXECUTION_TARGETS: dict[str, ExecutionTarget] = {
    **dict.fromkeys(_EVM_CHAIN_KEYS, ExecutionTarget.FORK),
    **dict.fromkeys(_SOLANA_CHAIN_KEYS, ExecutionTarget.TESTNET),
    **dict.fromkeys(_CEFI_PERP_VENUES, ExecutionTarget.TESTNET),
    **dict.fromkeys(_SPORTS_VENUES, ExecutionTarget.SIMULATION),
    **dict.fromkeys(_PREDICTION_VENUES, ExecutionTarget.SIMULATION),
}


def get_paper_target(chain_or_venue: str) -> ExecutionTarget:
    """Return the paper ExecutionTarget for a given chain or venue key.

    Falls back to SIMULATION for unknown keys — conservative default that
    prevents accidental live execution when routing is ambiguous.
    """
    return PAPER_EXECUTION_TARGETS.get(chain_or_venue, ExecutionTarget.SIMULATION)


__all__ = [
    "PAPER_EXECUTION_TARGETS",
    "get_paper_target",
]
