# VCR Cassette Auth Status — All 67 Venues

SSOT: `unified_api_contracts_external/<venue>/mocks/`
Tests: `unified-api-contracts/tests/vcr/`
Interface normalizer tests: `unified-reference-data-interface/tests/integration/` and `unified-market-interface/tests/integration/`

---

## Legend

| Status         | Meaning                                                  |
| -------------- | -------------------------------------------------------- |
| DONE           | Cassette + test written                                  |
| CASSETTE-ONLY  | Cassette recorded, test not yet written                  |
| SKIP-GUARD     | Auth-gated harness written; records on next run with key |
| TODO-PUBLIC    | No cassette; public endpoint — can record any time       |
| TODO-NEED-KEY  | No cassette; requires API key not yet in Secret Manager  |
| TODO-NEED-AUTH | No cassette; requires username/password or OAuth         |
| TODO-INTERNAL  | Not an HTTP API — no VCR cassette appropriate            |

---

## Group 1 — DONE (cassette + tests)

| Venue         | Cassettes                                                                                                 | Test File                      | Auth          | Notes                        |
| ------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------ | ------------- | ---------------------------- |
| alchemy       | `alchemy_ws_eth_subscription.yaml`                                                                        | _(test missing — see Group 2)_ | KEY           | WS message                   |
| barchart      | `get_quote_es1.yaml`                                                                                      | `test_barchart_vcr.py`         | KEY           | ES1 futures quote            |
| betdaq        | `betdaq_get_markets.yaml`                                                                                 | `test_betdaq_vcr.py`           | AUTH-FILTERED | Synthetic                    |
| betfair       | `list_market_catalogue.yaml`, `list_market_book.yaml`                                                     | `test_betfair_vcr.py`          | AUTH-FILTERED | From examples; app key in SM |
| binance       | `ticker_24hr.yaml`                                                                                        | `test_binance_vcr.py`          | PUBLIC        | BTCUSDT perp ticker          |
| bybit         | `ticker.yaml`                                                                                             | `test_bybit_vcr.py`            | PUBLIC        | BTCUSDT linear ticker        |
| defillama     | `protocols.yaml`                                                                                          | `test_defillama_vcr.py`        | PUBLIC        | Protocol TVL list            |
| fear_greed    | `fng_latest.yaml`                                                                                         | `test_fear_greed_vcr.py`       | PUBLIC        | CNN FNG index                |
| fred          | `series_observations_dgs10.yaml`                                                                          | `test_fred_vcr.py`             | API_KEY       | 10yr Treasury yield          |
| hyperliquid   | `meta.yaml`                                                                                               | `test_hyperliquid_vcr.py`      | PUBLIC        | Perp universe                |
| matchbook     | `matchbook_get_markets.yaml`                                                                              | `test_matchbook_vcr.py`        | AUTH-FILTERED | Synthetic                    |
| okx           | `ticker.yaml`                                                                                             | `test_okx_vcr.py`              | PUBLIC        | BTC-USDT-SWAP ticker         |
| open_meteo    | `forecast_current_weather.yaml`                                                                           | `test_open_meteo_vcr.py`       | PUBLIC        | Weather forecast             |
| polymarket    | `clob_markets.yaml`                                                                                       | `test_polymarket_vcr.py`       | PUBLIC        | CLOB markets                 |
| pyth          | `pyth_ws_price_update.yaml`                                                                               | `test_pyth_vcr.py`             | PUBLIC        | Hermes price update          |
| smarkets      | `smarkets_get_markets.yaml`                                                                               | `test_smarkets_vcr.py`         | AUTH-FILTERED | Synthetic                    |
| tardis        | `exchanges.yaml`                                                                                          | `test_tardis_vcr.py`           | PUBLIC        | Exchange list                |
| upbit         | `ticker.yaml`                                                                                             | `test_upbit_vcr.py`            | PUBLIC        | KRW-BTC ticker               |
| yahoo_finance | `chart_aapl_1d.yaml`, `dividends_aapl.yaml`, `earnings_msft.yaml`, `error_*.yaml` (2), `splits_tsla.yaml` | `test_yahoo_finance_vcr.py`    | PUBLIC        | AAPL/MSFT/TSLA data          |

