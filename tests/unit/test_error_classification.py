"""Unit tests for ErrorAction and venue error classify() methods."""

from unified_api_contracts.shared import ErrorAction


class TestErrorAction:
    """Test ErrorAction enum."""

    def test_error_action_values(self):
        """ErrorAction has expected values."""
        assert ErrorAction.RETRY_WITH_BACKOFF.value == "retry_backoff"
        assert ErrorAction.RECONNECT.value == "reconnect"
        assert ErrorAction.FAIL_HARD.value == "fail_hard"
        assert ErrorAction.IGNORE.value == "ignore"


class TestBinanceClassify:
    """Test BinanceError.classify()."""

    def test_retry_codes(self):
        """Transient errors map to RETRY_WITH_BACKOFF."""
        from unified_api_contracts.binance.schemas import BinanceError

        for code in (-1000, -1001, -1003, -1006, -1007, -1008):
            assert BinanceError.classify(code) == ErrorAction.RETRY_WITH_BACKOFF

    def test_reconnect_code(self):
        """Invalid listen key maps to RECONNECT."""
        from unified_api_contracts.binance.schemas import BinanceError

        assert BinanceError.classify(-1125) == ErrorAction.RECONNECT

    def test_ip_ban_retry(self):
        """IP ban (418) maps to RETRY_WITH_BACKOFF."""
        from unified_api_contracts.binance.schemas import BinanceError

        assert BinanceError.classify(418) == ErrorAction.RETRY_WITH_BACKOFF

    def test_fail_hard(self):
        """Unknown codes map to FAIL_HARD."""
        from unified_api_contracts.binance.schemas import BinanceError

        assert BinanceError.classify(-100) == ErrorAction.FAIL_HARD
        assert BinanceError.classify(400) == ErrorAction.FAIL_HARD


class TestBybitClassify:
    """Test BybitError.classify()."""

    def test_retry_codes(self):
        """Transient errors map to RETRY_WITH_BACKOFF."""
        from unified_api_contracts.bybit.schemas import BybitError

        for code in (10000, 10016, 20003, 10429, 429):
            assert BybitError.classify(code) == ErrorAction.RETRY_WITH_BACKOFF

    def test_reconnect_code(self):
        """WS restart maps to RECONNECT."""
        from unified_api_contracts.bybit.schemas import BybitError

        assert BybitError.classify(10019) == ErrorAction.RECONNECT

    def test_fail_hard(self):
        """Unknown codes map to FAIL_HARD."""
        from unified_api_contracts.bybit.schemas import BybitError

        assert BybitError.classify(10001) == ErrorAction.FAIL_HARD


class TestOKXClassify:
    """Test OKXError.classify()."""

    def test_retry_codes(self):
        """Transient errors map to RETRY_WITH_BACKOFF."""
        from unified_api_contracts.okx.schemas import OKXError

        for code in ("50011", "50026", "50061"):
            assert OKXError.classify(code) == ErrorAction.RETRY_WITH_BACKOFF

    def test_reconnect_code(self):
        """Connection upgrading maps to RECONNECT."""
        from unified_api_contracts.okx.schemas import OKXError

        assert OKXError.classify("64008") == ErrorAction.RECONNECT

    def test_fail_hard(self):
        """Unknown codes map to FAIL_HARD."""
        from unified_api_contracts.okx.schemas import OKXError

        assert OKXError.classify("50000") == ErrorAction.FAIL_HARD
        assert OKXError.classify(50000) == ErrorAction.FAIL_HARD


class TestDeribitClassify:
    """Test DeribitError.classify()."""

    def test_retry_codes(self):
        """Transient errors map to RETRY_WITH_BACKOFF."""
        from unified_api_contracts.deribit.schemas import DeribitError

        assert DeribitError.classify(10028) == ErrorAction.RETRY_WITH_BACKOFF
        assert DeribitError.classify(10040) == ErrorAction.RETRY_WITH_BACKOFF

    def test_reconnect_codes(self):
        """Invalid/revoked token maps to RECONNECT."""
        from unified_api_contracts.deribit.schemas import DeribitError

        assert DeribitError.classify(13009) == ErrorAction.RECONNECT
        assert DeribitError.classify(13010) == ErrorAction.RECONNECT

    def test_fail_hard(self):
        """Unknown codes map to FAIL_HARD."""
        from unified_api_contracts.deribit.schemas import DeribitError

        assert DeribitError.classify(10000) == ErrorAction.FAIL_HARD


