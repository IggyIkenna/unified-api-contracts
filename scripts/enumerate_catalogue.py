"""Enumerate all strategy instances from STRATEGY_REGISTRY in human-readable form.

Grouped by family → archetype → instances. Outputs a markdown table.

Usage:
    cd unified-api-contracts
    source ../.venv-workspace/bin/activate
    python scripts/enumerate_catalogue.py 2>&1 | tee /tmp/catalogue_snapshot.md

This is a one-off audit script — not part of CI.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

# Ensure UAC package is importable when run from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from unified_api_contracts.internal.domain.strategy_service.registry import STRATEGY_REGISTRY  # noqa: E402  # placed after conditional setup to avoid circular import at load time


def run() -> None:
    entries = STRATEGY_REGISTRY.all()

    # Group: family → archetype → [entries]
    grouped: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for e in entries:
        grouped[str(e.family)][str(e.archetype)].append(e)

    total = len(entries)
    family_count = len(grouped)
    archetype_count = sum(len(v) for v in grouped.values())

    print(f"# Strategy Catalogue Snapshot")
    print(f"\n**Total instances**: {total}  |  **Families**: {family_count}  |  **Archetypes**: {archetype_count}\n")
    print(f"Generated from `STRATEGY_REGISTRY` in `unified-api-contracts`.\n")

    for family in sorted(grouped.keys()):
        archetypes = grouped[family]
        family_total = sum(len(v) for v in archetypes.values())
        print(f"\n---\n\n## {family}  ({family_total} instances)\n")

        for archetype in sorted(archetypes.keys()):
            instances = archetypes[archetype]
            print(f"\n### {archetype}  ({len(instances)} instances)\n")
            print(f"| {'Slot Label':<70} | {'Category':<12} | {'Status':<14} |")
            print(f"|{'-'*71}|{'-'*13}|{'-'*15}|")
            for inst in sorted(instances, key=lambda x: x.strategy_id):
                slot = inst.strategy_id
                cat = str(inst.category)
                status = str(inst.coverage_status)
                print(f"| {slot:<70} | {cat:<12} | {status:<14} |")


if __name__ == "__main__":
    run()
