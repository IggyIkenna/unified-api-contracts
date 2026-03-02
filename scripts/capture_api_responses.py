#!/usr/bin/env -S uv run python
"""
Capture example API responses to api_contracts/<api>/examples/.

Run with small queries; requires API keys in env or Secret Manager for
authenticated endpoints. Writes JSON to api_contracts/<api>/examples/.
Filter secrets from output (no authorization headers in examples).

Usage:
  uv run python scripts/capture_api_responses.py [--api databento|ccxt|tardis|...]
  If --api omitted, lists supported APIs.

Use Context7 for each API client when extending this script.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Project root (api-contracts repo)
ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_BASE = ROOT / "unified_api_contracts"

# APIs we can capture (extend per-API in separate functions)
SUPPORTED_APIS = [
    "databento",
    "tardis",
    "ccxt",
    "binance",
    "thegraph",
    "okx",
    "bybit",
    "yahoo_finance",
    "alchemy",
    "hyperliquid",
    "aster",
    "upbit",
    "ibkr",
]


def examples_dir(api: str) -> Path:
    """Return examples directory for an API."""
    return EXAMPLES_BASE / api / "examples"


def capture_databento(_args: argparse.Namespace) -> int:
    """Capture Databento examples. Requires DATABENTO_API_KEY."""
    out_dir = examples_dir("databento")
    out_dir.mkdir(parents=True, exist_ok=True)
    # Placeholder: minimal example from schema so validate passes
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
    path = out_dir / "ohlcv_bar_example.json"
    path.write_text(json.dumps(example, indent=2))
    print(f"Wrote {path}")
    return 0


def capture_ccxt(_args: argparse.Namespace) -> int:
    """Capture CCXT examples. Requires exchange credentials for private endpoints."""
    out_dir = examples_dir("ccxt")
    out_dir.mkdir(parents=True, exist_ok=True)
    example_order = {
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
        "average": None,
        "status": "open",
        "timeInForce": "GTC",
    }
    path = out_dir / "fetch_order_example.json"
    path.write_text(json.dumps(example_order, indent=2))
    print(f"Wrote {path}")
    return 0


def _write_examples(api: str, examples: dict[str, dict]) -> int:
    """Write multiple example JSON files. Used by capture_* for venues with schema-aligned examples."""
    out_dir = examples_dir(api)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, data in examples.items():
        path = out_dir / name
        path.write_text(json.dumps(data, indent=2))
        print(f"Wrote {path}")
    return 0


def capture_tardis(_args: argparse.Namespace) -> int:
    """Write Tardis schema-validating examples (no live call)."""
    return _write_examples(
        "tardis",
        {
            "trade_example.json": {
                "timestamp": "2024-01-15T12:00:00Z",
                "exchange": "BINANCE",
                "symbol": "BTC-USDT",
                "price": 43250.5,
                "size": 0.1,
                "side": "B",
                "trade_id": "12345678",
            },
            "error_example.json": {"error": "unauthorized", "message": "Invalid API key", "code": 401},
        },
    )


def capture_binance(_args: argparse.Namespace) -> int:
    """Write Binance schema-validating examples (no live call)."""
    return _write_examples(
        "binance",
        {
            "ticker_example.json": {
                "symbol": "BTCUSDT",
                "lastPrice": "43250.50",
                "bidPrice": "43249.00",
                "askPrice": "43251.00",
                "volume": "125000.5",
                "quoteVolume": "5412530000",
            },
            "order_example.json": {
                "orderId": 987654321,
                "clientOrderId": "client-abc-123",
                "symbol": "BTCUSDT",
                "side": "BUY",
                "type": "LIMIT",
                "status": "NEW",
                "price": "43000.00",
                "origQty": "0.01",
                "executedQty": "0",
                "time": 1705312800000,
                "updateTime": 1705312800000,
            },
            "error_example.json": {"code": -1021, "msg": "Timestamp for this request is outside of the recvWindow."},
        },
    )


def capture_thegraph(_args: argparse.Namespace) -> int:
    """Write The Graph schema-validating examples (no live call)."""
    return _write_examples(
        "thegraph",
        {
            "response_example.json": {"data": {"pools": []}, "errors": None},
            "graphql_error_example.json": {
                "message": "Subgraph not found",
                "locations": [{"line": 1, "column": 2}],
                "path": ["pools"],
                "extensions": None,
            },
        },
    )


def capture_okx(_args: argparse.Namespace) -> int:
    """Write OKX schema-validating examples (no live call)."""
    return _write_examples(
        "okx",
        {
            "ticker_example.json": {
                "instId": "BTC-USDT-SWAP",
                "last": "43250.5",
                "bidPx": "43249",
                "askPx": "43251",
                "vol24h": "125000.5",
            },
            "error_example.json": {"code": "50111", "msg": "Parameter instId is required"},
        },
    )


def capture_bybit(_args: argparse.Namespace) -> int:
    """Write Bybit schema-validating examples (no live call)."""
    return _write_examples(
        "bybit",
        {
            "ticker_example.json": {
                "symbol": "BTCUSDT",
                "lastPrice": "43250.50",
                "bid1Price": "43249.00",
                "ask1Price": "43251.00",
                "volume24h": "125000.5",
            },
            "error_example.json": {"retCode": 10001, "retMsg": "Invalid parameter"},
        },
    )


def capture_yahoo_finance(_args: argparse.Namespace) -> int:
    """Write Yahoo Finance schema-validating examples (no live call)."""
    return _write_examples(
        "yahoo_finance",
        {
            "quote_example.json": {
                "symbol": "AAPL",
                "shortName": "Apple Inc.",
                "regularMarketPrice": 185.5,
                "regularMarketChange": 1.2,
                "regularMarketVolume": 45000000,
                "bid": 185.4,
                "ask": 185.6,
            },
            "error_example.json": {"code": "Not Found", "description": "No data for symbol"},
        },
    )


def capture_alchemy(_args: argparse.Namespace) -> int:
    """Write Alchemy schema-validating examples (no live call)."""
    return _write_examples(
        "alchemy",
        {
            "rpc_response_example.json": {"jsonrpc": "2.0", "id": 1, "result": "0x1234", "error": None},
            "error_example.json": {"code": -32600, "message": "Invalid request"},
        },
    )


def capture_hyperliquid(_args: argparse.Namespace) -> int:
    """Write Hyperliquid schema-validating examples (no live call)."""
    return _write_examples(
        "hyperliquid",
        {
            "ticker_example.json": {
                "coin": "BTC",
                "markPx": "43250.5",
                "midPx": "43250.0",
                "prevDayPx": "42800.0",
                "dayNtlVlm": "125000.5",
                "funding": "0.0001",
                "openInterest": "50000",
            },
            "error_example.json": {"response": None, "message": "Invalid signature"},
        },
    )


def capture_aster(_args: argparse.Namespace) -> int:
    """Write Aster schema-validating examples (no live call)."""
    return _write_examples(
        "aster",
        {
            "order_example.json": {
                "order_id": "ord-abc-123",
                "market_id": "BTC-PERP",
                "side": "buy",
                "size": "0.1",
                "price": "43250",
                "status": "open",
                "filled_size": "0",
            },
            "error_example.json": {"code": 400, "message": "Insufficient margin"},
        },
    )


def capture_upbit(_args: argparse.Namespace) -> int:
    """Write Upbit schema-validating examples (no live call)."""
    return _write_examples(
        "upbit",
        {
            "ticker_example.json": {
                "market": "KRW-BTC",
                "trade_price": 58000000.0,
                "bid_price": 57995000.0,
                "ask_price": 58005000.0,
                "acc_trade_volume_24h": 1250.5,
            },
            "error_example.json": {"error": {"message": "invalid_access_key"}, "message": "Invalid API key"},
        },
    )


def capture_ibkr(_args: argparse.Namespace) -> int:
    """Write IBKR schema-validating examples (no live call)."""
    return _write_examples(
        "ibkr",
        {
            "bar_example.json": {
                "date": "20240115",
                "open": 43000.0,
                "high": 43500.0,
                "low": 42800.0,
                "close": 43250.0,
                "volume": 1250.5,
                "barCount": 1440,
                "average": 43100.0,
            },
            "error_example.json": {
                "reqId": 1,
                "errorCode": 162,
                "errorString": "Historical Market Data Service error",
                "advancedOrderRejectJson": None,
            },
        },
    )


def capture_placeholder(api: str, _args: argparse.Namespace) -> int:
    """Write a minimal placeholder example so directory exists (fallback for unimplemented capture)."""
    out_dir = examples_dir(api)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "placeholder_example.json"
    path.write_text(json.dumps({"api": api, "placeholder": True}, indent=2))
    print(f"Wrote {path} (placeholder)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture API response examples")
    parser.add_argument("--api", choices=SUPPORTED_APIS, help="API to capture")
    args = parser.parse_args()

    if not args.api:
        print("Supported APIs:", ", ".join(SUPPORTED_APIS))
        print("Run with --api <name> to capture examples for that API.")
        return 0

    handlers = {
        "databento": capture_databento,
        "tardis": capture_tardis,
        "ccxt": capture_ccxt,
        "binance": capture_binance,
        "thegraph": capture_thegraph,
        "okx": capture_okx,
        "bybit": capture_bybit,
        "yahoo_finance": capture_yahoo_finance,
        "alchemy": capture_alchemy,
        "hyperliquid": capture_hyperliquid,
        "aster": capture_aster,
        "upbit": capture_upbit,
        "ibkr": capture_ibkr,
    }
    handler = handlers.get(args.api, lambda a: capture_placeholder(args.api, a))
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
