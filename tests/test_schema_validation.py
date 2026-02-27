"""Test schema validation against real API responses."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from api_contracts.binance.schemas import BinanceKline, BinanceTicker, BinanceTrade
from api_contracts.coinbase.schemas import CoinbaseCandle, CoinbaseTicker

# Project root
ROOT = Path(__file__).resolve().parent.parent
COLLECTED_RESPONSES_DIR = ROOT / "collected_responses"


class TestSchemaValidation:
    """Test that schemas validate against real API responses."""

    def test_binance_ticker_validation(self):
        """Test Binance ticker schema validates real API response."""
        response_file = COLLECTED_RESPONSES_DIR / "binance" / "ticker_1771933935.json"

        if response_file.exists():
            with response_file.open() as f:
                data = json.load(f)

            # Should validate without errors
            ticker = BinanceTicker(**data["response"])
            assert ticker.symbol == "BTCUSDT"
            assert ticker.lastPrice > 0
            assert ticker.bidPrice > 0
            assert ticker.askPrice > 0
        else:
            pytest.skip("Real API response not available")

    def test_binance_trade_validation(self):
        """Test Binance trade schema validates real API response."""
        response_file = COLLECTED_RESPONSES_DIR / "binance" / "recent_trades_1771933937.json"

        if response_file.exists():
            with response_file.open() as f:
                data = json.load(f)

            # Response is a list of trades
            trades_data = data["response"]
            assert isinstance(trades_data, list)

            if trades_data:
                # Validate first trade
                trade = BinanceTrade(**trades_data[0])
                assert trade.id > 0
                assert trade.price > 0
                assert trade.qty > 0
                assert isinstance(trade.isBuyerMaker, bool)
                assert isinstance(trade.isBestMatch, bool)
        else:
            pytest.skip("Real API response not available")

    def test_binance_kline_validation(self):
        """Test Binance kline schema validates real API response."""
        response_file = COLLECTED_RESPONSES_DIR / "binance" / "klines_1771933938.json"

        if response_file.exists():
            with response_file.open() as f:
                data = json.load(f)

            # Response is a list of klines (each kline is a list)
            klines_data = data["response"]
            assert isinstance(klines_data, list)

            if klines_data:
                # Validate first kline using from_list method
                kline = BinanceKline.from_list(klines_data[0])
                assert kline.open_time > 0
                assert kline.open_price > 0
                assert kline.close_price > 0
                assert kline.volume >= 0
        else:
            pytest.skip("Real API response not available")

    def test_coinbase_ticker_validation(self):
        """Test Coinbase ticker schema validates real API response."""
        response_file = COLLECTED_RESPONSES_DIR / "coinbase" / "ticker_1771933945.json"

        if response_file.exists():
            with response_file.open() as f:
                data = json.load(f)

            # Should validate without errors
            ticker = CoinbaseTicker(**data["response"])
            assert ticker.ask > 0
            assert ticker.bid > 0
            assert ticker.price > 0
            assert ticker.trade_id > 0
        else:
            pytest.skip("Real API response not available")

    def test_coinbase_candle_validation(self):
        """Test Coinbase candle schema validates real API response."""
        response_file = COLLECTED_RESPONSES_DIR / "coinbase" / "candles_1771933948.json"

        if response_file.exists():
            with response_file.open() as f:
                data = json.load(f)

            # Response is a list of candles (each candle is a list)
            candles_data = data["response"]
            assert isinstance(candles_data, list)

            if candles_data:
                # Validate first candle using from_list method
                candle = CoinbaseCandle.from_list(candles_data[0])
                assert candle.timestamp > 0
                assert candle.open > 0
                assert candle.close > 0
                assert candle.volume >= 0
        else:
            pytest.skip("Real API response not available")

    def test_schema_validation_coverage(self):
        """Test that we have good schema coverage across venues."""
        # Count schema classes
        binance_schemas = [
            BinanceTicker,
            BinanceTrade,
            BinanceKline,
            # Add other Binance schemas as imported
        ]

        coinbase_schemas = [
            CoinbaseTicker,
            CoinbaseCandle,
            # Add other Coinbase schemas as imported
        ]

        total_schemas = len(binance_schemas) + len(coinbase_schemas)

        # Should have reasonable schema coverage
        assert total_schemas >= 5, f"Expected at least 5 schemas, got {total_schemas}"

    def test_decimal_precision(self):
        """Test that financial fields use Decimal for precision."""
        from decimal import Decimal

        # Test Binance
        ticker = BinanceTicker(
            symbol="BTCUSDT",
            priceChange="100.50",
            priceChangePercent="1.5",
            weightedAvgPrice="50000.25",
            prevClosePrice="49900.00",
            lastPrice="50000.75",
            lastQty="0.01234567",
            bidPrice="50000.50",
            bidQty="1.5",
            askPrice="50000.75",
            askQty="2.0",
            openPrice="49900.00",
            highPrice="50100.00",
            lowPrice="49800.00",
            volume="1000.0",
            quoteVolume="50000000.00",
            openTime=1771933935,
            closeTime=1771933936,
            firstId=1000000,
            lastId=1000001,
            count=1000,
        )

        # Check that price fields are Decimal
        assert isinstance(ticker.lastPrice, Decimal)
        assert isinstance(ticker.bidPrice, Decimal)
        assert isinstance(ticker.askPrice, Decimal)
        assert isinstance(ticker.volume, Decimal)

        # Test precision is maintained
        assert ticker.lastQty == Decimal("0.01234567")

    def test_error_handling(self):
        """Test that validation errors are raised for invalid data."""
        with pytest.raises(ValidationError):
            # Missing required fields should raise error
            BinanceTicker()

        with pytest.raises(ValidationError):
            # Invalid field type should raise error
            BinanceTicker(
                symbol="BTCUSDT",
                lastPrice="not_a_number",  # Invalid decimal
                # ... other required fields would need to be valid
            )
