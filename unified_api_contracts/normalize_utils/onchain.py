"""Alternative data normalizers: on-chain, oracle, and DeFi metrics.

Covers:
- Glassnode — on-chain analytics (MVRV, SOPR, NVT, HODL waves, exchange reserves, etc.)
- Arkham Intelligence — entity labeling and on-chain token flows
- Pyth Network — oracle price feeds (fixed-point conversion: price * 10^expo)
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

# Arkham
from ..external.arkham.normalize import (
    normalize_arkham_alert_event,
    normalize_arkham_net_flow,
    normalize_arkham_token_flow,
)

# Bloxroute (already external)
from ..external.bloxroute.normalize import (
    normalize_bloxroute_error,
    normalize_bloxroute_mempool_to_oracle_feed,
    normalize_bloxroute_mempool_to_trade,
    normalize_bloxroute_tx_submit_to_trade,
)

# CryptoQuant (already external)
from ..external.cryptoquant.normalize import (
    normalize_cryptoquant_exchange_flow,
    normalize_cryptoquant_miner_metrics,
    normalize_cryptoquant_reserve_metrics,
    normalize_cryptoquant_stablecoin_metrics,
    normalize_cryptoquant_whale_metrics,
)

# DeFiLlama
from ..external.defillama.normalize import (
    normalize_defillama_chain_tvl,
    normalize_defillama_protocol,
    normalize_defillama_tvl_history_point,
    normalize_defillama_yield_pool,
)

# Glassnode
from ..external.glassnode.normalize import (
    normalize_glassnode_exchange_reserves,
    normalize_glassnode_hodl_wave,
    normalize_glassnode_mvrv,
    normalize_glassnode_mvrv_z_score,
    normalize_glassnode_nvt,
    normalize_glassnode_nvt_signal,
    normalize_glassnode_realized_cap,
    normalize_glassnode_sopr,
    normalize_glassnode_thermocap,
    normalize_glassnode_timeseries_point,
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

# Pyth
from ..external.pyth.normalize import normalize_pyth_price_feed

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
    "normalize_arkham_alert_event",
    "normalize_arkham_net_flow",
    "normalize_arkham_token_flow",
    "normalize_bloxroute_error",
    "normalize_bloxroute_mempool_to_oracle_feed",
    "normalize_bloxroute_mempool_to_trade",
    "normalize_bloxroute_tx_submit_to_trade",
    "normalize_cryptoquant_exchange_flow",
    "normalize_cryptoquant_miner_metrics",
    "normalize_cryptoquant_reserve_metrics",
    "normalize_cryptoquant_stablecoin_metrics",
    "normalize_cryptoquant_whale_metrics",
    "normalize_defillama_chain_tvl",
    "normalize_defillama_protocol",
    "normalize_defillama_tvl_history_point",
    "normalize_defillama_yield_pool",
    "normalize_flashbots_bundle_result",
    "normalize_glassnode_exchange_reserves",
    "normalize_glassnode_hodl_wave",
    "normalize_glassnode_mvrv",
    "normalize_glassnode_mvrv_z_score",
    "normalize_glassnode_nvt",
    "normalize_glassnode_nvt_signal",
    "normalize_glassnode_realized_cap",
    "normalize_glassnode_sopr",
    "normalize_glassnode_thermocap",
    "normalize_glassnode_timeseries_point",
    "normalize_instadapp_position",
    "normalize_instadapp_reserve",
    "normalize_instadapp_smart_account",
    "normalize_mev_share_bundle_result",
    "normalize_pyth_price_feed",
    "normalize_thegraph_pair_hour_to_metric",
    "normalize_thegraph_pool_hour_to_metric",
    "normalize_thegraph_pool_to_instrument",
    "normalize_thegraph_swap_to_trade",
    "normalize_thegraph_token_to_instrument",
]
