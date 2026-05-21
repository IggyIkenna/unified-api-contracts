"""Per-venue HTTP endpoint config for VCR recording and replay.

Each entry: url, method, optional headers builder key (env var name), response_path to extract
body for schema validation (e.g. '' = whole JSON, 'data.0' = first data element), schema class name.
Recording is done in the six interfaces; AC uses this config for tests/test_vcr_replay.py (replay only).

schema_version: bump this string when the response schema for this endpoint changes.
Cassettes store x-contract-schema-version header; test_vcr_replay.py asserts they match.
"""

from __future__ import annotations

from typing import NotRequired, TypedDict


# orphan: kept because it is used internally to type VCR_ENDPOINTS and the _get/_post helpers
# in this module; downstream consumers import VCR_ENDPOINTS (the constant) not VCREndpoint
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
    json_body: NotRequired[dict[str, object]]  # POST body
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
    "thegraph": [
        _post(
            "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2",
            "pools_query.yaml",
            "data",
            "TheGraphResponse",
            json_body={
                "query": (
                    "{ pools(first: 2, orderBy: totalValueLockedUSD, orderDirection: desc)"
                    " { id token0 { id symbol decimals } token1 { id symbol decimals }"
                    " reserve0 reserve1 reserveUSD token0Price token1Price } }"
                )
            },
            schema_version="1.0",
        ),
    ],
    "alchemy": [],
    # ------------------------------------------------------------------
    # DeFi protocols — The Graph subgraphs
    # ------------------------------------------------------------------
    "thegraph_aave": [
        _post(
            "https://gateway.thegraph.com/api/{THE_GRAPH_API_KEY}/subgraphs/id/GQFbb95cE6d8mV989mL5figjaGaKCQB3xqYrr1bRyXqF",
            "aave_v3_reserves.yaml",
            "data",
            "TheGraphResponse",
            json_body={
                "query": (
                    "{ reserves(first: 5, orderBy: totalLiquidity, orderDirection: desc)"
                    " { id name symbol decimals liquidityRate variableBorrowRate"
                    "   totalLiquidity totalCurrentVariableDebt } }"
                )
            },
            key_env="THE_GRAPH_API_KEY",
            schema_version="1.0",
        ),
    ],
    "thegraph_morpho": [
        _post(
            "https://api.thegraph.com/subgraphs/name/morpho-association/morpho-blue",
            "morpho_markets.yaml",
            "data",
            "TheGraphResponse",
            json_body={
                "query": (
                    "{ markets(first: 5, orderBy: totalValueLockedUSD, orderDirection: desc)"
                    " { id loanToken { id symbol decimals } collateralToken { id symbol decimals }"
                    "   lltv totalSupplyAssets totalBorrowAssets } }"
                )
            },
            schema_version="1.0",
        ),
    ],
    "thegraph_uniswap_v3": [
        _post(
            "https://gateway.thegraph.com/api/{THE_GRAPH_API_KEY}/subgraphs/id/5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV",
            "uniswap_v3_pools.yaml",
            "data",
            "TheGraphResponse",
            json_body={
                "query": (
                    "{ pools(first: 5, orderBy: totalValueLockedUSD, orderDirection: desc)"
                    " { id token0 { id symbol decimals } token1 { id symbol decimals }"
                    "   feeTier liquidity sqrtPrice tick totalValueLockedUSD } }"
                )
            },
            key_env="THE_GRAPH_API_KEY",
            schema_version="1.0",
        ),
    ],
    "thegraph_uniswap_v4": [
        _post(
            "https://gateway.thegraph.com/api/{THE_GRAPH_API_KEY}/subgraphs/id/DiYPVdygkfjDWhbxGSqAQxwBKmfKnkWQojqeM3iEwqCK",
            "uniswap_v4_pools.yaml",
            "data",
            "TheGraphResponse",
            json_body={
                "query": (
                    "{ pools(first: 5, orderBy: totalValueLockedUSD, orderDirection: desc)"
                    " { id token0 { id symbol } token1 { id symbol }"
                    "   fee liquidity totalValueLockedUSD } }"
                )
            },
            key_env="THE_GRAPH_API_KEY",
            schema_version="1.0",
        ),
    ],
    "thegraph_instadapp": [
        _post(
            "https://api.thegraph.com/subgraphs/name/instadapp/dsa-v2",
            "dsa_accounts.yaml",
            "data",
            "TheGraphResponse",
            json_body={"query": "{ accounts(first: 5) { id owner { id } version createdAt } }"},
            schema_version="1.0",
        ),
    ],
    "thegraph_balancer": [
        _post(
            "https://api-v3.balancer.fi/graphql",
            "balancer_pools.yaml",
            "data",
            "TheGraphResponse",
            json_body={
                "query": (
                    "{ pools(first: 5, orderBy: totalLiquidity, orderDirection: desc)"
                    " { id name symbol poolType totalLiquidity totalSwapVolume } }"
                )
            },
            schema_version="1.0",
        ),
    ],
    # ------------------------------------------------------------------
    # DeFi protocols — Alchemy RPC (eth_call / eth_getLogs)
    # ------------------------------------------------------------------
    "alchemy_eth_call": [
        _post(
            "https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
            "aave_v3_user_data.yaml",
            "",
            "AlchemyRpcResponse",
            json_body={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_call",
                "params": [
                    {
                        "to": "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2",
                        "data": "0xbf92857c0000000000000000000000000000000000000000000000000000000000000000",
                    },
                    "latest",
                ],
            },
            key_env="ALCHEMY_API_KEY",
            header_name="Authorization",
            schema_version="1.0",
        ),
    ],
    "alchemy_eth_getlogs": [
        _post(
            "https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
            "aave_v3_supply_logs.yaml",
            "",
            "AlchemyRpcResponse",
            json_body={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_getLogs",
                "params": [
                    {
                        "address": "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2",
                        "topics": ["0x2b627736bca15cd5381dcf80b0bf11fd197d01a037c52b927a881a10fb73ba61"],
                        "fromBlock": "latest",
                        "toBlock": "latest",
                    }
                ],
            },
            key_env="ALCHEMY_API_KEY",
            header_name="Authorization",
            schema_version="1.0",
        ),
    ],
    # ------------------------------------------------------------------
    # DeFi protocols — DefiLlama additional endpoints
    # (defillama entry above has protocols + chains; add TVL + yields here)
    # ------------------------------------------------------------------
    # defillama_tvl: cassette in external/defillama/mocks/ → registered under "defillama" below
    # defillama_yields: cassette in external/defillama/mocks/ → registered under "defillama" below
    # defillama_coins: cassette in external/defillama/mocks/ → registered under "defillama" below
    "morpho_blue_api": [
        # Covers: Morpho Blue lending markets (MTDS morpho_adapter.py)
        # Separate from thegraph_morpho — this is the native Morpho Blue API (not The Graph).
        _post(
            "https://blue-api.morpho.org/graphql",
            "markets.yaml",
            "",
            "MorphoBlueMarketsResponse",
            json_body={
                "query": (
                    "query GetMarkets { markets(where: {chainId_in: [1]}) {"
                    " items { uniqueKey loanAsset { address symbol decimals }"
                    " collateralAsset { address symbol decimals } lltv"
                    " state { supplyAssets borrowAssets supplyApy borrowApy } } } }"
                )
            },
            schema_version="1.0",
        ),
    ],
    "eigenlayer": [
        # Covers: EigenLayer restaking rewards for EtherFi weETH holders
        # BLOCKED-CREDENTIALS: sidecar-rpc.eigenlayer.xyz is Cloudflare-protected.
        # Stub cassette ships; re-record from production environment.
        _get(
            "https://sidecar-rpc.eigenlayer.xyz/eigenlayer/rewards/v1/earner-historical-rewards",
            "earner_historical_rewards.yaml",
            "",
            "EigenLayerRewardsResponse",
            schema_version="1.0",
        ),
    ],
    "solayer": [
        # Covers: Solayer sSOL restaking APY (BLOCKED-NO-ADAPTER — adapter not yet in MTDS)
        # API URL declared in UAC _defi.py capability: https://app.solayer.org/api
        # Stub cassette ships; re-record when MTDS adapter is implemented.
        _get(
            "https://app.solayer.org/api/info/restaking",
            "restaking_apy.yaml",
            "",
            "SolayerRestakingResponse",
            schema_version="1.0",
        ),
    ],
    "cambrian": [
        # Covers: Cambrian Network AVS restaking (BLOCKED-NO-ADAPTER — adapter not yet in MTDS)
        # API URL declared in UAC _defi_chain_data.py: https://api.cambrian.network
        # Stub cassette ships; re-record when MTDS adapter is implemented.
        _get(
            "https://api.cambrian.network/restaking/operator-sets",
            "restaking_rewards.yaml",
            "",
            "CambrianRestakingResponse",
            schema_version="1.0",
        ),
    ],
    "picasso": [
        # Covers: Picasso Network cross-chain restaking (BLOCKED-NO-ADAPTER — adapter not yet in MTDS)
        # API URL declared in UAC _defi_chain_data.py: https://api.picasso.network
        # Stub cassette ships; re-record when MTDS adapter is implemented.
        _get(
            "https://api.picasso.network/restaking/routes",
            "restaking_rewards.yaml",
            "",
            "PicassoRestakingResponse",
            schema_version="1.0",
        ),
    ],
    "sky": [
        # Covers: Sky Protocol (MakerDAO rebrand) savings rate (BLOCKED-NO-ADAPTER — adapter not yet in MTDS)
        # DSR/SSR yield products — DAI Savings Rate + Sky Savings Rate (sUSDS).
        # Stub cassette ships; re-record when MTDS adapter is implemented.
        _get(
            "https://api.sky.money/rates",
            "savings_rate.yaml",
            "",
            "SkySavingsRateResponse",
            schema_version="1.0",
        ),
    ],
    # ------------------------------------------------------------------
    # DeFi protocols — AaveScan analytics
    # ------------------------------------------------------------------
    "aavescan": [
        _get(
            "https://aavescan.com/api/v1/market-data",
            "market_data.yaml",
            "",
            "AaveScanMarketData",
            key_env="AAVESCAN_API_KEY",
            header_name="X-API-Key",
            schema_version="1.0",
        ),
    ],
    # ------------------------------------------------------------------
    # Hyperliquid testnet (TESTNET_MODE=true)
    # ------------------------------------------------------------------
    "hyperliquid_testnet": [
        _post(
            "https://api.hyperliquid-testnet.xyz/info",
            "meta.yaml",
            "",
            "HyperliquidMeta",
            json_body={"type": "meta"},
            schema_version="1.0",
        ),
        _post(
            "https://api.hyperliquid-testnet.xyz/info",
            "all_mids.yaml",
            "",
            "HyperliquidAllMids",
            json_body={"type": "allMids"},
            schema_version="1.0",
        ),
    ],
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
            "https://api.elections.kalshi.com/trade-api/v2/markets?limit=1&status=open",
            "markets.yaml",
            "markets.0",
            "KalshiMarket",
            schema_version="1.0",
        ),
        _get(
            "https://api.elections.kalshi.com/trade-api/v2/markets/KXHIGHNY-24JAN01-T60/orderbook",
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
        # yields.llama.fi/pools — covers Ethena, Pendle, Beefy, Yearn, Convex, Karak,
        # Symbiotic, Idle (all MTDS adapters filter this shared endpoint by project name)
        _get(
            "https://yields.llama.fi/pools",
            "yields.yaml",
            "data.0",
            "DefiLlamaYieldPool",
            schema_version="1.0",
        ),
        # coins.llama.fi — covers Solblaze(bSOL), Puffer(pufETH), EtherFi(eETH/weETH)
        _get(
            "https://coins.llama.fi/prices/historical/1779223474/solana:bSo13r4TkiE4KumL71LsHTPpL2euBYLFx6h9HP3piy1",
            "coins_historical.yaml",
            "",
            "DefiLlamaCoinsResponse",
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
    "defillama:protocol": "DefiLlamaProtocol",
    "defillama:tvl": "DefiLlamaTvlValue",
    "defillama:pool": "DefiLlamaYieldPool",
    "defillama:coins": "DefiLlamaCoinsResponse",
    # DeFi protocol direct APIs (non-subgraph)
    "morpho_blue_api:markets": "MorphoBlueMarketsResponse",
    "eigenlayer:rewards": "EigenLayerRewardsResponse",
    "solayer:restaking": "SolayerRestakingResponse",
    "cambrian:restaking": "CambrianRestakingResponse",
    "picasso:restaking": "PicassoRestakingResponse",
    "sky:savings_rate": "SkySavingsRateResponse",
    # DeFi protocol subgraphs (The Graph)
    "thegraph_aave:reserves": "TheGraphResponse",
    "thegraph_morpho:markets": "TheGraphResponse",
    "thegraph_uniswap_v3:pools": "TheGraphResponse",
    "thegraph_uniswap_v4:pools": "TheGraphResponse",
    "thegraph_instadapp:accounts": "TheGraphResponse",
    "thegraph_balancer:pools": "TheGraphResponse",
    # Alchemy RPC
    "alchemy_eth_call:response": "AlchemyRpcResponse",
    "alchemy_eth_getlogs:response": "AlchemyRpcResponse",
    # AaveScan
    "aavescan:market_data": "AaveScanMarketData",
    # Hyperliquid testnet
    "hyperliquid_testnet:meta": "HyperliquidMeta",
    "hyperliquid_testnet:all_mids": "HyperliquidAllMids",
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
