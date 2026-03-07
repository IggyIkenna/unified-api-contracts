"""Integration/smoke tests for Phase 6 schemas.

Validates CcxtBorrowRate, CcxtInsuranceFund, CcxtLiquidation, CcxtSubaccount,
CcxtCurrency, BinanceMarkPriceKline, BinanceIndexPriceKline, TardisBookSnapshot25,
TardisIncrementalBookL2, TardisQuotes against fixtures or examples.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
from unified_api_contracts.binance.market_schemas import (
    BinanceIndexPriceKline,
    BinanceMarkPriceKline,
)
from unified_api_contracts.ccxt.schemas import (
    CcxtBorrowRate,
    CcxtCurrency,
    CcxtInsuranceFund,
    CcxtLiquidation,
    CcxtSubaccount,
)
from unified_api_contracts.tardis.schemas import (
    TardisBookSnapshot25,
    TardisIncrementalBookL2,
    TardisQuotes,
)

ROOT = Path(__file__).resolve().parent.parent.parent
_EXTERNAL = ROOT / "unified_api_contracts" / "unified_api_contracts_external"
CCXT_EXAMPLES = _EXTERNAL / "ccxt" / "examples"
BINANCE_EXAMPLES = _EXTERNAL / "binance" / "examples"
TARDIS_EXAMPLES = _EXTERNAL / "tardis" / "examples"


# --- CCXT new schemas ---


@pytest.mark.unit
def test_ccxt_borrow_rate_validates() -> None:
    """Validate CcxtBorrowRate against fixture."""
    path = CCXT_EXAMPLES / "borrow_rate_example.json"
    assert path.exists(), f"Example missing: {path}"
    data = json.loads(path.read_text())
    obj = CcxtBorrowRate.model_validate(data)
    assert obj.currency == "USDT"
    assert obj.rate == 0.0001
    assert obj.period == 86400000


@pytest.mark.unit
def test_ccxt_insurance_fund_validates() -> None:
    """Validate CcxtInsuranceFund against fixture."""
    path = CCXT_EXAMPLES / "insurance_fund_example.json"
    assert path.exists(), f"Example missing: {path}"
    data = json.loads(path.read_text())
    obj = CcxtInsuranceFund.model_validate(data)
    assert obj.symbol == "BTCUSDT"
    assert obj.balance == 1250000.5
    assert obj.balanceInUsd == 1250000.5


@pytest.mark.unit
def test_ccxt_liquidation_validates() -> None:
    """Validate CcxtLiquidation against fixture."""
    path = CCXT_EXAMPLES / "liquidation_example.json"
    assert path.exists(), f"Example missing: {path}"
    data = json.loads(path.read_text())
    obj = CcxtLiquidation.model_validate(data)
    assert obj.symbol == "BTCUSDT"
    assert obj.price == 42000.5
    assert obj.side == "long"
    assert obj.leverage == 10


@pytest.mark.unit
def test_ccxt_subaccount_validates() -> None:
    """Validate CcxtSubaccount against fixture."""
    path = CCXT_EXAMPLES / "subaccount_example.json"
    assert path.exists(), f"Example missing: {path}"
    data = json.loads(path.read_text())
    obj = CcxtSubaccount.model_validate(data)
    assert obj.id == "sub-001"
    assert obj.type == "subaccount"
    assert obj.name == "Trading Sub 1"


@pytest.mark.unit
def test_ccxt_currency_validates() -> None:
    """Validate CcxtCurrency against fixture."""
    path = CCXT_EXAMPLES / "currency_example.json"
    assert path.exists(), f"Example missing: {path}"
    data = json.loads(path.read_text())
    obj = CcxtCurrency.model_validate(data)
    assert obj.id == "USDT"
    assert obj.code == "USDT"
    assert obj.active is True
    assert obj.networks is not None
    assert "ERC20" in obj.networks


# --- Binance mark price klines ---


@pytest.mark.unit
def test_binance_mark_price_kline_validates() -> None:
    """Validate BinanceMarkPriceKline against fixture (dict format)."""
    path = BINANCE_EXAMPLES / "mark_price_kline_example.json"
    assert path.exists(), f"Example missing: {path}"
    data = json.loads(path.read_text())
    obj = BinanceMarkPriceKline.model_validate(data)
    assert obj.open_time == 1704067200000
    assert obj.open_price == Decimal("50000.5")
    assert obj.high_price == Decimal("50100.25")
    assert obj.low_price == Decimal("49900.75")
    assert obj.close_price == Decimal("50050.00")
    assert obj.volume == Decimal("1000.5")


@pytest.mark.unit
def test_binance_mark_price_kline_from_list_coinm() -> None:
    """Validate BinanceMarkPriceKline from Coin-M array format (12 fields)."""
    kline = [
        1704067200000,
        "50000.5",
        "50100.25",
        "49900.75",
        "50050.00",
        "1000.5",
        1704070800000,
        "50000000",
        100,
        "500",
        "25000000",
        "0",
    ]
    obj = BinanceMarkPriceKline.from_list(kline)
    assert obj.open_time == 1704067200000
    assert obj.close_time == 1704070800000
    assert obj.number_of_trades == 100


@pytest.mark.unit
def test_binance_index_price_kline_validates() -> None:
    """Validate BinanceIndexPriceKline against fixture (dict format)."""
    path = BINANCE_EXAMPLES / "index_price_kline_example.json"
    assert path.exists(), f"Example missing: {path}"
    data = json.loads(path.read_text())
    obj = BinanceIndexPriceKline.model_validate(data)
    assert obj.open_time == 1704067200000
    assert obj.open_price == Decimal("50000.5")
    assert obj.close_price == Decimal("50050.00")


# --- Tardis new schemas ---


@pytest.mark.unit
def test_tardis_book_snapshot_25_validates() -> None:
    """Validate TardisBookSnapshot25 against fixture."""
    path = TARDIS_EXAMPLES / "book_snapshot_25_example.json"
    assert path.exists(), f"Example missing: {path}"
    data = json.loads(path.read_text())
    obj = TardisBookSnapshot25.model_validate(data)
    assert obj.exchange == "BINANCE"
    assert obj.symbol == "BTC-USDT"
    assert obj.ask_price_0 == 50050.5
    assert obj.bid_price_0 == 50049.5
    assert obj.ask_price_1 == 50051.0


@pytest.mark.unit
def test_tardis_incremental_book_l2_validates() -> None:
    """Validate TardisIncrementalBookL2 against fixture."""
    path = TARDIS_EXAMPLES / "incremental_book_L2_example.json"
    assert path.exists(), f"Example missing: {path}"
    data = json.loads(path.read_text())
    obj = TardisIncrementalBookL2.model_validate(data)
    assert obj.exchange == "BINANCE"
    assert obj.symbol == "BTC-USDT"
    assert obj.is_snapshot is False
    assert obj.side == "bid"
    assert obj.price == 50049.5
    assert obj.amount == 2.5


@pytest.mark.unit
def test_tardis_quotes_validates() -> None:
    """Validate TardisQuotes against fixture."""
    path = TARDIS_EXAMPLES / "quotes_example.json"
    assert path.exists(), f"Example missing: {path}"
    data = json.loads(path.read_text())
    obj = TardisQuotes.model_validate(data)
    assert obj.exchange == "BINANCE"
    assert obj.symbol == "BTC-USDT"
    assert obj.ask_price == 50050.5
    assert obj.bid_price == 50049.5
    assert obj.ask_amount == 1.5
    assert obj.bid_amount == 2.0
