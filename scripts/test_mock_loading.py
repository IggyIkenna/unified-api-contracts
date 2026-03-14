#!/usr/bin/env python3
"""
Test script to load and demonstrate Yahoo Finance mock data usage.

This script shows how to load and use the mock data files in tests.
"""

import logging
from pathlib import Path

import pandas as pd
import yaml

logger = logging.getLogger(__name__)

# Path to mock files
MOCKS_DIR = Path(__file__).parent.parent / "unified_api_contracts" / "external" / "yahoo_finance" / "mocks"


def load_mock_data(mock_file: str) -> dict[str, object]:
    """Load mock data from YAML file."""
    file_path = MOCKS_DIR / mock_file
    with open(file_path) as f:
        return yaml.safe_load(f)


def simulate_yfinance_dividends(mock_data: dict[str, object]) -> pd.Series:
    """Simulate yfinance dividends Series from mock data."""
    dividends_data = mock_data["dividends_series"]

    # Convert to pandas Series
    dates = [pd.to_datetime(date_str, utc=True) for date_str in dividends_data]
    amounts = list(dividends_data.values())

    return pd.Series(amounts, index=dates, name="Dividends")


def simulate_yfinance_splits(mock_data: dict[str, object]) -> pd.Series:
    """Simulate yfinance splits Series from mock data."""
    splits_data = mock_data["splits_series"]

    # Convert to pandas Series
    dates = [pd.to_datetime(date_str, utc=True) for date_str in splits_data]
    ratios = list(splits_data.values())

    return pd.Series(ratios, index=dates, name="Stock Splits")


def simulate_yfinance_earnings(mock_data: dict[str, object]) -> pd.DataFrame:
    """Simulate yfinance earnings DataFrame from mock data."""
    earnings_data = mock_data["earnings_dataframe"]

    # Extract columns and data
    columns = earnings_data["columns"]
    data_dict = earnings_data["data"]

    # Convert to DataFrame
    dates = [pd.to_datetime(date_str, utc=True) for date_str in data_dict]
    rows = list(data_dict.values())

    df = pd.DataFrame(rows, index=dates, columns=columns)
    return df


def demonstrate_mock_usage():
    """Demonstrate how to use mock data in tests."""
    logger.info("🧪 Yahoo Finance Mock Data Demonstration\n")

    # 1. Load AAPL dividends mock
    logger.info("1. Loading AAPL Dividends Mock:")
    aapl_mock = load_mock_data("dividends_aapl.yaml")
    logger.info(f"   Ticker: {aapl_mock['metadata']['ticker']}")
    logger.info(f"   Total Records: {aapl_mock['metadata']['total_records']}")

    # Simulate yfinance dividends Series
    dividends_series = simulate_yfinance_dividends(aapl_mock)
    logger.info(f"   Dividends Series Shape: {dividends_series.shape}")
    logger.info(f"   Sample dividend: {dividends_series.iloc[0]} on {dividends_series.index[0].date()}")

    # 2. Load TSLA splits mock
    logger.info("\n2. Loading TSLA Splits Mock:")
    tsla_mock = load_mock_data("splits_tsla.yaml")
    logger.info(f"   Ticker: {tsla_mock['metadata']['ticker']}")
    logger.info(f"   Total Records: {tsla_mock['metadata']['total_records']}")

    # Simulate yfinance splits Series
    splits_series = simulate_yfinance_splits(tsla_mock)
    logger.info(f"   Splits Series Shape: {splits_series.shape}")
    for i, (date, ratio) in enumerate(splits_series.items()):
        logger.info(f"   Split {i + 1}: {ratio}:1 on {date.date()}")

    # 3. Load MSFT earnings mock
    logger.info("\n3. Loading MSFT Earnings Mock:")
    msft_mock = load_mock_data("earnings_msft.yaml")
    logger.info(f"   Ticker: {msft_mock['metadata']['ticker']}")
    logger.info(f"   Total Records: {msft_mock['metadata']['total_records']}")

    # Simulate yfinance earnings DataFrame
    earnings_df = simulate_yfinance_earnings(msft_mock)
    logger.info(f"   Earnings DataFrame Shape: {earnings_df.shape}")
    logger.info(f"   Columns: {list(earnings_df.columns)}")

    # Show recent earnings
    latest_earnings = earnings_df.iloc[-1]
    latest_date = earnings_df.index[-1].date()
    logger.info(f"   Latest earnings ({latest_date}):")
    logger.info(f"     Reported EPS: ${latest_earnings['Reported EPS']}")
    logger.info(f"     Estimated EPS: ${latest_earnings['EPS Estimate']}")
    logger.info(f"     Surprise: {latest_earnings['Surprise(%)']}%")

    # 4. Load error mocks
    logger.info("\n4. Loading Error Mocks:")

    # Invalid symbol errors
    invalid_mock = load_mock_data("error_invalid_symbol.yaml")
    logger.info(f"   Invalid Symbol Errors: {invalid_mock['metadata']['error_category']}")
    logger.info(f"   Example exception: {invalid_mock['yfinance_exceptions']['no_data_exception']['exception_type']}")

    # Rate limit errors
    rate_limit_mock = load_mock_data("error_rate_limit.yaml")
    logger.info(f"   Rate Limit Errors: {rate_limit_mock['metadata']['error_category']}")
    logger.info(f"   HTTP 429 status: {rate_limit_mock['http_429_responses']['standard_rate_limit']['status_code']}")
    retry = rate_limit_mock["http_429_responses"]["standard_rate_limit"]["headers"]["Retry-After"]
    logger.info(f"   Retry after: {retry} seconds")


