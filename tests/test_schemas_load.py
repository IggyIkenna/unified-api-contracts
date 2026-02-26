"""Test that schema modules load and example validation works."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Import schema modules to ensure they load


def test_databento_ohlcv_bar_schema() -> None:
    from api_contracts.databento.schemas import DatabentoOhlcvBar

    example = {
        "ts_event": 1609459200000000000,
        "rtype": 32,
        "publisher_id": 1,
        "instrument_id": 12345,
        "open": 5000000000000,
        "high": 5010000000000,
        "low": 4990000000000,
        "close": 5005000000000,
        "volume": 1000,
    }
    bar = DatabentoOhlcvBar.model_validate(example)
    assert bar.close == 5005000000000
    assert bar.volume == 1000


def test_ccxt_order_schema() -> None:
    from api_contracts.ccxt.schemas import CcxtOrder

    example = {
        "id": "order-123",
        "clientOrderId": "client-456",
        "timestamp": 1609459200000,
        "symbol": "BTC/USDT",
        "type": "limit",
        "side": "buy",
        "price": 50000.0,
        "amount": 0.01,
        "filled": 0.0,
        "remaining": 0.01,
        "status": "open",
        "timeInForce": "GTC",
    }
    order = CcxtOrder.model_validate(example)
    assert order.id == "order-123"
    assert order.side == "buy"


def test_validate_examples_if_present() -> None:
    """Validate all JSON files under api_contracts/*/examples/ with the matching schema if we have a loader."""
    root = Path(__file__).resolve().parent.parent / "api_contracts"
    if not root.exists():
        pytest.skip("api_contracts package not found")

    validated = 0
    for api_dir in root.iterdir():
        if not api_dir.is_dir():
            continue
        examples_dir = api_dir / "examples"
        if not examples_dir.exists():
            continue
        for path in examples_dir.glob("*.json"):
            data = json.loads(path.read_text())
            if api_dir.name == "databento" and "ts_event" in data and "close" in data:
                from api_contracts.databento.schemas import DatabentoOhlcvBar

                DatabentoOhlcvBar.model_validate(data)
                validated += 1
            elif api_dir.name == "ccxt" and "id" in data and "symbol" in data:
                from api_contracts.ccxt.schemas import CcxtOrder

                CcxtOrder.model_validate(data)
                validated += 1
    assert validated >= 1, "At least one example should validate"
