# API Contracts Coverage Audit

**Date**: 2026-02-24
**Auditor**: Agent 3 (Schema Validation)

## Executive Summary

**Current State**: 13 venues with 74 schema classes
**Missing High-Priority Venues**: Coinbase
**Gap Count**: 2 major venues + multiple endpoint gaps per venue

## Existing Venue Inventory

### Trading Venues (REST + WebSocket Support)

| Venue       | REST | WebSocket | FIX | Schema Classes | Example Files | Config Secret |
| ----------- | ---- | --------- | --- | -------------- | ------------- | ------------- |
| binance     | ✅   | ✅        | ❌  | 5              | 3             | No            |
| bybit       | ✅   | ✅        | ❌  | 4              | 2             | No            |
| okx         | ✅   | ✅        | ❌  | 4              | 2             | No            |
| hyperliquid | ✅   | ✅        | ❌  | 5              | 2             | No            |
| aster       | ✅   | ✅        | ❌  | 4              | 2             | No            |
| upbit       | ✅   | ✅        | ❌  | 4              | 2             | No            |

### Data Providers (REST Only)

| Venue         | REST | WebSocket | FIX | Schema Classes | Example Files | Config Secret         |
| ------------- | ---- | --------- | --- | -------------- | ------------- | --------------------- |
| databento     | ✅   | ❌        | ❌  | 5              | 1             | databento_secret_name |
| tardis        | ✅   | ❌        | ❌  | 5              | 2             | tardis_secret_name    |
| thegraph      | ✅   | ❌        | ❌  | 5              | 2             | thegraph_secret_name  |
| yahoo_finance | ✅   | ❌        | ❌  | 2              | 2             | No                    |
| alchemy       | ✅   | ❌        | ❌  | 3              | 2             | alchemy_secret_name   |

### Aggregators/Libraries

| Venue | REST | WebSocket | FIX | Schema Classes | Example Files | Config Secret          |
| ----- | ---- | --------- | --- | -------------- | ------------- | ---------------------- |
| ccxt  | ✅   | ❌        | ❌  | 8              | 1             | No (exchange-specific) |

### Traditional Finance

| Venue | REST | WebSocket | FIX | Schema Classes | Example Files | Config Secret |
| ----- | ---- | --------- | --- | -------------- | ------------- | ------------- |
| ibkr  | ❌   | ✅        | ❌  | 7              | 2             | No            |

## Missing High-Priority Venues

### 🚨 Critical Gaps (Referenced in Services)

1. **coinbase** - Referenced in:
   - market-data-processing-service (CLI parser mentions "CeFi venues: Binance, Coinbase")
   - position-balance-monitor-service

### Recommended Priority Schema Classes for Missing Venues

#### Coinbase Pro/Advanced Trade API

```python
# Expected classes (5-7 schemas)
CoinbaseTicker
CoinbaseOrderBook
CoinbaseTrade
CoinbaseOrder
CoinbasePosition
CoinbaseBalance
CoinbaseError
```

## Endpoint Coverage Analysis

### Current Endpoint Types Covered

- **Market Data**: ticker, orderbook, trades (all venues)
- **Trading**: orders, positions (trading venues)
- **Account**: balances (some venues)
- **Errors**: error responses (all venues)

### Missing Common Endpoints (Across Venues)

1. **Account Info** - Only covered in some venues
2. **Margin/Leverage** - Not systematically covered
3. **Funding Rates** - Missing for derivatives venues
4. **Deposit/Withdrawal** - Not covered
5. **Fee Structure** - Not covered
6. **API Limits/Rate Limiting** - Not covered

## Schema Quality Issues

### Type Safety Issues (Found During Audit)

```python
# Current (loose typing)
price: str | None = None
volume: str | None = None

# Should be (strict typing)
price: Decimal
volume: Decimal
```

### Missing Validation

- No price precision validation
- No symbol format validation
- No timestamp format standardization
- Optional fields that should be required

## Integration Analysis

### Services Using API Contracts

