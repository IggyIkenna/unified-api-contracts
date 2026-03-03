"""Per-venue HTTP endpoint config for VCR recording and replay.

Each entry: url, method, optional headers builder key (env var name), response_path to extract
body for schema validation (e.g. '' = whole JSON, 'data.0' = first data element), schema class name.
Recording is done in the six interfaces; AC uses this config for tests/test_vcr_replay.py (replay only).

schema_version: bump this string when the response schema for this endpoint changes.
Cassettes store x-contract-schema-version header; test_vcr_replay.py asserts they match.
"""

from __future__ import annotations

from typing import NotRequired, TypedDict


class VCREndpoint(TypedDict):
    """Single request to record/replay and validate."""

    url: str
    method: str
    cassette_name: str
    response_path: str
    schema_class: str
    key_env: str
    header_name: str
    schema_version: NotRequired[str]  # bumped when response schema changes
    json_body: NotRequired[dict]  # POST body
    auth_query_param: NotRequired[str]  # key goes in URL query (e.g. apiKey) not header
    is_internal_service: NotRequired[bool]  # True for inter-service cassettes (local only)


def _get(
    url: str,
    cassette: str,
    response_path: str,
    schema_class: str,
    key_env: str = "",
    header_name: str = "Authorization",
    schema_version: str = "1.0",
) -> VCREndpoint:
    return {
        "url": url,
        "method": "GET",
        "cassette_name": cassette,
        "response_path": response_path,
        "schema_class": schema_class,
        "key_env": key_env,
        "header_name": header_name,
        "schema_version": schema_version,
    }


def _post(
    url: str,
    cassette: str,
    response_path: str,
    schema_class: str,
    json_body: dict[str, object] | None = None,
    key_env: str = "",
    header_name: str = "Authorization",
    schema_version: str = "1.0",
) -> VCREndpoint:
    out: VCREndpoint = {
        "url": url,
        "method": "POST",
        "cassette_name": cassette,
        "response_path": response_path,
        "schema_class": schema_class,
        "key_env": key_env,
        "header_name": header_name,
        "schema_version": schema_version,
    }
    if json_body is not None:
        out["json_body"] = json_body
    return out


