"""Socket.tech cross-chain bridge API contracts (api.socket.tech/v2/).

Used by execution-service bridge.py for USDC cross-chain transfers.
Requires API-KEY header (Socket API key via Secret Manager 'socket-api-key').
"""

from unified_api_contracts.external.socket.schemas import (
    SocketQuoteResponse,
    SocketRoute,
    SocketTokenInfo,
)

__all__ = ["SocketQuoteResponse", "SocketRoute", "SocketTokenInfo"]