---

## Group 2 — CASSETTE-ONLY (cassette recorded, test file needed)

| Venue   | Cassette                           | Missing Test          | Notes                                                                  |
| ------- | ---------------------------------- | --------------------- | ---------------------------------------------------------------------- |
| alchemy | `alchemy_ws_eth_subscription.yaml` | `test_alchemy_vcr.py` | Alchemy WS subscription message; validates `AlchemyTransaction` schema |

---

## Group 3 — SKIP-GUARD (auth-gated harness written; records on next run with key)

| Venue          | Cassette Target                                                | Test File                  | Secret Manager Key           | Recording Command                                                 |
| -------------- | -------------------------------------------------------------- | -------------------------- | ---------------------------- | ----------------------------------------------------------------- |
| tardis (hist)  | `instruments_binance_futures.yaml`, `instruments_deribit.yaml` | `test_tardis_auth_vcr.py`  | `TARDIS_API_KEY` (needed)    | `TARDIS_API_KEY=<k> pytest tests/vcr/test_tardis_auth_vcr.py -v`  |
| databento      | `list_datasets.yaml`, `symbology_resolve_es.yaml`              | `test_databento_vcr.py`    | `DATABENTO_API_KEY` (needed) | `DATABENTO_API_KEY=<k> pytest tests/vcr/test_databento_vcr.py -v` |
| betfair (live) | `list_market_catalogue.yaml` (update)                          | `test_betfair_auth_vcr.py` | `BETFAIR_APP_KEY` ✓ SM       | Also needs `BETFAIR_SESSION_TOKEN` from login                     |

---

## Group 4 — TODO-PUBLIC (public endpoints; no auth; record any time)

All can be recorded via `curl` + manual cassette YAML, same as Tardis exchanges cassette.

| Venue                | Priority | Endpoint to Record                                            | Schema to Validate    |
| -------------------- | -------- | ------------------------------------------------------------- | --------------------- |
| coingecko            | P0       | `GET /api/v3/coins/markets?vs_currency=usd&ids=bitcoin`       | `CoingeckoMarket`     |
| kraken               | P0       | `GET /0/public/Ticker?pair=XBTUSD`                            | `KrakenTicker`        |
| deribit              | P0       | `GET /api/v2/public/get_instruments?currency=BTC&kind=future` | `DeribitInstrument`   |
| kucoin               | P0       | `GET /api/v1/market/orderbook/level1?symbol=BTC-USDT`         | `KucoinOrderBook`     |
| gateio               | P0       | `GET /api/v4/spot/tickers?currency_pair=BTC_USDT`             | `GateioTicker`        |
| mexc                 | P0       | `GET /api/v3/ticker/24hr?symbol=BTCUSDT`                      | `MEXCTicker`          |
| huobi                | P1       | `GET /market/detail/merged?symbol=btcusdt`                    | `HuobiTicker`         |
| bitstamp             | P1       | `GET /api/v2/ticker/btcusd/`                                  | `BitstampTicker`      |
| bitfinex             | P1       | `GET /v2/ticker/tBTCUSD`                                      | `BitfinexTicker`      |
| bitget               | P1       | `GET /api/v2/spot/market/tickers?symbol=BTCUSDT`              | `BitgetTicker`        |
| dydx                 | P1       | `GET /v4/markets` (dydx v4 REST)                              | `DydxMarket`          |
| ecb                  | P1       | `GET /service/data/EXR/D.USD.EUR.SP00.A?format=jsondata`      | `ECBRate`             |
| ofr                  | P1       | `GET /v1/series/REPO-DVP-FAR-BGCR-P50?startdate=2024-01-01`   | `OFRRepoRate`         |
| manifold             | P1       | `GET /v0/markets?limit=5`                                     | `ManifoldMarket`      |
| predictit            | P1       | `GET /api/marketdata/all/`                                    | `PredictItMarket`     |
| transfermarkt        | P2       | Unofficial scrape endpoint                                    | `TransfermarktPlayer` |
| understat            | P2       | Unofficial JSON endpoint                                      | `UnderstatStat`       |
| soccer_football_info | P2       | `GET /soccer-api` public endpoint                             | `SoccerFootballInfo`  |
| thegraph             | P2       | GraphQL `POST /subgraphs/name/uniswap/uniswap-v3`             | `TheGraphPool`        |
| coinbase (public)    | P2       | `GET /api/v3/brokerage/products/BTC-USDT/ticker`              | `CoinbaseTicker`      |

