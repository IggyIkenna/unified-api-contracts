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
        endpoint_path="wss://api.elections.kalshi.com/trade-api/ws/v2",
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
    # --- Barchart RETIRED 2026-06-24 (VIX 15m now aggregates from VX futures via
    #     Databento XCBF.PITCH; the manual-CSV Barchart endpoint is removed). ---
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
    # --- Bitfinex ---
    # F42: BitfinexCeFiAdapter (execution-service bitfinex_native.py) covers both
    # spot ("EXCHANGE" order type) and margin trading against the same base URL/
    # endpoint (no separate futures product/domain) — single venue key, like OKX.
    EndpointSpec(
        venue="bitfinex",
        endpoint_path="https://api.bitfinex.com/v2/ticker/{Symbol}",
        http_method="GET",
        schema_class="BitfinexTicker",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v2",
        notes="Public trading pair ticker. No auth required.",
        requires_auth=False,
        cassette_status=CassetteStatus.PENDING,
    ),
    EndpointSpec(
        venue="bitfinex",
        endpoint_path="https://api.bitfinex.com/v2/auth/w/order/submit",
        http_method="POST",
        schema_class="BitfinexOrderRequest",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v2",
        notes=(
            "Private order submission (spot EXCHANGE + margin, same endpoint). "
            "Auth: bfx-apikey header + HMAC-SHA384 signature. "
            "Secret Manager key: bitfinex-api-credentials. "
            "BitfinexCeFiAdapter.place_order raises NotImplementedError today (HTTP client "
            "not injected, BLOCKED-CREDENTIALS) — signing is implemented, no order reaches the venue."
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
    # --- Kraken ---
    # F42: Kraken spot (api.kraken.com) and futures (futures.kraken.com) are separate
    # domains/API surfaces with their own schemas modules (external/kraken,
    # external/kraken_futures) — kept as distinct venue keys, unlike OKX's unified API.
    EndpointSpec(
        venue="kraken",
        endpoint_path="https://api.kraken.com/0/public/Ticker",
        http_method="GET",
        schema_class="KrakenTickerData",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="0",
        notes="Public spot ticker. No auth required.",
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
        version="0",
        notes=(
            "Private spot/margin order submission. Auth: API-Key header + HMAC-SHA512 "
            "signature (nonce-based). Secret Manager key: kraken-api-credentials. "
            "KrakenCeFiAdapter.place_order genuinely POSTs (real implementation, not a "
            "credentials-blocked scaffold)."
        ),
        requires_auth=True,
        cassette_status=CassetteStatus.AUTH_BLOCKED,
    ),
    EndpointSpec(
        venue="kraken_futures",
        endpoint_path="https://futures.kraken.com/derivatives/api/v3/tickers",
        http_method="GET",
        schema_class="KrakenFuturesTicker",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.LIVE_ONLY,
        version="v3",
        notes="Public futures ticker. No auth required.",
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
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
    # Consumers should check available_from_date to avoid querying markets that
    # don't exist for the requested time range (there is no v3_era_cutoff field —
    # an earlier version of this comment referenced one that was never built).
    #
    # GRANULARITY-MISLABELING CHECK (2026-07-25, watch-item from
    # sports_canonical_universe_and_apifootball_reference_expansion_2026_06_24.md):
    # checked whether pre-cutover 10-min snapshots would be evaluated against a
    # 5-min expectation anywhere downstream and read as "missing" coverage.
    # RESULT: not confirmed, no dated capability entry added. Every actual
    # sports-odds completeness path is grain-insensitive to the raw poll
    # interval — MDPS bucket assignment (bucket_assignment_adapter.py
    # TIER1_HORIZONS) matches snapshots to fixed pre-match offsets with a
    # 30-90min staleness tolerance, and the honest-coverage expected-universe
    # key for odds is (date, league_id, timeframe/horizon) with no per-snapshot
    # or per-minute axis. No code path computes an expected snapshot count from
    # a 5-min/10-min cadence constant, so the mislabeling scenario cannot occur
    # today. Re-check this note before building any future raw-tick-count
    # completeness check for odds_api.
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
    # F38: ``venue="ibkr"`` is a BROKER, not a venue — it routes to CME/ICE/CBOE.
    # This key is LOAD-BEARING as the tradfi data-pipeline SOURCE id; do NOT rename.
    # Broker→routed-venue truth: internal.architecture_v2.broker_routes.BROKER_ROUTES.
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
    # --- FX ---
    # F42: FXAdapter (execution-service fx_adapter.py) is IbkrTradFiAdapter with
    # venue_name="FX" — OTC forex execution via IBKR IDEALPRO (secType="CASH"), no
    # dedicated FX vendor endpoint. Market data is Yahoo Finance (separate venue).
    EndpointSpec(
        venue="fx",
        endpoint_path="reqContractDetails(secType=CASH,exchange=IDEALPRO)",
        http_method="TWS",
        schema_class="IBKRCashContract",
        access_mode=AccessMode.STREAMING_WEBSOCKET,
        data_availability=DataAvailability.LIVE_ONLY,
        version="tws-api",
        notes=(
            "OTC forex spot pairs (e.g. EUR.USD) via IBKR IDEALPRO, secType=CASH — no FUT/OPT "
            "contracts. Auth via TWS Gateway API key. Secret Manager key: ibkr-api-credentials."
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
        notes="Free, no auth. Weather forecast (recent + future dates).",
        requires_auth=False,
        cassette_status=CassetteStatus.RECORDED,
    ),
    EndpointSpec(
        venue="open_meteo",
        endpoint_path="https://archive-api.open-meteo.com/v1/archive",
        http_method="GET",
        schema_class="OpenMeteoResponse",
        access_mode=AccessMode.REST_POLLING,
        data_availability=DataAvailability.BOTH,
        version="v1",
        notes="Free, no auth. Historical weather (dates older than ~3 months).",
        requires_auth=False,
        cassette_status=CassetteStatus.PENDING,
    ),
]
