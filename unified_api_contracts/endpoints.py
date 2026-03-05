"""Base URLs and endpoint-to-schema mapping for all venues.

Cross-cutting infrastructure for TradFi (Databento ~506 venues, IBKR), CeFi, and DeFi.
Used by VCR recording (scripts) and schema validation in the six interfaces.

TradFi: IBKR + Databento only; no direct CME/NASDAQ/NYSE. Databento provides
market data across ~506 venues via publisher_id; IBKR provides execution.
"""

from __future__ import annotations

import types
from typing import cast

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Base URLs (REST APIs only; WebSocket/TWS use different connection models)
# ---------------------------------------------------------------------------

BASE_URLS: dict[str, str] = {
    # Sports
    "betfair": "https://api.betfair.com/exchange/betting/rest/v1.0",
    "kalshi": "https://trading-api.kalshi.com/trade-api/v2",
    "pinnacle": "https://api.pinnacle.com",
    "polymarket": "https://clob.polymarket.com",
    "polymarket-gamma": "https://gamma-api.polymarket.com",
    "odds_api": "https://api.the-odds-api.com/v4",
    "api_football": "https://v3.football.api-sports.io",
    # CeFi
    "binance": "https://api.binance.com/api/v3",
    "binance-futures": "https://fapi.binance.com/fapi/v1",
    "binance-coinm": "https://dapi.binance.com/dapi/v1",
    "binance-papi": "https://papi.binance.com/papi/v1",
    "coinbase": "https://api.exchange.coinbase.com",
    "okx": "https://www.okx.com/api/v5",
    "bybit": "https://api.bybit.com/v5",
    "deribit": "https://www.deribit.com/api/v2",
    "upbit": "https://api.upbit.com/v1",
    "hyperliquid": "https://api.hyperliquid.xyz",
    "aster": "https://api.aster.finance",
    # TradFi
    "databento": "https://hist.databento.com",
    "databento-live": "https://feed.databento.com",
    # ibkr: TWS API (no REST); uses ib_insync / WebSocket
    # CeFi data
    "tardis": "https://api.tardis.dev/v1",
    "yahoo_finance": "https://query1.finance.yahoo.com",
    # DeFi
    "thegraph": "https://api.thegraph.com",
    "alchemy": "https://eth-mainnet.g.alchemy.com/v2",
    "mev": "https://relay.flashbots.net",
    "bloxroute": "https://api.blxrbdn.com",
    # CCXT: per-exchange; no single base URL
}

# ---------------------------------------------------------------------------
# (venue, endpoint) -> schema class name
# Used by VCR recording and schema validation in the six interfaces.
# Endpoint = logical endpoint key (ticker, orderbook, ohlcv, etc.)
# ---------------------------------------------------------------------------