---

## Group 5 — TODO-NEED-KEY (API key required; no key currently in Secret Manager)

| Venue         | Secret Manager Key       | Endpoint                                       | Schema                 |
| ------------- | ------------------------ | ---------------------------------------------- | ---------------------- |
| api_football  | `API_FOOTBALL_KEY`       | `GET /v3/fixtures?league=39&season=2024`       | `APIFootballFixture`   |
| arkham        | `ARKHAM_API_KEY`         | `GET /api/address/{addr}/transactions`         | `ArkhamTransaction`    |
| aster         | `ASTER_API_KEY`          | Aster DEX REST                                 | `AsterMarket`          |
| bloxroute     | `BLOXROUTE_AUTH_HEADER`  | WS subscription                                | `BloxrouteTransaction` |
| coinglass     | `COINGLASS_API_KEY`      | `GET /api/futures/openInterest/chart`          | `CoinglassOI`          |
| databento     | `DATABENTO_API_KEY`      | `GET /v0/metadata.list_datasets`               | `DatabentoDataset`     |
| footystats    | `FOOTYSTATS_API_KEY`     | `GET /api/?action=get-leagues`                 | `FootystatsLeague`     |
| glassnode     | `GLASSNODE_API_KEY`      | `GET /v1/metrics/market/price_usd_close?a=BTC` | `GlassnodeMetric`      |
| kalshi        | `KALSHI_API_KEY`         | `GET /trade-api/v2/markets`                    | `KalshiMarket`         |
| metabet       | `METABET_API_KEY`        | Metabet odds endpoint                          | `MetabetOdds`          |
| mev           | `MEV_API_KEY`            | MEV data endpoint                              | `MEVTransaction`       |
| odds_api      | `ODDS_API_KEY`           | `GET /v4/sports/soccer_epl/odds`               | `OddsAPIGame`          |
| openbb        | `OPENBB_TOKEN`           | OpenBB Platform REST                           | `OpenBBData`           |
| pinnacle      | `PINNACLE_API_KEY`       | `GET /v1/fixtures?sportId=29`                  | `PinnacleFixture`      |
| sharpapi      | `SHARPAPI_API_KEY`       | SharpAPI endpoint                              | `SharpAPIData`         |
| tardis (hist) | `TARDIS_API_KEY`         | `GET /v1/instruments/{exchange}`               | `TardisInstrument`     |
| versifi       | `VERSIFI_API_KEY`        | Versifi REST                                   | `VersifiData`          |
| github        | `GITHUB_TOKEN` (Actions) | `GET /repos/{owner}/{repo}`                    | `GithubRepo`           |

---

## Group 6 — TODO-NEED-AUTH (username/password, OAuth, or complex auth)

| Venue              | Auth Type                 | Notes                                                                      |
| ------------------ | ------------------------- | -------------------------------------------------------------------------- |
| betfair (live)     | App key + session token   | App key in SM; session token from `POST /api/login` with username+password |
| coinbase (private) | API key + secret          | For private order/position endpoints                                       |
| deribit (private)  | client_id + client_secret | OAuth2; public instrument endpoints are public                             |
| ibkr               | TWS Gateway               | Requires running TWS locally; not HTTP                                     |
| instadapp          | Wallet signature          | On-chain; WS subscription for positions                                    |

---

## Group 7 — TODO-INTERNAL (not HTTP APIs; no VCR cassette appropriate)

