"""Kraken Futures REST API contracts (futures.kraken.com/derivatives/api/v3/)."""

from unified_api_contracts.external.kraken_futures.schemas import (
    KrakenFuturesTicker,
    KrakenFuturesTickersResponse,
)

__all__ = ["KrakenFuturesTicker", "KrakenFuturesTickersResponse"]