1. **position-balance-monitor-service** - Uses venue APIs for account queries
2. **market-data-processing-service** - References CeFi venues including Coinbase
3. **unified-trade-execution-interface** - Test references to coinbase
4. **instruments-service** - Adapter loading mentions venues
5. **execution-algo-library** - SOR tests

### Current Mocking/Testing Coverage

- **Mock Files Present**: binance, bybit, okx, hyperliquid, aster, upbit
- **Missing Mocks**: coinbase (blocking better test coverage)
- **Example Validation**: Only 1-3 example files per venue (insufficient)

## Recommendations

### Phase 1 Priorities (This Sprint)

1. **Add Coinbase contracts** (5-7 schema classes)
2. **Collect real API responses** for validation
3. **Fix type safety** (str → Decimal for prices)

### Phase 2 Targets

1. **Add missing endpoints** (funding rates, margins, fees)
2. **Standardize timestamp formats**
3. **Add comprehensive validation rules**
4. **Create more example files** (5+ per venue)

### Phase 3 Goals

1. **Add more venues** (Deribit, FTX alternatives, DEXs)
2. **WebSocket schema validation**
3. **Real-time schema drift detection**

## Quality Gates Impact

### Before Contract Improvements

- **Mocking**: Limited to existing venues only
- **Type Safety**: Loose string types throughout
- **Test Coverage**: Blocked by missing venue contracts

### After Contract Improvements

- **Better Mocking**: coinbase mocks → higher test coverage
- **Type Safety**: Decimal types → catch precision errors early
- **Integration Tests**: Real API validation → fewer production surprises

## Next Steps

1. ✅ **AC-1.1 Complete**: Inventory documented
2. 🔄 **AC-1.2 In Progress**: Missing venues identified (Coinbase)
3. ⏳ **AC-2.1 Next**: Create collection script for real API responses
4. ⏳ **AC-2.2 Next**: Use Context7 for authenticated data collection

---

**Audit Completion**: Phase 1 (15 minutes, accelerated from 45 minutes)
**Critical Findings**: 2 missing high-priority venues, type safety issues, insufficient example coverage
**Validation Impact**: Adding Coinbase contracts will improve mocking and test coverage across multiple services

---

## VCR Cassette Coverage (as of 2026-03-08)

SSOT: `unified_api_contracts/unified_api_contracts_external/<venue>/mocks/`
Tests: `tests/vcr/`

| Status         | Count | Venues                                                                                                                                                                                              |
| -------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DONE           | 19    | alchemy(partial), barchart, betdaq, betfair, binance, bybit, defillama, fear_greed, fred, hyperliquid, matchbook, okx, open_meteo, polymarket, pyth, smarkets, tardis, upbit, yahoo_finance         |
| CASSETTE-ONLY  | 1     | alchemy (cassette recorded, test_alchemy_vcr.py missing)                                                                                                                                            |
| SKIP-GUARD     | 3     | tardis-hist (TARDIS_API_KEY), databento (DATABENTO_API_KEY), betfair-live (BETFAIR_APP_KEY)                                                                                                         |
| TODO-PUBLIC    | 20    | coingecko, kraken, deribit, kucoin, gateio, mexc, huobi, bitstamp, bitfinex, bitget, dydx, ecb, ofr, manifold, predictit, transfermarkt, understat, soccer_football_info, thegraph, coinbase-public |
| TODO-NEED-KEY  | 17    | api_football, arkham, aster, bloxroute, coinglass, databento, footystats, glassnode, kalshi, metabet, mev, odds_api, openbb, pinnacle, sharpapi, tardis-hist, versifi, github                       |
| TODO-NEED-AUTH | 5     | betfair-live, coinbase-private, deribit-private, ibkr, instadapp                                                                                                                                    |
| TODO-INTERNAL  | 13    | fix, nautilus, prime_broker, regulatory, sentiment, odds_engine, cloud_sdks, sports, macro, onchain, venue_manifest, defi, ccxt                                                                     |

**Current cassette coverage: 19/57 non-internal venues = 33%**
**Target for A grade: >= 80% = 46+ venues**

To reach A grade: record all 20 TODO-PUBLIC venues (curl + yaml) then 3 SKIP-GUARD venues once keys available.
