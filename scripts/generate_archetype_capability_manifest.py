# Epic: infrastructure_master
# Lifecycle: permanent
# Delete-when: NA
"""Serialise :data:`ARCHETYPE_CAPABILITY_REGISTRY` to deterministic JSON.

Dual-purpose: ``--write`` rewrites the committed
``archetype_capability_manifest.json``; ``--check`` (default) verifies the
committed file is byte-identical to the regenerated form and exits 1 on drift.
The in-process parity test calls this module's :func:`render_json` to catch
hand-edits to the JSON that don't survive a round-trip through the Pydantic
schema.

Usage::

    python scripts/generate_archetype_capability_manifest.py            # --check
    python scripts/generate_archetype_capability_manifest.py --write    # rewrite
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from unified_api_contracts.internal.architecture_v2.archetype_capability import (
    ARCHETYPE_CAPABILITY_REGISTRY,
    ArchetypeCapability,
)


MANIFEST_PATH = (
    Path(__file__).resolve().parent.parent
    / "unified_api_contracts"
    / "internal"
    / "architecture_v2"
    / "archetype_capability_manifest.json"
)


def _entry_to_dict(entry: ArchetypeCapability) -> dict[str, object]:
    return {
        "archetype_id": entry.archetype_id.value,
        "family": entry.family.value,
        "uses_rolling_futures": entry.uses_rolling_futures,
        "bespoke_capable": entry.bespoke_capable,
        "cells": [
            {
                "asset_group": cell.asset_group.value,
                "instrument_type": cell.instrument_type.value,
                "status": cell.status.value,
                "venue_ids": list(cell.venue_ids),
                "signal_variants": list(cell.signal_variants),
                "roll_mode": cell.roll_mode.value,
                "block_list_refs": list(cell.block_list_refs),
                "representative_slot_labels": list(cell.representative_slot_labels),
                "notes": cell.notes,
            }
            for cell in entry.cells
        ],
    }


def render_json() -> str:
    """Return the deterministic JSON form of the live registry.

    Schema fields keep declaration order; nested lists keep the registry's
    own ordering (coverage.ts declaration order). Uses two-space indent and
    a trailing newline so prettier + text diffs stay sane.
    """

    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "source": "unified_api_contracts.internal.architecture_v2.archetype_capability",
        "archetype_count": len(ARCHETYPE_CAPABILITY_REGISTRY),
        "archetypes": [_entry_to_dict(entry) for entry in ARCHETYPE_CAPABILITY_REGISTRY],
    }
    return json.dumps(payload, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write", action="store_true", help="rewrite the committed manifest instead of checking"
    )
    args = parser.parse_args()

    rendered = render_json()

    if args.write:
        MANIFEST_PATH.write_text(rendered, encoding="utf-8")
        print(f"wrote {MANIFEST_PATH}")
        return 0

    committed = MANIFEST_PATH.read_text(encoding="utf-8") if MANIFEST_PATH.exists() else ""
    if committed == rendered:
        print("archetype_capability_manifest.json is up-to-date")
        return 0

    sys.stderr.write(
        "archetype_capability_manifest.json drift detected.\n"
        "Re-run: python scripts/generate_archetype_capability_manifest.py --write\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
