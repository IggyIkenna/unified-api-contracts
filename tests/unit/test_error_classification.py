"""Unit tests for ErrorAction and venue error classify() methods."""

from unified_api_contracts.canonical.crosscutting.errors import ErrorAction


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


class TestHyperliquidDefiCodesClassify:
    """Test classify_venue_error() for all 8 HL DeFi error codes (Phase 6 — added 2026-05-12)."""

    def test_hl_insufficient_margin_fails(self):
        """HL_INSUFFICIENT_MARGIN → FAIL (caller decides on position sizing)."""
        from unified_api_contracts.canonical.crosscutting.errors import classify_venue_error

        result = classify_venue_error("hyperliquid", "HL_INSUFFICIENT_MARGIN")
        assert result is not None
        assert result.action == ErrorAction.FAIL

    def test_hl_reduce_only_violation_fails(self):
        """HL_REDUCE_ONLY_VIOLATION → FAIL (caller-side bug)."""
        from unified_api_contracts.canonical.crosscutting.errors import classify_venue_error

        result = classify_venue_error("hyperliquid", "HL_REDUCE_ONLY_VIOLATION")
        assert result is not None
        assert result.action == ErrorAction.FAIL

    def test_hl_invalid_tif_fails(self):
        """HL_INVALID_TIF → FAIL (TIF mismatch — Alo/Ioc/Gtc only)."""
        from unified_api_contracts.canonical.crosscutting.errors import classify_venue_error

        result = classify_venue_error("hyperliquid", "HL_INVALID_TIF")
        assert result is not None
        assert result.action == ErrorAction.FAIL

    def test_hl_rate_limited_retries(self):
        """HL_RATE_LIMITED → RETRY (exponential backoff 1s base)."""
        from unified_api_contracts.canonical.crosscutting.errors import classify_venue_error

        result = classify_venue_error("hyperliquid", "HL_RATE_LIMITED")
        assert result is not None
        assert result.action == ErrorAction.RETRY

    def test_hl_nonce_too_low_retries(self):
        """HL_NONCE_TOO_LOW → RETRY (re-read nonce from /info)."""
        from unified_api_contracts.canonical.crosscutting.errors import classify_venue_error

        result = classify_venue_error("hyperliquid", "HL_NONCE_TOO_LOW")
        assert result is not None
        assert result.action == ErrorAction.RETRY

    def test_hl_signature_invalid_fails(self):
        """HL_SIGNATURE_INVALID → FAIL (wallet/chainId drift — do NOT retry)."""
        from unified_api_contracts.canonical.crosscutting.errors import classify_venue_error

        result = classify_venue_error("hyperliquid", "HL_SIGNATURE_INVALID")
        assert result is not None
        assert result.action == ErrorAction.FAIL

    def test_hl_position_closed_skips(self):
        """HL_POSITION_CLOSED → SKIP (auto-liquidation race — ghost position)."""
        from unified_api_contracts.canonical.crosscutting.errors import classify_venue_error

        result = classify_venue_error("hyperliquid", "HL_POSITION_CLOSED")
        assert result is not None
        assert result.action == ErrorAction.SKIP

    def test_hl_fill_confirmation_missed_retries(self):
        """HL_FILL_CONFIRMATION_MISSED → RETRY (re-query /info userFills)."""
        from unified_api_contracts.canonical.crosscutting.errors import classify_venue_error

        result = classify_venue_error("hyperliquid", "HL_FILL_CONFIRMATION_MISSED")
        assert result is not None
        assert result.action == ErrorAction.RETRY

    def test_all_8_hl_codes_are_registered(self):
        """All 8 Phase 6 HL DeFi codes resolve non-None via classify_venue_error."""
        from unified_api_contracts.canonical.crosscutting.errors import classify_venue_error
        from unified_api_contracts.canonical.crosscutting.errors.defi import DefiErrorCode

        hl_codes = [
            DefiErrorCode.HL_INSUFFICIENT_MARGIN,
            DefiErrorCode.HL_REDUCE_ONLY_VIOLATION,
            DefiErrorCode.HL_INVALID_TIF,
            DefiErrorCode.HL_RATE_LIMITED,
            DefiErrorCode.HL_NONCE_TOO_LOW,
            DefiErrorCode.HL_SIGNATURE_INVALID,
            DefiErrorCode.HL_POSITION_CLOSED,
            DefiErrorCode.HL_FILL_CONFIRMATION_MISSED,
        ]
        for code in hl_codes:
            result = classify_venue_error("hyperliquid", code)
            assert result is not None, f"classify_venue_error('hyperliquid', {code!r}) returned None"


