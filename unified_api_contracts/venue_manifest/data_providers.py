"""Data provider venue contracts: market data and alternative data sources."""

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


DATA_PROVIDER_VENUES: dict[str, VenueContract] = {
    "databento": {
        "has_rest": True,
        "has_websocket": False,
        "has_fix": False,
        "config_secret_field": "databento_secret_name",
        "response_schema_classes": [
            "DatabentoOhlcvBar",
            "DatabentoTrade",
            "DatabentoMbp1",
            "DatabentoMbp10",
            "DatabentoMbo",
            "DatabentoBbo1s",
            "DatabentoBbo1m",
            "DatabentoCmbp1",
            "DatabentoStatus",
            "DatabentoImbalance",
            "DatabentoStatistics",
            "DatabentoTbbo",
            "DatabentoDefinition",
            "DatabentoSymbol",
        ],
        "error_schema_classes": ["DatabentoError"],
        "example_schema_map": {"ohlcv_bar_example.json": "DatabentoOhlcvBar", "error_example.json": "DatabentoError"},
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
            "TardisBookSnapshot5",
            "TardisBookSnapshot25",
            "TardisIncrementalBookL2",
            "TardisQuotes",
            "TardisLiquidations",
            "TardisDerivativeTicker",
            "TardisOptionsChain",
        ],
        "error_schema_classes": ["TardisError"],
        "example_schema_map": {
            "trade_example.json": "TardisTrade",
            "error_example.json": "TardisError",
            "book_snapshot_25_example.json": "TardisBookSnapshot25",
            "incremental_book_L2_example.json": "TardisIncrementalBookL2",
            "quotes_example.json": "TardisQuotes",
        },
    },
    "ccxt": {
        "has_rest": True,
        "has_websocket": False,
        "has_fix": False,
        "config_secret_field": "",
        "response_schema_classes": [
            "CcxtOrder",
            "CcxtTrade",
            "CcxtBalance",
            "CcxtBalanceResponse",
            "CcxtPosition",
            "CcxtMarket",
            "CcxtTicker",
            "CcxtOrderBook",
            "CcxtFundingRate",
            "CcxtFundingRateHistory",
            "CcxtOpenInterest",
            "CcxtOpenInterestHistory",
            "CcxtOhlcv",
            "CcxtAggTrade",
            "CcxtLeverageTiers",
            "CcxtLongShortRatio",
            "CcxtGreeks",
            "CcxtWithdrawal",
            "CcxtDeposit",
            "CcxtDepositAddress",
            "CcxtLedger",
            "CcxtTransfer",
            "CcxtTradingFee",
            "CcxtBorrowRate",
            "CcxtBorrowInterest",
            "CcxtMarginAdjustment",
            "CcxtInsuranceFund",
            "CcxtLiquidation",
            "CcxtSettlementHistory",
            "CcxtSubaccount",
            "CcxtCurrency",
            "CcxtCurrencyNetwork",
            "CcxtOption",
            "CcxtFees",
            "CcxtVolatilityHistory",
            "CcxtLeverage",
        ],
        "error_schema_classes": ["CcxtErrorPayload"],
        "example_schema_map": {
            "fetch_order_example.json": "CcxtOrder",
            "error_example.json": "CcxtErrorPayload",
            "borrow_rate_example.json": "CcxtBorrowRate",
            "insurance_fund_example.json": "CcxtInsuranceFund",
            "liquidation_example.json": "CcxtLiquidation",
            "subaccount_example.json": "CcxtSubaccount",
            "currency_example.json": "CcxtCurrency",
        },
    },
}
