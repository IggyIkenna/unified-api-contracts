"""Capability declaration sub-modules, split by source category."""

from __future__ import annotations

from ._altdata import ALTDATA_CAPABILITIES
from ._cefi import CEFI_CAPABILITIES
from ._defi import (
    CHAIN_RPC_TEMPLATES,
    DEFI_CAPABILITIES,
    SUBGRAPH_IDS,
    DeFiDataSource,
    get_subgraph_id,
)
from ._sports import SPORTS_CAPABILITIES
from ._tradfi import TRADFI_CAPABILITIES

__all__ = [
    "ALTDATA_CAPABILITIES",
    "CEFI_CAPABILITIES",
    "CHAIN_RPC_TEMPLATES",
    "DEFI_CAPABILITIES",
    "SPORTS_CAPABILITIES",
    "SUBGRAPH_IDS",
    "TRADFI_CAPABILITIES",
    "DeFiDataSource",
    "get_subgraph_id",
]
