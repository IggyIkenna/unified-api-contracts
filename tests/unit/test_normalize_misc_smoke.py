"""Smoke tests for rate limits, connectivity, sides, symbols, and module imports.

Continuation of test_normalize_smoke.py — split to keep files under size limit.
"""

from unified_api_contracts.canonical.crosscutting.errors import RateLimitInfo

# ---------------------------------------------------------------------------
# Rate limits module
# ---------------------------------------------------------------------------


class TestRateLimitExtractors:
    """Smoke test all rate limit extractors."""

    def test_binance_mbx_weight(self):
        from unified_api_contracts.normalize_utils.rate_limits import (
            extract_binance_rate_limit,
        )

        info = extract_binance_rate_limit({"X-MBX-Used-Weight-1M": "300"})
        assert info.limit == 6000
        assert info.remaining == 5700
        assert info.venue == "binance"

    def test_binance_standard_headers(self):
        from unified_api_contracts.normalize_utils.rate_limits import (
            extract_binance_rate_limit,
        )

        info = extract_binance_rate_limit({"X-RateLimit-Limit": "100", "X-RateLimit-Remaining": "50"})
        assert info.limit == 100

    def test_bybit_headers(self):
        from unified_api_contracts.normalize_utils.rate_limits import (
            extract_bybit_rate_limit,
        )

        info = extract_bybit_rate_limit({"X-Bapi-Limit": "200", "X-Bapi-Limit-Status": "150"})
        assert info.limit == 200
        assert info.remaining == 150
        assert info.venue == "bybit"

    def test_okx_headers(self):
        from unified_api_contracts.normalize_utils.rate_limits import (
            extract_okx_rate_limit,
        )

        info = extract_okx_rate_limit({"Retry-After": "5"})
        assert info.retry_after == 5.0
        assert info.venue == "okx"

    def test_deribit_headers(self):
        from unified_api_contracts.normalize_utils.rate_limits import (
            extract_deribit_rate_limit,
        )

        info = extract_deribit_rate_limit({"X-RateLimit-Remaining": "10"})
        assert info.remaining == 10
        assert info.venue == "deribit"

    def test_deribit_ws_rate_limit(self):
        from unified_api_contracts.normalize_utils.rate_limits import (
            extract_deribit_ws_rate_limit,
        )

        info = extract_deribit_ws_rate_limit({"retry_after": 10})
        assert info.retry_after == 10.0

    def test_deribit_ws_rate_limit_retryafter_alt(self):
        from unified_api_contracts.normalize_utils.rate_limits import (
            extract_deribit_ws_rate_limit,
        )

        info = extract_deribit_ws_rate_limit({"retryAfter": "5"})
        assert info.retry_after == 5.0

    def test_deribit_ws_rate_limit_empty(self):
        from unified_api_contracts.normalize_utils.rate_limits import (
            extract_deribit_ws_rate_limit,
        )

        info = extract_deribit_ws_rate_limit({})
        assert info.retry_after is None

    def test_coinbase_headers(self):
        from unified_api_contracts.normalize_utils.rate_limits import (
            extract_coinbase_rate_limit,
        )

        info = extract_coinbase_rate_limit({"Retry-After": "2"})
        assert info.retry_after == 2.0
        assert info.venue == "coinbase"

    def test_hyperliquid_headers(self):
        from unified_api_contracts.normalize_utils.rate_limits import (
            extract_hyperliquid_rate_limit,
        )

        info = extract_hyperliquid_rate_limit({})
        assert isinstance(info, RateLimitInfo)
        assert info.venue == "hyperliquid"

    def test_tardis_headers(self):
        from unified_api_contracts.normalize_utils.rate_limits import (
            extract_tardis_rate_limit,
        )

        info = extract_tardis_rate_limit({"X-RateLimit-Limit": "60"})
        assert info.limit == 60
        assert info.venue == "tardis"

    def test_api_football_rate_limit(self):
        from unified_api_contracts.normalize_utils.rate_limits import (
            extract_api_football_rate_limit,
        )

        info = extract_api_football_rate_limit(
            {"X-RateLimit-Requests-Limit": "100", "X-RateLimit-Requests-Remaining": "90"}
        )
        assert info.limit == 100
        assert info.remaining == 90

    def test_github_rate_limit(self):
        from unified_api_contracts.normalize_utils.rate_limits import (
            extract_github_rate_limit,
        )

        info = extract_github_rate_limit({"X-RateLimit-Limit": "5000", "X-RateLimit-Remaining": "4500"})
        assert info.limit == 5000
        assert info.venue == "github"


