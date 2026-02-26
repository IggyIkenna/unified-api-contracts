"""Single source of truth for per-venue contract coverage: REST, WebSocket, FIX, schemas, errors.

Used by tests to assert we have the right schemas and by optional live verification for secret names.
Align with docs/INDEX.md; update both if adding a venue or capability.
"""

from __future__ import annotations

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


VENUE_MANIFEST: dict[str, VenueContract] = {
    "databento": {
        "has_rest": True,
        "has_websocket": False,
        "has_fix": False,
        "config_secret_field": "databento_secret_name",
        "response_schema_classes": [
            "DatabentoOhlcvBar",
            "DatabentoTrade",
            "DatabentoMbp1",
            "DatabentoDefinition",
            "DatabentoSymbol",
        ],
        "error_schema_classes": [],
        "example_schema_map": {"ohlcv_bar_example.json": "DatabentoOhlcvBar"},
    },
    "tardis": {
        "has_rest": True,
        "has_websocket": False,
        "has_fix": False,
        "config_secret_field": "tardis_secret_name",
        "response_schema_classes": [
            "TardisExchange",
            "TardisInstrument",
            "TardisTrade",
            "TardisOrderBookLevel",
            "TardisOrderBook",
        ],
        "error_schema_classes": ["TardisError"],
        "example_schema_map": {
            "trade_example.json": "TardisTrade",
            "error_example.json": "TardisError",
        },
    },
    "ccxt": {
        "has_rest": True,
        "has_websocket": False,
        "has_fix": False,
        "config_secret_field": "",  # CCXT uses exchange-specific keys
        "response_schema_classes": [
            "CcxtOrder",
            "CcxtTrade",
            "CcxtBalance",
            "CcxtBalanceResponse",
            "CcxtPosition",
            "CcxtMarket",
            "CcxtTicker",
            "CcxtOrderBook",
        ],
        "error_schema_classes": ["CcxtErrorPayload"],
        "example_schema_map": {"fetch_order_example.json": "CcxtOrder"},
    },
    "binance": {
        "has_rest": True,
        "has_websocket": True,
        "has_fix": False,
        "config_secret_field": "",
        "response_schema_classes": [
            "BinanceTicker",
            "BinanceOrderBook",
            "BinanceTrade",
            "BinanceOrder",
            "BinancePosition",
            "BinanceKline",
            "BinanceSymbol",
            "BinanceExchangeInfo",
        ],
        "error_schema_classes": ["BinanceError"],
        "example_schema_map": {
            "ticker_example.json": "BinanceTicker",
            "order_example.json": "BinanceOrder",
            "error_example.json": "BinanceError",
            "klines_example.json": "BinanceKline",
            "exchange_info_example.json": "BinanceExchangeInfo",
        },
    },
    "thegraph": {
        "has_rest": True,
        "has_websocket": False,
        "has_fix": False,
        "config_secret_field": "thegraph_secret_name",
        "response_schema_classes": [
            "TheGraphResponse",
            "SubgraphPool",
            "SubgraphSwap",
            "SubgraphToken",
            "SubgraphReserve",
        ],
        "error_schema_classes": ["GraphQLError"],
        "example_schema_map": {
            "response_example.json": "TheGraphResponse",
            "graphql_error_example.json": "GraphQLError",
        },
    },
    "okx": {
        "has_rest": True,
        "has_websocket": True,
        "has_fix": False,
        "config_secret_field": "",
        "response_schema_classes": ["OKXMarket", "OKXTicker", "OKXOrder", "OKXPosition"],
        "error_schema_classes": ["OKXError"],
        "example_schema_map": {
            "ticker_example.json": "OKXTicker",
            "error_example.json": "OKXError",
        },
    },
    "bybit": {
        "has_rest": True,
        "has_websocket": True,
        "has_fix": False,
        "config_secret_field": "",
        "response_schema_classes": ["BybitMarket", "BybitTicker", "BybitOrder", "BybitPosition"],
        "error_schema_classes": ["BybitError"],
        "example_schema_map": {
            "ticker_example.json": "BybitTicker",
            "error_example.json": "BybitError",
        },
    },
    "deribit": {
        "has_rest": True,
        "has_websocket": True,
        "has_fix": False,
        "config_secret_field": "",
        "response_schema_classes": [
            "DeribitInstrument",
            "DeribitTicker",
            "DeribitOrderBook",
            "DeribitOrder",
            "DeribitPosition",
        ],
        "error_schema_classes": ["DeribitError"],
        "example_schema_map": {
            "order_example.json": "DeribitOrder",
            "error_example.json": "DeribitError",
        },
    },
    "yahoo_finance": {
        "has_rest": True,
        "has_websocket": False,
        "has_fix": False,
        "config_secret_field": "",
        "response_schema_classes": ["YahooQuote", "YahooChartResult"],
        "error_schema_classes": ["YahooError"],
        "example_schema_map": {
            "quote_example.json": "YahooQuote",
            "error_example.json": "YahooError",
        },
    },
    "alchemy": {
        "has_rest": True,
        "has_websocket": False,
        "has_fix": False,
        "config_secret_field": "alchemy_secret_name",
        "response_schema_classes": ["AlchemyRpcResponse", "AlchemyAssetTransfer", "AlchemyTokenBalance"],
        "error_schema_classes": ["AlchemyError"],
        "example_schema_map": {
            "rpc_response_example.json": "AlchemyRpcResponse",
            "error_example.json": "AlchemyError",
        },
    },
    "hyperliquid": {
        "has_rest": True,
        "has_websocket": True,
        "has_fix": False,
        "config_secret_field": "",
        "response_schema_classes": [
            "HyperliquidMeta",
            "HyperliquidTicker",
            "HyperliquidOrder",
            "HyperliquidPosition",
            "HyperliquidStatsRow",
        ],
        "error_schema_classes": ["HyperliquidError"],
        "example_schema_map": {
            "ticker_example.json": "HyperliquidTicker",
            "error_example.json": "HyperliquidError",
        },
    },
    "aster": {
        "has_rest": True,
        "has_websocket": True,
        "has_fix": False,
        "config_secret_field": "",
        "response_schema_classes": ["AsterMarket", "AsterOrderBook", "AsterOrder", "AsterPosition"],
        "error_schema_classes": ["AsterError"],
        "example_schema_map": {
            "order_example.json": "AsterOrder",
            "error_example.json": "AsterError",
        },
    },
    "upbit": {
        "has_rest": True,
        "has_websocket": True,
        "has_fix": False,
        "config_secret_field": "",
        "response_schema_classes": ["UpbitMarket", "UpbitTicker", "UpbitOrder", "UpbitBalance"],
        "error_schema_classes": ["UpbitError"],
        "example_schema_map": {
            "ticker_example.json": "UpbitTicker",
            "error_example.json": "UpbitError",
        },
    },
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
            "IBKRPortfolioItem",
            "IBKRPnL",
        ],
        "error_schema_classes": ["IBKRError"],
        "example_schema_map": {
            "bar_example.json": "IBKRBar",
            "error_example.json": "IBKRError",
        },
    },
    "coinbase": {
        "has_rest": True,
        "has_websocket": True,
        "has_fix": False,
        "config_secret_field": "coinbase_secret_name",
        "response_schema_classes": [
            "CoinbaseTicker",
            "CoinbaseOrderBook",
            "CoinbaseTrade",
            "CoinbaseCandle",
            "CoinbaseProduct",
        ],
        "error_schema_classes": ["CoinbaseError"],
        "example_schema_map": {
            "ticker_example.json": "CoinbaseTicker",
            "orderbook_example.json": "CoinbaseOrderBook",
            "trade_example.json": "CoinbaseTrade",
            "candle_example.json": "CoinbaseCandle",
            "error_example.json": "CoinbaseError",
        },
    },
    "kraken": {
        "has_rest": True,
        "has_websocket": True,
        "has_fix": False,
        "config_secret_field": "kraken_secret_name",
        "response_schema_classes": [
            "KrakenTickerResponse",
            "KrakenTickerData",
            "KrakenOrderBook",
            "KrakenOrderBookLevel",
            "KrakenTrade",
            "KrakenOHLC",
            "KrakenAssetPair",
        ],
        "error_schema_classes": ["KrakenError"],
        "example_schema_map": {
            "ticker_example.json": "KrakenTickerResponse",
            "orderbook_example.json": "KrakenOrderBook",
            "trade_example.json": "KrakenTrade",
            "ohlc_example.json": "KrakenOHLC",
            "error_example.json": "KrakenError",
        },
    },
}