ENDPOINT_SCHEMA_MAP: dict[tuple[str, str], str] = {
    # Binance
    ("binance", "ticker"): "BinanceTicker",
    ("binance", "orderbook"): "BinanceOrderBook",
    ("binance", "recent_trades"): "BinanceTrade",
    ("binance", "agg_trades"): "BinanceAggTrade",
    ("binance", "klines"): "BinanceKline",
    ("binance", "exchange_info"): "BinanceExchangeInfo",
    ("binance", "deposit_address"): "BinanceDepositAddress",
    ("binance", "deposit_history"): "BinanceDepositHistory",
    ("binance", "withdrawal_history"): "BinanceWithdrawalHistory",
    ("binance", "fee_rate"): "BinanceFeeRate",
    ("binance", "internal_transfer"): "BinanceInternalTransfer",
    ("binance", "sub_account"): "BinanceSubAccount",
    ("binance", "sub_account_assets"): "BinanceSubAccountAssets",
    ("binance-futures", "ticker"): "BinanceTicker",
    ("binance-futures", "orderbook"): "BinanceOrderBook",
    ("binance-futures", "agg_trades"): "BinanceAggTrade",
    ("binance-futures", "funding_rate"): "BinanceFundingRateHistory",
    ("binance-futures", "premium_index"): "BinancePremiumIndex",
    ("binance-futures", "mark_price_kline"): "BinanceMarkPriceKline",
    ("binance-futures", "index_price_kline"): "BinanceIndexPriceKline",
    ("binance-futures", "my_trades"): "BinanceMyTrades",
    ("binance-futures", "income"): "BinanceIncome",
    ("binance-futures", "delivery_price"): "BinanceDeliveryPrice",
    ("binance-futures", "delivery_history"): "BinanceDeliveryHistory",
    ("binance-futures", "adl_quantile"): "BinanceAdlQuantile",
    ("binance-futures", "insurance_fund"): "BinanceInsuranceFund",
    ("binance-futures", "position_risk"): "BinancePositionRisk",
    ("binance-coinm", "mark_price_kline"): "BinanceMarkPriceKline",
    ("binance-coinm", "index_price_kline"): "BinanceIndexPriceKline",
    ("binance-coinm", "my_trades"): "BinanceMyTrades",
    ("binance-coinm", "delivery_history"): "BinanceDeliveryHistory",
    ("binance-coinm", "income"): "BinanceIncome",
    ("binance-papi", "account"): "BinancePapiAccount",
    ("binance-papi", "balance"): "BinancePapiBalance",
    ("binance-papi", "position"): "BinancePapiPosition",
    # Coinbase
    ("coinbase", "ticker"): "CoinbaseTicker",
    ("coinbase", "orderbook"): "CoinbaseOrderBook",
    ("coinbase", "recent_trades"): "CoinbaseTrade",
    ("coinbase", "candles"): "CoinbaseCandle",
    ("coinbase", "exchange_info"): "CoinbaseProduct",
    ("coinbase", "fee_schedule"): "CoinbaseFeeSchedule",
    ("coinbase", "order"): "CoinbaseOrder",
    ("coinbase", "fill"): "CoinbaseFill",
    # OKX
    ("okx", "ticker"): "OKXTicker",
    ("okx", "orderbook"): "OKXOrderBook",
    ("okx", "mark_price_kline"): "OKXMarkPriceKline",
    ("okx", "index_price_kline"): "OKXIndexPriceKline",
    ("okx", "option_summary"): "OKXOptionSummary",
    ("okx", "option_ticker"): "OKXOptionTicker",
    ("okx", "fee_rate"): "OKXFeeRate",
    ("okx", "funding_rate_history"): "OKXFundingRateHistory",
    ("okx", "deposit_address"): "OKXDepositAddress",
    ("okx", "deposit_history"): "OKXDepositHistory",
    ("okx", "withdrawal_history"): "OKXWithdrawalHistory",
    ("okx", "fund_transfer"): "OKXFundTransfer",
    ("okx", "long_short_ratio"): "OKXLongShortRatio",
    ("okx", "open_interest"): "OKXOpenInterest",
    ("okx", "open_interest_history"): "OKXOpenInterestHistory",
    ("okx", "risk_limit"): "OKXRiskLimit",
    ("okx", "portfolio_margin_account"): "OKXPortfolioMarginAccount",
    ("okx", "delivery_exercise_history"): "OKXDeliveryExerciseHistory",
    # Bybit
    ("bybit", "ticker"): "BybitTicker",
    ("bybit", "orderbook"): "BybitOrderBook",
    ("bybit", "mark_price_kline"): "BybitMarkPriceKline",
    ("bybit", "index_price_kline"): "BybitIndexPriceKline",
    ("bybit", "fee_rate"): "BybitFeeRate",
    ("bybit", "funding_rate_history"): "BybitFundingRateHistory",
    ("bybit", "deposit_address"): "BybitDepositAddress",
    ("bybit", "deposit_records"): "BybitDepositRecords",
    ("bybit", "withdrawals"): "BybitWithdrawals",
    ("bybit", "account_transfer"): "BybitAccountTransfer",
    ("bybit", "long_short_ratio"): "BybitLongShortRatio",
    ("bybit", "risk_limit"): "BybitRiskLimit",
    ("bybit", "insurance_fund"): "BybitInsuranceFund",
    ("bybit", "delivery_record"): "BybitDeliveryRecord",
    # Databento (TradFi ~506 venues via publisher_id)
    ("databento", "ohlcv"): "DatabentoOhlcvBar",
    ("databento", "trades"): "DatabentoTrade",
    ("databento", "mbp1"): "DatabentoMbp1",
    ("databento", "mbp10"): "DatabentoMbp10",
    ("databento", "mbo"): "DatabentoMbo",
    ("databento", "bbo1s"): "DatabentoBbo1s",
    ("databento", "bbo1m"): "DatabentoBbo1m",
    ("databento", "cmbp1"): "DatabentoCmbp1",
    ("databento", "status"): "DatabentoStatus",
    ("databento", "imbalance"): "DatabentoImbalance",
    ("databento", "statistics"): "DatabentoStatistics",
    ("databento", "system_msg"): "DatabentoSystemMsg",
    ("databento", "error_msg"): "DatabentoErrorMsg",
    ("databento", "tbbo"): "DatabentoTbbo",
    ("databento", "definition"): "DatabentoDefinition",
    ("databento", "symbology"): "DatabentoSymbol",
    # IBKR (TWS/ib_insync; no REST; schemas for callbacks)
    ("ibkr", "bar"): "IBKRBar",
    ("ibkr", "ticker"): "IBKRTicker",
    ("ibkr", "order"): "IBKROrder",
    ("ibkr", "position"): "IBKRPosition",
    ("ibkr", "account_value"): "IBKRAccountValue",
    ("ibkr", "account_update_multi"): "IBKRAccountUpdateMulti",
    ("ibkr", "portfolio"): "IBKRPortfolioItem",
    ("ibkr", "pnl"): "IBKRPnL",
    ("ibkr", "contract_details"): "IBKRContractDetails",
    ("ibkr", "scanner_subscription"): "IBKRScannerSubscription",
    ("ibkr", "scanner_data"): "IBKRScannerData",
    ("ibkr", "execution"): "IBKRExecution",
    ("ibkr", "commission_report"): "IBKRCommissionReport",
    ("ibkr", "pnl_single"): "IBKRPnLSingle",
    ("ibkr", "pnl_history"): "IBKRPnLHistory",
    ("ibkr", "market_depth"): "IBKRMarketDepth",
    ("ibkr", "historical_tick"): "IBKRHistoricalTick",
    ("ibkr", "historical_tick_bid_ask"): "IBKRHistoricalTickBidAsk",
    ("ibkr", "historical_tick_last"): "IBKRHistoricalTickLast",
    ("ibkr", "sec_def_opt_params"): "IBKRSecDefOptParams",
    ("ibkr", "option_greeks"): "IBKROptionGreeks",
    ("ibkr", "historical_volatility"): "IBKRHistoricalVolatility",
    ("ibkr", "real_time_bar"): "IBKRRealTimeBar",
    # Barchart (CSV only; no API; schema for parsed rows)
    ("barchart", "ohlcv_15m"): "BarchartOhlcv15m",
    # Tardis
    ("tardis", "exchanges"): "TardisExchange",
    ("tardis", "instruments"): "TardisInstrument",
    ("tardis", "trades"): "TardisTrade",
    ("tardis", "orderbook"): "TardisOrderBook",
    ("tardis", "book_snapshot_25"): "TardisBookSnapshot25",
    ("tardis", "incremental_book_L2"): "TardisIncrementalBookL2",
    ("tardis", "quotes"): "TardisQuotes",
    # Yahoo Finance
    ("yahoo_finance", "quote"): "YahooQuote",
    ("yahoo_finance", "chart"): "YahooChartResult",
    # Deribit
    ("deribit", "account_summary"): "DeribitAccountSummary",
    ("deribit", "portfolio_margin"): "DeribitPortfolioMarginSummary",
    ("deribit", "volatility_index"): "DeribitVolatilityIndex",
    ("deribit", "funding_rate_history"): "DeribitFundingRateHistory",
    ("deribit", "settlement_cash_flows"): "DeribitSettlementCashFlows",
    ("deribit", "risk_limit"): "DeribitRiskLimit",
    ("deribit", "session_bankruptcy"): "DeribitSessionBankruptcyDetails",
    ("deribit", "instrument"): "DeribitInstrument",
    ("deribit", "ticker"): "DeribitTicker",
    ("deribit", "orderbook"): "DeribitOrderBook",
    ("deribit", "order"): "DeribitOrder",
    ("deribit", "position"): "DeribitPosition",
    ("deribit", "instrument_info"): "DeribitInstrumentInfoFull",
    ("deribit", "user_portfolio"): "DeribitUserPortfolio",
    ("deribit", "settlement_history"): "DeribitSettlementHistory",
    # Hyperliquid
    ("hyperliquid", "meta"): "HyperliquidMeta",
    ("hyperliquid", "ticker"): "HyperliquidTicker",
    ("hyperliquid", "user_state"): "HyperliquidUserState",
    ("hyperliquid", "l2_book"): "HyperliquidL2Book",
    ("hyperliquid", "funding_history"): "HyperliquidFundingHistoryEntry",
    ("hyperliquid", "fill"): "HyperliquidFill",
    ("hyperliquid", "open_order"): "HyperliquidOpenOrder",
    ("hyperliquid", "candle"): "HyperliquidCandle",
    ("hyperliquid", "vault_details"): "HyperliquidVaultDetails",
    ("hyperliquid", "liquidation"): "HyperliquidLiquidation",
    ("hyperliquid", "spot_meta"): "HyperliquidSpotMeta",
    ("hyperliquid", "spot_asset_info"): "HyperliquidSpotAssetInfo",
    ("hyperliquid", "user_fees"): "HyperliquidUserFees",
    ("hyperliquid", "sub_account"): "HyperliquidSubAccount",
    ("hyperliquid", "order"): "HyperliquidOrder",
    ("hyperliquid", "position"): "HyperliquidPosition",
    # Upbit
    ("upbit", "ticker"): "UpbitTicker",
    # Aster (Binance Futures-compatible)
    ("aster", "agg_trade"): "AsterAggTrade",
    ("aster", "trade"): "AsterTrade",
    ("aster", "kline"): "AsterKline",
    ("aster", "mark_price"): "AsterMarkPrice",
    ("aster", "funding_rate"): "AsterFundingRate",
    ("aster", "open_interest"): "AsterOpenInterest",
    ("aster", "open_interest_history"): "AsterOpenInterestHistory",
    ("aster", "ticker_24hr"): "AsterTicker24hr",
    ("aster", "exchange_info"): "AsterExchangeInfo",
    ("aster", "account"): "AsterAccount",
    ("aster", "balance"): "AsterBalance",
    ("aster", "income"): "AsterIncome",
    ("aster", "leverage_bracket"): "AsterLeverageBracket",
    ("aster", "order_trade_update"): "AsterOrderTradeUpdate",
    ("aster", "account_update"): "AsterAccountUpdate",
    ("aster", "liquidation_order"): "AsterLiquidationOrder",
    ("aster", "market"): "AsterMarket",
    ("aster", "orderbook"): "AsterOrderBook",
    ("aster", "order"): "AsterOrder",
    ("aster", "position"): "AsterPosition",
    ("upbit", "fee_rate"): "UpbitFeeRate",
    ("upbit", "deposit"): "UpbitDeposit",
    ("upbit", "withdrawal"): "UpbitWithdrawal",
    # CCXT (unified)
    ("ccxt", "order"): "CcxtOrder",
    ("ccxt", "trade"): "CcxtTrade",
    ("ccxt", "ticker"): "CcxtTicker",
    ("ccxt", "orderbook"): "CcxtOrderBook",
    ("ccxt", "market"): "CcxtMarket",
    ("ccxt", "balance"): "CcxtBalanceResponse",
    ("ccxt", "position"): "CcxtPosition",
    ("ccxt", "borrow_rate"): "CcxtBorrowRate",
    ("ccxt", "borrow_interest"): "CcxtBorrowInterest",
    ("ccxt", "margin_adjustment"): "CcxtMarginAdjustment",
    ("ccxt", "insurance_fund"): "CcxtInsuranceFund",
    ("ccxt", "liquidation"): "CcxtLiquidation",
    ("ccxt", "settlement_history"): "CcxtSettlementHistory",
    ("ccxt", "subaccount"): "CcxtSubaccount",
    ("ccxt", "currency"): "CcxtCurrency",
    ("ccxt", "option"): "CcxtOption",
    # The Graph
    ("thegraph", "response"): "TheGraphResponse",
    ("thegraph", "aave_user_position"): "SubgraphAaveUserPosition",
    ("thegraph", "univ3_position"): "SubgraphUniV3Position",
    ("thegraph", "univ3_pool_tick"): "SubgraphUniV3PoolTick",
    ("thegraph", "curve_gauge"): "SubgraphCurveGauge",
    ("thegraph", "curve_voting_escrow"): "SubgraphCurveVotingEscrow",
    ("thegraph", "morpho_position"): "SubgraphMorphoPosition",
    ("thegraph", "lido_rebase"): "SubgraphLidoRebase",
    ("thegraph", "ethena_yield"): "SubgraphEthenaYield",
    ("thegraph", "erc20_transfer"): "SubgraphERC20Transfer",
    ("thegraph", "erc20_approval"): "SubgraphERC20Approval",
    # Alchemy
    ("alchemy", "rpc"): "AlchemyRpcResponse",
    ("alchemy", "transfers"): "AlchemyAssetTransfer",
    ("alchemy", "block"): "AlchemyBlock",
    ("alchemy", "transaction"): "AlchemyTransaction",
    ("alchemy", "transaction_receipt"): "AlchemyTransactionReceipt",
    ("alchemy", "log"): "AlchemyLog",
    ("alchemy", "decoded_log"): "AlchemyDecodedLog",
    ("alchemy", "gas_oracle"): "AlchemyGasOracle",
    ("alchemy", "ens_resolution"): "AlchemyEnsResolution",
    ("alchemy", "nft_metadata"): "AlchemyNFTMetadata",
    ("alchemy", "nft_ownership"): "AlchemyNFTOwnership",
    ("alchemy", "token_metadata"): "AlchemyTokenMetadata",
    ("alchemy", "simulation_result"): "AlchemySimulationResult",
    ("alchemy", "webhook"): "AlchemyWebhookSubscription",
    # MEV (Flashbots, MEV Blocker)
    ("mev", "cancel_private_tx"): "FlashbotsCancelPrivateTransactionParams",
    ("mev", "send_private_tx"): "FlashbotsPrivateTransactionParams",
    ("mev", "send_bundle"): "FlashbotsBundleParams",
    ("mev", "call_bundle"): "FlashbotsCallBundleParams",
    ("mev", "mev_share_bundle"): "MevShareBundleParams",
    # bloXroute BDN (Gateway-API, Cloud-API, Protect RPC)
    ("bloxroute", "tx_submit"): "BloxrouteTxSubmitResult",
    ("bloxroute", "bdn_blocks"): "BloxrouteBdnBlocksParams",
    ("bloxroute", "subscribe"): "BloxrouteSubscribeParams",
    ("bloxroute", "protect_endpoints"): "BloxrouteProtectEndpoints",
    # DeFi protocol lending (Aave, Compound, Morpho, Euler)
    ("defi", "aave_reserve"): "AaveV3ReserveData",
    ("defi", "aave_user_account"): "AaveV3UserAccountData",
    ("defi", "aave_user_reserve"): "AaveV3UserReserveData",
    ("defi", "compound_market"): "CompoundV3MarketInfo",
    ("defi", "compound_user_position"): "CompoundV3UserPosition",
    ("defi", "morpho_market"): "MorphoMarketParams",
    ("defi", "morpho_user_position"): "MorphoUserPosition",
    ("defi", "euler_vault"): "EulerVaultData",
    ("defi", "euler_user_position"): "EulerUserPosition",
    # Sports: Betfair, Pinnacle, Polymarket, Odds API, API-Football
    ("betfair", "auth"): "BetfairAuthResponse",
    ("betfair", "market_book"): "BetfairMarketBook",
    ("betfair", "market_catalogue"): "BetfairMarketCatalogue",
    ("betfair", "market_change"): "BetfairMarketChangeMessage",
    ("betfair", "order_update"): "BetfairOrderUpdate",
    ("betfair", "place_orders"): "BetfairPlaceOrdersResponse",
    ("betfair", "list_current_orders"): "BetfairListCurrentOrdersResponse",
    ("pinnacle", "league"): "PinnacleLeague",
    ("pinnacle", "event"): "PinnacleEvent",
    ("pinnacle", "odds"): "PinnacleOddsResponse",
    ("pinnacle", "settlement"): "PinnacleSettlementResponse",
    ("kalshi", "series"): "KalshiSeries",
    ("kalshi", "event"): "KalshiEvent",
    ("kalshi", "market"): "KalshiMarket",
    ("kalshi", "orderbook"): "KalshiOrderBook",
    ("kalshi", "trade"): "KalshiTrade",
    ("kalshi", "order"): "KalshiOrder",
    ("kalshi", "fill"): "KalshiFill",
    ("kalshi", "position"): "KalshiPosition",
    ("kalshi", "balance"): "KalshiBalance",
    ("kalshi", "candlestick"): "KalshiCandlestick",
    ("kalshi", "historical_cutoff"): "KalshiHistoricalCutoff",
    ("polymarket", "market"): "PolymarketMarket",
    ("polymarket", "orderbook"): "PolymarketOrderBook",
    ("polymarket", "trade"): "PolymarketTrade",
    ("polymarket", "order"): "PolymarketCLOBOrder",
    ("polymarket", "fill"): "PolymarketFill",
    ("polymarket", "market_result"): "PolymarketMarketResult",
    # Gamma API (gamma-api.polymarket.com): events, markets, tags
    ("polymarket", "gamma_events"): "PolymarketGammaEvent",
    ("polymarket", "gamma_markets"): "PolymarketGammaMarket",
    ("polymarket", "gamma_tags"): "PolymarketGammaTag",
    ("odds_api", "fixture"): "OddsApiFixture",
    ("odds_api", "historical_odds"): "OddsApiHistoricalOdds",
    ("api_football", "team"): "ApiFootballTeam",
    ("api_football", "league"): "ApiFootballLeague",
    ("api_football", "fixture"): "ApiFootballFixture",
    ("api_football", "lineup"): "ApiFootballLineup",
    ("api_football", "standing"): "ApiFootballStanding",
    ("api_football", "odds"): "ApiFootballOdds",
    ("api_football", "odds_live"): "ApiFootballOdds",
}


