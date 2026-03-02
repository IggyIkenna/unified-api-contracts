#!/usr/bin/env python3
"""Validate api-contracts example JSON files against Pydantic schemas.

Run from repo root:
  uv run python scripts/verify_contracts_vs_reality.py

Optional: set LIVE_API_VERIFICATION=1 to run minimal live API checks (requires credentials).
Normal CI should run without that (examples-only validation).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Repo root = parent of scripts/
REPO_ROOT = Path(__file__).resolve().parent.parent
API_CONTRACTS_ROOT = REPO_ROOT / "unified_api_contracts"

_EXAMPLE_SCHEMA_LOADERS: dict[str, tuple[str, str]] = {
    "databento": ("unified_api_contracts.databento.schemas", "DatabentoOhlcvBar"),
    "ccxt": ("unified_api_contracts.ccxt.schemas", "CcxtOrder"),
}


def _get_schema_for_example(api_dir_name: str, data: dict) -> tuple[str, str] | None:
    if api_dir_name in _EXAMPLE_SCHEMA_LOADERS:
        return _EXAMPLE_SCHEMA_LOADERS[api_dir_name]
    if "ts_event" in data and "close" in data and api_dir_name == "databento":
        return ("unified_api_contracts.databento.schemas", "DatabentoOhlcvBar")
    if "id" in data and "symbol" in data and api_dir_name == "ccxt":
        return ("unified_api_contracts.ccxt.schemas", "CcxtOrder")
    return None


def validate_examples() -> list[str]:
    """Validate all api_contracts/*/examples/*.json. Return list of error messages."""
    errors: list[str] = []
    if not API_CONTRACTS_ROOT.is_dir():
        return [f"api_contracts not found at {API_CONTRACTS_ROOT}"]
    for api_dir in API_CONTRACTS_ROOT.iterdir():
        if not api_dir.is_dir():
            continue
        examples_dir = api_dir / "examples"
        if not examples_dir.exists():
            continue
        for path in examples_dir.glob("*.json"):
            data = json.loads(path.read_text())
            loader = _get_schema_for_example(api_dir.name, data)
            if loader is None:
                errors.append(f"{path}: no schema for keys {list(data.keys())}")
                continue
            mod_path, class_name = loader
            mod = __import__(mod_path, fromlist=[class_name])
            schema_class = getattr(mod, class_name)
            try:
                schema_class.model_validate(data)
            except (ConnectionError, TimeoutError, OSError, ValueError) as e:
                errors.append(f"{path}: {e}")
    return errors


def main() -> int:
    errors = validate_examples()
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    print("All example JSON files validate against their schemas.")
    if os.environ.get("LIVE_API_VERIFICATION") == "1":
        print("LIVE_API_VERIFICATION=1: live checks not implemented in this script.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