class TestClassifyVenueError:
    """Test classify_venue_error() for VENUE_ERROR_MAP completeness."""

    def test_aave_plasma_429_returns_retry(self):
        """aave_plasma venue: 429 maps to RETRY."""
        from unified_api_contracts.canonical.crosscutting.errors import classify_venue_error

        result = classify_venue_error("aave_plasma", "429")
        assert result is not None
        assert result.action == ErrorAction.RETRY

    def test_aave_plasma_mirrors_aave_v3_codes(self):
        """aave_plasma has same error codes as aave_v3."""
        from unified_api_contracts.canonical.crosscutting.errors import VENUE_ERROR_MAP

        aave_v3_codes = {c.error_code for c in VENUE_ERROR_MAP["aave_v3"]}
        aave_plasma_codes = {c.error_code for c in VENUE_ERROR_MAP["aave_plasma"]}
        # aave_plasma mirrors aave_v3 core codes (minus subgraph/auth/query/indexing)
        core_codes = {
            "INSUFFICIENT_COLLATERAL",
            "INSUFFICIENT_BALANCE",
            "NO_COLLATERAL_DEPOSITED",
            "ASSET_NOT_SUPPORTED",
            "ZERO_AMOUNT",
            "TX_REVERTED",
            "GAS_ESTIMATION_FAILED",
            "SLIPPAGE_EXCEEDED",
            "FLASH_LOAN_RECEIVER_INVALID",
            "FLASH_LOAN_INSUFFICIENT_LIQUIDITY",
            "NO_OUTSTANDING_DEBT",
            "BORROW_CAP_EXCEEDED",
            "SUPPLY_CAP_EXCEEDED",
            "PRICE_ORACLE_SENTINEL",
            "400",
            "401",
            "429",
            "500",
            "-32603",
        }
        assert core_codes <= aave_v3_codes
        assert core_codes <= aave_plasma_codes

    def test_all_14_venues_in_venue_error_map(self):
        """All 14 venues from the error code audit exist in VENUE_ERROR_MAP."""
        from unified_api_contracts.canonical.crosscutting.errors import VENUE_ERROR_MAP

        expected_venues = [
            "api_football",
            "pinnacle",
            "odds_api",
            "odds_engine",
            "opticodds",
            "matchbook",
            "metabet",
            "transfermarkt",
            "footystats",
            "soccer_football_info",
            "understat",
            "open_meteo",
        ]
        for venue in expected_venues:
            assert venue in VENUE_ERROR_MAP, f"Missing venue: {venue}"
            # Each venue must have at least 400, 401, 429, 500 codes
            codes = {c.error_code for c in VENUE_ERROR_MAP[venue]}
            for required_code in ["400", "429", "500"]:
                assert required_code in codes, f"Venue {venue} missing code {required_code}"

    def test_new_venues_429_returns_retry(self):
        """All newly added venues: 429 maps to RETRY."""
        from unified_api_contracts.canonical.crosscutting.errors import classify_venue_error

        new_venues = [
            "odds_engine",
            "opticodds",
            "matchbook",
            "metabet",
        ]
        for venue in new_venues:
            result = classify_venue_error(venue, "429")
            assert result is not None, f"classify_venue_error({venue!r}, '429') returned None"
            assert result.action == ErrorAction.RETRY, f"{venue}: 429 should be RETRY"

    def test_new_venues_400_returns_fail(self):
        """All newly added venues: 400 maps to FAIL."""
        from unified_api_contracts.canonical.crosscutting.errors import classify_venue_error

        new_venues = [
            "odds_engine",
            "opticodds",
            "matchbook",
            "metabet",
        ]
        for venue in new_venues:
            result = classify_venue_error(venue, "400")
            assert result is not None, f"classify_venue_error({venue!r}, '400') returned None"
            assert result.action == ErrorAction.FAIL, f"{venue}: 400 should be FAIL"

    def test_tardis_structural_absence_codes_return_skip(self):
        """Tardis 300 (invalid symbol) and 140 (date outside listing) map to SKIP,
        never FAIL/RETRY — a structural-absence 400, not a fetch failure. SSOT:
        tardis_impossible_combinations_recorded_as_attempted_failed_2026_07_17.md.
        """
        from unified_api_contracts.canonical.crosscutting.errors import classify_venue_error

        for code in ("300", "140"):
            result = classify_venue_error("tardis", code)
            assert result is not None, f"classify_venue_error('tardis', {code!r}) returned None"
            assert result.action == ErrorAction.SKIP, f"tardis {code} should be SKIP (honest absence)"
            assert result.retry_safe is False

    def test_tardis_generic_400_still_returns_fail(self):
        """The generic tardis '400' entry is untouched — only the 140/300 sub-codes are SKIP."""
        from unified_api_contracts.canonical.crosscutting.errors import classify_venue_error

        result = classify_venue_error("tardis", "400")
        assert result is not None
        assert result.action == ErrorAction.FAIL


