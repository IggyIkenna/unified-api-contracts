"""ENDPOINT_REGISTRY data — venue endpoint entries with cassette status annotations.

Separated from endpoint_registry.py to keep each file under the 900-line SRP limit.
Consumers should import ENDPOINT_REGISTRY from endpoint_registry, not from this private module.
"""

from __future__ import annotations

from ._endpoint_registry_types import (
    AccessMode,
    CassetteStatus,
    DataAvailability,
    EndpointSpec,
    ResponseFormat,
)

ENDPOINT_REGISTRY: list[EndpointSpec] = [
    # --- Kalshi ---
    EndpointSpec(
        venue="kalshi",
        endpoint_path="/trade-api/v2/markets/{ticker}",
        http_method="GET",
        schema_class="KalshiMarket",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.BOTH,
        version="v2",
        notes=(
            "Integer cent fields (yes_bid, yes_ask, volume) deprecated March 5 2026; "
            "migrate to yes_bid_dollars (string fixed-point). "
            "Historical window shrinks to ~3 months same date."
        ),
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    EndpointSpec(
        venue="kalshi",
        endpoint_path="/trade-api/v2/markets",
        http_method="GET",
        schema_class="KalshiMarket",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.BOTH,
        version="v2",
        is_paginated=True,
        pagination_style="cursor",
        max_lookback_days=90,
        notes="Bulk-download historical markets before March 6 2026 when window shrinks.",
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    EndpointSpec(
        venue="kalshi",
        endpoint_path="wss://trading-api.kalshi.com/trade-api/ws/v2",
        http_method="WS",
        schema_class="KalshiWebSocketTickerMsg",
        access_mode=AccessMode.STREAMING_WEBSOCKET,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v2",
        notes="Public channels: ticker, trade, orderbook_delta, market_lifecycle_v2. Private: fill, market_positions.",
        requires_auth=False,
        cassette_status=CassetteStatus.NOT_APPLICABLE,
    ),
    EndpointSpec(
        venue="kalshi",
        endpoint_path="/trade-api/v2/portfolio/fills",
        http_method="GET",
        schema_class="KalshiFill",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.HISTORICAL_ONLY,
        version="v2",
        max_lookback_days=90,
        notes=(
            "Bulk-download fill history before March 6 2026 window shrink. Secret Manager key: kalshi-api-credentials."
        ),
        requires_auth=True,
        cassette_status=CassetteStatus.AUTH_BLOCKED,
    ),
    # --- Polymarket ---
    EndpointSpec(
        venue="polymarket",
        endpoint_path="https://gamma-api.polymarket.com/events",
        http_method="GET",
        schema_class="PolymarketGammaEvent",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.BOTH,
        version="gamma-v1",
        notes="Gamma API events: questions, outcomes, volumes, resolution. No auth required.",
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    EndpointSpec(
        venue="polymarket",
        endpoint_path="https://gamma-api.polymarket.com/markets",
        http_method="GET",
        schema_class="PolymarketGammaMarket",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.BOTH,
        version="gamma-v1",
        notes="Gamma API has full market metadata including tags, neg_risk, resolution_source. No auth required.",
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    EndpointSpec(
        venue="polymarket",
        endpoint_path="https://gamma-api.polymarket.com/tags",
        http_method="GET",
        schema_class="PolymarketGammaTag",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.BOTH,
        version="gamma-v1",
        notes="Gamma API market tags. No auth required.",
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    EndpointSpec(
        venue="polymarket",
        endpoint_path="https://clob.polymarket.com/prices-history",
        http_method="GET",
        schema_class="PolymarketPriceHistory",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.HISTORICAL_ONLY,
        version="clob-v1",
        is_paginated=False,
        max_lookback_days=None,
        notes="CLOB era only: from Nov 21 2022. AMM era (pre-Nov 2022) has splits/merges only, no price series.",
        available_from_date="2022-11-21",
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    EndpointSpec(
        venue="polymarket",
        endpoint_path="wss://ws-subscriptions-clob.polymarket.com/ws/market",
        http_method="WS",
        schema_class="PolymarketOrderBook",
        access_mode=AccessMode.STREAMING_WEBSOCKET,
        data_availability=DataAvailability.LIVE_ONLY,
        version="clob-v1",
        notes=(
            "Live order book streaming. Auth via L2 HMAC-SHA256 POLY_* headers. "
            "Secret Manager key: polymarket-api-credentials."
        ),
        requires_auth=True,
        cassette_status=CassetteStatus.NOT_APPLICABLE,
    ),
    # --- Databento ---
    EndpointSpec(
        venue="databento",
        endpoint_path="https://hist.databento.com/v0/timeseries.get_range",
        http_method="GET",
        schema_class="DatabentoOhlcvBar",
        access_mode=AccessMode.BATCH_FILE,
        data_availability=DataAvailability.HISTORICAL_ONLY,
        version="v0",
        response_format=ResponseFormat.DBN_ZST,
        notes=(
            "Batch download; returns zstd-compressed DBN file. Use dbn Python library to decode. "
            "Each rtype maps to a different schema (rtype=32 = ohlcv-1h, rtype=10 = mbp-10, etc.). "
            "Secret Manager key: databento-api-key."
        ),
        requires_auth=True,
        cassette_status=CassetteStatus.NOT_APPLICABLE,
    ),
    EndpointSpec(
        venue="databento",
        endpoint_path="wss://live.databento.com/v0/live",
        http_method="WS",
        schema_class="DatabentoTrade",
        access_mode=AccessMode.STREAMING_WEBSOCKET,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v0",
        notes=(
            "Live streaming of same schemas as batch. Requires separate live API key. "
            "Secret Manager key: databento-live-api-key."
        ),
        requires_auth=True,
        cassette_status=CassetteStatus.NOT_APPLICABLE,
    ),
    # --- Tardis ---
    EndpointSpec(
        venue="tardis",
        endpoint_path=("https://datasets.tardis.dev/v1/{exchange}/{dataType}/{year}/{month}/{day}/{symbol}.csv.gz"),
        http_method="GET",
        schema_class="TardisTrade",
        access_mode=AccessMode.BATCH_FILE,
        data_availability=DataAvailability.HISTORICAL_ONLY,
        version="v1",
        response_format=ResponseFormat.CSV_GZIP,
        notes=(
            "Full-day gzip CSV files. Must download entire day; no streaming partial. "
            "Memory-efficient: stream decompress. Secret Manager key: tardis-api-key."
        ),
        requires_auth=True,
        cassette_status=CassetteStatus.AUTH_BLOCKED,
    ),
    # --- Barchart ---
    EndpointSpec(
        venue="barchart",
        endpoint_path="manual_csv_export",
        http_method=None,
        schema_class="BarchartOhlcv15m",
        access_mode=AccessMode.BATCH_FILE,
        data_availability=DataAvailability.HISTORICAL_ONLY,
        version=None,
        response_format=ResponseFormat.CSV,
        notes=(
            "No programmatic API. Data sourced via manual Barchart subscription CSV exports. "
            "Timestamps in US Eastern Time."
        ),
        requires_auth=False,
        cassette_status=CassetteStatus.NOT_APPLICABLE,
    ),
    # --- The Graph / Subgraph ---
    EndpointSpec(
        venue="thegraph",
        endpoint_path="https://api.thegraph.com/subgraphs/name/{org}/{subgraph}",
        http_method="POST",
        schema_class="TheGraphResponse",
        access_mode=AccessMode.GRAPHQL,
        data_availability=DataAvailability.BOTH,
        version="graphql",
        response_format=ResponseFormat.JSON,
        notes=(
            "GraphQL queries. Historical via pagination (first/skip). Live: polling or subscriptions "
            "(subgraph-specific). Goldsky subgraphs used for Polymarket on-chain history."
        ),
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    # --- Glassnode ---
    EndpointSpec(
        venue="glassnode",
        endpoint_path="https://api.glassnode.com/v1/metrics/{category}/{metric}",
        http_method="GET",
        schema_class="GlassnodeMetricResponse",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.BOTH,
        version="v1",
        is_paginated=False,
        max_lookback_days=365,
        notes=(
            "Auth via ?api_key=KEY query param. Free tier limited to daily (24h) resolution and "
            "1-year history. Paid tier: 10-minute resolution, full history. "
            "Response always: list[{t: int, v: float|dict}]. Secret Manager key: glassnode-api-key."
        ),
        requires_auth=True,
        cassette_status=CassetteStatus.AUTH_BLOCKED,
    ),
    # --- alternative.me Fear & Greed ---
    EndpointSpec(
        venue="fear_greed",
        endpoint_path="https://api.alternative.me/fng/",
        http_method="GET",
        schema_class="FearGreedResponse",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.BOTH,
        version=None,
        notes=(
            "Free, no auth. Updates once daily at midnight UTC. Crypto-specific (not CNN stock F&G). "
            "Use ?limit=N for history, ?limit=1 for latest (includes time_until_update)."
        ),
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    # --- Hyperliquid ---
    EndpointSpec(
        venue="hyperliquid",
        endpoint_path="https://api.hyperliquid.xyz/info",
        http_method="POST",
        schema_class="HyperliquidUserState",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version=None,
        notes=(
            "All REST endpoints are POST to /info with JSON body {type: ..., ...}. "
            "No separate GET endpoints. Public endpoints: no auth. Private (account/orders): "
            "auth via EIP-712 signature. Secret Manager key: hyperliquid-api-credentials."
        ),
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    # --- OKX ---
    EndpointSpec(
        venue="okx",
        endpoint_path="/api/v5/market/ticker",
        http_method="GET",
        schema_class="OKXOptionTicker",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v5",
        notes=(
            "For OPTION instType: returns per-instrument greeks (delta, gamma, vega, theta, "
            "markVol, bidVol, askVol). OKX v5 unifies spot/margin/swap/futures/options in one API. "
            "Public market endpoints do not require auth."
        ),
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    EndpointSpec(
        venue="okx",
        endpoint_path="/api/v5/otc/rfq/create-rfq",
        http_method="POST",
        schema_class="OKXRfqCreateRequest",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v5",
        notes=(
            "Multi-leg block trades via RFQ system. OKX has no native combo instrument type; "
            "multi-leg done via RFQ. Auth: OK-ACCESS-KEY/SIGN/TIMESTAMP/PASSPHRASE headers. "
            "Secret Manager key: okx-api-credentials."
        ),
        requires_auth=True,
        cassette_status=CassetteStatus.AUTH_BLOCKED,
    ),
    # --- Binance ---
    EndpointSpec(
        venue="binance",
        endpoint_path="https://api.binance.com/api/v3/ticker/24hr",
        http_method="GET",
        schema_class="BinanceTicker",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v3",
        notes="Public 24hr ticker. No auth required for market data.",
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    EndpointSpec(
        venue="binance",
        endpoint_path="https://eapi.binance.com/eapi/v1/order",
        http_method="POST",
        schema_class="BinanceEapiOrderSubmitRequest",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="eapi-v1",
        notes=(
            "European options API. Separate endpoint/base URL from spot (api.binance.com) and "
            "futures (fapi/dapi). Requires options trading permission in account. "
            "Auth: X-MBX-APIKEY header. Secret Manager key: binance-api-credentials."
        ),
        requires_auth=True,
        cassette_status=CassetteStatus.AUTH_BLOCKED,
    ),
    # --- Bybit ---
    EndpointSpec(
        venue="bybit",
        endpoint_path="https://api.bybit.com/v5/market/tickers",
        http_method="GET",
        schema_class="BybitTicker",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v5",
        notes="Public market tickers. No auth required.",
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    EndpointSpec(
        venue="bybit",
        endpoint_path="https://api.bybit.com/v5/order/create",
        http_method="POST",
        schema_class="BybitOrderSubmitRequest",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v5",
        notes=(
            "Unified account order submission (spot/linear/inverse/option). "
            "Auth: X-BAPI-API-KEY + HMAC-SHA256 signature. "
            "Secret Manager key: bybit-api-credentials."
        ),
        requires_auth=True,
        cassette_status=CassetteStatus.AUTH_BLOCKED,
    ),
    # --- Kraken ---
    EndpointSpec(
        venue="kraken",
        endpoint_path="https://api.kraken.com/0/public/Ticker",
        http_method="GET",
        schema_class="KrakenTicker",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v0",
        notes="Public ticker. No auth required.",
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    EndpointSpec(
        venue="kraken",
        endpoint_path="https://api.kraken.com/0/private/AddOrder",
        http_method="POST",
        schema_class="KrakenOrderRequest",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v0",
        notes=(
            "Private order submission. Auth: API-Key + API-Sign (HMAC-SHA512 nonce+payload). "
            "Secret Manager key: kraken-api-credentials."
        ),
        requires_auth=True,
        cassette_status=CassetteStatus.AUTH_BLOCKED,
    ),
    # --- Deribit ---
    EndpointSpec(
        venue="deribit",
        endpoint_path="/public/get_instruments",
        http_method="GET",
        schema_class="DeribitComboInstrument",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.BOTH,
        version=None,
        notes=(
            "Use ?kind=combo or ?kind=future_combo or ?kind=option_combo to get combo instruments. "
            "Combo instruments added Q3 2023."
        ),
        available_from_date="2023-07-01",
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    EndpointSpec(
        venue="deribit",
        endpoint_path="/private/buy",
        http_method="GET",
        schema_class="DeribitOrderResult",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version=None,
        notes=(
            "Private order placement (spot, perp, option). Auth: OAuth2 client_credentials flow. "
            "client_id and client_secret from Secret Manager key: deribit-api-credentials."
        ),
        requires_auth=True,
        cassette_status=CassetteStatus.AUTH_BLOCKED,
    ),
    # --- Coinbase ---
    EndpointSpec(
        venue="coinbase",
        endpoint_path="https://api.exchange.coinbase.com/products",
        http_method="GET",
        schema_class="CoinbaseExchangeProduct",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.BOTH,
        version="exchange-v1",
        notes="Coinbase Exchange (formerly Pro) public products list. No auth required.",
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    EndpointSpec(
        venue="coinbase",
        endpoint_path="https://api.coinbase.com/api/v3/brokerage/products",
        http_method="GET",
        schema_class="CoinbaseProduct",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.BOTH,
        version="v3",
        notes="Public product list. V3 requires auth (CDP API key + JWT). Use V2 for public unauthenticated access.",
        requires_auth=True,
        cassette_status=CassetteStatus.AUTH_BLOCKED,
    ),
    EndpointSpec(
        venue="coinbase",
        endpoint_path="https://api.coinbase.com/api/v3/brokerage/orders",
        http_method="POST",
        schema_class="CoinbaseOrderRequest",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v3",
        notes=(
            "Advanced Trade order placement. Auth: CDP API key + EC private key (JWT). "
            "Secret Manager key: coinbase-api-credentials."
        ),
        requires_auth=True,
        cassette_status=CassetteStatus.AUTH_BLOCKED,
    ),
    # --- Bitstamp ---
    EndpointSpec(
        venue="bitstamp",
        endpoint_path="https://www.bitstamp.net/api/v2/ticker/{currency_pair}/",
        http_method="GET",
        schema_class="BitstampTicker",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v2",
        notes="Public ticker. No auth required.",
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    EndpointSpec(
        venue="bitstamp",
        endpoint_path="https://www.bitstamp.net/api/v2/buy/{currency_pair}/",
        http_method="POST",
        schema_class="BitstampOrderResult",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v2",
        notes=(
            "Private order placement. Auth: HMAC-SHA256 API key + secret. Secret Manager key: bitstamp-api-credentials."
        ),
        requires_auth=True,
        cassette_status=CassetteStatus.AUTH_BLOCKED,
    ),
    # --- Bitget ---
    EndpointSpec(
        venue="bitget",
        endpoint_path="https://api.bitget.com/api/v2/spot/market/tickers",
        http_method="GET",
        schema_class="BitgetTicker",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v2",
        notes="Public tickers. No auth required.",
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    EndpointSpec(
        venue="bitget",
        endpoint_path="https://api.bitget.com/api/v2/spot/trade/place-order",
        http_method="POST",
        schema_class="BitgetOrderRequest",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v2",
        notes=(
            "Private spot order. Auth: ACCESS-KEY + HMAC-SHA256 signature + PASSPHRASE. "
            "Secret Manager key: bitget-api-credentials."
        ),
        requires_auth=True,
        cassette_status=CassetteStatus.AUTH_BLOCKED,
    ),
    # --- KuCoin ---
    EndpointSpec(
        venue="kucoin",
        endpoint_path="https://api.kucoin.com/api/v1/market/allTickers",
        http_method="GET",
        schema_class="KuCoinTicker",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v1",
        notes="Public tickers. No auth required.",
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    EndpointSpec(
        venue="kucoin",
        endpoint_path="https://api.kucoin.com/api/v1/orders",
        http_method="POST",
        schema_class="KuCoinOrderRequest",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v1",
        notes=(
            "Private order submission. Auth: KC-API-KEY + HMAC-SHA256 + KC-API-PASSPHRASE. "
            "Secret Manager key: kucoin-api-credentials."
        ),
        requires_auth=True,
        cassette_status=CassetteStatus.AUTH_BLOCKED,
    ),
    # --- MEXC ---
    EndpointSpec(
        venue="mexc",
        endpoint_path="https://api.mexc.com/api/v3/ticker/24hr",
        http_method="GET",
        schema_class="MEXCTicker",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v3",
        notes="Public 24hr ticker. No auth required.",
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    EndpointSpec(
        venue="mexc",
        endpoint_path="https://api.mexc.com/api/v3/order",
        http_method="POST",
        schema_class="MEXCOrderRequest",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v3",
        notes=("Private order. Auth: X-MEXC-APIKEY + HMAC-SHA256 signature. Secret Manager key: mexc-api-credentials."),
        requires_auth=True,
        cassette_status=CassetteStatus.AUTH_BLOCKED,
    ),
    # --- Huobi ---
    EndpointSpec(
        venue="huobi",
        endpoint_path="https://api.huobi.pro/market/detail/merged",
        http_method="GET",
        schema_class="HuobiTicker",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v1",
        notes="Public merged ticker. No auth required.",
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    EndpointSpec(
        venue="huobi",
        endpoint_path="https://api.huobi.pro/v1/order/orders/place",
        http_method="POST",
        schema_class="HuobiOrderRequest",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v1",
        notes=(
            "Private order. Auth: AccessKeyId + HMAC-SHA256 signature + Timestamp. "
            "Secret Manager key: huobi-api-credentials."
        ),
        requires_auth=True,
        cassette_status=CassetteStatus.AUTH_BLOCKED,
    ),
    # --- dYdX ---
    EndpointSpec(
        venue="dydx",
        endpoint_path="https://indexer.dydx.trade/v4/markets",
        http_method="GET",
        schema_class="DydxMarket",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.BOTH,
        version="v4",
        notes="Public dYdX v4 (Cosmos chain) markets via indexer. No auth required.",
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    EndpointSpec(
        venue="dydx",
        endpoint_path="https://indexer.dydx.trade/v4/orders",
        http_method="POST",
        schema_class="DydxOrderRequest",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v4",
        notes=(
            "Private order placement. Auth: cosmos-sdk signed tx via dydx-v4-client. "
            "Secret Manager key: dydx-api-credentials (mnemonic or private key)."
        ),
        requires_auth=True,
        cassette_status=CassetteStatus.AUTH_BLOCKED,
    ),
    # --- Odds API (v4 endpoint, but data fidelity varies by era) ---
    #
    # All queries use v4. However the Odds API is a live-capture service — it
    # records odds snapshots in real time, so historical data fidelity is bounded
    # by what was actually collected at the time:
    #
    #   Pre-2023 (v3 era):
    #     - Markets: h2h, spreads, totals ONLY (no btts/draw_no_bet/double_chance/player_props)
    #     - Polling interval: ~10 minutes
    #     - Querying btts for a 2021 match will return empty — the data was never captured
    #
    #   Post-2023 (v4 era):
    #     - Markets: h2h, spreads, totals, btts, draw_no_bet, double_chance, player_props, outrights
    #     - Polling interval: ~5 minutes
    #
    # Consumers should check available_from_date and v3_era_cutoff to avoid
    # querying markets or intervals that don't exist for the requested time range.
    #
    EndpointSpec(
        venue="odds_api",
        endpoint_path="https://api.the-odds-api.com/v4/sports/{sport}/odds",
        http_method="GET",
        schema_class="OddsAPIEvent",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.BOTH,
        version="v4",
        available_from_date="2018-01-01",
        notes=(
            "Auth via ?apiKey=KEY query param. 500 free requests/month. "
            "Secret Manager key: odds-api-key. "
            "DATA FIDELITY WARNING: Pre-2023 data was captured under v3 constraints — "
            "only h2h/spreads/totals markets at ~10min intervals. "
            "btts, draw_no_bet, double_chance, player_props only exist from ~2023 onward. "
            "Querying these markets for pre-2023 events returns empty. "
            "Post-2023 data has full v4 market coverage at ~5min intervals."
        ),
        requires_auth=True,
        cassette_status=CassetteStatus.AUTH_BLOCKED,
    ),
    # --- api-football ---
    EndpointSpec(
        venue="api_football",
        endpoint_path="https://v3.football.api-sports.io/fixtures",
        http_method="GET",
        schema_class="APIFootballFixture",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.BOTH,
        version="v3",
        notes=("Auth: x-apisports-key header. 100 requests/day free. Secret Manager key: api-football-api-key."),
        requires_auth=True,
        cassette_status=CassetteStatus.AUTH_BLOCKED,
    ),
    # --- Betfair ---
    EndpointSpec(
        venue="betfair",
        endpoint_path="https://identitysso.betfair.com/api/login",
        http_method="POST",
        schema_class="BetfairAuthResponse",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v1",
        notes=(
            "Interactive session login. Requires X-Application (app key from Secret Manager: "
            "betfair-api-credentials) + form-encoded username/password. "
            "Returns session token valid for ~8h. "
            "Cert login endpoint: https://identitysso-cert.betfair.com/api/certlogin"
        ),
        requires_auth=True,
        cassette_status=CassetteStatus.AUTH_BLOCKED,
    ),
    EndpointSpec(
        venue="betfair",
        endpoint_path="https://api.betfair.com/exchange/betting/json-rpc/v1",
        http_method="POST",
        schema_class="BetfairMarketCatalogue",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.BOTH,
        version="v1",
        notes=(
            "JSON-RPC endpoint for listMarketCatalogue / listMarketBook. "
            "Auth: X-Application (app key) + X-Authentication (session token). "
            "Secret Manager key: betfair-api-credentials (JSON: {app_key, username, password}). "
            "Status: KEY_NOT_IN_SM — must provision before cassette can be recorded."
        ),
        requires_auth=True,
        cassette_status=CassetteStatus.AUTH_BLOCKED,
    ),
    # --- Pinnacle ---
    EndpointSpec(
        venue="pinnacle",
        endpoint_path="https://api.pinnacle.com/v1/odds",
        http_method="GET",
        schema_class="PinnacleOddsResponse",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v1",
        notes=(
            "Basic auth (username:password base64) via Authorization header. "
            "Secret Manager key: pinnacle-api-credentials (JSON: {username, password}). "
            "Status: KEY_NOT_IN_SM — must provision before cassette can be recorded."
        ),
        requires_auth=True,
        cassette_status=CassetteStatus.AUTH_BLOCKED,
    ),
    # --- IBKR ---
    EndpointSpec(
        venue="ibkr",
        endpoint_path="reqContractDetails(secType=BAG)",
        http_method="TWS",
        schema_class="IBKRComboContract",
        access_mode=AccessMode.STREAMING_WEBSOCKET,
        data_availability=DataAvailability.LIVE_ONLY,
        version="tws-api",
        notes=(
            "secType=BAG is IBKR's combination/spread contract type. All spread strategies "
            "(straddles, butterflies, calendar spreads, EFPs) use this. comboLegs define the legs. "
            "Auth via TWS Gateway API key. Secret Manager key: ibkr-api-credentials."
        ),
        requires_auth=True,
        cassette_status=CassetteStatus.NOT_APPLICABLE,
    ),
    # --- Upbit ---
    EndpointSpec(
        venue="upbit",
        endpoint_path="https://api.upbit.com/v1/ticker",
        http_method="GET",
        schema_class="UpbitTicker",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v1",
        notes="Public ticker. No auth required for market data.",
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    # --- DeFiLlama ---
    EndpointSpec(
        venue="defillama",
        endpoint_path="https://api.llama.fi/protocols",
        http_method="GET",
        schema_class="DefiLlamaProtocol",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.BOTH,
        version="v1",
        notes="Free, no auth. TVL and protocol metadata for all tracked protocols.",
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    # --- Open-Meteo ---
    EndpointSpec(
        venue="open_meteo",
        endpoint_path="https://api.open-meteo.com/v1/forecast",
        http_method="GET",
        schema_class="OpenMeteoResponse",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.BOTH,
        version="v1",
        notes="Free, no auth. Weather forecast for commodity and sports modelling.",
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    # --- CoinGecko ---
    EndpointSpec(
        venue="coingecko",
        endpoint_path="https://api.coingecko.com/api/v3/coins/markets",
        http_method="GET",
        schema_class="CoinGeckoMarket",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.BOTH,
        version="v3",
        notes=(
            "Free tier: no auth, 30 calls/min. Pro: x-cg-pro-api-key header. "
            "Secret Manager key: coingecko-api-key (optional for free tier)."
        ),
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
]