# ---------------------------------------------------------------------------
# Connectivity module
# ---------------------------------------------------------------------------


class TestConnectivityNormalizers:
    """Smoke test WS lifecycle normalizers."""

    def test_ws_connect(self):
        from unified_api_contracts.normalize_utils.connectivity import (
            normalize_ws_connect,
        )

        result = normalize_ws_connect("binance", channel="btcusdt@trade")
        assert result.venue == "binance"
        assert result.event.value == "connect"

    def test_ws_disconnect(self):
        from unified_api_contracts.normalize_utils.connectivity import (
            normalize_ws_disconnect,
        )

        result = normalize_ws_disconnect("binance", code=1000, reason="normal close")
        assert result.code == 1000

    def test_ws_ping(self):
        from unified_api_contracts.normalize_utils.connectivity import (
            normalize_ws_ping,
        )

        result = normalize_ws_ping("bybit", latency_ms=5.3)
        assert result.latency_ms == 5.3

    def test_ws_pong(self):
        from unified_api_contracts.normalize_utils.connectivity import (
            normalize_ws_pong,
        )

        result = normalize_ws_pong("okx")
        assert result.event.value == "pong"

    def test_binance_ws_subscription_success(self):
        from unified_api_contracts.normalize_utils.connectivity import (
            normalize_binance_ws_subscription,
        )

        result = normalize_binance_ws_subscription(None, channel="btcusdt@trade")
        assert result.event.value == "subscribe"

    def test_binance_ws_subscription_error(self):
        from unified_api_contracts.normalize_utils.connectivity import (
            normalize_binance_ws_subscription,
        )

        result = normalize_binance_ws_subscription("error message")
        assert result.event.value == "error"

    def test_bybit_ws_subscription(self):
        from unified_api_contracts.normalize_utils.connectivity import (
            normalize_bybit_ws_subscription,
        )

        assert normalize_bybit_ws_subscription(True, "orderbook.1.BTCUSDT").event.value == "subscribe"
        assert normalize_bybit_ws_subscription(False).event.value == "error"

    def test_okx_ws_subscription(self):
        from unified_api_contracts.normalize_utils.connectivity import (
            normalize_okx_ws_subscription,
        )

        assert normalize_okx_ws_subscription("subscribe").event.value == "subscribe"
        assert normalize_okx_ws_subscription("unsubscribe").event.value == "unsubscribe"
        assert normalize_okx_ws_subscription("error").event.value == "error"

    def test_deribit_ws_heartbeat(self):
        from unified_api_contracts.normalize_utils.connectivity import (
            normalize_deribit_ws_heartbeat,
        )

        assert normalize_deribit_ws_heartbeat("heartbeat").event.value == "ping"
        assert normalize_deribit_ws_heartbeat("test_request").event.value == "pong"

    def test_coinbase_ws_subscription(self):
        from unified_api_contracts.normalize_utils.connectivity import (
            normalize_coinbase_ws_subscription,
        )

        assert normalize_coinbase_ws_subscription("subscriptions").event.value == "subscribe"
        assert normalize_coinbase_ws_subscription("error").event.value == "error"

    def test_hyperliquid_ws_subscription(self):
        from unified_api_contracts.normalize_utils.connectivity import (
            normalize_hyperliquid_ws_subscription,
        )

        assert normalize_hyperliquid_ws_subscription("subscribed").event.value == "subscribe"
        assert normalize_hyperliquid_ws_subscription("failed").event.value == "error"

    def test_tardis_ws_subscription(self):
        from unified_api_contracts.normalize_utils.connectivity import (
            normalize_tardis_ws_subscription,
        )

        assert normalize_tardis_ws_subscription(True).event.value == "subscribe"
        assert normalize_tardis_ws_subscription(False).event.value == "error"

    def test_aster_ws_subscription(self):
        from unified_api_contracts.normalize_utils.connectivity import (
            normalize_aster_ws_subscription,
        )

        assert normalize_aster_ws_subscription("SUBSCRIBE").event.value == "subscribe"
        assert normalize_aster_ws_subscription("UNSUBSCRIBE").event.value == "unsubscribe"

    def test_ws_close_functions(self):
        from unified_api_contracts.normalize_utils.connectivity import (
            normalize_aster_ws_close,
            normalize_ibkr_ws_close,
            normalize_kalshi_ws_lifecycle,
            normalize_upbit_ws_close,
        )

        assert normalize_aster_ws_close(1000).event.value == "disconnect"
        assert normalize_ibkr_ws_close(1001, "going away").code == 1001
        assert normalize_upbit_ws_close(1000).event.value == "disconnect"

        opened = normalize_kalshi_ws_lifecycle("opened", "BTC-USD")
        assert opened.event.value in (
            "connect",
            "disconnect",
            "subscribe",
            "unsubscribe",
            "error",
            "reconnect",
        )

    def test_versifi_ws_message(self):
        from unified_api_contracts.normalize_utils.connectivity import (
            normalize_versifi_ws_message,
        )

        result = normalize_versifi_ws_message("order_update", "versifi")
        assert result.venue == "versifi"