def get_schema_class_for_endpoint(venue: str, endpoint: str) -> type[BaseModel] | None:
    """Resolve (venue, endpoint) to schema class. Returns None if not found."""
    key = (venue, endpoint)
    schema_name = ENDPOINT_SCHEMA_MAP.get(key)
    if not schema_name:
        return None

    # Map venue to module (barchart -> unified_api_contracts.barchart)
    module_map: dict[str, str] = {
        "betfair": "betfair",
        "kalshi": "kalshi",
        "pinnacle": "pinnacle",
        "polymarket": "polymarket",
        "odds_api": "odds_api",
        "api_football": "api_football",
        "binance": "binance",
        "binance-futures": "binance",
        "binance-coinm": "binance",
        "binance-papi": "binance",
        "coinbase": "coinbase",
        "okx": "okx",
        "bybit": "bybit",
        "deribit": "deribit",
        "databento": "databento",
        "ibkr": "ibkr",
        "barchart": "barchart",
        "tardis": "tardis",
        "yahoo_finance": "yahoo_finance",
        "hyperliquid": "hyperliquid",
        "aster": "aster",
        "upbit": "upbit",
        "ccxt": "ccxt",
        "thegraph": "thegraph",
        "alchemy": "alchemy",
        "mev": "mev",
        "bloxroute": "bloxroute",
        "defi": "defi",
    }
    module_name = module_map.get(venue, venue)

    # Binance split its schemas into sub-modules; try each in order
    if module_name == "binance":
        for sub in ("market_schemas", "order_schemas", "account_schemas", "ws_schemas"):
            try:
                mod = cast(
                    types.ModuleType,
                    __import__(
                        f"unified_api_contracts.unified_api_contracts_external.{module_name}.{sub}",
                        fromlist=[schema_name],
                    ),
                )
                result = getattr(mod, schema_name, None)
                if result is not None:
                    return cast("type[BaseModel] | None", result)
            except (ImportError, AttributeError):
                continue
        return None

    mod = cast(
        types.ModuleType,
        __import__(f"unified_api_contracts.{module_name}.schemas", fromlist=[schema_name]),
    )
    result = getattr(mod, schema_name, None)
    return cast("type[BaseModel] | None", result)
