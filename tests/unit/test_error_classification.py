"""Unit tests for ErrorAction and venue error classify() methods."""

from unified_api_contracts.shared import ErrorAction


class TestErrorAction:
    """Test ErrorAction enum."""

    def test_error_action_values(self):
        """ErrorAction has expected values."""
        assert ErrorAction.RETRY.value == "retry"
        assert ErrorAction.RECONNECT.value == "reconnect"
        assert ErrorAction.FAIL.value == "fail"


class TestBinanceClassify:
    """Test BinanceError.classify()."""

    def test_retry_codes(self):
        """Transient errors map to RETRY."""
        from unified_api_contracts.binance.order_schemas import BinanceError

        for code in (-1000, -1001, -1003, -1006, -1007, -1008):
            assert BinanceError.classify(code) == ErrorAction.RETRY

    def test_reconnect_code(self):
        """Invalid listen key maps to RECONNECT."""
        from unified_api_contracts.binance.order_schemas import BinanceError

        assert BinanceError.classify(-1125) == ErrorAction.RECONNECT

    def test_ip_ban_retry(self):
        """IP ban (418) maps to RETRY."""
        from unified_api_contracts.binance.order_schemas import BinanceError

        assert BinanceError.classify(418) == ErrorAction.RETRY

    def test_fail_hard(self):
        """Unknown codes map to FAIL."""
        from unified_api_contracts.binance.order_schemas import BinanceError

        assert BinanceError.classify(-100) == ErrorAction.FAIL
        assert BinanceError.classify(400) == ErrorAction.FAIL


class TestBybitClassify:
    """Test BybitError.classify()."""

    def test_retry_codes(self):
        """Transient errors map to RETRY."""
        from unified_api_contracts.bybit.schemas import BybitError

        for code in (10000, 10016, 20003, 10429, 429):
            assert BybitError.classify(code) == ErrorAction.RETRY

    def test_reconnect_code(self):
        """WS restart maps to RECONNECT."""
        from unified_api_contracts.bybit.schemas import BybitError

        assert BybitError.classify(10019) == ErrorAction.RECONNECT

    def test_fail_hard(self):
        """Unknown codes map to FAIL."""
        from unified_api_contracts.bybit.schemas import BybitError

        assert BybitError.classify(10001) == ErrorAction.FAIL


class TestOKXClassify:
    """Test OKXError.classify()."""

    def test_retry_codes(self):
        """Transient errors map to RETRY."""
        from unified_api_contracts.okx.schemas import OKXError

        for code in ("50011", "50026", "50061"):
            assert OKXError.classify(code) == ErrorAction.RETRY

    def test_reconnect_code(self):
        """Connection upgrading maps to RECONNECT."""
        from unified_api_contracts.okx.schemas import OKXError

        assert OKXError.classify("64008") == ErrorAction.RECONNECT

    def test_fail_hard(self):
        """Unknown codes map to FAIL."""
        from unified_api_contracts.okx.schemas import OKXError

        assert OKXError.classify("50000") == ErrorAction.FAIL
        assert OKXError.classify(50000) == ErrorAction.FAIL


class TestDeribitClassify:
    """Test DeribitError.classify()."""

    def test_retry_codes(self):
        """Transient errors map to RETRY."""
        from unified_api_contracts.deribit.schemas import DeribitError

        assert DeribitError.classify(10028) == ErrorAction.RETRY
        assert DeribitError.classify(10040) == ErrorAction.RETRY

    def test_reconnect_codes(self):
        """Invalid/revoked token maps to RECONNECT."""
        from unified_api_contracts.deribit.schemas import DeribitError

        assert DeribitError.classify(13009) == ErrorAction.RECONNECT
        assert DeribitError.classify(13010) == ErrorAction.RECONNECT

    def test_fail_hard(self):
        """Unknown codes map to FAIL."""
        from unified_api_contracts.deribit.schemas import DeribitError

        assert DeribitError.classify(10000) == ErrorAction.FAIL


