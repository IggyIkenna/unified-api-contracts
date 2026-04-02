"""Capability declaration sub-modules, split by source category."""

from __future__ import annotations

from ._altdata import ALTDATA_CAPABILITIES
from ._cefi import CEFI_CAPABILITIES
from ._defi import (
    BITCOIN_RPC_TEMPLATES,
    CHAIN_RPC_TEMPLATES,
    DEFI_CAPABILITIES,
    PROTECTED_RPC_URLS,
    SOLANA_DEFI_PROTOCOLS,
    SOLANA_MINT_TO_SYMBOL,
    SOLANA_RPC_TEMPLATES,
    SOLANA_TOKEN_ADDRESSES,
    SUBGRAPH_IDS,
    TBTC_ADDRESSES,
    DeFiDataSource,
    NonEvmChain,
    get_solana_protocol_url,
    get_solana_rpc_url,
    get_solana_token_address,
    get_subgraph_id,
    get_supported_chains_for_protocol,
    resolve_solana_mint,
)
from ._sports import SPORTS_CAPABILITIES
from ._tradfi import TRADFI_CAPABILITIES

__all__ = [
    "ALTDATA_CAPABILITIES",
    "BITCOIN_RPC_TEMPLATES",
    "CEFI_CAPABILITIES",
    "CHAIN_RPC_TEMPLATES",
    "DEFI_CAPABILITIES",
    "PROTECTED_RPC_URLS",
    "SOLANA_DEFI_PROTOCOLS",
    "SOLANA_MINT_TO_SYMBOL",
    "SOLANA_RPC_TEMPLATES",
    "SOLANA_TOKEN_ADDRESSES",
    "SPORTS_CAPABILITIES",
    "SUBGRAPH_IDS",
    "TBTC_ADDRESSES",
    "TRADFI_CAPABILITIES",
    "DeFiDataSource",
    "NonEvmChain",
    "get_solana_protocol_url",
    "get_solana_rpc_url",
    "get_solana_token_address",
    "get_subgraph_id",
    "get_supported_chains_for_protocol",
    "resolve_solana_mint",
]
