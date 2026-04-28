#!/usr/bin/env python3
"""Generate ui-reference-data.json from UAC registries.

Extracts all 13 registry categories into a single deterministic JSON file
that UIs consume for reference data (dropdowns, validation, display labels).

Usage:
    python scripts/generate_ui_reference_data.py [--output path]

Output: ui-reference-data.json with sorted keys and stable ordering.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Ensure UAC is importable
_repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_repo_root))

from unified_api_contracts.canonical.crosscutting.errors import (
    VENUE_ERROR_MAP,
)
from unified_api_contracts.canonical.crosscutting.risk_taxonomy import (
    RISK_TYPE_CATEGORIES,
    RiskCategory,
    RiskType,
)
from unified_api_contracts.registry import (
    CAPABILITY_DECLARATIONS,
    CEFI_BASE_ASSETS,
    CHAIN_RPC_TEMPLATES,
    CME_MONTH_CODES,
    DATA_TYPES_BY_ASSET_GROUP,
    DEFI_INSTRUMENTS,
    DEFI_LENDING_ASSETS,
    DEFI_POOL_PAIRS,
    DEFI_PROTOCOLS,
    DEFI_VENUE_TO_PROTOCOL,
    INSTRUCTION_CONSTRAINTS,
    OPTIONS_CHAIN_CONFIG,
    QUARTERLY_MONTHS,
    SPORTS_LEAGUES,
    SUBGRAPH_IDS,
    TIMEFRAMES,
    TRADFI_EQUITIES,
    TRADFI_FUTURES,
    VENUES_BY_ASSET_GROUP,
)
from unified_api_contracts.registry.venue_rate_limits import VENUE_RATE_LIMITS


def _get_version() -> str:
    """Read version from pyproject.toml."""
    pyproject = _repo_root / "pyproject.toml"
    for line in pyproject.read_text().splitlines():
        if line.strip().startswith("version"):
            return line.split("=")[1].strip().strip('"')
    return "unknown"


def _serialize_venue_error_map() -> dict[str, list[dict[str, Any]]]:
    """Serialize VENUE_ERROR_MAP to JSON-safe dicts."""
    result: dict[str, list[dict[str, Any]]] = {}
    for venue in sorted(VENUE_ERROR_MAP):
        classifications = VENUE_ERROR_MAP[venue]
        result[venue] = [
            {
                "venue": c.venue,
                "error_code": c.error_code,
                "retry_safe": c.retry_safe,
                "reconnect": c.reconnect,
                "action": c.action.value if hasattr(c.action, "value") else str(c.action),
                "description": c.description,
            }
            for c in sorted(classifications, key=lambda x: x.error_code)
        ]
    return result


def _serialize_instruction_constraints() -> dict[str, dict[str, Any]]:
    """Serialize INSTRUCTION_CONSTRAINTS to JSON-safe dicts."""
    result: dict[str, dict[str, Any]] = {}
    for itype in sorted(INSTRUCTION_CONSTRAINTS):
        c = INSTRUCTION_CONSTRAINTS[itype]
        result[itype] = {
            "order_types": sorted(c["order_types"]),
            "instrument_types": sorted(c["instrument_types"]),
            "venue_categories": sorted(c["venue_categories"]),
            "operation_types": sorted(c["operation_types"]),
            "requires_price": c["requires_price"],
            "allows_partial_fill": c["allows_partial_fill"],
        }
    return result


def _serialize_risk_taxonomy() -> dict[str, Any]:
    """Serialize risk taxonomy to JSON-safe dict."""
    return {
        "risk_types": [{"name": rt.name, "value": rt.value} for rt in RiskType],
        "risk_categories": [{"name": rc.name, "value": rc.value} for rc in RiskCategory],
        "category_mapping": {
            cat.value: sorted(rt.value for rt in types)
            for cat, types in sorted(RISK_TYPE_CATEGORIES.items(), key=lambda x: x[0].value)
        },
    }


def _serialize_venue_rate_limits() -> dict[str, dict[str, Any]]:
    """Serialize VENUE_RATE_LIMITS to JSON-safe dicts."""
    result: dict[str, dict[str, Any]] = {}
    for venue in sorted(VENUE_RATE_LIMITS):
        spec = VENUE_RATE_LIMITS[venue]
        result[venue] = {
            "venue": spec.venue,
            "requests_per_second": spec.requests_per_second,
            "requests_per_minute": spec.requests_per_minute,
            "notes": spec.notes,
        }
    return result


def _serialize_capability_declarations() -> list[dict[str, Any]]:
    """Serialize CAPABILITY_DECLARATIONS to JSON-safe list."""
    result = []
    for cap in sorted(CAPABILITY_DECLARATIONS, key=lambda c: c.source):
        entry: dict[str, Any] = {
            "source": cap.source,
            "domains": sorted(cap.domains),
            "supports_live": cap.supports_live,
            "supports_batch": cap.supports_batch,
            "supports_testnet": cap.supports_testnet,
            "operations": {domain: sorted(ops) for domain, ops in sorted(cap.operations.items())},
        }
        result.append(entry)
    return result


def _serialize_defi_protocol_registry() -> dict[str, Any]:
    """Serialize DeFi protocol registry to JSON-safe dict."""
    return {
        "protocols": sorted(DEFI_PROTOCOLS),
        "venue_to_protocol": {k: v for k, v in sorted(DEFI_VENUE_TO_PROTOCOL.items())},
    }


def _serialize_representative_sample() -> dict[str, Any]:
    """Serialize REPRESENTATIVE_INSTRUMENT_SAMPLE to JSON-safe dict."""
    return {
        "cefi_base_assets": CEFI_BASE_ASSETS,
        "tradfi_equities": {k: v for k, v in sorted(TRADFI_EQUITIES.items())},
        "tradfi_futures": {k: [list(spec) for spec in specs] for k, specs in sorted(TRADFI_FUTURES.items())},
        "defi_instruments": {k: v for k, v in sorted(DEFI_INSTRUMENTS.items())},
        "defi_lending_assets": DEFI_LENDING_ASSETS,
        "defi_pool_pairs": [list(pair) for pair in DEFI_POOL_PAIRS],
        "sports_leagues": SPORTS_LEAGUES,
        "options_chain_config": {k: v for k, v in sorted(OPTIONS_CHAIN_CONFIG.items())},
        "cme_month_codes": {str(k): v for k, v in sorted(CME_MONTH_CODES.items())},
        "quarterly_months": QUARTERLY_MONTHS,
    }


def _serialize_uic_deployment_enums() -> dict[str, list[str]]:
    """Serialize UIC deployment enums for the UI.

    Returns empty dict if unified-internal-contracts is not installed
    (UAC is T0 — cannot depend on UIC).
    """
    try:
        from unified_api_contracts.internal.domain.deployment_service import (
            DeploymentCluster,
            DeploymentOperationMode,
            DeploymentStatus,
            DeploymentTier,
        )
    except ImportError:
        return {}

    return {
        "DeploymentCluster": sorted(e.value for e in DeploymentCluster),
        "DeploymentTier": sorted(e.value for e in DeploymentTier),
        "DeploymentOperationMode": sorted(e.value for e in DeploymentOperationMode),
        "DeploymentStatus": sorted(e.value for e in DeploymentStatus),
    }


def generate() -> dict[str, Any]:
    """Generate the complete ui-reference-data structure."""
    version = _get_version()

    return {
        "_meta": {
            "version": version,
            "generator": "generate_ui_reference_data.py",
            "registry_count": 15,
        },
        # ── 4 existing registries (pre-audit baseline) ──
        "venue_error_map": {
            "registry_name": "venue_error_map",
            "version": version,
            "venue_count": len(VENUE_ERROR_MAP),
            "entries": _serialize_venue_error_map(),
        },
        "instruction_constraints": {
            "registry_name": "instruction_constraints",
            "version": version,
            "entry_count": len(INSTRUCTION_CONSTRAINTS),
            "entries": _serialize_instruction_constraints(),
        },
        "market_data_categories": {
            "registry_name": "market_data_categories",
            "version": version,
            "entries": {
                "data_types_by_asset_group": {
                    k: sorted(v) for k, v in sorted(DATA_TYPES_BY_ASSET_GROUP.items())
                },
                "venues_by_asset_group": {k: sorted(v) for k, v in sorted(VENUES_BY_ASSET_GROUP.items())},
                "timeframes": TIMEFRAMES,
            },
        },
        "venue_rate_limits": {
            "registry_name": "venue_rate_limits",
            "version": version,
            "venue_count": len(VENUE_RATE_LIMITS),
            "entries": _serialize_venue_rate_limits(),
        },
        # ── 9 new registries ──
        "risk_taxonomy": {
            "registry_name": "risk_taxonomy",
            "version": version,
            "entries": _serialize_risk_taxonomy(),
        },
        "defi_protocol_registry": {
            "registry_name": "defi_protocol_registry",
            "version": version,
            "entries": _serialize_defi_protocol_registry(),
        },
        "chain_rpc_templates": {
            "registry_name": "chain_rpc_templates",
            "version": version,
            "chain_count": len(CHAIN_RPC_TEMPLATES),
            "entries": {k: v for k, v in sorted(CHAIN_RPC_TEMPLATES.items())},
        },
        "subgraph_ids": {
            "registry_name": "subgraph_ids",
            "version": version,
            "protocol_count": len(SUBGRAPH_IDS),
            "entries": {
                proto: {chain: sid for chain, sid in sorted(chains.items())}
                for proto, chains in sorted(SUBGRAPH_IDS.items())
            },
        },
        "capability_declarations": {
            "registry_name": "capability_declarations",
            "version": version,
            "entry_count": len(CAPABILITY_DECLARATIONS),
            "entries": _serialize_capability_declarations(),
        },
        # ── Composite registries (derived from multiple sources) ──
        "venue_capabilities": {
            "registry_name": "venue_capabilities",
            "version": version,
            "description": "Combined view: venues with their capabilities, rate limits, and error maps",
            "entries": _build_venue_capabilities(),
        },
        "data_pipeline_config": {
            "registry_name": "data_pipeline_config",
            "version": version,
            "description": "Data types, timeframes, and venues by asset_group for pipeline configuration",
            "entries": {
                "asset_groups": sorted(DATA_TYPES_BY_ASSET_GROUP.keys()),
                "timeframes": TIMEFRAMES,
            },
        },
        "error_classifications": {
            "registry_name": "error_classifications",
            "version": version,
            "description": "Error action summary by venue — how many RETRY/FAIL/SKIP/RECONNECT per venue",
            "entries": _build_error_classification_summary(),
        },
        "tradfi_symbology": {
            "registry_name": "tradfi_symbology",
            "version": version,
            "description": "TradFi instrument definitions and data provider bindings",
            "entries": _build_tradfi_symbology(),
        },
        "representative_instrument_sample": {
            "registry_name": "representative_instrument_sample",
            "version": version,
            "description": "SSOT for mock/test instrument selection — Layer 1 of 3-layer architecture",
            "entries": _serialize_representative_sample(),
        },
        "deployment_enums": {
            "registry_name": "deployment_enums",
            "version": version,
            "description": "Deployment clusters, tiers, operation modes, statuses from UIC",
            "entries": _serialize_uic_deployment_enums(),
        },
    }


def _build_venue_capabilities() -> dict[str, dict[str, Any]]:
    """Build combined venue capability view."""
    venues: dict[str, dict[str, Any]] = {}
    for venue in sorted(VENUE_ERROR_MAP):
        entry: dict[str, Any] = {"venue": venue}
        if venue in VENUE_RATE_LIMITS:
            rl = VENUE_RATE_LIMITS[venue]
            entry["rate_limit"] = {
                "requests_per_second": rl.requests_per_second,
                "requests_per_minute": rl.requests_per_minute,
            }
        entry["error_code_count"] = len(VENUE_ERROR_MAP[venue])
        venues[venue] = entry
    return venues


def _build_error_classification_summary() -> dict[str, dict[str, int]]:
    """Build error action summary per venue."""
    result: dict[str, dict[str, int]] = {}
    for venue in sorted(VENUE_ERROR_MAP):
        actions: dict[str, int] = {}
        for c in VENUE_ERROR_MAP[venue]:
            action_str = c.action.value if hasattr(c.action, "value") else str(c.action)
            actions[action_str] = actions.get(action_str, 0) + 1
        result[venue] = actions
    return result


def _build_tradfi_symbology() -> dict[str, Any]:
    """Build TradFi symbology summary."""
    from unified_api_contracts.registry.tradfi_symbology import (
        TRADFI_INSTRUMENTS,
        TRADFI_VENUE_MAPPINGS,
    )

    instruments = []
    for inst in sorted(TRADFI_INSTRUMENTS, key=lambda x: x.symbol):
        instruments.append(
            {
                "symbol": inst.symbol,
                "base_asset": inst.base_asset,
                "venue": inst.venue,
                "instrument_type": inst.instrument_type,
            }
        )

    venue_count = len(TRADFI_VENUE_MAPPINGS) if TRADFI_VENUE_MAPPINGS else 0

    return {
        "instrument_count": len(instruments),
        "instruments": instruments,
        "venue_mapping_count": venue_count,
    }


def main() -> None:
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate UI reference data from UAC registries")
    parser.add_argument(
        "--output",
        type=Path,
        default=_repo_root / "ui-reference-data.json",
        help="Output JSON file path",
    )
    args = parser.parse_args()

    data = generate()
    output_path: Path = args.output
    output_path.write_text(json.dumps(data, indent=2, sort_keys=False, default=str) + "\n")
    print(f"Generated {output_path} with {data['_meta']['registry_count']} registries")


if __name__ == "__main__":
    main()