class TestCoinbaseClassify:
    """Test CoinbaseError.classify()."""

    def test_http_500_retry(self):
        """HTTP 5xx maps to RETRY."""
        from unified_api_contracts.coinbase.schemas import CoinbaseError

        assert CoinbaseError.classify("UNKNOWN", 500) == ErrorAction.RETRY
        assert CoinbaseError.classify("UNKNOWN", 503) == ErrorAction.RETRY

    def test_retry_types(self):
        """Internal/temporary errors map to RETRY."""
        from unified_api_contracts.coinbase.schemas import CoinbaseError

        assert CoinbaseError.classify("INTERNAL_SERVICE_ERROR") == ErrorAction.RETRY
        assert CoinbaseError.classify("TEMPORARILY_UNAVAILABLE") == ErrorAction.RETRY

    def test_fail_hard(self):
        """Unknown types map to FAIL."""
        from unified_api_contracts.coinbase.schemas import CoinbaseError

        assert CoinbaseError.classify("INVALID_REQUEST") == ErrorAction.FAIL


class TestHyperliquidClassify:
    """Test HyperliquidError.classify()."""

    def test_http_500_retry(self):
        """HTTP 5xx maps to RETRY."""
        from unified_api_contracts.hyperliquid.schemas import HyperliquidError

        assert HyperliquidError.classify(http_status=500) == ErrorAction.RETRY
        assert HyperliquidError.classify(http_status=503) == ErrorAction.RETRY

    def test_fail_hard(self):
        """4xx or None maps to FAIL."""
        from unified_api_contracts.hyperliquid.schemas import HyperliquidError

        assert HyperliquidError.classify(http_status=400) == ErrorAction.FAIL
        assert HyperliquidError.classify() == ErrorAction.FAIL


class TestAsterClassify:
    """Test AsterError.classify()."""

    def test_retry_codes(self):
        """Transient errors map to RETRY."""
        from unified_api_contracts.aster.schemas import AsterError

        assert AsterError.classify(-1000) == ErrorAction.RETRY
        assert AsterError.classify(429) == ErrorAction.RETRY
        assert AsterError.classify(503) == ErrorAction.RETRY

    def test_fail_hard(self):
        """Unknown codes map to FAIL."""
        from unified_api_contracts.aster.schemas import AsterError

        assert AsterError.classify(-200) == ErrorAction.FAIL


class TestDatabentoClassify:
    """Test DatabentoError.classify()."""

    def test_server_error_retry(self):
        """BentoServerError maps to RETRY."""
        from unified_api_contracts.databento.schemas import DatabentoError

        assert DatabentoError.classify("BentoServerError") == ErrorAction.RETRY

    def test_status_500_retry(self):
        """HTTP 5xx maps to RETRY."""
        from unified_api_contracts.databento.schemas import DatabentoError

        assert DatabentoError.classify("BentoHttpError", 500) == ErrorAction.RETRY

    def test_fail_hard(self):
        """BentoClientError maps to FAIL."""
        from unified_api_contracts.databento.schemas import DatabentoError

        assert DatabentoError.classify("BentoClientError") == ErrorAction.FAIL
        assert DatabentoError.classify("BentoClientError", 400) == ErrorAction.FAIL


class TestTardisClassify:
    """Test TardisError.classify()."""

    def test_rate_limit_retry(self):
        """429 and rate error map to RETRY."""
        from unified_api_contracts.tardis.schemas import TardisError

        assert TardisError.classify(code=429) == ErrorAction.RETRY
        assert TardisError.classify(error="rate limit exceeded") == ErrorAction.RETRY

    def test_server_error_retry(self):
        """5xx maps to RETRY."""
        from unified_api_contracts.tardis.schemas import TardisError

        assert TardisError.classify(code=500) == ErrorAction.RETRY

    def test_unauthorized_fail(self):
        """401 maps to FAIL."""
        from unified_api_contracts.tardis.schemas import TardisError

        assert TardisError.classify(code=401) == ErrorAction.FAIL


