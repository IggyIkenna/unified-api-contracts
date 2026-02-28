# Mocks and VCR

How to record and use VCR cassettes per venue so tests can replay HTTP (and optionally WebSocket) without live API keys.

## Where cassettes live

- **Path**: `unified_api_contracts/<venue>/mocks/`
- **Naming**: `{endpoint_or_operation}.yaml` (e.g. `ticker_rest.yaml`, `order_book.yaml`, `fetch_order_ccxt.yaml`).
- **Format**: vcrpy YAML (request URL/method/headers + response status/headers/body).

## Recording cassettes

1. **Use vcrpy** with `cassette_library_dir` pointing at `unified_api_contracts/<venue>/mocks/`.
2. **Filter secrets** so nothing sensitive is committed:
   - Request headers: `Authorization`, `X-API-Key`, `X-Auth-Token`, `api-key`, `api_key`, and any venue-specific key header (e.g. Binance `X-MBX-APIKEY`, OKX `OK-ACCESS-KEY`).
   - Query params: strip `api_key`, `apikey`, `token` from recorded query strings.
   - Replace with placeholders in the cassette (e.g. `[FILTERED]`) so replay still works.

Example filter (use in VCR config or pytest fixture):

```python
def vcr_filter_request(request):
    if request.headers.get("Authorization"):
        request.headers["Authorization"] = "[FILTERED]"
    if request.headers.get("X-API-Key"):
        request.headers["X-API-Key"] = "[FILTERED]"
    return request
```

3. **Record mode**: `record_mode='once'` — record on first run, then replay from cassette.

## Using cassettes in tests

- In UMI/UOI/market-tick-data-service (or any consumer), set `VCR_CASSETTE_DIR` or pass `cassette_library_dir` to the path inside unified-api-contracts: `unified_api_contracts/<venue>/mocks/`.
- In unified-api-contracts repo, tests that perform HTTP (e.g. future “live” contract tests with replay) should use the same mocks path and filter so that CI runs without credentials.

## Per-venue notes

| Venue     | Auth header / param     | Suggested cassette names (REST)        |
|----------|-------------------------|----------------------------------------|
| databento| `Authorization` / key  | `timeseries_range.yaml`, `symbology.yaml` |
| tardis   | API key in header/param| `exchanges.yaml`, `trades.yaml`, `orderbook.yaml` |
| ccxt     | Exchange-specific      | `fetch_order_<exchange>.yaml`, `fetch_ticker.yaml` |
| binance  | `X-MBX-APIKEY` + sig   | `ticker.yaml`, `order.yaml`, `position.yaml` |
| thegraph | API key in URL/header  | `subgraph_query.yaml`                  |
| okx      | `OK-ACCESS-KEY` etc.   | `ticker.yaml`, `order.yaml`            |
| bybit    | `X-BAPI-API-KEY` etc.  | `ticker.yaml`, `order.yaml`            |
| alchemy  | API key in URL         | `rpc_eth_blockNumber.yaml`             |

WebSocket: if the test library supports recording WS frames, store under the same `mocks/` with names like `ws_ticker_stream.yaml`. Otherwise mock the WS client and feed canned JSON validated by unified-api-contracts schemas.

## Recording in this repo

Run once (with network) to record or refresh cassettes:

```bash
uv run python scripts/record_vcr_cassettes.py           # all venues with public endpoints
uv run python scripts/record_vcr_cassettes.py --venue binance
```

For key-based venues (e.g. tardis), set the env var and run:

```bash
export TARDIS_API_KEY=your_key
uv run python scripts/record_vcr_cassettes.py --venue tardis
```

Cassettes are written to `unified_api_contracts/<venue>/mocks/<name>.yaml`. Replay tests in `tests/test_vcr_replay.py` validate each recorded response against the venue schema. CI runs replay only (no live requests, no keys).

## References

- CONTRIBUTING.md — adding venues, capture script, filtering.
- docs/TRANSPORT_AND_ENDPOINTS.md — REST vs WebSocket vs FIX per venue.
- unified_api_contracts/vcr_endpoints.py — per-venue URLs and schema mapping for record/replay.
