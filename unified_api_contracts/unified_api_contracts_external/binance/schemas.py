# This file was a backward-compat re-export shim and has been RETIRED.
# Import directly from the canonical sub-module instead:
#
#   account schemas:
#     from unified_api_contracts.unified_api_contracts_external.binance.account_schemas import BinanceFeeRate
#
#   market schemas:
#     from unified_api_contracts.unified_api_contracts_external.binance.market_schemas import BinanceTrade
#     from unified_api_contracts.unified_api_contracts_external.binance.market_schemas import BinanceTicker
#     from unified_api_contracts.unified_api_contracts_external.binance.market_schemas import BinanceKline
#     from unified_api_contracts.unified_api_contracts_external.binance.market_schemas import BinanceOrderBook
#
#   order schemas:
#     from unified_api_contracts.unified_api_contracts_external.binance.order_schemas import BinanceOrder
#     from unified_api_contracts.unified_api_contracts_external.binance.order_schemas import BinanceError
#     from unified_api_contracts.unified_api_contracts_external.binance.order_schemas import BinanceMyTrades
#
#   websocket schemas:
#     from unified_api_contracts.unified_api_contracts_external.binance.ws_schemas import BinanceMarkPriceUpdate
#     from unified_api_contracts.unified_api_contracts_external.binance.ws_schemas import BinanceLiquidationOrder
raise ImportError(
    "binance/schemas.py was a backward-compat shim and has been retired. "
    "Import directly from the specific sub-module: "
    "account_schemas, market_schemas, order_schemas, or ws_schemas. "
    "See the comments in this file for canonical import paths."
)
