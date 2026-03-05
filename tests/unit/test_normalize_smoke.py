"""Smoke tests for the normalize/ submodule.

Exercises every normalizer with minimal valid inputs to ensure:
1. No import errors
2. Functions are callable and return the expected canonical type
3. Coverage > 0% for all normalize modules (driving total coverage above 70%)
"""

from unified_api_contracts.unified_normalised_contracts.errors import (
    CanonicalAuthenticationError,
    CanonicalAuthorizationError,
    CanonicalError,
    CanonicalInsufficientBalanceError,
    CanonicalInternalServerError,
    CanonicalInvalidRequestError,
    CanonicalMarketClosedError,
    CanonicalNetworkError,
    CanonicalOrderRejectedError,
    CanonicalRateLimitError,
    CanonicalServiceUnavailableError,
    RateLimitInfo,
)

# ---------------------------------------------------------------------------
# Errors module — all 52 normalizers
# ---------------------------------------------------------------------------


class TestErrorNormalizers:
    """Smoke test every normalize_<venue>_error function."""

    def test_binance_known_rate_limit(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_binance_error

        result = normalize_binance_error("-1003", "too many requests")
        assert isinstance(result, CanonicalRateLimitError)
        assert result.venue == "binance"

    def test_binance_unknown_code(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_binance_error

        result = normalize_binance_error("9999", "unknown")
        assert isinstance(result, CanonicalError)

    def test_binance_integer_code(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_binance_error

        result = normalize_binance_error(-1022)
        assert isinstance(result, CanonicalAuthenticationError)

    def test_bybit_known(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_bybit_error

        assert isinstance(normalize_bybit_error("10006"), CanonicalRateLimitError)
        assert isinstance(normalize_bybit_error("10001"), CanonicalAuthenticationError)
        assert isinstance(normalize_bybit_error("99999"), CanonicalError)

    def test_okx_known(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_okx_error

        assert isinstance(normalize_okx_error("50011"), CanonicalRateLimitError)
        assert isinstance(normalize_okx_error("51008"), CanonicalInsufficientBalanceError)
        assert isinstance(normalize_okx_error("UNKNOWN"), CanonicalError)

    def test_deribit_known(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_deribit_error

        assert isinstance(normalize_deribit_error("10028"), CanonicalRateLimitError)
        assert isinstance(normalize_deribit_error("10010"), CanonicalError)  # ContractExpired
        assert isinstance(normalize_deribit_error("00000"), CanonicalError)

    def test_coinbase_known(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_coinbase_error

        assert isinstance(normalize_coinbase_error("RATE_LIMIT_EXCEEDED"), CanonicalRateLimitError)
        assert isinstance(normalize_coinbase_error("ORDER_REJECTED"), CanonicalOrderRejectedError)
        assert isinstance(normalize_coinbase_error("UNKNOWN_CODE"), CanonicalError)

    def test_hyperliquid_known(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_hyperliquid_error

        assert isinstance(normalize_hyperliquid_error("RATE_LIMIT"), CanonicalRateLimitError)
        assert isinstance(normalize_hyperliquid_error("ORDER_REJECTED"), CanonicalOrderRejectedError)
        assert isinstance(normalize_hyperliquid_error("UNKNOWN"), CanonicalError)

    def test_ccxt_known(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_ccxt_error

        assert isinstance(normalize_ccxt_error("RateLimitExceeded"), CanonicalRateLimitError)
        assert isinstance(normalize_ccxt_error("NetworkError"), CanonicalNetworkError)
        assert isinstance(normalize_ccxt_error("UNKNOWN"), CanonicalError)

    def test_tardis_known_and_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_tardis_error

        assert isinstance(normalize_tardis_error("429"), CanonicalRateLimitError)
        assert isinstance(normalize_tardis_error(400), CanonicalInvalidRequestError)
        assert isinstance(normalize_tardis_error("NONCODE"), CanonicalError)

    def test_upbit_known(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_upbit_error

        assert isinstance(normalize_upbit_error("too_many_requests"), CanonicalRateLimitError)
        assert isinstance(normalize_upbit_error("invalid_access_key"), CanonicalAuthenticationError)
        assert isinstance(normalize_upbit_error("UNKNOWN"), CanonicalError)

    def test_alchemy_known_and_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_alchemy_error

        assert isinstance(normalize_alchemy_error("-32600"), CanonicalInvalidRequestError)
        assert isinstance(normalize_alchemy_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_alchemy_error("500"), CanonicalInternalServerError)
        assert isinstance(normalize_alchemy_error("NOCODE"), CanonicalError)

    def test_ibkr_known(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_ibkr_error

        assert isinstance(normalize_ibkr_error("1100"), CanonicalNetworkError)
        assert isinstance(normalize_ibkr_error("1300"), CanonicalOrderRejectedError)
        assert isinstance(normalize_ibkr_error("9999"), CanonicalError)

    def test_kalshi_known_and_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_kalshi_error

        assert isinstance(normalize_kalshi_error("MARKET_CLOSED"), CanonicalMarketClosedError)
        assert isinstance(normalize_kalshi_error("429"), CanonicalRateLimitError)
        assert isinstance(normalize_kalshi_error(503), CanonicalServiceUnavailableError)
        assert isinstance(normalize_kalshi_error("NOCODE"), CanonicalError)

    def test_polymarket_known_and_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_polymarket_error

        assert isinstance(normalize_polymarket_error("RATE_LIMIT"), CanonicalRateLimitError)
        assert isinstance(normalize_polymarket_error("400"), CanonicalInvalidRequestError)
        assert isinstance(normalize_polymarket_error("NOCODE"), CanonicalError)

    def test_betfair_known_and_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_betfair_error

        assert isinstance(normalize_betfair_error("TOO_MANY_REQUESTS"), CanonicalRateLimitError)
        assert isinstance(normalize_betfair_error("MARKET_CLOSED"), CanonicalMarketClosedError)
        assert isinstance(normalize_betfair_error("INVALID_BET_SIZE"), CanonicalError)
        assert isinstance(normalize_betfair_error("400"), CanonicalInvalidRequestError)
        assert isinstance(normalize_betfair_error("NOCODE"), CanonicalError)

    def test_versifi_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_versifi_error

        assert isinstance(normalize_versifi_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_versifi_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_versifi_error("NOCODE"), CanonicalError)

    def test_kraken_known_and_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_kraken_error

        assert isinstance(normalize_kraken_error("EAPI:Rate limit exceeded"), CanonicalRateLimitError)
        assert isinstance(normalize_kraken_error("429"), CanonicalRateLimitError)
        assert isinstance(normalize_kraken_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_kraken_error("UNKNOWN_STR"), CanonicalError)

    def test_kucoin_known_and_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_kucoin_error

        assert isinstance(normalize_kucoin_error("401000"), CanonicalRateLimitError)
        assert isinstance(normalize_kucoin_error("200004"), CanonicalInsufficientBalanceError)
        assert isinstance(normalize_kucoin_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_kucoin_error("NOCODE"), CanonicalError)

    def test_gateio_known_and_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_gateio_error

        assert isinstance(normalize_gateio_error("RATE_LIMIT"), CanonicalRateLimitError)
        assert isinstance(normalize_gateio_error("BALANCE_NOT_ENOUGH"), CanonicalInsufficientBalanceError)
        assert isinstance(normalize_gateio_error(500), CanonicalInternalServerError)
        assert isinstance(normalize_gateio_error("NOCODE"), CanonicalError)

    def test_bitfinex_known_and_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_bitfinex_error

        assert isinstance(normalize_bitfinex_error("ERR_RATE_LIMIT"), CanonicalRateLimitError)
        assert isinstance(normalize_bitfinex_error("ERR_NOT_ENOUGH_BALANCE"), CanonicalInsufficientBalanceError)
        assert isinstance(normalize_bitfinex_error(500), CanonicalInternalServerError)
        assert isinstance(normalize_bitfinex_error("NOCODE"), CanonicalError)

    def test_bitstamp_known_and_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_bitstamp_error

        assert isinstance(normalize_bitstamp_error("API0002"), CanonicalAuthenticationError)
        assert isinstance(normalize_bitstamp_error("429"), CanonicalRateLimitError)
        assert isinstance(normalize_bitstamp_error(403), CanonicalAuthorizationError)
        assert isinstance(normalize_bitstamp_error("NOCODE"), CanonicalError)

    def test_mexc_known_and_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_mexc_error

        assert isinstance(normalize_mexc_error("10072"), CanonicalAuthenticationError)
        assert isinstance(normalize_mexc_error("30004"), CanonicalInsufficientBalanceError)
        assert isinstance(normalize_mexc_error(500), CanonicalInternalServerError)
        assert isinstance(normalize_mexc_error("NOCODE"), CanonicalError)

    def test_huobi_known_and_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_huobi_error

        assert isinstance(normalize_huobi_error("too-many-requests"), CanonicalRateLimitError)
        assert isinstance(normalize_huobi_error("api-signature-not-valid"), CanonicalAuthenticationError)
        assert isinstance(normalize_huobi_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_huobi_error("NOCODE"), CanonicalError)

    def test_bitget_known_and_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_bitget_error

        assert isinstance(normalize_bitget_error("40018"), CanonicalRateLimitError)
        assert isinstance(normalize_bitget_error("40001"), CanonicalAuthenticationError)
        assert isinstance(normalize_bitget_error(500), CanonicalInternalServerError)
        assert isinstance(normalize_bitget_error("NOCODE"), CanonicalError)

    def test_dydx_known_and_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_dydx_error

        assert isinstance(normalize_dydx_error("RESOURCE_EXHAUSTED"), CanonicalRateLimitError)
        assert isinstance(normalize_dydx_error("UNAUTHENTICATED"), CanonicalAuthenticationError)
        assert isinstance(normalize_dydx_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_dydx_error("NOCODE"), CanonicalError)

    def test_databento_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_databento_error

        assert isinstance(normalize_databento_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_databento_error("429"), CanonicalRateLimitError)
        assert isinstance(normalize_databento_error("NOCODE"), CanonicalError)

    def test_aster_known_and_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_aster_error

        assert isinstance(normalize_aster_error("RATE_LIMIT_EXCEEDED"), CanonicalRateLimitError)
        assert isinstance(normalize_aster_error("MARKET_CLOSED"), CanonicalMarketClosedError)
        assert isinstance(normalize_aster_error(503), CanonicalServiceUnavailableError)
        assert isinstance(normalize_aster_error("NOCODE"), CanonicalError)

    def test_fix_known(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_fix_error

        assert isinstance(normalize_fix_error("0"), CanonicalOrderRejectedError)
        assert isinstance(normalize_fix_error("SESSION_REJECTED"), CanonicalAuthenticationError)
        assert isinstance(normalize_fix_error("99"), CanonicalError)

    def test_prime_broker_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_prime_broker_error

        assert isinstance(normalize_prime_broker_error(400), CanonicalInvalidRequestError)
        assert isinstance(normalize_prime_broker_error("NOCODE"), CanonicalError)

    def test_nautilus_known(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_nautilus_error

        assert isinstance(normalize_nautilus_error("ORDER_DENIED"), CanonicalOrderRejectedError)
        assert isinstance(normalize_nautilus_error("VENUE_NOT_AVAILABLE"), CanonicalServiceUnavailableError)
        assert isinstance(normalize_nautilus_error("UNKNOWN"), CanonicalError)

    def test_betdaq_known_and_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_betdaq_error

        assert isinstance(normalize_betdaq_error("1001"), CanonicalRateLimitError)
        assert isinstance(normalize_betdaq_error("40"), CanonicalInsufficientBalanceError)
        assert isinstance(normalize_betdaq_error(503), CanonicalServiceUnavailableError)
        assert isinstance(normalize_betdaq_error("NOCODE"), CanonicalError)

    def test_smarkets_known_and_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_smarkets_error

        assert isinstance(normalize_smarkets_error("too_many_requests"), CanonicalRateLimitError)
        assert isinstance(normalize_smarkets_error("unauthorized"), CanonicalAuthenticationError)
        assert isinstance(normalize_smarkets_error(500), CanonicalInternalServerError)
        assert isinstance(normalize_smarkets_error("NOCODE"), CanonicalError)

    def test_pinnacle_known_and_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_pinnacle_error

        assert isinstance(normalize_pinnacle_error("INSUFFICIENT_FUNDS"), CanonicalInsufficientBalanceError)
        assert isinstance(normalize_pinnacle_error("LINE_CHANGED"), CanonicalOrderRejectedError)
        assert isinstance(normalize_pinnacle_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_pinnacle_error("NOCODE"), CanonicalError)

    def test_manifold_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_manifold_error

        assert isinstance(normalize_manifold_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_manifold_error("NOCODE"), CanonicalError)

    def test_api_football_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_api_football_error

        assert isinstance(normalize_api_football_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_api_football_error("NOCODE"), CanonicalError)

    def test_arkham_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_arkham_error

        assert isinstance(normalize_arkham_error(403), CanonicalAuthorizationError)
        assert isinstance(normalize_arkham_error("NOCODE"), CanonicalError)

    def test_bloxroute_known_and_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_bloxroute_error

        assert isinstance(normalize_bloxroute_error("-32600"), CanonicalInvalidRequestError)
        assert isinstance(normalize_bloxroute_error("-32603"), CanonicalInternalServerError)
        assert isinstance(normalize_bloxroute_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_bloxroute_error("NOCODE"), CanonicalError)

    def test_cloud_sdks_known(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_cloud_sdks_error

        assert isinstance(normalize_cloud_sdks_error("unauthorized"), CanonicalAuthenticationError)
        assert isinstance(normalize_cloud_sdks_error("forbidden"), CanonicalAuthorizationError)
        assert isinstance(normalize_cloud_sdks_error("401"), CanonicalAuthenticationError)
        assert isinstance(normalize_cloud_sdks_error(400), CanonicalInvalidRequestError)
        assert isinstance(normalize_cloud_sdks_error("NOCODE"), CanonicalError)

    def test_defillama_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_defillama_error

        assert isinstance(normalize_defillama_error(503), CanonicalServiceUnavailableError)
        assert isinstance(normalize_defillama_error("NOCODE"), CanonicalError)

    def test_footystats_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_footystats_error

        assert isinstance(normalize_footystats_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_footystats_error("NOCODE"), CanonicalError)

    def test_github_known_and_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_github_error

        assert isinstance(normalize_github_error("422"), CanonicalInvalidRequestError)
        assert isinstance(normalize_github_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_github_error("NOCODE"), CanonicalError)

    def test_glassnode_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_glassnode_error

        assert isinstance(normalize_glassnode_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_glassnode_error("NOCODE"), CanonicalError)

    def test_metabet_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_metabet_error

        assert isinstance(normalize_metabet_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_metabet_error("NOCODE"), CanonicalError)

    def test_odds_api_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_odds_api_error

        assert isinstance(normalize_odds_api_error(403), CanonicalAuthorizationError)
        assert isinstance(normalize_odds_api_error("NOCODE"), CanonicalError)

    def test_odds_engine_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_odds_engine_error

        assert isinstance(normalize_odds_engine_error(400), CanonicalInvalidRequestError)
        assert isinstance(normalize_odds_engine_error("NOCODE"), CanonicalError)

    def test_open_meteo_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_open_meteo_error

        assert isinstance(normalize_open_meteo_error(500), CanonicalInternalServerError)
        assert isinstance(normalize_open_meteo_error("NOCODE"), CanonicalError)

    def test_regulatory_prefix_dispatch(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_regulatory_error

        assert isinstance(normalize_regulatory_error("VALIDATION_FAILED"), CanonicalInvalidRequestError)
        assert isinstance(normalize_regulatory_error("AUTH_MISSING"), CanonicalAuthorizationError)
        assert isinstance(normalize_regulatory_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_regulatory_error("NOCODE"), CanonicalError)

    def test_sharpapi_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_sharpapi_error

        assert isinstance(normalize_sharpapi_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_sharpapi_error("NOCODE"), CanonicalError)

    def test_sports_error_keyword_dispatch(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_sports_error

        assert isinstance(normalize_sports_error("market_unavailable"), CanonicalServiceUnavailableError)
        assert isinstance(normalize_sports_error("market_suspended"), CanonicalServiceUnavailableError)
        assert isinstance(normalize_sports_error("market_closed"), CanonicalMarketClosedError)
        assert isinstance(normalize_sports_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_sports_error("NOCODE"), CanonicalError)

    def test_thegraph_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_thegraph_error

        assert isinstance(normalize_thegraph_error(503), CanonicalServiceUnavailableError)
        assert isinstance(normalize_thegraph_error("NOCODE"), CanonicalError)

    def test_transfermarkt_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_transfermarkt_error

        assert isinstance(normalize_transfermarkt_error(400), CanonicalInvalidRequestError)
        assert isinstance(normalize_transfermarkt_error("NOCODE"), CanonicalError)

    def test_understat_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_understat_error

        assert isinstance(normalize_understat_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_understat_error("NOCODE"), CanonicalError)

    def test_yahoo_finance_http_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_yahoo_finance_error

        assert isinstance(normalize_yahoo_finance_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_yahoo_finance_error("NOCODE"), CanonicalError)

    def test_extract_rate_limit_headers_basic(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import extract_rate_limit_headers

        info = extract_rate_limit_headers(
            {
                "Retry-After": "30",
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": "5",
                "X-RateLimit-Reset": "1700000000",
            },
            venue="test",
            endpoint="/api",
        )
        assert info.retry_after == 30.0
        assert info.limit == 100
        assert info.remaining == 5
        assert info.reset == 1700000000.0

    def test_extract_rate_limit_headers_used_fallback(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import extract_rate_limit_headers

        info = extract_rate_limit_headers(
            {"X-RateLimit-Limit": "1000", "X-RateLimit-Used": "200"},
        )
        assert info.limit == 1000
        assert info.remaining == 800

    def test_extract_rate_limit_headers_empty(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import extract_rate_limit_headers

        info = extract_rate_limit_headers({})
        assert info.retry_after is None
        assert info.limit is None

    def test_http_status_helper_coverage(self):
        """Test _from_http_status via venues that use it."""
        from unified_api_contracts.unified_normalised_contracts.normalize.errors import normalize_databento_error

        assert isinstance(normalize_databento_error(400), CanonicalInvalidRequestError)
        assert isinstance(normalize_databento_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_databento_error(403), CanonicalAuthorizationError)
        assert isinstance(normalize_databento_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_databento_error(503), CanonicalServiceUnavailableError)
        assert isinstance(normalize_databento_error(500), CanonicalInternalServerError)
        assert isinstance(normalize_databento_error(502), CanonicalInternalServerError)


# ---------------------------------------------------------------------------
# Rate limits module
# ---------------------------------------------------------------------------


class TestRateLimitExtractors:
    """Smoke test all rate limit extractors."""

    def test_binance_mbx_weight(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.rate_limits import extract_binance_rate_limit

        info = extract_binance_rate_limit({"X-MBX-Used-Weight-1M": "300"})
        assert info.limit == 6000
        assert info.remaining == 5700
        assert info.venue == "binance"

    def test_binance_standard_headers(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.rate_limits import extract_binance_rate_limit

        info = extract_binance_rate_limit({"X-RateLimit-Limit": "100", "X-RateLimit-Remaining": "50"})
        assert info.limit == 100

    def test_bybit_headers(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.rate_limits import extract_bybit_rate_limit

        info = extract_bybit_rate_limit({"X-Bapi-Limit": "200", "X-Bapi-Limit-Status": "150"})
        assert info.limit == 200
        assert info.remaining == 150
        assert info.venue == "bybit"

    def test_okx_headers(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.rate_limits import extract_okx_rate_limit

        info = extract_okx_rate_limit({"Retry-After": "5"})
        assert info.retry_after == 5.0
        assert info.venue == "okx"

    def test_deribit_headers(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.rate_limits import extract_deribit_rate_limit

        info = extract_deribit_rate_limit({"X-RateLimit-Remaining": "10"})
        assert info.remaining == 10
        assert info.venue == "deribit"

    def test_deribit_ws_rate_limit(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.rate_limits import (
            extract_deribit_ws_rate_limit,
        )

        info = extract_deribit_ws_rate_limit({"retry_after": 10})
        assert info.retry_after == 10.0

    def test_deribit_ws_rate_limit_retryafter_alt(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.rate_limits import (
            extract_deribit_ws_rate_limit,
        )

        info = extract_deribit_ws_rate_limit({"retryAfter": "5"})
        assert info.retry_after == 5.0

    def test_deribit_ws_rate_limit_empty(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.rate_limits import (
            extract_deribit_ws_rate_limit,
        )

        info = extract_deribit_ws_rate_limit({})
        assert info.retry_after is None

    def test_coinbase_headers(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.rate_limits import extract_coinbase_rate_limit

        info = extract_coinbase_rate_limit({"Retry-After": "2"})
        assert info.retry_after == 2.0
        assert info.venue == "coinbase"

    def test_hyperliquid_headers(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.rate_limits import (
            extract_hyperliquid_rate_limit,
        )

        info = extract_hyperliquid_rate_limit({})
        assert isinstance(info, RateLimitInfo)
        assert info.venue == "hyperliquid"

    def test_tardis_headers(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.rate_limits import extract_tardis_rate_limit

        info = extract_tardis_rate_limit({"X-RateLimit-Limit": "60"})
        assert info.limit == 60
        assert info.venue == "tardis"

    def test_api_football_rate_limit(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.rate_limits import (
            extract_api_football_rate_limit,
        )

        info = extract_api_football_rate_limit(
            {"X-RateLimit-Requests-Limit": "100", "X-RateLimit-Requests-Remaining": "90"}
        )
        assert info.limit == 100
        assert info.remaining == 90

    def test_github_rate_limit(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.rate_limits import extract_github_rate_limit

        info = extract_github_rate_limit({"X-RateLimit-Limit": "5000", "X-RateLimit-Remaining": "4500"})
        assert info.limit == 5000
        assert info.venue == "github"


# ---------------------------------------------------------------------------
# Connectivity module
# ---------------------------------------------------------------------------


class TestConnectivityNormalizers:
    """Smoke test WS lifecycle normalizers."""

    def test_ws_connect(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.connectivity import normalize_ws_connect

        result = normalize_ws_connect("binance", channel="btcusdt@trade")
        assert result.venue == "binance"
        assert result.event.value == "connect"

    def test_ws_disconnect(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.connectivity import normalize_ws_disconnect

        result = normalize_ws_disconnect("binance", code=1000, reason="normal close")
        assert result.code == 1000

    def test_ws_ping(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.connectivity import normalize_ws_ping

        result = normalize_ws_ping("bybit", latency_ms=5.3)
        assert result.latency_ms == 5.3

    def test_ws_pong(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.connectivity import normalize_ws_pong

        result = normalize_ws_pong("okx")
        assert result.event.value == "pong"

    def test_binance_ws_subscription_success(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.connectivity import (
            normalize_binance_ws_subscription,
        )

        result = normalize_binance_ws_subscription(None, channel="btcusdt@trade")
        assert result.event.value == "subscribe"

    def test_binance_ws_subscription_error(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.connectivity import (
            normalize_binance_ws_subscription,
        )

        result = normalize_binance_ws_subscription("error message")
        assert result.event.value == "error"

    def test_bybit_ws_subscription(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.connectivity import (
            normalize_bybit_ws_subscription,
        )

        assert normalize_bybit_ws_subscription(True, "orderbook.1.BTCUSDT").event.value == "subscribe"
        assert normalize_bybit_ws_subscription(False).event.value == "error"

    def test_okx_ws_subscription(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.connectivity import (
            normalize_okx_ws_subscription,
        )

        assert normalize_okx_ws_subscription("subscribe").event.value == "subscribe"
        assert normalize_okx_ws_subscription("unsubscribe").event.value == "unsubscribe"
        assert normalize_okx_ws_subscription("error").event.value == "error"

    def test_deribit_ws_heartbeat(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.connectivity import (
            normalize_deribit_ws_heartbeat,
        )

        assert normalize_deribit_ws_heartbeat("heartbeat").event.value == "ping"
        assert normalize_deribit_ws_heartbeat("test_request").event.value == "pong"

    def test_coinbase_ws_subscription(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.connectivity import (
            normalize_coinbase_ws_subscription,
        )

        assert normalize_coinbase_ws_subscription("subscriptions").event.value == "subscribe"
        assert normalize_coinbase_ws_subscription("error").event.value == "error"

    def test_hyperliquid_ws_subscription(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.connectivity import (
            normalize_hyperliquid_ws_subscription,
        )

        assert normalize_hyperliquid_ws_subscription("subscribed").event.value == "subscribe"
        assert normalize_hyperliquid_ws_subscription("failed").event.value == "error"

    def test_tardis_ws_subscription(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.connectivity import (
            normalize_tardis_ws_subscription,
        )

        assert normalize_tardis_ws_subscription(True).event.value == "subscribe"
        assert normalize_tardis_ws_subscription(False).event.value == "error"

    def test_aster_ws_subscription(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.connectivity import (
            normalize_aster_ws_subscription,
        )

        assert normalize_aster_ws_subscription("SUBSCRIBE").event.value == "subscribe"
        assert normalize_aster_ws_subscription("UNSUBSCRIBE").event.value == "unsubscribe"

    def test_ws_close_functions(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.connectivity import (
            normalize_aster_ws_close,
            normalize_ibkr_ws_close,
            normalize_kalshi_ws_lifecycle,
            normalize_upbit_ws_close,
        )

        assert normalize_aster_ws_close(1000).event.value == "disconnect"
        assert normalize_ibkr_ws_close(1001, "going away").code == 1001
        assert normalize_upbit_ws_close(1000).event.value == "disconnect"

        opened = normalize_kalshi_ws_lifecycle("opened", "BTC-USD")
        assert opened.event.value in ("connect", "disconnect", "subscribe", "unsubscribe", "error", "reconnect")

    def test_versifi_ws_message(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.connectivity import (
            normalize_versifi_ws_message,
        )

        result = normalize_versifi_ws_message("order_update", "versifi")
        assert result.venue == "versifi"


# ---------------------------------------------------------------------------
# Sides module
# ---------------------------------------------------------------------------


class TestSideNormalizer:
    def test_buy_variants(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.sides import normalize_side

        for raw in ("BUY", "buy", "B", "b", "bid", "long", "Long", "LONG", 1, 0, None):
            assert normalize_side(raw) == "buy"

    def test_sell_variants(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.sides import normalize_side

        for raw in ("SELL", "sell", "S", "s", "ask", "short", "SHORT", 2, "2"):
            assert normalize_side(raw) == "sell"


# ---------------------------------------------------------------------------
# Symbols module
# ---------------------------------------------------------------------------


class TestSymbolNormalizer:
    def test_binance_spot(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.symbols import normalize_symbol

        assert normalize_symbol("binance", "BTCUSDT") == "BTC-USDT"

    def test_binance_perp(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.symbols import normalize_symbol

        assert normalize_symbol("binance", "BTCUSDT_PERP") == "BTC-USDT-PERP"

    def test_binance_unknown_quote(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.symbols import normalize_symbol

        result = normalize_symbol("binance", "XYZABC")
        assert isinstance(result, str)

    def test_okx_swap(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.symbols import normalize_symbol

        assert normalize_symbol("okx", "BTC-USDT-SWAP") == "BTC-USDT-PERP"

    def test_okx_spot(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.symbols import normalize_symbol

        assert normalize_symbol("okx", "BTC-USDT") == "BTC-USDT"

    def test_deribit_perp(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.symbols import normalize_symbol

        assert normalize_symbol("deribit", "BTC-PERPETUAL") == "BTC-PERP"

    def test_deribit_future(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.symbols import normalize_symbol

        result = normalize_symbol("deribit", "BTC-31DEC24")
        assert "BTC" in result

    def test_hyperliquid_perp(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.symbols import normalize_symbol

        assert normalize_symbol("hyperliquid", "BTC") == "BTC-USDC-PERP"

    def test_kraken_legacy(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.symbols import normalize_symbol

        result = normalize_symbol("kraken", "XXBTZUSD")
        assert "BTC" in result

    def test_kraken_futures(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.symbols import normalize_symbol

        result = normalize_symbol("kraken", "PI_XBTUSD")
        assert "BTC" in result or "PERP" in result

    def test_gateio(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.symbols import normalize_symbol

        assert normalize_symbol("gateio", "BTC_USDT") == "BTC-USDT"

    def test_kucoin(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.symbols import normalize_symbol

        assert normalize_symbol("kucoin", "BTC-USDT") == "BTC-USDT"

    def test_bitfinex_t_prefix(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.symbols import normalize_symbol

        assert normalize_symbol("bitfinex", "tBTCUSD") == "BTC-USD"

    def test_dydx_perp(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.symbols import normalize_symbol

        assert normalize_symbol("dydx", "BTC-USD") == "BTC-USD-PERP"
        assert normalize_symbol("dydx", "ETH-USD-PERP") == "ETH-USD-PERP"

    def test_tardis_passthrough(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.symbols import normalize_symbol

        assert normalize_symbol("tardis", "btcusdt") == "BTCUSDT"

    def test_databento_passthrough(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.symbols import normalize_symbol

        assert normalize_symbol("databento", "btcusdt") == "BTCUSDT"

    def test_unknown_venue(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.symbols import normalize_symbol

        assert normalize_symbol("unknown_venue", "btcusdt") == "BTCUSDT"

    def test_bybit(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.symbols import normalize_symbol

        assert normalize_symbol("bybit", "BTCUSDT") == "BTC-USDT"

    def test_coinbase(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.symbols import normalize_symbol

        assert normalize_symbol("coinbase", "BTC-USD") == "BTC-USD"


# ---------------------------------------------------------------------------
# Fees module — covered via import smoke below
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Import smoke — ensure all modules load without error
# ---------------------------------------------------------------------------


class TestModuleImports:
    """Verify every normalize submodule imports cleanly."""

    def test_cefi_extended_imports(self):
        from unified_api_contracts.unified_normalised_contracts.normalize import cefi_extended  # noqa: F401

    def test_connectivity_imports(self):
        from unified_api_contracts.unified_normalised_contracts.normalize import connectivity  # noqa: F401

    def test_derivative_tickers_imports(self):
        from unified_api_contracts.unified_normalised_contracts.normalize import derivative_tickers  # noqa: F401

    def test_errors_imports(self):
        from unified_api_contracts.unified_normalised_contracts.normalize import errors  # noqa: F401

    def test_fees_imports(self):
        from unified_api_contracts.unified_normalised_contracts.normalize import fees  # noqa: F401

    def test_instruments_imports(self):
        from unified_api_contracts.unified_normalised_contracts.normalize import instruments  # noqa: F401

    def test_liquidations_imports(self):
        from unified_api_contracts.unified_normalised_contracts.normalize import liquidations  # noqa: F401

    def test_ohlcv_imports(self):
        from unified_api_contracts.unified_normalised_contracts.normalize import ohlcv  # noqa: F401

    def test_options_imports(self):
        from unified_api_contracts.unified_normalised_contracts.normalize import options  # noqa: F401

    def test_orderbooks_imports(self):
        from unified_api_contracts.unified_normalised_contracts.normalize import orderbooks  # noqa: F401

    def test_orders_fills_imports(self):
        from unified_api_contracts.unified_normalised_contracts.normalize import orders_fills  # noqa: F401

    def test_rate_limits_imports(self):
        from unified_api_contracts.unified_normalised_contracts.normalize import rate_limits  # noqa: F401

    def test_reference_data_imports(self):
        from unified_api_contracts.unified_normalised_contracts.normalize import reference_data  # noqa: F401

    def test_sides_imports(self):
        from unified_api_contracts.unified_normalised_contracts.normalize import sides  # noqa: F401

    def test_sports_imports(self):
        from unified_api_contracts.unified_normalised_contracts.normalize import sports  # noqa: F401

    def test_symbols_imports(self):
        from unified_api_contracts.unified_normalised_contracts.normalize import symbols  # noqa: F401

    def test_tickers_imports(self):
        from unified_api_contracts.unified_normalised_contracts.normalize import tickers  # noqa: F401

    def test_trades_imports(self):
        from unified_api_contracts.unified_normalised_contracts.normalize import trades  # noqa: F401

    def test_versifi_imports(self):
        from unified_api_contracts.unified_normalised_contracts.normalize import versifi  # noqa: F401