# Public or optional-auth endpoints only. Key-required venues: set key_env so recorder adds header.
VCR_ENDPOINTS: dict[str, list[VCREndpoint]] = {
    # ------------------------------------------------------------------
    # CeFi — public endpoints
    # ------------------------------------------------------------------
    "binance": [
        _get(
            "https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=BTCUSDT",
            "ticker_24hr.yaml",
            "",
            "BinanceTicker",
            schema_version="1.0",
        ),
    ],
    "okx": [
        _get(
            "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT-SWAP",
            "ticker.yaml",
            "data.0",
            "OKXTicker",
            schema_version="1.0",
        ),
    ],
    "bybit": [
        _get(
            "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT",
            "ticker.yaml",
            "result.list.0",
            "BybitTicker",
            schema_version="1.0",
        ),
    ],
    "upbit": [
        _get(
            "https://api.upbit.com/v1/ticker?markets=KRW-BTC",
            "ticker.yaml",
            "0",
            "UpbitTicker",
            schema_version="1.0",
        ),
    ],
    "hyperliquid": [
        _post(
            "https://api.hyperliquid.xyz/info",
            "meta.yaml",
            "",
            "HyperliquidMeta",
            json_body={"type": "meta"},
            schema_version="1.0",
        ),
    ],
    "yahoo_finance": [],  # Chart endpoint rate-limits; use examples/ for schema validation
    "databento": [],  # Requires DATABENTO_API_KEY; set env var when recording
    "tardis": [
        _get(
            "https://api.tardis.dev/v1/exchanges",
            "exchanges.yaml",
            "0",
            "TardisExchange",
            key_env="TARDIS_API_KEY",
            header_name="Authorization",
            schema_version="1.0",
        ),
    ],
    "thegraph": [],
    "alchemy": [],
    "ccxt": [],
    "aster": [],
    "ibkr": [],
    # ------------------------------------------------------------------
    # Sports / prediction markets
    # ------------------------------------------------------------------
    "betfair": [],  # All endpoints require auth; use examples/ for schema validation
    "pinnacle": [
        _get(
            "https://api.pinnacle.com/v2/sports/29/leagues",
            "leagues.yaml",
            "0",
            "PinnacleLeague",
            key_env="PINNACLE_API_KEY",
            header_name="Authorization",
            schema_version="1.0",
        ),
    ],
    "kalshi": [
        _get(
            "https://trading-api.kalshi.com/trade-api/v2/markets?limit=1&status=open",
            "markets.yaml",
            "markets.0",
            "KalshiMarket",
            schema_version="1.0",
        ),
        _get(
            "https://trading-api.kalshi.com/trade-api/v2/markets/KXHIGHNY-24JAN01-T60/orderbook",
            "orderbook.yaml",
            "",
            "KalshiOrderBook",
            schema_version="1.0",
        ),
    ],
    "polymarket": [
        _get(
            "https://clob.polymarket.com/markets",
            "markets.yaml",
            "0",
            "PolymarketMarket",
            schema_version="1.0",
        ),
    ],
    "odds_api": [
        {
            **_get(
                "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds?regions=us&oddsFormat=decimal",
                "odds.yaml",
                "0",
                "OddsApiFixture",
                key_env="ODDS_API_KEY",
                header_name="Authorization",
                schema_version="1.0",
            ),
            "auth_query_param": "apiKey",
        },
    ],
    "api_football": [
        _get(
            "https://v3.football.api-sports.io/leagues",
            "leagues.yaml",
            "response.0.league",
            "ApiFootballLeague",
            key_env="API_FOOTBALL_API_KEY",
            header_name="x-apisports-key",
            schema_version="1.0",
        ),
    ],
    # ------------------------------------------------------------------
    # On-chain / DeFi analytics
    # ------------------------------------------------------------------
    "glassnode": [
        _get(
            "https://api.glassnode.com/v1/metrics/market/price_usd_close?a=BTC&i=24h&f=JSON",
            "price_usd_close.yaml",
            "0",
            "GlassnodeTimeseriesPoint",
            key_env="GLASSNODE_API_KEY",
            header_name="X-Api-Key",
            schema_version="1.0",
        ),
    ],
    "fear_greed": [
        _get(
            "https://api.alternative.me/fng/?limit=1&format=json",
            "fng.yaml",
            "data.0",
            "FearGreedReading",
            schema_version="1.0",
        ),
    ],
    "arkham": [
        _get(
            "https://api.arkhamintelligence.com/intelligence/address/0xbe0eb53f46cd790cd13851d5eff43d12404d33e8",
            "entity.yaml",
            "",
            "ArkhamEntity",
            key_env="ARKHAM_API_KEY",
            header_name="API-Key",
            schema_version="1.0",
        ),
    ],
    "defillama": [
        _get(
            "https://api.llama.fi/protocols",
            "protocols.yaml",
            "0",
            "DefiLlamaProtocol",
            schema_version="1.0",
        ),
        _get(
            "https://api.llama.fi/v2/chains",
            "chains.yaml",
            "0",
            "DefiLlamaChainTvl",
            schema_version="1.0",
        ),
    ],
    # ------------------------------------------------------------------
    # Sports stats APIs
    # ------------------------------------------------------------------
    "soccer_football_info": [
        _get(
            "https://api.football-data.org/v4/competitions",
            "championships.yaml",
            "competitions.0",
            "SoccerFootballChampionship",
            key_env="FOOTBALL_DATA_API_KEY",
            header_name="X-Auth-Token",
            schema_version="1.0",
        ),
    ],
    "footystats": [
        _get(
            "https://api.football-data-api.com/league-list?key=example",
            "leagues.yaml",
            "data.0",
            "FootystatsLeague",
            key_env="FOOTYSTATS_API_KEY",
            header_name="X-Api-Key",
            schema_version="1.0",
        ),
    ],
    "understat": [],  # HTML scraping endpoint, no standard REST cassette
    "open_meteo": [
        _get(
            "https://api.open-meteo.com/v1/forecast"
            "?latitude=51.5&longitude=-0.1&hourly=temperature_2m,precipitation&forecast_days=1",
            "forecast.yaml",
            "",
            "OpenMeteoResponse",
            schema_version="1.0",
        ),
    ],
    "transfermarkt": [],  # No official API — stub module only
    # ------------------------------------------------------------------
    # Developer tools
    # ------------------------------------------------------------------
    "github": [
        _get(
            "https://api.github.com/repos/octocat/Hello-World",
            "repository.yaml",
            "",
            "GitHubRepository",
            key_env="GITHUB_TOKEN",
            header_name="Authorization",
            schema_version="1.0",
        ),
        _get(
            "https://api.github.com/rate_limit",
            "rate_limit.yaml",
            "rate",
            "GitHubRateLimit",
            key_env="GITHUB_TOKEN",
            header_name="Authorization",
            schema_version="1.0",
        ),
    ],
    # ------------------------------------------------------------------
    # Internal service cassettes (record against a running local service)
    # Skip in CI unless cassette pre-exists; never make live calls to localhost in CI.
    # ------------------------------------------------------------------
    "internal_execution_services": [
        {
            **_get(
                "http://localhost:8080/health",
                "health.yaml",
                "",
                "ServiceHealthStatus",
                schema_version="1.0",
            ),
            "is_internal_service": True,
        },
        {
            **_post(
                "http://localhost:8080/manual/instruction",
                "manual_instruction.yaml",
                "",
                "ManualInstructionResponse",
                json_body={
                    "client_id": "test-client",
                    "strategy_id": "manual_strategy",
                    "instruction_type": "TRADE",
                    "venue": "binance",
                    "instrument_id": "BTC-USDT",
                    "side": "BUY",
                    "quantity": "0.001",
                },
                schema_version="1.0",
            ),
            "is_internal_service": True,
        },
    ],
}