class TestCoinbaseClassify:
    """Test CoinbaseError.classify()."""

    def test_http_500_retry(self):
        """HTTP 5xx maps to RETRY_WITH_BACKOFF."""
        from unified_api_contracts.coinbase.schemas import CoinbaseError

        assert CoinbaseError.classify("UNKNOWN", 500) == ErrorAction.RETRY_WITH_BACKOFF
        assert CoinbaseError.classify("UNKNOWN", 503) == ErrorAction.RETRY_WITH_BACKOFF

    def test_retry_types(self):
        """Internal/temporary errors map to RETRY_WITH_BACKOFF."""
        from unified_api_contracts.coinbase.schemas import CoinbaseError

        assert CoinbaseError.classify("INTERNAL_SERVICE_ERROR") == ErrorAction.RETRY_WITH_BACKOFF
        assert CoinbaseError.classify("TEMPORARILY_UNAVAILABLE") == ErrorAction.RETRY_WITH_BACKOFF

    def test_fail_hard(self):
        """Unknown types map to FAIL_HARD."""
        from unified_api_contracts.coinbase.schemas import CoinbaseError

        assert CoinbaseError.classify("INVALID_REQUEST") == ErrorAction.FAIL_HARD


class TestHyperliquidClassify:
    """Test HyperliquidError.classify()."""

    def test_http_500_retry(self):
        """HTTP 5xx maps to RETRY_WITH_BACKOFF."""
        from unified_api_contracts.hyperliquid.schemas import HyperliquidError

        assert HyperliquidError.classify(http_status=500) == ErrorAction.RETRY_WITH_BACKOFF
        assert HyperliquidError.classify(http_status=503) == ErrorAction.RETRY_WITH_BACKOFF

    def test_fail_hard(self):
        """4xx or None maps to FAIL_HARD."""
        from unified_api_contracts.hyperliquid.schemas import HyperliquidError

        assert HyperliquidError.classify(http_status=400) == ErrorAction.FAIL_HARD
        assert HyperliquidError.classify() == ErrorAction.FAIL_HARD


class TestAsterClassify:
    """Test AsterError.classify()."""

    def test_retry_codes(self):
        """Transient errors map to RETRY_WITH_BACKOFF."""
        from unified_api_contracts.aster.schemas import AsterError

        assert AsterError.classify(-1000) == ErrorAction.RETRY_WITH_BACKOFF
        assert AsterError.classify(429) == ErrorAction.RETRY_WITH_BACKOFF
        assert AsterError.classify(503) == ErrorAction.RETRY_WITH_BACKOFF

    def test_fail_hard(self):
        """Unknown codes map to FAIL_HARD."""
        from unified_api_contracts.aster.schemas import AsterError

        assert AsterError.classify(-200) == ErrorAction.FAIL_HARD


class TestDatabentoClassify:
    """Test DatabentoError.classify()."""

    def test_server_error_retry(self):
        """BentoServerError maps to RETRY_WITH_BACKOFF."""
        from unified_api_contracts.databento.schemas import DatabentoError

        assert DatabentoError.classify("BentoServerError") == ErrorAction.RETRY_WITH_BACKOFF

    def test_status_500_retry(self):
        """HTTP 5xx maps to RETRY_WITH_BACKOFF."""
        from unified_api_contracts.databento.schemas import DatabentoError

        assert DatabentoError.classify("BentoHttpError", 500) == ErrorAction.RETRY_WITH_BACKOFF

    def test_fail_hard(self):
        """BentoClientError maps to FAIL_HARD."""
        from unified_api_contracts.databento.schemas import DatabentoError

        assert DatabentoError.classify("BentoClientError") == ErrorAction.FAIL_HARD
        assert DatabentoError.classify("BentoClientError", 400) == ErrorAction.FAIL_HARD


class TestTardisClassify:
    """Test TardisError.classify()."""

    def test_rate_limit_retry(self):
        """429 and rate error map to RETRY_WITH_BACKOFF."""
        from unified_api_contracts.tardis.schemas import TardisError

        assert TardisError.classify(code=429) == ErrorAction.RETRY_WITH_BACKOFF
        assert TardisError.classify(error="rate limit exceeded") == ErrorAction.RETRY_WITH_BACKOFF

    def test_server_error_retry(self):
        """5xx maps to RETRY_WITH_BACKOFF."""
        from unified_api_contracts.tardis.schemas import TardisError

        assert TardisError.classify(code=500) == ErrorAction.RETRY_WITH_BACKOFF

    def test_unauthorized_fail(self):
        """401 maps to FAIL_HARD."""
        from unified_api_contracts.tardis.schemas import TardisError

        assert TardisError.classify(code=401) == ErrorAction.FAIL_HARD


