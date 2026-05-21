"""Drift Protocol REST API contracts (market stats via data.api.drift.trade)."""

from unified_api_contracts.external.drift.schemas import (
    DriftMarket,
    DriftMarketsResponse,
)

__all__ = ["DriftMarket", "DriftMarketsResponse"]
