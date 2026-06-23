#!/usr/bin/env python3
# Epic: infrastructure_master
# Lifecycle: permanent
# Delete-when: NA
"""Generate a Domain x Source coverage matrix from registered capabilities.

Reads all registered SourceCapability declarations and prints a matrix
showing which domains and operations each source covers, plus coverage gaps.

Usage:
    python scripts/coverage_matrix.py [--json]
"""

from __future__ import annotations

import json
import sys

# Bootstrap capabilities before resolving
from unified_api_contracts.registry.capability_data import (
    CAPABILITY_DECLARATIONS,
)


def _collect_domains(caps: list) -> list[str]:
    """Return sorted union of all domains across capabilities."""
    domains: set[str] = set()
    for cap in caps:
        domains.update(cap.domains)
    return sorted(domains)


def _build_matrix(caps: list, domains: list[str]) -> list[dict[str, str | list[str]]]:
    """Build matrix rows: one per source with domain coverage indicators."""
    rows: list[dict[str, str | list[str]]] = []
    for cap in caps:
        row: dict[str, str | list[str]] = {"source": cap.source}
        for domain in domains:
            ops = cap.operations.get(domain, [])
            if domain in cap.domains and ops:
                row[domain] = ops
            elif domain in cap.domains:
                row[domain] = ["(declared, no ops listed)"]
            else:
                row[domain] = []
        rows.append(row)
    return rows


def _find_gaps(caps: list, domains: list[str]) -> list[dict[str, str | list[str]]]:
    """Find sources missing coverage for each domain."""
    gaps: list[dict[str, str | list[str]]] = []
    for domain in domains:
        sources_with = [c.source for c in caps if domain in c.domains]
        sources_without = [c.source for c in caps if domain not in c.domains]
        if sources_without:
            gaps.append({
                "domain": domain,
                "covered_by": sources_with,
                "missing_from": sources_without,
                "coverage_pct": f"{len(sources_with) * 100 // len(caps)}%",
            })
    return gaps


def main() -> None:
    """Generate and print the coverage matrix."""
    use_json = "--json" in sys.argv

    caps = CAPABILITY_DECLARATIONS
    domains = _collect_domains(caps)
    matrix = _build_matrix(caps, domains)
    gaps = _find_gaps(caps, domains)

    if use_json:
        output = {
            "domains": domains,
            "matrix": matrix,
            "gaps": gaps,
            "summary": {
                "total_sources": len(caps),
                "total_domains": len(domains),
                "sources_with_live": sum(1 for c in caps if c.supports_live),
                "sources_with_testnet": sum(1 for c in caps if c.supports_testnet),
                "sources_with_historical": sum(1 for c in caps if c.supports_historical),
            },
        }
        print(json.dumps(output, indent=2))
        return

    # --- Text table output ---
    col_width = 14
    src_width = 14

    # Header
    header = f"{'Source':<{src_width}}"
    for d in domains:
        header += f" | {d:<{col_width}}"
    print(header)
    print("-" * len(header))

    # Rows
    for row in matrix:
        line = f"{row['source']:<{src_width}}"
        for d in domains:
            ops = row[d]
            if isinstance(ops, list) and ops:
                indicator = f"{len(ops)} ops"
            else:
                indicator = "-"
            line += f" | {indicator:<{col_width}}"
        print(line)

    # Gaps summary
    print("\n--- Coverage Gaps ---")
    for gap in gaps:
        missing = gap["missing_from"]
        if isinstance(missing, list) and missing:
            print(f"  {gap['domain']}: {gap['coverage_pct']} coverage, missing from: {', '.join(missing)}")

    # Feature support summary
    print("\n--- Feature Support ---")
    print(f"  Live:       {sum(1 for c in caps if c.supports_live)}/{len(caps)}")
    print(f"  Batch:      {sum(1 for c in caps if c.supports_batch)}/{len(caps)}")
    print(f"  Historical: {sum(1 for c in caps if c.supports_historical)}/{len(caps)}")
    print(f"  Testnet:    {sum(1 for c in caps if c.supports_testnet)}/{len(caps)}")


if __name__ == "__main__":
    main()