# ---------------------------------------------------------------------------
# Sides module
# ---------------------------------------------------------------------------


class TestSideNormalizer:
    def test_buy_variants(self):
        from unified_api_contracts.normalize_utils.sides import (
            normalize_side,
        )

        for raw in ("BUY", "buy", "B", "b", "bid", "long", "Long", "LONG", 1, 0, None):
            assert normalize_side(raw) == "buy"

    def test_sell_variants(self):
        from unified_api_contracts.normalize_utils.sides import (
            normalize_side,
        )

        for raw in ("SELL", "sell", "S", "s", "ask", "short", "SHORT", 2, "2"):
            assert normalize_side(raw) == "sell"


# ---------------------------------------------------------------------------
# Symbols module
# ---------------------------------------------------------------------------


class TestSymbolNormalizer:
    def test_binance_spot(self):
        from unified_api_contracts.normalize_utils.symbols import (
            normalize_symbol,
        )

        assert normalize_symbol("binance", "BTCUSDT") == "BTC-USDT"

    def test_binance_perp(self):
        from unified_api_contracts.normalize_utils.symbols import (
            normalize_symbol,
        )

        assert normalize_symbol("binance", "BTCUSDT_PERP") == "BTC-USDT-PERP"

    def test_binance_unknown_quote(self):
        from unified_api_contracts.normalize_utils.symbols import (
            normalize_symbol,
        )

        result = normalize_symbol("binance", "XYZABC")
        assert isinstance(result, str)

    def test_okx_swap(self):
        from unified_api_contracts.normalize_utils.symbols import (
            normalize_symbol,
        )

        assert normalize_symbol("okx", "BTC-USDT-SWAP") == "BTC-USDT-PERP"

    def test_okx_spot(self):
        from unified_api_contracts.normalize_utils.symbols import (
            normalize_symbol,
        )

        assert normalize_symbol("okx", "BTC-USDT") == "BTC-USDT"

    def test_deribit_perp(self):
        from unified_api_contracts.normalize_utils.symbols import (
            normalize_symbol,
        )

        assert normalize_symbol("deribit", "BTC-PERPETUAL") == "BTC-PERP"

    def test_deribit_future(self):
        from unified_api_contracts.normalize_utils.symbols import (
            normalize_symbol,
        )

        result = normalize_symbol("deribit", "BTC-31DEC24")
        assert "BTC" in result

    def test_hyperliquid_perp(self):
        from unified_api_contracts.normalize_utils.symbols import (
            normalize_symbol,
        )

        assert normalize_symbol("hyperliquid", "BTC") == "BTC-USDC-PERP"

    def test_kucoin(self):
        from unified_api_contracts.normalize_utils.symbols import (
            normalize_symbol,
        )

        assert normalize_symbol("kucoin", "BTC-USDT") == "BTC-USDT"

    def test_tardis_passthrough(self):
        from unified_api_contracts.normalize_utils.symbols import (
            normalize_symbol,
        )

        assert normalize_symbol("tardis", "btcusdt") == "BTCUSDT"

    def test_databento_passthrough(self):
        from unified_api_contracts.normalize_utils.symbols import (
            normalize_symbol,
        )

        assert normalize_symbol("databento", "btcusdt") == "BTCUSDT"

    def test_unknown_venue(self):
        from unified_api_contracts.normalize_utils.symbols import (
            normalize_symbol,
        )

        assert normalize_symbol("unknown_venue", "btcusdt") == "BTCUSDT"

    def test_bybit(self):
        from unified_api_contracts.normalize_utils.symbols import (
            normalize_symbol,
        )

        assert normalize_symbol("bybit", "BTCUSDT") == "BTC-USDT"

    def test_coinbase(self):
        from unified_api_contracts.normalize_utils.symbols import (
            normalize_symbol,
        )

        assert normalize_symbol("coinbase", "BTC-USD") == "BTC-USD"


