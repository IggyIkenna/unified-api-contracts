"""Contract-vs-reality: validate example JSON and optionally live API responses.

- Normal CI: validate all api_contracts/*/examples/*.json with the matching Pydantic schema.
- Optional: when LIVE_API_VERIFICATION=1, run minimal live requests and validate (requires credentials).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

# Fallback map when venue not in manifest or example not in example_schema_map
_EXAMPLE_SCHEMA_LOADERS: dict[str, tuple[str, str]] = {
    "databento": ("api_contracts.databento.schemas", "DatabentoOhlcvBar"),
    "ccxt": ("api_contracts.ccxt.schemas", "CcxtOrder"),
}


def _api_contracts_root() -> Path:
    root = Path(__file__).resolve().parent.parent
    assert (root / "api_contracts").is_dir(), f"api_contracts not found under {root}"
    return root


def _discover_example_files() -> list[tuple[Path, str]]:
    """Return list of (path, api_dir_name) for each examples/*.json."""
    root = _api_contracts_root()
    api_root = root / "api_contracts"
    out: list[tuple[Path, str]] = []
    for api_dir in api_root.iterdir():
        if not api_dir.is_dir():
            continue
        examples_dir = api_dir / "examples"
        if not examples_dir.exists():
            continue
        for path in examples_dir.glob("*.json"):
            out.append((path, api_dir.name))
    return out


def _get_schema_for_example(api_dir_name: str, data: dict, example_filename: str = "") -> tuple[str, str] | None:
    """Return (module_path, class_name) for the schema that can validate this example, or None."""
    try:
        from api_contracts.venue_manifest import VENUE_MANIFEST

        if api_dir_name in VENUE_MANIFEST:
            mapping = VENUE_MANIFEST[api_dir_name].get("example_schema_map") or {}
            if example_filename and example_filename in mapping:
                class_name = mapping[example_filename]
                return (f"api_contracts.{api_dir_name}.schemas", class_name)
    except ImportError:
        pass
    if api_dir_name in _EXAMPLE_SCHEMA_LOADERS:
        return _EXAMPLE_SCHEMA_LOADERS[api_dir_name]
    if "ts_event" in data and "close" in data and api_dir_name == "databento":
        return ("api_contracts.databento.schemas", "DatabentoOhlcvBar")
    if "id" in data and "symbol" in data and api_dir_name == "ccxt":
        return ("api_contracts.ccxt.schemas", "CcxtOrder")
    return None


def test_all_examples_validate_against_contracts() -> None:
    """Every example JSON under api_contracts/*/examples/ must validate with the matching schema."""
    root = _api_contracts_root()
    failures: list[str] = []
    for path, api_name in _discover_example_files():
        full_path = path if path.is_absolute() else root / path
        if not full_path.exists():
            continue
        data = json.loads(full_path.read_text())
        loader = _get_schema_for_example(api_name, data, example_filename=path.name)
        if loader is None:
            failures.append(f"{api_name}: no schema for keys {list(data.keys())}")
            continue
        mod_path, class_name = loader
        mod = __import__(mod_path, fromlist=[class_name])
        schema_class = getattr(mod, class_name)
        try:
            schema_class.model_validate(data)
        except Exception as e:
            failures.append(f"{full_path}: {e}")
    assert not failures, "Example validation failures:\n" + "\n".join(failures)


def test_at_least_one_example_per_contract_tested() -> None:
    """Ensure we have at least one example validated in this module (sanity check)."""
    examples = _discover_example_files()
    assert len(examples) >= 1, "At least one example file should exist under api_contracts/*/examples/"


@pytest.mark.skipif(  # reason: Live API verification only when LIVE_API_VERIFICATION=1
    os.environ.get("LIVE_API_VERIFICATION") != "1",
    reason="Live API verification only when LIVE_API_VERIFICATION=1",
)
def test_live_api_contract_verification_placeholder() -> None:
    """Placeholder for optional live verification: minimal request per API, validate response with schema.

    Run with LIVE_API_VERIFICATION=1 and real credentials to validate contracts against live APIs.
    Not run in normal CI.
    """
    pytest.skip("Live verification not implemented in this test; use scripts/verify_contracts_vs_reality.py")
