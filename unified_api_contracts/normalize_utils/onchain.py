"""Alternative data normalizers: on-chain and DeFi metrics.

Covers:
- Glassnode — on-chain analytics (MVRV, SOPR, NVT, HODL waves, exchange reserves, etc.)
- DeFiLlama — protocol TVL, stablecoin circulating supply, yield pools

All numeric values are converted to Decimal for precision.
"""

from __future__ import annotations

# Alchemy (already external)
from ..external.alchemy.normalize import (
    normalize_alchemy_asset_transfer,
    normalize_alchemy_block_to_metric,
    normalize_alchemy_token_balance,
    normalize_alchemy_transaction_to_metric,
)

# DeFiLlama
from ..external.defillama.normalize import (
    normalize_defillama_chain_tvl,
    normalize_defillama_protocol,
    normalize_defillama_tvl_history_point,
    normalize_defillama_yield_pool,
)

# Instadapp (already external)
from ..external.instadapp.normalize import (
    normalize_instadapp_position,
    normalize_instadapp_reserve,
    normalize_instadapp_smart_account,
)

# MEV (already external)
from ..external.mev.normalize import (
    normalize_flashbots_bundle_result,
    normalize_mev_share_bundle_result,
)

# TheGraph (already external)
from ..external.thegraph.normalize import (
    normalize_thegraph_pair_hour_to_metric,
    normalize_thegraph_pool_hour_to_metric,
    normalize_thegraph_pool_to_instrument,
    normalize_thegraph_swap_to_trade,
    normalize_thegraph_token_to_instrument,
)

__all__ = [
    "normalize_alchemy_asset_transfer",
    "normalize_alchemy_block_to_metric",
    "normalize_alchemy_token_balance",
    "normalize_alchemy_transaction_to_metric",
    "normalize_defillama_chain_tvl",
    "normalize_defillama_protocol",
    "normalize_defillama_tvl_history_point",
    "normalize_defillama_yield_pool",
    "normalize_flashbots_bundle_result",
    "normalize_instadapp_position",
    "normalize_instadapp_reserve",
    "normalize_instadapp_smart_account",
    "normalize_mev_share_bundle_result",
    "normalize_thegraph_pair_hour_to_metric",
    "normalize_thegraph_pool_hour_to_metric",
    "normalize_thegraph_pool_to_instrument",
    "normalize_thegraph_swap_to_trade",
    "normalize_thegraph_token_to_instrument",
]