# ---------------------------------------------------------------------------
# Import smoke — ensure all modules load without error
# ---------------------------------------------------------------------------


class TestModuleImports:
    """Verify every normalize submodule imports cleanly."""

    def test_cefi_extended_imports(self):
        from unified_api_contracts.normalize_utils import cefi_extended

        assert cefi_extended is not None

    def test_connectivity_imports(self):
        from unified_api_contracts.normalize_utils import connectivity

        assert connectivity is not None

    def test_derivative_tickers_imports(self):
        from unified_api_contracts.normalize_utils import derivative_tickers

        assert derivative_tickers is not None

    def test_errors_imports(self):
        from unified_api_contracts.normalize_utils import errors

        assert errors is not None

    def test_fees_imports(self):
        from unified_api_contracts.normalize_utils import fees

        assert fees is not None

    def test_instruments_imports(self):
        from unified_api_contracts.normalize_utils import instruments

        assert instruments is not None

    def test_liquidations_imports(self):
        from unified_api_contracts.normalize_utils import liquidations

        assert liquidations is not None

    def test_ohlcv_imports(self):
        from unified_api_contracts.normalize_utils import ohlcv

        assert ohlcv is not None

    def test_options_imports(self):
        from unified_api_contracts.normalize_utils import options

        assert options is not None

    def test_orderbooks_imports(self):
        from unified_api_contracts.normalize_utils import orderbooks

        assert orderbooks is not None

    def test_orders_fills_imports(self):
        from unified_api_contracts.normalize_utils import orders_fills

        assert orders_fills is not None

    def test_rate_limits_imports(self):
        from unified_api_contracts.normalize_utils import rate_limits

        assert rate_limits is not None

    def test_sides_imports(self):
        from unified_api_contracts.normalize_utils import sides

        assert sides is not None

    def test_sports_imports(self):
        from unified_api_contracts.normalize_utils import sports

        assert sports is not None

    def test_symbols_imports(self):
        from unified_api_contracts.normalize_utils import symbols

        assert symbols is not None

    def test_tickers_imports(self):
        from unified_api_contracts.normalize_utils import tickers

        assert tickers is not None

    def test_trades_imports(self):
        from unified_api_contracts.normalize_utils import trades

        assert trades is not None

    def test_versifi_imports(self):
        from unified_api_contracts.normalize_utils import versifi

        assert versifi is not None