class TestAlchemyClassify:
    """Test AlchemyError.classify()."""

    def test_http_500_retry(self):
        """HTTP 5xx maps to RETRY."""
        from unified_api_contracts.alchemy.schemas import AlchemyError

        assert AlchemyError.classify(http_status=500) == ErrorAction.RETRY

    def test_429_retry(self):
        """429 maps to RETRY."""
        from unified_api_contracts.alchemy.schemas import AlchemyError

        assert AlchemyError.classify(http_status=429) == ErrorAction.RETRY

    def test_invalid_request_fail(self):
        """-32600 maps to FAIL."""
        from unified_api_contracts.alchemy.schemas import AlchemyError

        assert AlchemyError.classify(code=-32600) == ErrorAction.FAIL


class TestYahooClassify:
    """Test YahooError.classify()."""

    def test_429_retry(self):
        """429 maps to RETRY."""
        from unified_api_contracts.yahoo_finance.schemas import YahooError

        assert YahooError.classify(http_status=429) == ErrorAction.RETRY
        assert YahooError.classify(code="RATE_LIMIT_EXCEEDED") == ErrorAction.RETRY

    def test_fail_hard(self):
        """Unknown maps to FAIL."""
        from unified_api_contracts.yahoo_finance.schemas import YahooError

        assert YahooError.classify() == ErrorAction.FAIL


class TestUpbitClassify:
    """Test UpbitError.classify()."""

    def test_rate_limit_retry(self):
        """too_many_requests maps to RETRY."""
        from unified_api_contracts.upbit.schemas import UpbitError

        assert UpbitError.classify(error_key="too_many_requests") == ErrorAction.RETRY
        assert UpbitError.classify(http_status=429) == ErrorAction.RETRY

    def test_invalid_key_fail(self):
        """invalid_access_key maps to FAIL."""
        from unified_api_contracts.upbit.schemas import UpbitError

        assert UpbitError.classify(error_key="invalid_access_key") == ErrorAction.FAIL


class TestIBKRClassify:
    """Test IBKRError.classify()."""

    def test_retry_codes(self):
        """Transient errors map to RETRY."""
        from unified_api_contracts.ibkr.schemas import IBKRError

        assert IBKRError.classify(100) == ErrorAction.RETRY

    def test_reconnect_code(self):
        """1100 maps to RECONNECT."""
        from unified_api_contracts.ibkr.schemas import IBKRError

        assert IBKRError.classify(1100) == ErrorAction.RECONNECT

    def test_order_reject_fail(self):
        """13xx order rejections map to FAIL."""
        from unified_api_contracts.ibkr.schemas import IBKRError

        assert IBKRError.classify(1300) == ErrorAction.FAIL


class TestTheGraphClassify:
    """Test GraphQLError.classify()."""

    def test_429_retry(self):
        """429 maps to RETRY."""
        from unified_api_contracts.thegraph.schemas import GraphQLError

        assert GraphQLError.classify(http_status=429) == ErrorAction.RETRY

    def test_not_found_fail(self):
        """not found message maps to FAIL."""
        from unified_api_contracts.thegraph.schemas import GraphQLError

        assert GraphQLError.classify(message="Subgraph not found") == ErrorAction.FAIL


class TestCcxtClassify:
    """Test CcxtErrorPayload.classify()."""

    def test_retry_types(self):
        """RateLimitExceeded, ExchangeNotAvailable map to RETRY."""
        from unified_api_contracts.ccxt.schemas import CcxtErrorPayload

        assert CcxtErrorPayload.classify(code="RateLimitExceeded") == ErrorAction.RETRY
        assert CcxtErrorPayload.classify(code="ExchangeNotAvailable") == ErrorAction.RETRY

    def test_fail_hard(self):
        """Unknown maps to FAIL."""
        from unified_api_contracts.ccxt.schemas import CcxtErrorPayload

        assert CcxtErrorPayload.classify(code="InvalidOrder") == ErrorAction.FAIL
