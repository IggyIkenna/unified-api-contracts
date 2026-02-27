#!/usr/bin/env -S uv run python
"""
Schema validation tool - compare existing schemas against real API responses.

Reads collected responses from collected_responses/{venue}/*.json and validates
them against existing schemas in api_contracts/{venue}/schemas.py.

Reports mismatches, missing fields, type errors, and suggests schema improvements.

Usage:
    # Validate all venues
    uv run python scripts/validate_schemas.py

    # Validate specific venue
    uv run python scripts/validate_schemas.py --venue binance

    # Generate new schemas from responses
    uv run python scripts/validate_schemas.py --generate-schemas --venue coinbase

Output:
    - Validation report with mismatches
    - Suggested schema improvements
    - New schema classes for missing venues
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

# Project root
ROOT = Path(__file__).resolve().parent.parent
COLLECTED_RESPONSES_DIR = ROOT / "collected_responses"

# Import existing schemas
sys.path.append(str(ROOT))


class ValidationResult:
    """Result of schema validation with detailed feedback."""

    def __init__(self, venue: str, endpoint: str):
        self.venue = venue
        self.endpoint = endpoint
        self.is_valid = True
        self.missing_fields: set[str] = set()
        self.extra_fields: set[str] = set()
        self.type_mismatches: dict[str, tuple] = {}
        self.validation_errors: list[str] = []
        self.sample_data: dict[str, Any] = {}


def load_response_files(venue: str) -> dict[str, list[dict]]:
    """Load all collected response files for a venue."""
    venue_dir = COLLECTED_RESPONSES_DIR / venue
    if not venue_dir.exists():
        return {}

    responses = {}
    for file_path in venue_dir.glob("*.json"):
        try:
            with file_path.open() as f:
                data = json.load(f)
                endpoint = data.get("endpoint", "unknown")

                if endpoint not in responses:
                    responses[endpoint] = []
                responses[endpoint].append(data["response"])
        except Exception as e:
            print(f"Warning: Failed to load {file_path}: {e}")

    return responses


def get_existing_schema(venue: str, schema_class_name: str) -> BaseModel | None:
    """Import and return existing schema class."""
    try:
        module_name = f"api_contracts.{venue}.schemas"
        module = __import__(module_name, fromlist=[schema_class_name])
        return getattr(module, schema_class_name, None)
    except ImportError:
        return None


def analyze_field_types(data: dict[str, Any]) -> dict[str, str]:
    """Analyze field types from sample data and suggest proper Pydantic types."""
    field_types = {}

    if not isinstance(data, dict):
        print(f"Warning: Expected dict but got {type(data)}: {data}")
        return field_types

    for field, value in data.items():
        if value is None:
            field_types[field] = "Any | None"
        elif isinstance(value, bool):
            field_types[field] = "bool"
        elif isinstance(value, int):
            # Check if it looks like a timestamp
            timestamp_fields = ['time', 'timestamp', 'opentime', 'closetime']
            if field.lower() in timestamp_fields or (str(value).isdigit() and len(str(value)) >= 10):
                field_types[field] = "int  # timestamp"
            else:
                field_types[field] = "int"
        elif isinstance(value, float):
            field_types[field] = "float"
        elif isinstance(value, str):
            # Check if it's a numeric string (price/quantity)
            if field.lower() in ['price', 'qty', 'quantity', 'volume', 'amount'] or is_numeric_string(value):
                field_types[field] = "Decimal  # Use Decimal for financial precision"
            else:
                field_types[field] = "str"
        elif isinstance(value, list):
            if value and isinstance(value[0], list):
                field_types[field] = "list[list[str]]  # order book format"
            else:
                field_types[field] = "list[Any]"
        elif isinstance(value, dict):
            field_types[field] = "dict[str, Any]"
        else:
            field_types[field] = "Any"

    return field_types


def is_numeric_string(value: str) -> bool:
    """Check if string represents a decimal number."""
    try:
        float(value)
        return True
    except ValueError:
        return False


def validate_venue_responses(venue: str) -> list[ValidationResult]:
    """Validate all responses for a venue against existing schemas."""
    results = []

    responses = load_response_files(venue)
    if not responses:
        print(f"No collected responses found for {venue}")
        return results

    # Map endpoints to schema classes (venue-specific mappings)
    if venue == "coinbase":
        endpoint_schema_map = {
            "ticker": "CoinbaseTicker",
            "orderbook": "CoinbaseOrderBook",
            "recent_trades": "CoinbaseTrade",
            "candles": "CoinbaseCandle",
            "exchange_info": "CoinbaseProduct",
        }
    else:
        # Default mappings for other venues (like Binance)
        endpoint_schema_map = {
            "ticker": f"{venue.capitalize()}Ticker",
            "orderbook": f"{venue.capitalize()}OrderBook",
            "order": f"{venue.capitalize()}Order",
            "position": f"{venue.capitalize()}Position",
            "trade": f"{venue.capitalize()}Trade",
            "recent_trades": f"{venue.capitalize()}Trade",
            "balance": f"{venue.capitalize()}Balance",
            "klines": f"{venue.capitalize()}Kline",
            "exchange_info": f"{venue.capitalize()}ExchangeInfo",
            "candles": f"{venue.capitalize()}Candle",
            "ohlc": f"{venue.capitalize()}OHLC",
        }

    for endpoint, response_list in responses.items():
        result = ValidationResult(venue, endpoint)

        if not response_list:
            continue

        # Use first response as sample
        sample_response = response_list[0]

        # Try to find corresponding schema
        schema_class_name = endpoint_schema_map.get(endpoint)
        if schema_class_name:
            schema_class = get_existing_schema(venue, schema_class_name)

            if schema_class:
                # Validate against existing schema
                try:
                    # Handle list responses (like trades)
                    if isinstance(sample_response, list):
                        if sample_response:
                            # Handle nested lists (klines) vs dict lists (trades)
                            if isinstance(sample_response[0], list):
                                # Special case for klines - use from_list method if available
                                if hasattr(schema_class, 'from_list'):
                                    schema_class.from_list(sample_response[0])
                                else:
                                    # Can't validate positional data without from_list method
                                    result.is_valid = False
                                    result.validation_errors = ["Positional list data requires from_list method"]
                            else:
                                # Validate first dict item in list
                                schema_class(**sample_response[0])
                        result.is_valid = True
                    else:
                        schema_class(**sample_response)
                        result.is_valid = True
                except (ValidationError, TypeError) as e:
                    result.is_valid = False
                    result.validation_errors = [str(e)]

                # Analyze field differences
                schema_fields = set(schema_class.model_fields.keys())

                # Handle list responses
                if isinstance(sample_response, list):
                    if sample_response:
                        # Handle nested lists (like klines)
                        if isinstance(sample_response[0], list):
                            # For klines, we'll skip field analysis since it's positional data
                            response_fields = set()
                            comparison_data = {}
                        else:
                            response_fields = set(sample_response[0].keys())
                            comparison_data = sample_response[0]
                    else:
                        response_fields = set()
                        comparison_data = {}
                else:
                    response_fields = set(sample_response.keys())
                    comparison_data = sample_response

                result.missing_fields = response_fields - schema_fields
                result.extra_fields = schema_fields - response_fields
                result.sample_data = comparison_data  # Store processed data for schema generation

                # Check type mismatches
                for field in schema_fields & response_fields:
                    schema_type = schema_class.model_fields[field].annotation
                    actual_value = comparison_data[field]
                    if not _is_type_compatible(actual_value, schema_type):
                        result.type_mismatches[field] = (type(actual_value).__name__, str(schema_type))
            else:
                result.is_valid = False
                result.validation_errors.append(f"Schema class {schema_class_name} not found")
        else:
            result.is_valid = False
            result.validation_errors.append(f"No schema mapping for endpoint {endpoint}")
            # Still store sample data for potential schema generation
            if isinstance(sample_response, list) and sample_response:
                result.sample_data = sample_response[0]
            else:
                result.sample_data = sample_response

        results.append(result)

    return results


def _is_type_compatible(value: Any, schema_type: type) -> bool:
    """Check if actual value is compatible with schema type annotation."""
    # Simplified type checking - could be more sophisticated
    if value is None:
        return True  # Most fields are optional

    # Handle Union types (like str | None)
    if hasattr(schema_type, '__args__'):
        return any(_is_type_compatible(value, arg) for arg in schema_type.__args__)

    return bool((schema_type is str and isinstance(value, str)) or (schema_type is int and isinstance(value, int)) or (schema_type is float and isinstance(value, (int, float))) or (schema_type is bool and isinstance(value, bool)))


def generate_schema_class(venue: str, endpoint: str, sample_data: dict[str, Any] | list) -> str:
    """Generate a complete Pydantic schema class from sample data."""
    class_name = f"{venue.capitalize()}{endpoint.replace('_', '').capitalize()}"

    # Handle list responses
    if isinstance(sample_data, list):
        if sample_data:
            analysis_data = sample_data[0]
            class_name += "Item"  # For list items
        else:
            analysis_data = {}
    else:
        analysis_data = sample_data

    field_types = analyze_field_types(analysis_data)

    imports = ["from pydantic import BaseModel"]
    if any("Decimal" in field_type for field_type in field_types.values()):
        imports.append("from decimal import Decimal")

    class_definition = f"""
{' '.join(imports)}


