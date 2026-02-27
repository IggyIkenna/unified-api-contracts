# OHLCV Source Truth

Tardis OHLCV is **computed** from tick trades (`computeTradeBars`). Direct exchange REST/WS provide **native** candles.

| Source | Type | Notes |
|--------|------|-------|
| Tardis | COMPUTED_FROM_TICKS | Aggregated from tick trades |
| Binance | NATIVE_CANDLE | GET /api/v3/klines, GET /fapi/v1/klines |
| OKX | NATIVE_CANDLE | GET /api/v5/market/candles |
| Bybit | NATIVE_CANDLE | GET /v5/market/kline |
| Deribit | NATIVE_CANDLE | /public/get_tradingview_chart_data |
| Hyperliquid | NATIVE_CANDLE | info:candleSnapshot; WS candle: t,T,s,i,o,c,h,l,v,n |
| Databento | NATIVE_CANDLE | OHLCV-1M, OHLCV-1S record types |

Hyperliquid WS candle subscription fields: `t` (start), `T` (close), `s` (symbol), `i` (interval), `o` (open), `c` (close), `h` (high), `l` (low), `v` (volume), `n` (trades).
