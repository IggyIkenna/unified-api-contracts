"""Alternative data normalizers: on-chain, oracle, and DeFi metrics.

Covers:
- Glassnode — on-chain analytics (MVRV, SOPR, NVT, HODL waves, exchange reserves, etc.)
- Arkham Intelligence — entity labeling and on-chain token flows
- Pyth Network — oracle price feeds (fixed-point conversion: price * 10^expo)
- DeFiLlama — protocol TVL, stablecoin circulating supply, yield pools

All numeric values are converted to Decimal for precision.
"""

from __future__ import annotations

from ..external.arkham.normalize import (
    normalize_arkham_alert_event,
    normalize_arkham_net_flow,
    normalize_arkham_token_flow,
)
from ..external.defillama.normalize import (
    normalize_defillama_chain_tvl,
    normalize_defillama_protocol,
    normalize_defillama_tvl_history_point,
    normalize_defillama_yield_pool,
)
from ..external.glassnode.normalize import (
    _unix_to_utc,
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
from ..external.pyth.normalize import normalize_pyth_price_feed
from ..external.tardis.normalize import _d

__all__ = [
    "_d",
    "_unix_to_utc",
    "normalize_arkham_alert_event",
    "normalize_arkham_net_flow",
    "normalize_arkham_token_flow",
    "normalize_defillama_chain_tvl",
    "normalize_defillama_protocol",
    "normalize_defillama_tvl_history_point",
    "normalize_defillama_yield_pool",
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
    "normalize_pyth_price_feed",
]
