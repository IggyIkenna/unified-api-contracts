"""Gate.io exchange API contracts (CeFi, spot + futures + options)."""

from unified_api_contracts.external.gateio.schemas import (
    GateioFill,
    GateioOrder,
    GateioOrderBook,
    GateioTicker,
    GateioTrade,
)

__all__ = [
    "GateioFill",
    "GateioOrder",
    "GateioOrderBook",
    "GateioTicker",
    "GateioTrade",
]
