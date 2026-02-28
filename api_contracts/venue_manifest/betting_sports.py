"""Betting and sports venue contracts: prediction markets and sportsbooks."""

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


BETTING_SPORTS_VENUES: dict[str, VenueContract] = {
    "betfair": {
        "has_rest": True,
        "has_websocket": True,
        "has_fix": False,
        "config_secret_field": "betfair_secret_name",
        "response_schema_classes": [
            "BetfairAuthResponse",
            "BetfairMarketBook",
            "BetfairMarketCatalogue",
            "BetfairMarketChangeMessage",
            "BetfairOrderUpdate",
            "BetfairPlaceOrdersResponse",
            "BetfairListCurrentOrdersResponse",
            "BetfairRunner",
            "BetfairRunnerChange",
        ],
        "error_schema_classes": ["BetfairError"],
        "example_schema_map": {
            "market_book_example.json": "BetfairMarketBook",
            "market_catalogue_example.json": "BetfairMarketCatalogue",
            "place_orders_example.json": "BetfairPlaceOrdersResponse",
            "list_current_orders_example.json": "BetfairListCurrentOrdersResponse",
            "error_example.json": "BetfairError",
        },
    },
    "pinnacle": {
        "has_rest": True,
        "has_websocket": False,
        "has_fix": False,
        "config_secret_field": "pinnacle_secret_name",
        "response_schema_classes": [
            "PinnacleLeague",
            "PinnacleEvent",
            "PinnaclePeriod",
            "PinnacleMoneyline",
            "PinnacleTotals",
            "PinnacleSpread",
            "PinnacleOddsResponse",
            "PinnacleSettlementResponse",
        ],
        "error_schema_classes": ["PinnacleError"],
        "example_schema_map": {
            "odds_response_example.json": "PinnacleOddsResponse",
            "error_example.json": "PinnacleError",
        },
    },
    "polymarket": {
        "has_rest": True,
        "has_websocket": False,
        "has_fix": False,
        "config_secret_field": "polymarket_secret_name",
        "response_schema_classes": [
            "PolymarketIdentifiers",
            "PolymarketMarket",
            "PolymarketToken",
            "PolymarketOrderBook",
            "PolymarketTrade",
            "PolymarketOrder",
            "PolymarketCLOBOrder",
            "PolymarketFill",
            "PolymarketMarketResult",
            "PolymarketGammaMarket",
            "PolymarketGammaEvent",
            "PolymarketGammaTag",
            "PolymarketGammaSeries",
            "PolymarketEvent",
            "PolymarketTag",
            "PolymarketNegRiskEvent",
            "PolymarketNegRiskMarket",
            "PolymarketResolution",
            "PolymarketSplit",
            "PolymarketMerge",
            "PolymarketL1AuthParams",
            "PolymarketPriceHistory",
        ],
        "error_schema_classes": ["PolymarketError"],
        "example_schema_map": {
            "market_example.json": "PolymarketMarket",
            "error_example.json": "PolymarketError",
        },
    },
    "odds_api": {
        "has_rest": True,
        "has_websocket": False,
        "has_fix": False,
        "config_secret_field": "odds_api_secret_name",
        "response_schema_classes": [
            "OddsApiFixture",
            "OddsApiBookmaker",
            "OddsApiMarket",
            "OddsApiOutcome",
            "OddsApiHistoricalOdds",
        ],
        "error_schema_classes": ["OddsApiError"],
        "example_schema_map": {
            "fixture_example.json": "OddsApiFixture",
            "error_example.json": "OddsApiError",
        },
    },
    "api_football": {
        "has_rest": True,
        "has_websocket": False,
        "has_fix": False,
        "config_secret_field": "api_football_secret_name",
        "response_schema_classes": [
            "ApiFootballFixture",
            "ApiFootballTeam",
            "ApiFootballLeague",
            "ApiFootballLineup",
            "ApiFootballStat",
            "ApiFootballScore",
            "ApiFootballPlayerStat",
            "ApiFootballStanding",
            "ApiFootballOdds",
            "ApiFootballOddsBookmaker",
            "ApiFootballOddsBet",
            "ApiFootballOddsValue",
        ],
        "error_schema_classes": ["ApiFootballError"],
        "example_schema_map": {
            "fixture_example.json": "ApiFootballFixture",
            "odds_example.json": "ApiFootballOdds",
            "error_example.json": "ApiFootballError",
        },
    },
    "kalshi": {
        "has_rest": True,
        "has_websocket": True,
        "has_fix": False,
        "config_secret_field": "kalshi_secret_name",
        "response_schema_classes": [
            "KalshiSeries",
            "KalshiEvent",
            "KalshiMarket",
            "KalshiOrderBook",
            "KalshiTrade",
            "KalshiOrder",
            "KalshiFill",
            "KalshiPosition",
            "KalshiBalance",
            "KalshiCandlestick",
            "KalshiHistoricalCutoff",
            "KalshiWebSocketTickerMsg",
            "KalshiWebSocketOrderbookDeltaMsg",
            "KalshiWebSocketTradeMsg",
            "KalshiWebSocketMarketLifecycleMsg",
        ],
        "error_schema_classes": ["KalshiError"],
        "example_schema_map": {
            "series_example.json": "KalshiSeries",
            "event_example.json": "KalshiEvent",
            "market_example.json": "KalshiMarket",
            "orderbook_example.json": "KalshiOrderBook",
            "trade_example.json": "KalshiTrade",
            "fill_example.json": "KalshiFill",
            "order_example.json": "KalshiOrder",
            "position_example.json": "KalshiPosition",
            "balance_example.json": "KalshiBalance",
            "error_example.json": "KalshiError",
        },
    },
}