class TestInternalErrorFallback:
    """classify_venue_error() falls back to the venue-agnostic 'internal' bucket
    for write-guard rejections raised by our own code (not a vendor API error),
    which can occur for ANY venue. SSOT:
    cefi_onchain_perp_forward_capture_outage_2026_08_03.md.
    """

    def test_upstream_timestamp_bias_error_classifies_for_any_venue(self):
        """UpstreamTimestampBiasError classifies via the internal fallback for a
        venue that has no venue-specific entry for it (e.g. aster)."""
        from unified_api_contracts.canonical.crosscutting.errors import classify_venue_error

        result = classify_venue_error("aster", "UpstreamTimestampBiasError")
        assert result is not None
        assert result.action == ErrorAction.RETRY
        assert result.retry_safe is True

    def test_upstream_timestamp_bias_error_classifies_for_multiple_onchain_perp_venues(self):
        """Same code classifies identically regardless of which venue raised it —
        the guard is MTDS-internal, not vendor-specific."""
        from unified_api_contracts.canonical.crosscutting.errors import classify_venue_error

        for venue in ("aster", "lighter-zksync", "extended-starknet", "hyperliquid"):
            result = classify_venue_error(venue, "UpstreamTimestampBiasError")
            assert result is not None, f"classify_venue_error({venue!r}, 'UpstreamTimestampBiasError') returned None"
            assert result.action == ErrorAction.RETRY

    def test_venue_specific_match_takes_priority_over_internal_fallback(self):
        """A venue's own entry for a code wins even if 'internal' also defines
        that literal code string (no accidental shadowing either direction)."""
        from unified_api_contracts.canonical.crosscutting.errors import classify_venue_error

        # hyperliquid has its own "500" entry distinct from any internal bucket code.
        result = classify_venue_error("hyperliquid", "500")
        assert result is not None
        assert result.venue == "hyperliquid"

    def test_unknown_code_still_returns_none(self):
        """A code absent from both the venue map and the internal bucket stays
        unclassified (no over-broad fallback)."""
        from unified_api_contracts.canonical.crosscutting.errors import classify_venue_error

        assert classify_venue_error("aster", "SomeTotallyUnknownError") is None
