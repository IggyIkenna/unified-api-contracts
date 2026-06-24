"""TradFi venue contracts: traditional finance and institutional brokers."""

from __future__ import annotations

__api_version__ = "v1"  # matches provider_api_versions.yaml


from typing import TypedDict


class VenueContract(TypedDict):
    """Per-venue contract claims."""

    has_rest: bool
    has_websocket: bool
    has_fix: bool
    """Config field name for Secret Manager (UnifiedCloudConfig), or empty if no API key."""
    config_secret_field: str
    """Expected schema class names in this venue's schemas.py (REST response types)."""
    response_schema_classes: list[str]
    """Expected error/status schema class names."""
    error_schema_classes: list[str]
    """Example file name pattern -> schema class name for validation."""
    example_schema_map: dict[str, str]


TRADFI_VENUES: dict[str, VenueContract] = {
    "ibkr": {
        "has_rest": False,
        "has_websocket": True,
        "has_fix": False,
        "config_secret_field": "",
        "response_schema_classes": [
            "IBKRBar",
            "IBKRTicker",
            "IBKROrder",
            "IBKRPosition",
            "IBKRAccountValue",
            "IBKRAccountUpdateMulti",
            "IBKRPortfolioItem",
            "IBKRPnL",
            "IBKRContractDetails",
            "IBKRScannerSubscription",
            "IBKRScannerData",
            "IBKRExecution",
            "IBKRCommissionReport",
            "IBKRPnLSingle",
            "IBKRPnLHistory",
            "IBKRMarketDepth",
            "IBKRHistoricalTick",
            "IBKRHistoricalTickBidAsk",
            "IBKRHistoricalTickLast",
            "IBKRSecDefOptParams",
            "IBKROptionGreeks",
            "IBKRHistoricalVolatility",
            "IBKRRealTimeBar",
        ],
        "error_schema_classes": ["IBKRError"],
        "example_schema_map": {
            "bar_example.json": "IBKRBar",
            "error_example.json": "IBKRError",
        },
    },
    "yahoo_finance": {
        "has_rest": True,
        "has_websocket": False,
        "has_fix": False,
        "config_secret_field": "",
        "response_schema_classes": [
            "YahooQuote",
            "YahooChartResult",
            "YahooOhlcv24h",
            "YahooSplits",
            "YahooDividends",
        ],
        "error_schema_classes": ["YahooError"],
        "example_schema_map": {
            "quote_example.json": "YahooQuote",
            "ohlcv_24h_example.json": "YahooOhlcv24h",
            "splits_example.json": "YahooSplits",
            "dividends_example.json": "YahooDividends",
            "error_example.json": "YahooError",
        },
    },
    # "barchart" venue manifest RETIRED 2026-06-24 — Barchart removed (VIX 15m now
    # aggregates from VX futures via Databento XCBF.PITCH). No shim.
}
