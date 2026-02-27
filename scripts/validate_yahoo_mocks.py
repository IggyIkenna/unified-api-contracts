#!/usr/bin/env python3
"""
Validation script for Yahoo Finance mock data files.

This script validates the YAML mock files for:
1. Valid YAML syntax
2. Required fields and structure
3. Data type validation
4. Business logic validation (e.g., positive amounts, valid dates)
5. Compatibility with instruments-service models

Usage:
    python scripts/validate_yahoo_mocks.py
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Path to mock files
MOCKS_DIR = Path(__file__).parent.parent / "api_contracts" / "yahoo_finance" / "mocks"

class MockValidator:
    """Validator for Yahoo Finance mock data files."""

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate_all_mocks(self) -> bool:
        """Validate all mock files. Returns True if all valid."""
        success = True

        mock_files = [
            "dividends_aapl.yaml",
            "splits_tsla.yaml",
            "earnings_msft.yaml",
            "error_invalid_symbol.yaml",
            "error_rate_limit.yaml"
        ]

        for mock_file in mock_files:
            file_path = MOCKS_DIR / mock_file
            logger.info(f"Validating {mock_file}...")

            if not file_path.exists():
                self.errors.append(f"Mock file not found: {file_path}")
                success = False
                continue

            file_success = self.validate_mock_file(file_path)
            if not file_success:
                success = False

        return success

    def validate_mock_file(self, file_path: Path) -> bool:
        """Validate a single mock file."""
        try:
            # Load YAML
            with open(file_path) as f:
                data = yaml.safe_load(f)

            if data is None:
                self.errors.append(f"Empty or invalid YAML: {file_path}")
                return False

            # Determine validation based on file name
            if "dividends" in file_path.name:
                return self.validate_dividends_mock(data, file_path)
            elif "splits" in file_path.name:
                return self.validate_splits_mock(data, file_path)
            elif "earnings" in file_path.name:
                return self.validate_earnings_mock(data, file_path)
            elif "error" in file_path.name:
                return self.validate_error_mock(data, file_path)
            else:
                self.warnings.append(f"Unknown mock file type: {file_path}")
                return True

        except yaml.YAMLError as e:
            self.errors.append(f"YAML syntax error in {file_path}: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Error validating {file_path}: {e}")
            return False

    def validate_dividends_mock(self, data: dict[str, Any], file_path: Path) -> bool:
        """Validate dividends mock structure and data."""
        success = True

        # Check required sections
        required_sections = ["metadata", "dividends_series", "dividend_records", "usage"]
        for section in required_sections:
            if section not in data:
                self.errors.append(f"{file_path}: Missing required section '{section}'")
                success = False

        # Validate metadata
        if "metadata" in data:
            metadata = data["metadata"]
            if metadata.get("ticker") != "AAPL":
                self.errors.append(f"{file_path}: Expected ticker 'AAPL' in metadata")
                success = False
            if metadata.get("data_type") != "dividends":
                self.errors.append(f"{file_path}: Expected data_type 'dividends' in metadata")
                success = False

        # Validate dividend records
        if "dividend_records" in data:
            records = data["dividend_records"]
            if not isinstance(records, list):
                self.errors.append(f"{file_path}: dividend_records must be a list")
                success = False
            else:
                success &= self.validate_dividend_records_structure(records, file_path)

        return success

    def validate_dividend_records_structure(self, records: list[dict], file_path: Path) -> bool:
        """Validate individual dividend record structure."""
        success = True

        required_fields = ["ticker", "ex_date", "amount", "dividend_type", "currency", "source"]

        for i, record in enumerate(records):
            if not isinstance(record, dict):
                self.errors.append(f"{file_path}: dividend_record[{i}] must be a dictionary")
                success = False
                continue

            # Check required fields
            for field in required_fields:
                if field not in record:
                    self.errors.append(f"{file_path}: dividend_record[{i}] missing field '{field}'")
                    success = False

            # Validate data types and values
            if "amount" in record:
                amount = record["amount"]
                if not isinstance(amount, (int, float)) or amount < 0:
                    self.errors.append(f"{file_path}: dividend_record[{i}] amount must be non-negative number")
                    success = False

            if "ex_date" in record:
                ex_date = record["ex_date"]
                if not isinstance(ex_date, str):
                    self.errors.append(f"{file_path}: dividend_record[{i}] ex_date must be string")
                    success = False
                else:
                    try:
                        datetime.fromisoformat(ex_date)
                    except ValueError:
                        self.errors.append(f"{file_path}: dividend_record[{i}] invalid ex_date format")
                        success = False

        return success

    def validate_splits_mock(self, data: dict[str, Any], file_path: Path) -> bool:
        """Validate stock splits mock structure and data."""
        success = True

        # Check required sections
        required_sections = ["metadata", "splits_series", "split_records", "usage"]
        for section in required_sections:
            if section not in data:
                self.errors.append(f"{file_path}: Missing required section '{section}'")
                success = False

        # Validate split records
        if "split_records" in data:
            records = data["split_records"]
            success &= self.validate_split_records_structure(records, file_path)

        return success

    def validate_split_records_structure(self, records: list[dict], file_path: Path) -> bool:
        """Validate individual split record structure."""
        success = True

        required_fields = ["ticker", "effective_date", "ratio", "split_from", "split_to", "source"]

        for i, record in enumerate(records):
            if not isinstance(record, dict):
                self.errors.append(f"{file_path}: split_record[{i}] must be a dictionary")
                success = False
                continue

            # Check required fields
            for field in required_fields:
                if field not in record:
                    self.errors.append(f"{file_path}: split_record[{i}] missing field '{field}'")
                    success = False

            # Validate ratio
            if "ratio" in record:
                ratio = record["ratio"]
                if not isinstance(ratio, (int, float)) or ratio <= 0:
                    self.errors.append(f"{file_path}: split_record[{i}] ratio must be positive number")
                    success = False

        return success

    def validate_earnings_mock(self, data: dict[str, Any], file_path: Path) -> bool:
        """Validate earnings mock structure and data."""
        success = True

        # Check required sections
        required_sections = ["metadata", "earnings_dataframe", "earnings_records", "usage"]
        for section in required_sections:
            if section not in data:
                self.errors.append(f"{file_path}: Missing required section '{section}'")
                success = False

        # Validate earnings records
        if "earnings_records" in data:
            records = data["earnings_records"]
            success &= self.validate_earnings_records_structure(records, file_path)

        return success

    def validate_earnings_records_structure(self, records: list[dict], file_path: Path) -> bool:
        """Validate individual earnings record structure."""
        success = True

        required_fields = ["ticker", "earnings_date", "source"]

        for i, record in enumerate(records):
            if not isinstance(record, dict):
                self.errors.append(f"{file_path}: earnings_record[{i}] must be a dictionary")
                success = False
                continue

            # Check required fields
            for field in required_fields:
                if field not in record:
                    self.errors.append(f"{file_path}: earnings_record[{i}] missing field '{field}'")
                    success = False

            # Validate EPS values (can be null)
            for eps_field in ["reported_eps", "estimated_eps"]:
                if eps_field in record:
                    eps_value = record[eps_field]
                    if eps_value is not None and not isinstance(eps_value, (int, float)):
                        self.errors.append(f"{file_path}: earnings_record[{i}] {eps_field} must be number or null")
                        success = False

        return success

    def validate_error_mock(self, data: dict[str, Any], file_path: Path) -> bool:
        """Validate error mock structure and data."""
        success = True

        # Check required sections
        required_sections = ["metadata", "usage"]
        for section in required_sections:
            if section not in data:
                self.errors.append(f"{file_path}: Missing required section '{section}'")
                success = False

        # Validate metadata
        if "metadata" in data:
            metadata = data["metadata"]
            if metadata.get("data_type") != "error_responses":
                self.errors.append(f"{file_path}: Expected data_type 'error_responses' in metadata")
                success = False

        return success

    def validate_business_logic(self) -> bool:
        """Validate business logic across mock files."""
        success = True

        # Load AAPL dividends and check quarterly pattern
        try:
            with open(MOCKS_DIR / "dividends_aapl.yaml") as f:
                aapl_data = yaml.safe_load(f)

            if "dividend_records" in aapl_data:
                records = aapl_data["dividend_records"]
                dates = [datetime.fromisoformat(r["ex_date"]).date() for r in records]
                dates.sort()

                # Check that dates are roughly quarterly (80-120 days apart)
                for i in range(1, len(dates)):
                    days_diff = (dates[i] - dates[i-1]).days
                    if not (80 <= days_diff <= 120):
                        self.warnings.append(f"AAPL dividend dates may not be quarterly: {days_diff} days between {dates[i-1]} and {dates[i]}")

        except Exception as e:
            self.warnings.append(f"Could not validate business logic for AAPL dividends: {e}")

        return success

    def print_results(self):
        """Print validation results."""
        if self.errors:
            logger.error("Validation errors found:")
            for error in self.errors:
                logger.error(f"  • {error}")

        if self.warnings:
            logger.warning("Validation warnings:")
            for warning in self.warnings:
                logger.warning(f"  • {warning}")

        if not self.errors and not self.warnings:
            logger.info("✅ All mock files are valid!")
        elif not self.errors:
            logger.info("✅ All mock files are valid (with warnings)")
        else:
            logger.error("❌ Validation failed")

def main():
    """Main validation function."""
    logger.info("Starting Yahoo Finance mock validation...")

    validator = MockValidator()

    # Validate mock files
    mock_success = validator.validate_all_mocks()

    # Validate business logic
    logic_success = validator.validate_business_logic()

    # Print results
    validator.print_results()

    # Exit with appropriate code
    if mock_success and logic_success and not validator.errors:
        logger.info("Validation completed successfully")
        sys.exit(0)
    else:
        logger.error("Validation failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
