#!/usr/bin/env -S uv run python
"""
Collect real API responses using Context7 for schema validation.

Uses unified-config-interface for configuration and Secret Manager for API keys.
Collects responses for high-priority venues: Binance, Coinbase.
Outputs to collected_responses/{venue}/*.json for later schema validation.

Usage:
    # Collect all venues
    LIVE_API_VERIFICATION=1 uv run python scripts/collect_responses.py

    # Collect specific venue
    LIVE_API_VERIFICATION=1 uv run python scripts/collect_responses.py --venue binance

    # List supported venues
    uv run python scripts/collect_responses.py --list

Dependencies (install from workspace):
    uv pip install -e ../unified-trading-services -e ../unified-config-interface
    uv pip install requests ccxt
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

# Project root
ROOT = Path(__file__).resolve().parent.parent
COLLECTED_RESPONSES_DIR = ROOT / "collected_responses"

# High-priority venues for this phase
SUPPORTED_VENUES = ["binance", "coinbase"]

# Common endpoints to collect for each venue
ENDPOINT_PATTERNS = {
    "ticker": "24hr ticker statistics",
    "orderbook": "Current order book snapshot",
    "recent_trades": "Recent trades list",
    "klines": "Kline/candlestick data",
    "exchange_info": "Exchange trading rules and symbol information",
}


def setup_output_dir(venue: str) -> Path:
    """Create output directory for venue responses."""
    output_dir = COLLECTED_RESPONSES_DIR / venue
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def load_context7_config():
    """Load Context7 configuration via unified-config-interface."""
    if not os.getenv("LIVE_API_VERIFICATION"):
        print("Set LIVE_API_VERIFICATION=1 to enable real API collection")
        return None

    try:
        from unified_config_interface import UnifiedCloudConfig
        return UnifiedCloudConfig()
    except ImportError:
        print(
            "Context7 requires unified-config-interface. "
            "Install: uv pip install -e ../unified-trading-services -e ../unified-config-interface",
            file=sys.stderr,
        )
        return None


def get_secret_safely(config: object, secret_name: str) -> str | None:
    """Get secret via Context7 (unified-trading-services) safely."""
    if not config:
        return None

    try:
        from unified_trading_services import get_secret_with_fallback

        project_id = getattr(config, "gcp_project_id", None) or getattr(config, "project_id", None)
        if not project_id:
            print("Warning: No GCP project ID configured, using environment variables only")
            return os.getenv(secret_name)

        return get_secret_with_fallback(
            secret_name=secret_name,
            project_id=project_id,
            env_fallback_key=secret_name,
        )
    except Exception as e:
        print(f"Warning: Secret retrieval failed for {secret_name}: {e}")
        return os.getenv(secret_name)


def save_response(venue: str, endpoint: str, data: dict[str, Any], metadata: dict[str, Any] | None = None) -> None:
    """Save API response to JSON file with metadata."""
    output_dir = setup_output_dir(venue)

    # Create response wrapper with metadata
    response_data = {
        "endpoint": endpoint,
        "timestamp": time.time(),
        "venue": venue,
        "metadata": metadata or {},
        "response": data,
    }

    # Save with timestamp in filename for uniqueness
    timestamp_str = str(int(time.time()))
    filename = f"{endpoint}_{timestamp_str}.json"
    filepath = output_dir / filename

    with filepath.open("w") as f:
        json.dump(response_data, f, indent=2, default=str)

    print(f"✅ Saved {venue} {endpoint} response to {filepath}")


def collect_binance_responses(config: object) -> int:
    """Collect Binance responses via REST API."""
    print("🔄 Collecting Binance API responses...")

    base_url = "https://api.binance.com/api/v3"

    # Public endpoints (no API key required)
    endpoints = {
        "ticker": f"{base_url}/ticker/24hr?symbol=BTCUSDT",
        "orderbook": f"{base_url}/depth?symbol=BTCUSDT&limit=10",
        "recent_trades": f"{base_url}/trades?symbol=BTCUSDT&limit=10",
        "klines": f"{base_url}/klines?symbol=BTCUSDT&interval=1h&limit=10",
        "exchange_info": f"{base_url}/exchangeInfo",
    }

    collected = 0
    for endpoint_name, url in endpoints.items():
        try:
            print(f"  Fetching {endpoint_name}...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            save_response(
                venue="binance",
                endpoint=endpoint_name,
                data=response.json(),
                metadata={
                    "url": url,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                }
            )
            collected += 1

            # Rate limiting courtesy
            time.sleep(0.5)

        except Exception as e:
            print(f"❌ Failed to collect Binance {endpoint_name}: {e}")

    print(f"✅ Collected {collected}/5 Binance endpoints")
    return 0 if collected > 0 else 1


def collect_coinbase_responses(config: object) -> int:
    """Collect Coinbase Advanced Trade API responses."""
    print("🔄 Collecting Coinbase API responses...")

    base_url = "https://api.exchange.coinbase.com"

    # Public endpoints
    endpoints = {
        "ticker": f"{base_url}/products/BTC-USD/ticker",
        "orderbook": f"{base_url}/products/BTC-USD/book?level=2",
        "recent_trades": f"{base_url}/products/BTC-USD/trades",
        "candles": f"{base_url}/products/BTC-USD/candles?granularity=3600",
        "exchange_info": f"{base_url}/products",
    }

    collected = 0
    for endpoint_name, url in endpoints.items():
        try:
            print(f"  Fetching {endpoint_name}...")
            headers = {"User-Agent": "api-contracts-validation/1.0"}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            save_response(
                venue="coinbase",
                endpoint=endpoint_name,
                data=response.json(),
                metadata={
                    "url": url,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                }
            )
            collected += 1

            # Rate limiting courtesy
            time.sleep(0.5)

        except Exception as e:
            print(f"❌ Failed to collect Coinbase {endpoint_name}: {e}")

    print(f"✅ Collected {collected}/5 Coinbase endpoints")
    return 0 if collected > 0 else 1


def collect_all_venues(config: object) -> int:
    """Collect responses from all supported venues."""
    print("🚀 Starting API response collection for schema validation...")
    print(f"Output directory: {COLLECTED_RESPONSES_DIR}")

    collectors = {
        "binance": collect_binance_responses,
        "coinbase": collect_coinbase_responses,
    }

    total_errors = 0
    for venue, collector in collectors.items():
        print(f"\n📊 === {venue.upper()} ===")
        result = collector(config)
        total_errors += result

    print(f"\n✅ Collection complete. Errors: {total_errors}")
    print(f"📁 Responses saved to: {COLLECTED_RESPONSES_DIR}")
    return total_errors


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Collect real API responses for schema validation using Context7",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--venue",
        choices=SUPPORTED_VENUES,
        help="Specific venue to collect (default: all)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List supported venues",
    )

    args = parser.parse_args()

    if args.list:
        print("Supported venues:")
        for venue in SUPPORTED_VENUES:
            print(f"  {venue}")
        return 0

    # Load Context7 config
    config = load_context7_config()
    if not config and os.getenv("LIVE_API_VERIFICATION"):
        return 1

    # Collect responses
    if args.venue:
        collectors = {
            "binance": collect_binance_responses,
            "coinbase": collect_coinbase_responses,
        }
        return collectors[args.venue](config)
    else:
        return collect_all_venues(config)


if __name__ == "__main__":
    sys.exit(main())