class {class_name}(BaseModel):
    \"\"\"{venue.capitalize()} {endpoint} response.\"\"\"

"""

    for field, field_type in field_types.items():
        # Make most fields optional since API responses can vary
        if "| None" not in field_type and field_type != "Any":
            field_type += " | None = None"
        elif field_type == "Any":
            field_type = "Any | None = None"

        class_definition += f"    {field}: {field_type}\n"

    return class_definition.strip()


def print_validation_report(results: list[ValidationResult]) -> None:
    """Print comprehensive validation report."""
    print("🔍 API Schema Validation Report")
    print("=" * 50)

    total_endpoints = len(results)
    valid_endpoints = sum(1 for r in results if r.is_valid)

    print(f"📊 Summary: {valid_endpoints}/{total_endpoints} endpoints validate successfully")
    print()

    for result in results:
        status = "✅" if result.is_valid else "❌"
        print(f"{status} {result.venue}.{result.endpoint}")

        if not result.is_valid:
            if result.validation_errors:
                print(f"   Errors: {', '.join(result.validation_errors[:2])}")

            if result.missing_fields:
                print(f"   Missing fields in schema: {', '.join(list(result.missing_fields)[:5])}")

            if result.extra_fields:
                print(f"   Extra fields in schema: {', '.join(list(result.extra_fields)[:5])}")

            if result.type_mismatches:
                for field, (actual, expected) in list(result.type_mismatches.items())[:3]:
                    print(f"   Type mismatch {field}: got {actual}, expected {expected}")
        else:
            # Show details even for "valid" schemas to check for missing fields
            if result.missing_fields:
                print(f"   ⚠️  API has extra fields: {', '.join(list(result.missing_fields)[:5])}")
            if result.extra_fields:
                print(f"   ⚠️  Schema has unused fields: {', '.join(list(result.extra_fields)[:5])}")
            if result.type_mismatches:
                print(f"   ⚠️  Type issues: {len(result.type_mismatches)} fields")

        print()


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate API contracts against real responses",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--venue",
        choices=["binance", "coinbase"],
        help="Specific venue to validate (default: all)",
    )
    parser.add_argument(
        "--generate-schemas",
        action="store_true",
        help="Generate new schema classes from responses",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "generated_schemas",
        help="Output directory for generated schemas",
    )

    args = parser.parse_args()

    venues = [args.venue] if args.venue else ["binance", "coinbase"]

    all_results = []
    for venue in venues:
        print(f"🔄 Validating {venue} schemas...")
        results = validate_venue_responses(venue)
        all_results.extend(results)

        if args.generate_schemas:
            # Generate new schemas for missing/invalid endpoints
            args.output_dir.mkdir(exist_ok=True)

            for result in results:
                if not result.is_valid and result.sample_data:
                    schema_code = generate_schema_class(venue, result.endpoint, result.sample_data)

                    output_file = args.output_dir / f"{venue}_{result.endpoint}_schema.py"
                    with output_file.open("w") as f:
                        f.write(schema_code)

                    print(f"📝 Generated schema: {output_file}")

    print_validation_report(all_results)

    # Return exit code based on validation success
    failed_count = sum(1 for r in all_results if not r.is_valid)
    return 1 if failed_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
