"""Smoke tests for the normalize/ submodule.

Exercises every normalizer with minimal valid inputs to ensure:
1. No import errors
2. Functions are callable and return the expected canonical type
3. Coverage > 0% for all normalize modules (driving total coverage above 70%)
"""

from unified_api_contracts.canonical.errors import (
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
)

# ---------------------------------------------------------------------------
# Errors module — all 52 normalizers
# ---------------------------------------------------------------------------


class TestErrorNormalizersExchanges:
    """Smoke test normalize_<venue>_error functions for exchange venues."""

    def test_binance_known_rate_limit(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_binance_error,
        )

        result = normalize_binance_error("-1003", "too many requests")
        assert isinstance(result, CanonicalRateLimitError)
        assert result.venue == "binance"

    def test_binance_unknown_code(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_binance_error,
        )

        result = normalize_binance_error("9999", "unknown")
        assert isinstance(result, CanonicalError)

    def test_binance_integer_code(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_binance_error,
        )

        result = normalize_binance_error(-1022)
        assert isinstance(result, CanonicalAuthenticationError)

    def test_bybit_known(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_bybit_error,
        )

        assert isinstance(normalize_bybit_error("10006"), CanonicalRateLimitError)
        assert isinstance(normalize_bybit_error("10001"), CanonicalAuthenticationError)
        assert isinstance(normalize_bybit_error("99999"), CanonicalError)

    def test_okx_known(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_okx_error,
        )

        assert isinstance(normalize_okx_error("50011"), CanonicalRateLimitError)
        assert isinstance(normalize_okx_error("51008"), CanonicalInsufficientBalanceError)
        assert isinstance(normalize_okx_error("UNKNOWN"), CanonicalError)

    def test_deribit_known(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_deribit_error,
        )

        assert isinstance(normalize_deribit_error("10028"), CanonicalRateLimitError)
        assert isinstance(normalize_deribit_error("10010"), CanonicalError)  # ContractExpired
        assert isinstance(normalize_deribit_error("00000"), CanonicalError)

    def test_coinbase_known(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_coinbase_error,
        )

        assert isinstance(normalize_coinbase_error("RATE_LIMIT_EXCEEDED"), CanonicalRateLimitError)
        assert isinstance(normalize_coinbase_error("ORDER_REJECTED"), CanonicalOrderRejectedError)
        assert isinstance(normalize_coinbase_error("UNKNOWN_CODE"), CanonicalError)

    def test_hyperliquid_known(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_hyperliquid_error,
        )

        assert isinstance(normalize_hyperliquid_error("RATE_LIMIT"), CanonicalRateLimitError)
        assert isinstance(normalize_hyperliquid_error("ORDER_REJECTED"), CanonicalOrderRejectedError)
        assert isinstance(normalize_hyperliquid_error("UNKNOWN"), CanonicalError)

    def test_ccxt_known(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_ccxt_error,
        )

        assert isinstance(normalize_ccxt_error("RateLimitExceeded"), CanonicalRateLimitError)
        assert isinstance(normalize_ccxt_error("NetworkError"), CanonicalNetworkError)
        assert isinstance(normalize_ccxt_error("UNKNOWN"), CanonicalError)

    def test_tardis_known_and_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_tardis_error,
        )

        assert isinstance(normalize_tardis_error("429"), CanonicalRateLimitError)
        assert isinstance(normalize_tardis_error(400), CanonicalInvalidRequestError)
        assert isinstance(normalize_tardis_error("NONCODE"), CanonicalError)

    def test_upbit_known(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_upbit_error,
        )

        assert isinstance(normalize_upbit_error("too_many_requests"), CanonicalRateLimitError)
        assert isinstance(normalize_upbit_error("invalid_access_key"), CanonicalAuthenticationError)
        assert isinstance(normalize_upbit_error("UNKNOWN"), CanonicalError)

    def test_alchemy_known_and_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_alchemy_error,
        )

        assert isinstance(normalize_alchemy_error("-32600"), CanonicalInvalidRequestError)
        assert isinstance(normalize_alchemy_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_alchemy_error("500"), CanonicalInternalServerError)
        assert isinstance(normalize_alchemy_error("NOCODE"), CanonicalError)

    def test_ibkr_known(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_ibkr_error,
        )

        assert isinstance(normalize_ibkr_error("1100"), CanonicalNetworkError)
        assert isinstance(normalize_ibkr_error("1300"), CanonicalOrderRejectedError)
        assert isinstance(normalize_ibkr_error("9999"), CanonicalError)

    def test_kalshi_known_and_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_kalshi_error,
        )

        assert isinstance(normalize_kalshi_error("MARKET_CLOSED"), CanonicalMarketClosedError)
        assert isinstance(normalize_kalshi_error("429"), CanonicalRateLimitError)
        assert isinstance(normalize_kalshi_error(503), CanonicalServiceUnavailableError)
        assert isinstance(normalize_kalshi_error("NOCODE"), CanonicalError)

    def test_polymarket_known_and_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_polymarket_error,
        )

        assert isinstance(normalize_polymarket_error("RATE_LIMIT"), CanonicalRateLimitError)
        assert isinstance(normalize_polymarket_error("400"), CanonicalInvalidRequestError)
        assert isinstance(normalize_polymarket_error("NOCODE"), CanonicalError)

    def test_betfair_known_and_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_betfair_error,
        )

        assert isinstance(normalize_betfair_error("TOO_MANY_REQUESTS"), CanonicalRateLimitError)
        assert isinstance(normalize_betfair_error("MARKET_CLOSED"), CanonicalMarketClosedError)
        assert isinstance(normalize_betfair_error("INVALID_BET_SIZE"), CanonicalError)
        assert isinstance(normalize_betfair_error("400"), CanonicalInvalidRequestError)
        assert isinstance(normalize_betfair_error("NOCODE"), CanonicalError)

    def test_versifi_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_versifi_error,
        )

        assert isinstance(normalize_versifi_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_versifi_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_versifi_error("NOCODE"), CanonicalError)

    def test_kraken_known_and_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_kraken_error,
        )

        assert isinstance(normalize_kraken_error("EAPI:Rate limit exceeded"), CanonicalRateLimitError)
        assert isinstance(normalize_kraken_error("429"), CanonicalRateLimitError)
        assert isinstance(normalize_kraken_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_kraken_error("UNKNOWN_STR"), CanonicalError)

    def test_kucoin_known_and_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_kucoin_error,
        )

        assert isinstance(normalize_kucoin_error("401000"), CanonicalRateLimitError)
        assert isinstance(normalize_kucoin_error("200004"), CanonicalInsufficientBalanceError)
        assert isinstance(normalize_kucoin_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_kucoin_error("NOCODE"), CanonicalError)

    def test_gateio_known_and_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_gateio_error,
        )

        assert isinstance(normalize_gateio_error("RATE_LIMIT"), CanonicalRateLimitError)
        assert isinstance(normalize_gateio_error("BALANCE_NOT_ENOUGH"), CanonicalInsufficientBalanceError)
        assert isinstance(normalize_gateio_error(500), CanonicalInternalServerError)
        assert isinstance(normalize_gateio_error("NOCODE"), CanonicalError)

    def test_bitfinex_known_and_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_bitfinex_error,
        )

        assert isinstance(normalize_bitfinex_error("ERR_RATE_LIMIT"), CanonicalRateLimitError)
        assert isinstance(normalize_bitfinex_error("ERR_NOT_ENOUGH_BALANCE"), CanonicalInsufficientBalanceError)
        assert isinstance(normalize_bitfinex_error(500), CanonicalInternalServerError)
        assert isinstance(normalize_bitfinex_error("NOCODE"), CanonicalError)

    def test_bitstamp_known_and_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_bitstamp_error,
        )

        assert isinstance(normalize_bitstamp_error("API0002"), CanonicalAuthenticationError)
        assert isinstance(normalize_bitstamp_error("429"), CanonicalRateLimitError)
        assert isinstance(normalize_bitstamp_error(403), CanonicalAuthorizationError)
        assert isinstance(normalize_bitstamp_error("NOCODE"), CanonicalError)

    def test_mexc_known_and_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_mexc_error,
        )

        assert isinstance(normalize_mexc_error("10072"), CanonicalAuthenticationError)
        assert isinstance(normalize_mexc_error("30004"), CanonicalInsufficientBalanceError)
        assert isinstance(normalize_mexc_error(500), CanonicalInternalServerError)
        assert isinstance(normalize_mexc_error("NOCODE"), CanonicalError)

    def test_huobi_known_and_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_huobi_error,
        )

        assert isinstance(normalize_huobi_error("too-many-requests"), CanonicalRateLimitError)
        assert isinstance(normalize_huobi_error("api-signature-not-valid"), CanonicalAuthenticationError)
        assert isinstance(normalize_huobi_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_huobi_error("NOCODE"), CanonicalError)

    def test_bitget_known_and_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_bitget_error,
        )

        assert isinstance(normalize_bitget_error("40018"), CanonicalRateLimitError)
        assert isinstance(normalize_bitget_error("40001"), CanonicalAuthenticationError)
        assert isinstance(normalize_bitget_error(500), CanonicalInternalServerError)
        assert isinstance(normalize_bitget_error("NOCODE"), CanonicalError)

    def test_dydx_known_and_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_dydx_error,
        )

        assert isinstance(normalize_dydx_error("RESOURCE_EXHAUSTED"), CanonicalRateLimitError)
        assert isinstance(normalize_dydx_error("UNAUTHENTICATED"), CanonicalAuthenticationError)
        assert isinstance(normalize_dydx_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_dydx_error("NOCODE"), CanonicalError)

    def test_databento_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_databento_error,
        )

        assert isinstance(normalize_databento_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_databento_error("429"), CanonicalRateLimitError)
        assert isinstance(normalize_databento_error("NOCODE"), CanonicalError)

    def test_aster_known_and_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_aster_error,
        )

        assert isinstance(normalize_aster_error("RATE_LIMIT_EXCEEDED"), CanonicalRateLimitError)
        assert isinstance(normalize_aster_error("MARKET_CLOSED"), CanonicalMarketClosedError)
        assert isinstance(normalize_aster_error(503), CanonicalServiceUnavailableError)
        assert isinstance(normalize_aster_error("NOCODE"), CanonicalError)

    def test_fix_known(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_fix_error,
        )

        assert isinstance(normalize_fix_error("0"), CanonicalOrderRejectedError)
        assert isinstance(normalize_fix_error("SESSION_REJECTED"), CanonicalAuthenticationError)
        assert isinstance(normalize_fix_error("99"), CanonicalError)


