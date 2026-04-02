"""Unit tests for unified-internal-contracts schemas."""

from datetime import UTC, datetime

from unified_api_contracts.internal import MessagingScope, MessagingTopic
from unified_api_contracts.internal.ml import InferenceRequest
from unified_api_contracts.internal.risk import PreTradeCheckRequest, PreTradeCheckResponse
from unified_api_contracts.internal.schemas import (
    EnhancedError,
    ErrorCategory,
    ErrorContext,
    ErrorRecoveryStrategy,
    ErrorSeverity,
)


def test_messaging_scope_values() -> None:
    assert MessagingScope.IN_PROCESS == "in_process"
    assert MessagingScope.SAME_VM == "same_vm"
    assert MessagingScope.CROSS_VM == "cross_vm"


def test_messaging_topic_values() -> None:
    assert MessagingTopic.ORDER_REQUESTS == "order-requests"
    assert MessagingTopic.MARKET_TICKS == "market-ticks"


def test_inference_request_roundtrip() -> None:
    ts = datetime.now(UTC)
    req = InferenceRequest(
        request_id="r1",
        model_id="m1",
        instrument_id="i1",
        timestamp=ts,
        features={"f1": 1.0},
    )
    assert req.request_id == "r1"
    assert req.timeframe == "1h"


def test_pre_trade_check_request_response() -> None:
    from decimal import Decimal

    req = PreTradeCheckRequest(
        client_id="c1",
        venue="binance",
        instrument="BTC-USDT",
        side="buy",
        quantity=Decimal("0.1"),
        estimated_price=Decimal("50000"),
    )
    assert req.client_id == "c1"
    resp = PreTradeCheckResponse(approved=True, client_id="c1", instrument="BTC-USDT")
    assert resp.approved is True


def test_enhanced_error_schema() -> None:
    err = EnhancedError(
        message="test",
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.MEDIUM,
        recovery_strategy=ErrorRecoveryStrategy.RETRY,
        context=ErrorContext(service="test-svc"),
    )
    assert err.error_type == "EnhancedError"
    assert err.category == ErrorCategory.VALIDATION
