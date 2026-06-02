"""Regression test: all data_types used across config + YAML must be UAC canonical.

Prevents recurrence of the 2026-05-23 canonicalization incident where:
- venue_data_types.yaml used 'swaps', 'liquidity', 'rate_indices'
- UAC canonical names are 'dex_swaps', 'dex_pools', 'lending_indices'
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from unified_api_contracts.registry.market_data_categories import (
    DATA_TYPES_BY_ASSET_GROUP,
)

_YAML_PATHS = [
    Path(__file__).parent.parent.parent / "unified-trading-pm" / "configs" / "venue_data_types.yaml",
    Path(__file__).parent.parent.parent / "market-tick-data-service" / "configs" / "venue_data_types.yaml",
]

_ALL_UAC_DATA_TYPES: frozenset[str] = frozenset(dt for dts in DATA_TYPES_BY_ASSET_GROUP.values() for dt in dts)

# These appear in YAML as non-data-type fields (field names in GCS records or
# domain-level metadata keys, not GCS data type identifiers)
_YAML_SKIP_KEYS = frozenset(
    {
        "domain",
        "book_type",
        "fee_type",
        "pool_version",
        "instrument_types",
        "accessible_instrument_types",
        "folders",
        "data_types",
        "common_data_types",
        "venues",
        "start_date",
        "underlyings",
        "notes",
        "default",
        "tick_window",
        "folder_mappings",
        "tick_windows",
        "start",
        "end",
        "description",
        "path_structure",
    }
)

# Strings that appear in data_types lists but are intentionally not in UAC
# (e.g. processed aggregate types managed by MDPS, not raw tick types)
_KNOWN_MDPS_DERIVED = frozenset(
    {
        "ohlcv_1m",
        "ohlcv_15m",
        "ohlcv_24h",
        "tbbo",
        "options_chain",
        "futures_chain",
        "evm_defi_lending",
        "evm_defi_amm",
    }
)

# Banned legacy aliases that must never appear in any data_types list.
# 2026-06-02 (A11c): the DeFi pool/swap data_type collapsed to the operator-locked
# canonical `dex_pool_state` / `dex_pool_swaps` everywhere (defi-canonical-naming-ssot.md),
# so the former canonical names `dex_pools` / `dex_swaps` are now THEMSELVES banned legacy aliases.
_BANNED_ALIASES = {
    "swaps": "dex_pool_swaps",
    "liquidity": "dex_pool_state",
    "dex_swaps": "dex_pool_swaps",
    "dex_pools": "dex_pool_state",
    "rate_indices": "lending_indices",
    "mev_bundles": "mev_events",
    "bridge_flows": "bridge_events",
    "flash_loans": "flash_loan_events",
}


def _extract_data_types_from_yaml(path: Path) -> list[tuple[str, str, str]]:
    """Yield (yaml_path, section_key, data_type) from all data_types lists in the YAML."""
    if not path.exists():
        return []
    with path.open() as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        return []

    results: list[tuple[str, str, str]] = []
    for domain_key, domain_val in raw.items():
        if not isinstance(domain_val, dict):
            continue
        # Top-level common_data_types
        for dt in domain_val.get("common_data_types", []):
            results.append((str(path.name), f"{domain_key}.common_data_types", dt))
        # Per-venue data_types
        venues = domain_val.get("venues", {})
        if isinstance(venues, dict):
            for venue_key, venue_val in venues.items():
                if not isinstance(venue_val, dict):
                    continue
                dts = venue_val.get("data_types", [])
                if isinstance(dts, list):
                    for dt in dts:
                        results.append((str(path.name), f"{domain_key}.venues.{venue_key}", dt))
                elif isinstance(dts, dict):
                    for sub_key, sub_list in dts.items():
                        if isinstance(sub_list, list):
                            for dt in sub_list:
                                results.append((str(path.name), f"{domain_key}.venues.{venue_key}.{sub_key}", dt))
    return results


@pytest.mark.parametrize("yaml_path", _YAML_PATHS, ids=[p.parent.parent.name for p in _YAML_PATHS])
def test_no_banned_aliases_in_yaml(yaml_path: Path) -> None:
    """venue_data_types.yaml must not use any legacy alias names."""
    entries = _extract_data_types_from_yaml(yaml_path)
    violations = [
        f"{section}: '{dt}' must be renamed to '{_BANNED_ALIASES[dt]}'"
        for (_fname, section, dt) in entries
        if dt in _BANNED_ALIASES
    ]
    assert not violations, f"Legacy data type aliases found in {yaml_path.name}:\n" + "\n".join(violations)


@pytest.mark.parametrize("yaml_path", _YAML_PATHS, ids=[p.parent.parent.name for p in _YAML_PATHS])
def test_yaml_data_types_in_uac(yaml_path: Path) -> None:
    """All data_types listed in venue_data_types.yaml must exist in UAC DATA_TYPES_BY_ASSET_GROUP."""
    entries = _extract_data_types_from_yaml(yaml_path)
    unknown = [
        f"{section}: '{dt}'"
        for (_fname, section, dt) in entries
        if dt not in _ALL_UAC_DATA_TYPES and dt not in _KNOWN_MDPS_DERIVED
    ]
    assert not unknown, (
        f"Data types in {yaml_path.name} not registered in UAC DATA_TYPES_BY_ASSET_GROUP:\n"
        + "\n".join(unknown)
        + "\n\nAdd them to unified_api_contracts/registry/market_data_categories.py"
    )


def test_uac_canonical_defi_names_present() -> None:
    """UAC must register the canonical DeFi data type names (not legacy aliases).

    Canonical pool/swap names are `dex_pool_state` / `dex_pool_swaps` (operator-locked
    collapse 2026-06-01, A11c); the former `dex_pools` / `dex_swaps` are now legacy.
    """
    defi_types = DATA_TYPES_BY_ASSET_GROUP.get("defi", frozenset())
    assert "dex_pool_swaps" in defi_types, "'dex_pool_swaps' missing from UAC defi data types"
    assert "dex_pool_state" in defi_types, "'dex_pool_state' missing from UAC defi data types"
    assert "lending_indices" in defi_types, "'lending_indices' missing from UAC defi data types"
    assert "swaps" not in defi_types, "Legacy 'swaps' alias must not be in UAC defi data types"
    assert "liquidity" not in defi_types, "Legacy 'liquidity' alias must not be in UAC defi data types"
    assert "dex_swaps" not in defi_types, "Legacy 'dex_swaps' alias must not be in UAC defi data types"
    assert "dex_pools" not in defi_types, "Legacy 'dex_pools' alias must not be in UAC defi data types"
    assert "rate_indices" not in defi_types, "Legacy 'rate_indices' alias must not be in UAC defi data types"


def test_prediction_types_not_in_shard_frozenset() -> None:
    """Retired prediction types must not appear in per-instrument shard data types."""
    from unified_api_contracts.registry.market_data_categories import (
        _PER_INSTRUMENT_SHARD_DATA_TYPES,
    )

    retired = {"prediction_trades", "prediction_book_snapshot", "prediction_market_metadata"}
    still_present = retired & _PER_INSTRUMENT_SHARD_DATA_TYPES
    assert not still_present, f"Retired prediction types still in _PER_INSTRUMENT_SHARD_DATA_TYPES: {still_present}"
