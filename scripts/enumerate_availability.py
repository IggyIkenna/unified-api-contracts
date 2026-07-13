# Epic: infrastructure_master
# Lifecycle: permanent
# Delete-when: NA
"""Strategy availability + capability rules → JSON for downstream consumers.

Emits the "negative space" of the catalogue: what each archetype is allowed
to do, what tenor buckets it spans, whether it's bespoke-capable, and which
(category, instrument_type) combinations are forbidden.

Output: ``catalogue/availability.json`` on the strategy bucket. UI / terminal
/ admin tooling reads this to decide:
- Which categories to enable/disable for an archetype
- Whether to show a "Request bespoke build" CTA
- Whether a tenor selector should appear (and which buckets)
- Whether a (category × archetype) cell is allowed at all
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from enumerate_envelope import (  # noqa: E402  # placed after conditional setup to avoid circular import at load time
    _ARCHETYPE_ALLOWED_CATEGORIES,
    _BESPOKE_CAPABLE,
    _CROSS_DOMAIN_SPLIT,
    _CROSS_VENUE_ARCHETYPES,
    _MEV_SPLIT,
    _MM_SPLIT,
    _SAME_VENUE_BASIS,
    _TENOR_BUCKETS_BY_ARCHETYPE,
    _VOL_SPLIT,
    _MANIFEST_PATH,
    _category_venues,
    _expand_defi_venues,
    _timeframes_for,
)

# Unified FLAT strategy-store bucket (cloud-providers.yaml storage kind
# `strategy-store` — asset-group-agnostic). Per the operator-ratified
# 2026-05-20 (D6 Phase 4) decision + the split-brain fix
# (plans/active/issues/strategy_store_split_brain_2026_07_13.md); UAC is a
# lower tier than unified-trading-library, so UTL's `resolve_bucket_name()`
# can't be imported here — derive the flat name from the project id.
_PROJECT_ID = "central-element-323112"
GCS_BUCKET = f"strategy-store-{_PROJECT_ID}"
GCS_OBJECT_PATH = "catalogue/availability.json"


def _build_availability() -> dict:
    with _MANIFEST_PATH.open("r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    _REPLACED = {
        "VOL_TRADING_OPTIONS",
        "MARKET_MAKING",
        "MARKET_MAKING_CONTINUOUS",
        "MARKET_MAKING_EVENT_SETTLED",
    }
    entries: list[dict] = []
    for entry in manifest["archetypes"]:
        if entry["archetype_id"] in _REPLACED:
            continue
        entries.append(entry)
    entries.extend(_VOL_SPLIT)
    entries.extend(_MM_SPLIT)
    entries.extend(_MEV_SPLIT)
    entries.extend(_CROSS_DOMAIN_SPLIT)

    archetypes: dict[str, dict] = {}
    for entry in entries:
        archetype_id = entry["archetype_id"]
        family = entry["family"]
        allowed_cats = sorted(_ARCHETYPE_ALLOWED_CATEGORIES.get(archetype_id, set()))
        bespoke = archetype_id in _BESPOKE_CAPABLE
        tenor_buckets = _TENOR_BUCKETS_BY_ARCHETYPE.get(archetype_id)
        timeframes = _timeframes_for(archetype_id)
        venue_combo_policy = (
            "cross_venue_pairs"
            if archetype_id in _CROSS_VENUE_ARCHETYPES
            else "same_venue_basis"
            if archetype_id in _SAME_VENUE_BASIS
            else "single_venue"
        )

        # Per-cell venue universe and instrument-types
        cells: list[dict] = []
        for cell in entry["cells"]:
            if cell.get("status") not in ("SUPPORTED", "PARTIAL"):
                continue
            category = cell["category"]
            instrument = cell["instrument_type"]
            venues = list(cell.get("venue_ids", []))
            universe = _category_venues(category, instrument, archetype_id)
            effective = universe if universe else venues
            if category == "DEFI":
                effective = _expand_defi_venues(effective)
            cells.append(
                {
                    "category": category,
                    "instrument_type": instrument,
                    "status": cell["status"],
                    "venue_count": len(effective),
                    "venue_examples": effective[:6],
                }
            )

        archetypes[archetype_id] = {
            "family": family,
            "allowed_categories": allowed_cats,
            "bespoke_capable": bespoke,
            "tenor_buckets": tenor_buckets,
            "timeframes": timeframes,
            "venue_combo_policy": venue_combo_policy,
            "cells": cells,
        }

    # Forbidden combinations — derived from rules
    all_categories = ["CEFI", "DEFI", "TRADFI", "SPORTS", "PREDICTION", "CROSS_CATEGORY"]
    forbidden: list[dict] = []
    for archetype_id, allowed in _ARCHETYPE_ALLOWED_CATEGORIES.items():
        for cat in all_categories:
            if cat not in allowed:
                forbidden.append({"archetype_id": archetype_id, "category": cat})

    return {
        "schema_version": "0.1.0",
        "source_script": "scripts/enumerate_availability.py",
        "archetype_count": len(archetypes),
        "archetypes": archetypes,
        "forbidden_combinations": forbidden,
        "tenor_buckets_known": [
            "0dte",
            "weekly",
            "monthly",
            "quarterly",
            "leaps",
            "multi-tenor",
        ],
        "categories_known": all_categories,
    }


def _upload_to_gcs(content: str, target: str) -> None:
    from unified_trading_library.cloud_interface import upload_to_storage

    bucket_name, _, object_path = target.partition("/")
    upload_to_storage(
        bucket=bucket_name,
        path=object_path,
        data=content.encode("utf-8"),
        content_type="application/json; charset=utf-8",
    )
    https_url = (
        f"https://console.cloud.google.com/storage/browser/_details/"
        f"{bucket_name}/{object_path}"
    )
    print(
        f"Uploaded {len(content):,} bytes to gs://{bucket_name}/{object_path}",
        file=sys.stderr,
    )
    print(f"Console: {https_url}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--gcs-target", type=str, default=None)
    args = parser.parse_args()

    payload = _build_availability()
    output = json.dumps(payload, indent=2, sort_keys=True)

    target = args.gcs_target or (
        f"{GCS_BUCKET}/{GCS_OBJECT_PATH}" if args.upload else None
    )
    if target is None:
        print(output)
    else:
        _upload_to_gcs(output, target)


if __name__ == "__main__":
    main()