| Venue/Directory   | Reason                                                                | What to do instead                                 |
| ----------------- | --------------------------------------------------------------------- | -------------------------------------------------- |
| `fix/`            | FIX protocol (binary/TCP; not HTTP)                                   | Unit tests with synthetic FIX messages             |
| `nautilus/`       | Nautilus trading framework data types; not an external API            | Unit tests against schema                          |
| `prime_broker/`   | Internal contract definitions                                         | Unit tests                                         |
| `regulatory/`     | Internal regulatory data types                                        | Unit tests                                         |
| `sentiment/`      | Internal sentiment aggregation schema                                 | Unit tests                                         |
| `odds_engine/`    | Internal odds calculation engine                                      | Unit tests                                         |
| `cloud_sdks/`     | GCP/AWS SDK wrappers; tested via `unified-cloud-interface`            | Integration tests using `aioresponses`/gRPC mock   |
| `sports/`         | Canonical sports data types (parent dir; venues are sub-items)        | Covered by betfair/betdaq/etc. tests               |
| `macro/`          | Macro data aggregation types (internal)                               | Unit tests                                         |
| `onchain/`        | On-chain data types (internal aggregation)                            | Unit tests                                         |
| `venue_manifest/` | Configuration, not an API                                             | No test needed                                     |
| `defi/`           | DeFi protocol schemas (covered by aave/uniswap/etc. individual tests) | Covered by specific protocol tests                 |
| `ccxt/`           | CCXT library wrapper (not a venue)                                    | Unit tests via CCXT mock; integration test in URDI |

---

## Summary

| Status         | Count  | Venues                                                                                                                                                                                              |
| -------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DONE           | 19     | alchemy(partial), barchart, betdaq, betfair, binance, bybit, defillama, fear_greed, fred, hyperliquid, matchbook, okx, open_meteo, polymarket, pyth, smarkets, tardis, upbit, yahoo_finance         |
| CASSETTE-ONLY  | 1      | alchemy                                                                                                                                                                                             |
| SKIP-GUARD     | 3      | tardis-hist, databento, betfair-live                                                                                                                                                                |
| TODO-PUBLIC    | 20     | coingecko, kraken, deribit, kucoin, gateio, mexc, huobi, bitstamp, bitfinex, bitget, dydx, ecb, ofr, manifold, predictit, transfermarkt, understat, soccer_football_info, thegraph, coinbase-public |
| TODO-NEED-KEY  | 17     | api_football, arkham, aster, bloxroute, coinglass, databento, footystats, glassnode, kalshi, metabet, mev, odds_api, openbb, pinnacle, sharpapi, versifi, github                                    |
| TODO-NEED-AUTH | 5      | betfair-live, coinbase-private, deribit-private, ibkr, instadapp                                                                                                                                    |
| TODO-INTERNAL  | 13     | fix, nautilus, prime_broker, regulatory, sentiment, odds_engine, cloud_sdks, sports, macro, onchain, venue_manifest, defi, ccxt                                                                     |
| **Total**      | **78** | _(some venues have multiple cassette targets)_                                                                                                                                                      |

**Current cassette coverage: 19/57 non-internal venues = 33%**
**Target for B grade: ≥ 50% = 29+ venues**
**Target for A grade: ≥ 80% = 46+ venues**

---

## Path to 80%+ Coverage (A grade)

Record these in order of effort:

1. All 20 TODO-PUBLIC venues (curl + yaml, ~2h) → coverage: 39/57 = 68%
2. All 3 SKIP-GUARD venues once keys available → coverage: 42/57 = 74%
3. Prioritize from TODO-NEED-KEY: github (token in Actions), odds_api, kalshi, coinglass, glassnode → coverage: 47/57 = 82% ✓

---

## Recording Recipe (public endpoints)

```bash
# 1. Record live response
curl -s -D /tmp/headers.txt "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=bitcoin" \
  -o /tmp/response.json

# 2. Construct cassette YAML (see existing cassettes for template)
python3 scripts/build_cassette.py \
  --url "https://api.coingecko.com/api/v3/coins/markets" \
  --params "vs_currency=usd&ids=bitcoin" \
  --response /tmp/response.json \
  --output unified_api_contracts/unified_api_contracts_external/coingecko/mocks/markets_bitcoin.yaml
```
