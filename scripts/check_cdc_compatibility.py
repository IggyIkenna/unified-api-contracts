#!/usr/bin/env python3
"""
Check CDC (Consumer-Driven Contract) compatibility.

Validates that each consumer's consumed_schemas.py declares only fields that exist
in the current canonical schemas (api-contracts, unified-internal-contracts).

Pattern: each consumer declares contracts/consumed_schemas.py:
  CONSUMED: dict[str, list[str]] = {
      "CanonicalTrade": ["instrument_key", "venue", "timestamp", "price", "size", "side"],
      "CanonicalDerivativeTicker": ["funding_rate", "mark_price", "open_interest"],
  }

This script asserts all declared fields exist in the current canonical schema.
Follows check_sdk_version_alignment.py pattern.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import cast

# Schema name -> (module_path, class_name) for canonical schemas
# api-contracts: unified_normalised_contracts
# unified-internal-contracts: market_data, risk, etc.
CANONICAL_SCHEMA_REGISTRY: dict[str, tuple[str, str]] = {
    "CanonicalTrade": ("api_contracts.unified_normalised_contracts", "CanonicalTrade"),
    "CanonicalOrderBook": ("api_contracts.unified_normalised_contracts", "CanonicalOrderBook"),
    "CanonicalOrder": ("api_contracts.unified_normalised_contracts", "CanonicalOrder"),
    "CanonicalFill": ("api_contracts.unified_normalised_contracts", "CanonicalFill"),
    "InstrumentRecord": ("api_contracts.unified_normalised_contracts", "InstrumentRecord"),
    "CanonicalDerivativeTicker": (
        "unified_internal_contracts.market_data",
        "CanonicalDerivativeTicker",
    ),
    "CanonicalLiquidityPool": (
        "unified_internal_contracts.market_data",
        "CanonicalLiquidityPool",
    ),
    "CanonicalSwap": ("unified_internal_contracts.market_data", "CanonicalSwap"),
    "GasCostEstimate": ("unified_internal_contracts", "GasCostEstimate"),
}

# Consumers that may have contracts/consumed_schemas.py (relative to api-contracts root)
CONSUMERS: list[tuple[str, Path]] = [
    ("market-data-processing-service", Path("../market-data-processing-service")),
    ("instruments-service", Path("../instruments-service")),
    ("execution-services", Path("../execution-services")),
    ("features-volatility-service", Path("../features-volatility-service")),
    ("features-onchain-service", Path("../features-onchain-service")),
    ("features-delta-one-service", Path("../features-delta-one-service")),
    ("features-calendar-service", Path("../features-calendar-service")),
    ("unified-market-interface", Path("../unified-market-interface")),
    ("unified-trade-execution-interface", Path("../unified-trade-execution-interface")),
    ("unified-reference-data-interface", Path("../unified-reference-data-interface")),
]


def _repo_root() -> Path:
    """api-contracts repo root (parent of scripts/)."""
    root = Path(__file__).resolve().parent.parent
    assert (root / "api_contracts").is_dir(), f"Expected api_contracts at {root}"
    return root


def _get_canonical_fields(schema_name: str) -> set[str] | None:
    """Get field names from canonical schema. Returns None if schema not found."""
    if schema_name not in CANONICAL_SCHEMA_REGISTRY:
        return None
    mod_path, class_name = CANONICAL_SCHEMA_REGISTRY[schema_name]
    try:
        mod = __import__(mod_path, fromlist=[class_name])
        cls = getattr(mod, class_name)
        if hasattr(cls, "model_fields"):
            return set(cast(dict[str, object], cls.model_fields).keys())
        if hasattr(cls, "__dataclass_fields__"):
            return set(cast(dict[str, object], cls.__dataclass_fields__).keys())
        return None
    except (ImportError, AttributeError):
        return None


def _load_consumed(consumer_path: Path) -> dict[str, list[str]] | None:
    """Load CONSUMED from consumer's contracts/consumed_schemas.py. Returns None if absent."""
    consumed = consumer_path / "contracts" / "consumed_schemas.py"
    if not consumed.exists():
        return None
    # Use importlib to load; avoid exec
    import importlib.util

    spec = importlib.util.spec_from_file_location("consumed_schemas", consumed)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "CONSUMED", None)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate consumed_schemas vs canonical schemas (CDC compatibility)."
    )
    parser.add_argument(
        "--consumer-path",
        type=str,
        default=None,
        metavar="PATH",
        help="Check only this consumer (path resolved relative to cwd). "
        "When omitted, check all CONSUMERS.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    root = _repo_root()
    errors: list[str] = []

    if args.consumer_path is not None:
        consumer_path = Path(args.consumer_path).resolve()
        if not consumer_path.exists():
            print(f"ERROR: consumer path does not exist: {consumer_path}", file=sys.stderr)
            return 1
        consumers_to_check: list[tuple[str, Path]] = [
            (consumer_path.name, consumer_path),
        ]
    else:
        consumers_to_check = [
            (name, (root / rel_path).resolve())
            for name, rel_path in CONSUMERS
        ]

    for consumer_name, consumer_path in consumers_to_check:
        if not consumer_path.exists():
            continue
        consumed = _load_consumed(consumer_path)
        if consumed is None:
            continue
        for schema_name, fields in consumed.items():
            canonical_fields = _get_canonical_fields(schema_name)
            if canonical_fields is None:
                errors.append(
                    f"{consumer_name}: schema '{schema_name}' not in canonical registry "
                    "(add to CANONICAL_SCHEMA_REGISTRY or fix schema name)"
                )
                continue
            missing = set(fields) - canonical_fields
            if missing:
                errors.append(
                    f"{consumer_name}: schema '{schema_name}' declares fields not in "
                    f"canonical: {sorted(missing)}"
                )

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print("CDC compatibility OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
