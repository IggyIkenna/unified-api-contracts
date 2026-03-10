#!/usr/bin/env python3
"""Generate UAC Adoption Matrix — shows which terminal consumer services import each UAC schema.

Usage:
    python scripts/check_uac_adoption.py [--output docs/UAC_ADOPTION_MATRIX.md] [--workspace /path/to/workspace]
    python scripts/check_uac_adoption.py --orphans-only   # print only 0-importer schemas

Exit code: 0 if all non-exempt schemas have at least one terminal consumer importer, 1 otherwise.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent

TERMINAL_CONSUMER_SERVICES = [
    "execution-service",
    "strategy-service",
    "market-data-processing-service",
    "market-tick-data-service",
    "market-data-api",
    "instruments-service",
    "alerting-service",
    "risk-and-exposure-service",
    "position-balance-monitor-service",
    "pnl-attribution-service",
    "ml-inference-service",
    "ml-training-service",
    "features-delta-one-service",
    "features-volatility-service",
    "features-cross-instrument-service",
    "features-onchain-service",
    "features-sports-service",
    "features-calendar-service",
    # Interface repos — direct UAC consumers for market/sports integration schemas
    "unified-market-interface",
    "unified-sports-execution-interface",
]

# Classes exempt from adoption check — not expected to be directly imported by class name.
# Reason categories:
#   venue-constant: registry/constant accessed programmatically, not by class name
#   config-dict: JSON schema dict (used via validation, not import)
#   utility-fn: utility functions used via module import pattern
#   narrow-external: vendor-specific schema used only in its own adapter
EXEMPT_CLASSES = frozenset(
    [
        # venue-constant: exchange/venue set constants accessed via set membership
        "BINANCE_FUTURES",
        "BINANCE_SPOT",
        "BYBIT_FUTURES",
        "BYBIT_SPOT",
        "CLOB_VENUES",
        "COINBASE_SPOT",
        "DEX_VENUES",
        "OKX_FUTURES",
        "OKX_SPOT",
        "SPORTS_VENUES",
        "ZERO_ALPHA_VENUES",
        "BOOKMAKER_REGISTRY",
        # config-dict: JSON schema dicts used for validation (not imported by class name)
        "CONFIG_REQUIRED_FIELDS",
        "CONFIG_SCHEMA",
        "INSTRUCTION_SCHEMA",
        "INSTRUMENT_SCHEMA",
        "OPTIONAL_CONFIG_FIELDS",
        "REQUIRED_CONFIG_FIELDS",
        "VALID_ALGORITHMS",
        "VALID_BOOK_TYPES",
        "VALID_CATEGORIES",
        "VALID_INSTRUCTION_TYPES",
        "VALID_MODES",
        "VALID_TIMEFRAMES",
        # config-dict: lookup registries/maps
        "DATABENTO_ERROR_MAP",
        "DATASET_TO_CANONICAL_VENUE",
        "DATA_SOURCE_TO_SECRET",
        "DATA_SOURCE_TO_VENUES",
        "ENDPOINT_REGISTRY",
        "INSTRUMENT_TYPES_BY_VENUE",
        "INSTRUMENT_TYPE_FOLDER_MAP",
        "SYMBOL_MAPPINGS",
        "VENUE_CATEGORY_MAP",
        "VENUE_ERROR_MAP",
        "VENUE_TO_DATA_SOURCE",
        # utility-fn: functions used via module-level import (not class name grep)
        "american_to_decimal",
        "decimal_to_american",
        "classify_venue_error",
        # shared enum/type used indirectly via other schemas
        "ComputeType",
        "ErrorAction",
        "AccessMode",
        "CassetteStatus",
        "DataAvailability",
        "ResponseFormat",
        "DataSourceMapping",
    ]
)


def get_uac_all() -> list[str]:
    """Return the list of public UAC names from __all__."""
    uac_init = WORKSPACE / "unified-api-contracts/unified_api_contracts/__init__.py"
    src = uac_init.read_text()
    all_match = re.search(r"__all__\s*=\s*\[(.*?)\]", src, re.DOTALL)
    if not all_match:
        raise RuntimeError("Could not parse __all__ from UAC __init__.py")
    names = re.findall(r'"(\w+)"', all_match.group(1))
    return sorted(set(names))


def grep_service(service: str, pattern: str) -> bool:
    """Return True if pattern is found in service source (excluding .venv, tests, __pycache__)."""
    service_path = WORKSPACE / service
    if not service_path.exists():
        return False
    result = subprocess.run(
        [
            "grep",
            "-r",
            pattern,
            "--include=*.py",
            "--exclude-dir=.venv*",
            "--exclude-dir=__pycache__",
            "--exclude-dir=tests",
            "-l",
            str(service_path),
        ],
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def build_matrix(classes: list[str]) -> dict[str, list[str]]:
    """Return {class_name: [service, ...]} for each class."""
    matrix: dict[str, list[str]] = {}
    for cls in classes:
        importers: list[str] = []
        for service in TERMINAL_CONSUMER_SERVICES:
            if grep_service(service, cls):
                importers.append(service)
        matrix[cls] = importers
    return matrix


def render_markdown(matrix: dict[str, list[str]], classes: list[str]) -> str:
    [s.replace("-service", "").replace("features-", "feat-") for s in TERMINAL_CONSUMER_SERVICES]
    header = f"# UAC Adoption Matrix\n\nGenerated: {date.today()}\n\n"
    header += "Terminal consumer services are rows; UAC schema classes are columns.\n"
    header += "`✓` = service imports this class. `·` = no import found.\n\n"
    header += (
        "Exempt (venue constants / config dicts / utility functions): " + ", ".join(sorted(EXEMPT_CLASSES)) + "\n\n"
    )

    non_exempt = [c for c in classes if c not in EXEMPT_CLASSES]
    orphans = [c for c in non_exempt if not matrix[c]]
    if orphans:
        header += f"## Orphaned Schemas ({len(orphans)} with 0 terminal consumer imports)\n\n"
        for o in orphans:
            header += f"- `{o}`\n"
        header += "\n"

    # Build table (non-exempt classes only — exempt are too numerous for readable table)
    max(len(c) for c in non_exempt) + 2 if non_exempt else 20
    service_col = max(len(s) for s in TERMINAL_CONSUMER_SERVICES) + 2

    rows = ["## Full Adoption Matrix (non-exempt schemas)\n"]
    header_row = f"| {'Service':<{service_col}} |"
    sep_row = f"| {'-' * service_col} |"
    for cls in non_exempt:
        short = cls[:18]
        header_row += f" {short:<18} |"
        sep_row += f" {'-' * 18} |"
    rows.append(header_row)
    rows.append(sep_row)

    for service in TERMINAL_CONSUMER_SERVICES:
        row = f"| {service:<{service_col}} |"
        for cls in non_exempt:
            mark = "✓" if service in matrix[cls] else "·"
            row += f" {mark:<18} |"
        rows.append(row)

    return header + "\n".join(rows) + "\n"


def main() -> int:
    global WORKSPACE
    parser = argparse.ArgumentParser(description="Generate UAC Adoption Matrix")
    parser.add_argument("--output", default="docs/UAC_ADOPTION_MATRIX.md", help="Output file path")
    parser.add_argument("--workspace", default=str(WORKSPACE), help="Workspace root path")
    parser.add_argument("--orphans-only", action="store_true", help="Print only orphaned schemas")
    args = parser.parse_args()

    WORKSPACE = Path(args.workspace)

    print("Loading UAC __all__...", file=sys.stderr)
    classes = get_uac_all()
    print(f"Found {len(classes)} public UAC classes.", file=sys.stderr)

    non_exempt = [c for c in classes if c not in EXEMPT_CLASSES]
    print(
        f"Checking adoption for {len(non_exempt)} non-exempt classes ({len(classes) - len(non_exempt)} exempt)...",
        file=sys.stderr,
    )

    print("Building adoption matrix (this may take 1-2 minutes)...", file=sys.stderr)
    matrix = build_matrix(classes)

    orphans = [c for c in non_exempt if not matrix[c]]

    if args.orphans_only:
        for o in orphans:
            print(o)
        return 1 if orphans else 0

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = Path(__file__).parent.parent / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    md = render_markdown(matrix, classes)
    output_path.write_text(md)
    print(f"Written: {output_path}", file=sys.stderr)

    if orphans:
        print(
            f"\nWARN: {len(orphans)} orphaned UAC schemas (0 terminal consumer imports):",
            file=sys.stderr,
        )
        for o in orphans:
            print(f"  - {o}", file=sys.stderr)
        return 1

    print("All non-exempt UAC schemas have at least one terminal consumer importer.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