class TestAlchemyClassify:
    """Test AlchemyError.classify()."""

    def test_http_500_retry(self):
        """HTTP 5xx maps to RETRY_WITH_BACKOFF."""
        from unified_api_contracts.alchemy.schemas import AlchemyError

        assert AlchemyError.classify(http_status=500) == ErrorAction.RETRY_WITH_BACKOFF

    def test_429_retry(self):
        """429 maps to RETRY_WITH_BACKOFF."""
        from unified_api_contracts.alchemy.schemas import AlchemyError

        assert AlchemyError.classify(http_status=429) == ErrorAction.RETRY_WITH_BACKOFF

    def test_invalid_request_fail(self):
        """-32600 maps to FAIL_HARD."""
        from unified_api_contracts.alchemy.schemas import AlchemyError

        assert AlchemyError.classify(code=-32600) == ErrorAction.FAIL_HARD


class TestYahooClassify:
    """Test YahooError.classify()."""

    def test_429_retry(self):
        """429 maps to RETRY_WITH_BACKOFF."""
        from unified_api_contracts.yahoo_finance.schemas import YahooError

        assert YahooError.classify(http_status=429) == ErrorAction.RETRY_WITH_BACKOFF
        assert YahooError.classify(code="RATE_LIMIT_EXCEEDED") == ErrorAction.RETRY_WITH_BACKOFF

    def test_fail_hard(self):
        """Unknown maps to FAIL_HARD."""
        from unified_api_contracts.yahoo_finance.schemas import YahooError

        assert YahooError.classify() == ErrorAction.FAIL_HARD


class TestUpbitClassify:
    """Test UpbitError.classify()."""

    def test_rate_limit_retry(self):
        """too_many_requests maps to RETRY_WITH_BACKOFF."""
        from unified_api_contracts.upbit.schemas import UpbitError

        assert UpbitError.classify(error_key="too_many_requests") == ErrorAction.RETRY_WITH_BACKOFF
        assert UpbitError.classify(http_status=429) == ErrorAction.RETRY_WITH_BACKOFF

    def test_invalid_key_fail(self):
        """invalid_access_key maps to FAIL_HARD."""
        from unified_api_contracts.upbit.schemas import UpbitError

        assert UpbitError.classify(error_key="invalid_access_key") == ErrorAction.FAIL_HARD


class TestIBKRClassify:
    """Test IBKRError.classify()."""

    def test_retry_codes(self):
        """Transient errors map to RETRY_WITH_BACKOFF."""
        from unified_api_contracts.ibkr.schemas import IBKRError

        assert IBKRError.classify(100) == ErrorAction.RETRY_WITH_BACKOFF

    def test_reconnect_code(self):
        """1100 maps to RECONNECT."""
        from unified_api_contracts.ibkr.schemas import IBKRError

        assert IBKRError.classify(1100) == ErrorAction.RECONNECT

    def test_order_reject_fail(self):
        """13xx order rejections map to FAIL_HARD."""
        from unified_api_contracts.ibkr.schemas import IBKRError

        assert IBKRError.classify(1300) == ErrorAction.FAIL_HARD


class TestTheGraphClassify:
    """Test GraphQLError.classify()."""

    def test_429_retry(self):
        """429 maps to RETRY_WITH_BACKOFF."""
        from unified_api_contracts.thegraph.schemas import GraphQLError

        assert GraphQLError.classify(http_status=429) == ErrorAction.RETRY_WITH_BACKOFF

    def test_not_found_fail(self):
        """not found message maps to FAIL_HARD."""
        from unified_api_contracts.thegraph.schemas import GraphQLError

        assert GraphQLError.classify(message="Subgraph not found") == ErrorAction.FAIL_HARD


class TestCcxtClassify:
    """Test CcxtErrorPayload.classify()."""

    def test_retry_types(self):
        """RateLimitExceeded, ExchangeNotAvailable map to RETRY_WITH_BACKOFF."""
        from unified_api_contracts.ccxt.schemas import CcxtErrorPayload

        assert CcxtErrorPayload.classify(code="RateLimitExceeded") == ErrorAction.RETRY_WITH_BACKOFF
        assert CcxtErrorPayload.classify(code="ExchangeNotAvailable") == ErrorAction.RETRY_WITH_BACKOFF

    def test_fail_hard(self):
        """Unknown maps to FAIL_HARD."""
        from unified_api_contracts.ccxt.schemas import CcxtErrorPayload

        assert CcxtErrorPayload.classify(code="InvalidOrder") == ErrorAction.FAIL_HARD