class TestErrorNormalizersProviders:
    """Smoke test normalize_<venue>_error functions for prime broker and data providers."""

    def test_prime_broker_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_prime_broker_error,
        )

        assert isinstance(normalize_prime_broker_error(400), CanonicalInvalidRequestError)
        assert isinstance(normalize_prime_broker_error("NOCODE"), CanonicalError)

    def test_nautilus_known(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_nautilus_error,
        )

        assert isinstance(normalize_nautilus_error("ORDER_DENIED"), CanonicalOrderRejectedError)
        assert isinstance(normalize_nautilus_error("VENUE_NOT_AVAILABLE"), CanonicalServiceUnavailableError)
        assert isinstance(normalize_nautilus_error("UNKNOWN"), CanonicalError)

    def test_betdaq_known_and_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_betdaq_error,
        )

        assert isinstance(normalize_betdaq_error("1001"), CanonicalRateLimitError)
        assert isinstance(normalize_betdaq_error("40"), CanonicalInsufficientBalanceError)
        assert isinstance(normalize_betdaq_error(503), CanonicalServiceUnavailableError)
        assert isinstance(normalize_betdaq_error("NOCODE"), CanonicalError)

    def test_smarkets_known_and_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_smarkets_error,
        )

        assert isinstance(normalize_smarkets_error("too_many_requests"), CanonicalRateLimitError)
        assert isinstance(normalize_smarkets_error("unauthorized"), CanonicalAuthenticationError)
        assert isinstance(normalize_smarkets_error(500), CanonicalInternalServerError)
        assert isinstance(normalize_smarkets_error("NOCODE"), CanonicalError)

    def test_pinnacle_known_and_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_pinnacle_error,
        )

        assert isinstance(normalize_pinnacle_error("INSUFFICIENT_FUNDS"), CanonicalInsufficientBalanceError)
        assert isinstance(normalize_pinnacle_error("LINE_CHANGED"), CanonicalOrderRejectedError)
        assert isinstance(normalize_pinnacle_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_pinnacle_error("NOCODE"), CanonicalError)

    def test_manifold_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_manifold_error,
        )

        assert isinstance(normalize_manifold_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_manifold_error("NOCODE"), CanonicalError)

    def test_api_football_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_api_football_error,
        )

        assert isinstance(normalize_api_football_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_api_football_error("NOCODE"), CanonicalError)

    def test_arkham_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_arkham_error,
        )

        assert isinstance(normalize_arkham_error(403), CanonicalAuthorizationError)
        assert isinstance(normalize_arkham_error("NOCODE"), CanonicalError)

    def test_bloxroute_known_and_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_bloxroute_error,
        )

        assert isinstance(normalize_bloxroute_error("-32600"), CanonicalInvalidRequestError)
        assert isinstance(normalize_bloxroute_error("-32603"), CanonicalInternalServerError)
        assert isinstance(normalize_bloxroute_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_bloxroute_error("NOCODE"), CanonicalError)

    def test_cloud_sdks_known(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_cloud_sdks_error,
        )

        assert isinstance(normalize_cloud_sdks_error("unauthorized"), CanonicalAuthenticationError)
        assert isinstance(normalize_cloud_sdks_error("forbidden"), CanonicalAuthorizationError)
        assert isinstance(normalize_cloud_sdks_error("401"), CanonicalAuthenticationError)
        assert isinstance(normalize_cloud_sdks_error(400), CanonicalInvalidRequestError)
        assert isinstance(normalize_cloud_sdks_error("NOCODE"), CanonicalError)

    def test_defillama_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_defillama_error,
        )

        assert isinstance(normalize_defillama_error(503), CanonicalServiceUnavailableError)
        assert isinstance(normalize_defillama_error("NOCODE"), CanonicalError)

    def test_footystats_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_footystats_error,
        )

        assert isinstance(normalize_footystats_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_footystats_error("NOCODE"), CanonicalError)

    def test_github_known_and_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_github_error,
        )

        assert isinstance(normalize_github_error("422"), CanonicalInvalidRequestError)
        assert isinstance(normalize_github_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_github_error("NOCODE"), CanonicalError)

    def test_glassnode_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_glassnode_error,
        )

        assert isinstance(normalize_glassnode_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_glassnode_error("NOCODE"), CanonicalError)

    def test_metabet_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_metabet_error,
        )

        assert isinstance(normalize_metabet_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_metabet_error("NOCODE"), CanonicalError)

    def test_odds_api_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_odds_api_error,
        )

        assert isinstance(normalize_odds_api_error(403), CanonicalAuthorizationError)
        assert isinstance(normalize_odds_api_error("NOCODE"), CanonicalError)

    def test_odds_engine_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_odds_engine_error,
        )

        assert isinstance(normalize_odds_engine_error(400), CanonicalInvalidRequestError)
        assert isinstance(normalize_odds_engine_error("NOCODE"), CanonicalError)

    def test_open_meteo_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_open_meteo_error,
        )

        assert isinstance(normalize_open_meteo_error(500), CanonicalInternalServerError)
        assert isinstance(normalize_open_meteo_error("NOCODE"), CanonicalError)

    def test_regulatory_prefix_dispatch(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_regulatory_error,
        )

        assert isinstance(normalize_regulatory_error("VALIDATION_FAILED"), CanonicalInvalidRequestError)
        assert isinstance(normalize_regulatory_error("AUTH_MISSING"), CanonicalAuthorizationError)
        assert isinstance(normalize_regulatory_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_regulatory_error("NOCODE"), CanonicalError)

    def test_sharpapi_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_sharpapi_error,
        )

        assert isinstance(normalize_sharpapi_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_sharpapi_error("NOCODE"), CanonicalError)

    def test_sports_error_keyword_dispatch(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_sports_error,
        )

        assert isinstance(normalize_sports_error("market_unavailable"), CanonicalServiceUnavailableError)
        assert isinstance(normalize_sports_error("market_suspended"), CanonicalServiceUnavailableError)
        assert isinstance(normalize_sports_error("market_closed"), CanonicalMarketClosedError)
        assert isinstance(normalize_sports_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_sports_error("NOCODE"), CanonicalError)

    def test_thegraph_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_thegraph_error,
        )

        assert isinstance(normalize_thegraph_error(503), CanonicalServiceUnavailableError)
        assert isinstance(normalize_thegraph_error("NOCODE"), CanonicalError)

    def test_transfermarkt_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_transfermarkt_error,
        )

        assert isinstance(normalize_transfermarkt_error(400), CanonicalInvalidRequestError)
        assert isinstance(normalize_transfermarkt_error("NOCODE"), CanonicalError)

    def test_understat_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_understat_error,
        )

        assert isinstance(normalize_understat_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_understat_error("NOCODE"), CanonicalError)

    def test_yahoo_finance_http_fallback(self):
        from unified_api_contracts.normalize_utils.errors import (
            normalize_yahoo_finance_error,
        )

        assert isinstance(normalize_yahoo_finance_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_yahoo_finance_error("NOCODE"), CanonicalError)

    def test_extract_rate_limit_headers_basic(self):
        from unified_api_contracts.normalize_utils.errors import (
            extract_rate_limit_headers,
        )

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
        from unified_api_contracts.normalize_utils.errors import (
            extract_rate_limit_headers,
        )

        info = extract_rate_limit_headers(
            {"X-RateLimit-Limit": "1000", "X-RateLimit-Used": "200"},
        )
        assert info.limit == 1000
        assert info.remaining == 800

    def test_extract_rate_limit_headers_empty(self):
        from unified_api_contracts.normalize_utils.errors import (
            extract_rate_limit_headers,
        )

        info = extract_rate_limit_headers({})
        assert info.retry_after is None
        assert info.limit is None

    def test_http_status_helper_coverage(self):
        """Test _from_http_status via venues that use it."""
        from unified_api_contracts.normalize_utils.errors import (
            normalize_databento_error,
        )

        assert isinstance(normalize_databento_error(400), CanonicalInvalidRequestError)
        assert isinstance(normalize_databento_error(401), CanonicalAuthenticationError)
        assert isinstance(normalize_databento_error(403), CanonicalAuthorizationError)
        assert isinstance(normalize_databento_error(429), CanonicalRateLimitError)
        assert isinstance(normalize_databento_error(503), CanonicalServiceUnavailableError)
        assert isinstance(normalize_databento_error(500), CanonicalInternalServerError)
        assert isinstance(normalize_databento_error(502), CanonicalInternalServerError)