# Endpoint → schema class map for validation. Key format: "data_source:endpoint_type" or "venue:path".
ENDPOINT_SCHEMA_MAP: dict[str, str] = {
    # Health/ping (generic)
    "health": "HealthPingResponse",
    "ping": "HealthPingResponse",
    # WebSocket lifecycle
    "websocket:opened": "WebSocketConnectionOpened",
    "websocket:closed": "WebSocketConnectionClosed",
    "websocket:ping": "WebSocketPingFrame",
    "websocket:pong": "WebSocketPongFrame",
    # Kalshi
    "kalshi:market": "KalshiMarket",
    "kalshi:orderbook": "KalshiOrderBook",
    # Binance
    "binance:ticker": "BinanceTicker",
    "binance:orderbook": "BinanceOrderBook",
    "binance:trades": "BinanceTrade",
    "binance:klines": "BinanceKline",
    "binance:exchange_info": "BinanceExchangeInfo",
    # OKX
    "okx:ticker": "OKXTicker",
    "okx:orderbook": "OKXOrderBook",
    # Bybit
    "bybit:ticker": "BybitTicker",
    "bybit:orderbook": "BybitOrderBook",
    # Upbit
    "upbit:ticker": "UpbitTicker",
    # Hyperliquid
    "hyperliquid:meta": "HyperliquidMeta",
    # Tardis
    "tardis:exchanges": "TardisExchange",
    "tardis:instruments": "TardisInstrument",
    # On-chain analytics
    "glassnode:timeseries": "GlassnodeTimeseriesPoint",
    "glassnode:metric": "GlassnodeMetricResponse",
    "fear_greed:fng": "FearGreedReading",
    "arkham:entity": "ArkhamEntity",
    "defillama:protocol": "DefiLlamaProtocol",
    # Sports
    "api_football:league": "ApiFootballLeague",
    "footystats:league": "FootystatsLeague",
    "open_meteo:forecast": "OpenMeteoResponse",
    # GitHub
    "github:repository": "GitHubRepository",
    "github:workflow_run": "GitHubWorkflowRun",
    "github:rate_limit": "GitHubRateLimit",
    # Internal services
    "internal:health": "ServiceHealthStatus",
    "internal:manual_instruction": "ManualInstructionResponse",
    "internal:fill_event": "FillEventMessage",
    "internal:risk_alert": "RiskAlertMessage",
}