def show_testing_examples():
    """Show examples of how to use mocks in unit tests.

    NOTE: Actual test implementations belong in instruments-service/tests/ (T3 service).
    UAC (T0 leaf) must not reference instruments_service directly.
    These examples show generic yfinance mock patterns only.
    """
    logger.info("\n Unit Test Examples:\n")

    logger.info("# Example: Mock yfinance dividends in unit test")
    logger.info("""
import unittest.mock
import pandas as pd
import logging
logger = logging.getLogger(__name__)

# In instruments-service tests, import from the service package directly:
# from <service_package>.corporate_actions.adapter import CorporateActionsAdapter
# NOTE: instruments_service imports belong in instruments-service/tests/, not UAC.

class TestCorporateActions:
    @patch("<service_package>.corporate_actions.adapter.CorporateActionsAdapter.yf")
    def test_fetch_aapl_dividends(self, mock_yf):
        # Load mock data
        mock_data = load_mock_data("dividends_aapl.yaml")
        dividends_series = simulate_yfinance_dividends(mock_data)

        # Setup mock
        mock_ticker = unittest.mock.MagicMock()
        mock_yf.Ticker.return_value = mock_ticker
        mock_ticker.dividends = dividends_series

        # Test adapter
        adapter = CorporateActionsAdapter()
        adapter._yf = mock_yf

        dividends = adapter.fetch_dividends(
            ticker="AAPL",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31)
        )

        # Assertions
        assert len(dividends) == 8  # Expected from mock
        assert all(d.ticker == "AAPL" for d in dividends)
        assert all(d.amount > 0 for d in dividends)
    """)

    logger.info("\n# Example: Test error handling with invalid symbol")
    logger.info("""
    @patch("<service_package>.corporate_actions.adapter.CorporateActionsAdapter.yf")
    def test_invalid_symbol_handling(self, mock_yf):
        # Load error mock data
        error_mock = load_mock_data("error_invalid_symbol.yaml")

        # Setup mock to raise exception
        mock_ticker = unittest.mock.MagicMock()
        mock_yf.Ticker.return_value = mock_ticker
        mock_ticker.dividends.side_effect = ValueError("No data found, symbol may be delisted")

        # Test adapter
        adapter = CorporateActionsAdapter()
        adapter._yf = mock_yf

        dividends = adapter.fetch_dividends("INVALID", date(2024,1,1), date(2024,12,31))

        # Should return empty list, not raise exception
        assert dividends == []
    """)


def validate_mock_compatibility():
    """Validate mocks are compatible with instruments-service models."""
    logger.info("\n🔍 Model Compatibility Check:\n")

    # Check dividend record compatibility
    aapl_mock = load_mock_data("dividends_aapl.yaml")
    dividend_records = aapl_mock["dividend_records"]

    logger.info("✓ Dividend records have all required fields:")
    required_fields = ["ticker", "ex_date", "amount", "dividend_type", "currency", "source"]
    sample_record = dividend_records[0]
    for field in required_fields:
        present = field in sample_record
        logger.info(f"   {field}: {'✓' if present else '✗'}")

    # Check split record compatibility
    tsla_mock = load_mock_data("splits_tsla.yaml")
    split_records = tsla_mock["split_records"]

    logger.info("\n✓ Split records have all required fields:")
    required_fields = ["ticker", "effective_date", "ratio", "split_from", "split_to", "source"]
    sample_record = split_records[0]
    for field in required_fields:
        present = field in sample_record
        logger.info(f"   {field}: {'✓' if present else '✗'}")

    # Check earnings record compatibility
    msft_mock = load_mock_data("earnings_msft.yaml")
    earnings_records = msft_mock["earnings_records"]

    logger.info("\n✓ Earnings records have all required fields:")
    required_fields = ["ticker", "earnings_date", "source"]
    optional_fields = ["reported_eps", "estimated_eps", "surprise_pct", "revenue"]
    sample_record = earnings_records[0]

    for field in required_fields:
        present = field in sample_record
        logger.info(f"   {field} (required): {'✓' if present else '✗'}")

    for field in optional_fields:
        present = field in sample_record
        logger.info(f"   {field} (optional): {'✓' if present else '○'}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demonstrate_mock_usage()
    show_testing_examples()
    validate_mock_compatibility()

    logger.info("\n🎉 Mock data validation complete!")
    logger.info("\nFiles created:")
    for mock_file in MOCKS_DIR.glob("*.yaml"):
        logger.info(f"   • {mock_file}")
