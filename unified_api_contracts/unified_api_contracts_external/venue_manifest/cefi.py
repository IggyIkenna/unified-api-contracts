"""CeFi venue contracts: centralized exchanges and traditional brokers."""

from __future__ import annotations

__api_version__ = "v1"  # matches provider_api_versions.yaml


from typing import TypedDict


class VenueContract(TypedDict, total=False):
    """Per-venue contract claims."""

    module: str
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


CEFI_VENUES: dict[str, VenueContract] = {
    "binance": {
        "module": "unified_api_contracts.unified_api_contracts_external.binance",
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
            "BinanceMarkPriceKline",
            "BinanceIndexPriceKline",
            "BinanceMyTrades",
            "BinanceIncome",
            "BinanceDeliveryPrice",
            "BinanceDeliveryHistory",
        ],
        "error_schema_classes": ["BinanceError"],
        "example_schema_map": {
            "ticker_example.json": "BinanceTicker",
            "order_example.json": "BinanceOrder",
            "error_example.json": "BinanceError",
            "klines_example.json": "BinanceKline",
            "exchange_info_example.json": "BinanceExchangeInfo",
            "mark_price_kline_example.json": "BinanceMarkPriceKline",
            "index_price_kline_example.json": "BinanceIndexPriceKline",
        },
    },
    "okx": {
        "has_rest": True,
        "has_websocket": True,
        "has_fix": False,
        "config_secret_field": "",
        "response_schema_classes": [
            "OKXMarket",
            "OKXTicker",
            "OKXOrder",
            "OKXOrderBook",
            "OKXPosition",
            "OKXFeeRate",
            "OKXFundingRateHistory",
            "OKXDepositAddress",
            "OKXDepositHistory",
            "OKXWithdrawalHistory",
            "OKXFundTransfer",
            "OKXLongShortRatio",
            "OKXOpenInterest",
            "OKXOpenInterestHistory",
            "OKXRiskLimit",
            "OKXPortfolioMarginAccount",
            "OKXDeliveryExerciseHistory",
        ],
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
        "response_schema_classes": [
            "BybitMarket",
            "BybitTicker",
            "BybitOrderBook",
            "BybitOrder",
            "BybitPosition",
            "BybitFeeRate",
            "BybitFundingRateHistory",
            "BybitDepositAddress",
            "BybitDepositRecords",
            "BybitWithdrawals",
            "BybitAccountTransfer",
            "BybitLongShortRatio",
            "BybitRiskLimit",
            "BybitInsuranceFund",
            "BybitDeliveryRecord",
        ],
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
            "DeribitAccountSummary",
            "DeribitPortfolioMarginSummary",
            "DeribitVolatilityIndex",
            "DeribitFundingRateHistory",
            "DeribitSettlementCashFlows",
            "DeribitRiskLimit",
            "DeribitSessionBankruptcyDetails",
            "DeribitInstrumentInfoFull",
            "DeribitUserPortfolio",
            "DeribitSettlementHistory",
        ],
        "error_schema_classes": ["DeribitError"],
        "example_schema_map": {
            "order_example.json": "DeribitOrder",
            "error_example.json": "DeribitError",
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
            "CoinbaseFeeSchedule",
            "CoinbaseOrder",
            "CoinbaseFill",
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
    "upbit": {
        "has_rest": True,
        "has_websocket": True,
        "has_fix": False,
        "config_secret_field": "",
        "response_schema_classes": [
            "UpbitMarket",
            "UpbitTicker",
            "UpbitOrder",
            "UpbitBalance",
            "UpbitFeeRate",
            "UpbitDeposit",
            "UpbitWithdrawal",
        ],
        "error_schema_classes": ["UpbitError"],
        "example_schema_map": {
            "ticker_example.json": "UpbitTicker",
            "error_example.json": "UpbitError",
        },
    },
    "aster": {
        "has_rest": True,
        "has_websocket": True,
        "has_fix": False,
        "config_secret_field": "",
        "response_schema_classes": [
            "AsterAggTrade",
            "AsterTrade",
            "AsterKline",
            "AsterMarkPrice",
            "AsterFundingRate",
            "AsterOpenInterest",
            "AsterOpenInterestHistory",
            "AsterTicker24hr",
            "AsterExchangeInfo",
            "AsterAccount",
            "AsterBalance",
            "AsterIncome",
            "AsterLeverageBracket",
            "AsterOrderTradeUpdate",
            "AsterAccountUpdate",
            "AsterLiquidationOrder",
            "AsterMarket",
            "AsterOrderBook",
            "AsterOrder",
            "AsterPosition",
        ],
        "error_schema_classes": ["AsterError"],
        "example_schema_map": {
            "order_example.json": "AsterOrder",
            "error_example.json": "AsterError",
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
            "HyperliquidUserState",
            "HyperliquidL2Book",
            "HyperliquidFundingHistoryEntry",
            "HyperliquidFill",
            "HyperliquidOpenOrder",
            "HyperliquidCandle",
            "HyperliquidVaultDetails",
            "HyperliquidLiquidation",
            "HyperliquidSpotMeta",
            "HyperliquidSpotAssetInfo",
            "HyperliquidUserFees",
            "HyperliquidSubAccount",
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
}
