"""Strategy → instruments resolver.

Joins the combinatoric catalogue envelope (archetype × venue × instrument_type)
with the latest instrument-definitions records from the per-category
``instruments-store-*`` GCS buckets, producing a mapping:

    { slot_label_or_archetype_dim_key: [InstrumentDefinition.key, ...] }

Output goes to gs://strategy-store-cefi-central-element-323112/catalogue/
strategy_instruments.json so UI / terminal / order-booking consumers have a
single canonical source of "which concrete instruments can I trade for this
strategy slot today?".

The instruments-service writes per-(category, day, venue) parquet rolls to
``gs://instruments-store-{category}-central-element-323112/
instrument_availability/by_date/day=YYYY-MM-DD/venue={VENUE}/instruments.parquet``.
This script picks the latest day per venue, reads the parquet, filters by
instrument_type matching the catalogue cell, and collects unique instrument
keys.

Stub behaviour today: emits the structure with venue lists as the instrument
proxy. The real parquet read is gated behind ``--with-real-instruments`` to
keep CI and pre-commit fast and credential-free. Phase 10 of the DART UI plan
upgrades this to a full parquet join.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Reuse all the archetype/category/venue declarations from enumerate_envelope.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from enumerate_envelope import (  # noqa: E402  (path setup precedes import)
    _ARCHETYPE_ALLOWED_CATEGORIES,
    _CROSS_DOMAIN_SPLIT,
    _MEV_SPLIT,
    _MM_SPLIT,
    _VOL_SPLIT,
    _category_allowed,
    _category_venues,
    _expand_defi_venues,
    _MANIFEST_PATH,
)

GCS_BUCKET = "strategy-store-cefi-central-element-323112"
GCS_OBJECT_PATH = "catalogue/strategy_instruments.json"

_CATEGORY_TO_INSTRUMENT_BUCKET = {
    "CEFI": "instruments-store-cefi-central-element-323112",
    "DEFI": "instruments-store-defi-central-element-323112",
    "SPORTS": "instruments-store-sports-central-element-323112",
    "PREDICTION": "instruments-store-prediction-central-element-323112",
    # TRADFI: no dedicated bucket today — instruments declared in UAC universe registry
    "TRADFI": None,
    "CROSS_CATEGORY": None,
}


def _slot_key(archetype_id: str, category: str, instrument: str, venue: str) -> str:
    """Stable key: ``{archetype}@{category}-{instrument}-{venue}``."""
    return f"{archetype_id}@{category.lower()}-{instrument}-{venue}"


def _resolve_instruments_stub(
    archetype_id: str,
    category: str,
    instrument: str,
    expanded_venues: list[str],
) -> list[str]:
    """Stub resolver — emits venue tokens as instrument proxies.

    Real implementation reads
    ``gs://instruments-store-{category}/instrument_availability/by_date/
    day=LATEST/venue=VENUE/instruments.parquet`` and filters by
    ``instrument_type``. Phase 10 of the DART UI plan.
    """
    return list(expanded_venues)


def _build_mapping() -> dict[str, dict]:
    with _MANIFEST_PATH.open("r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    entries: list[dict] = []
    _REPLACED = {
        "VOL_TRADING_OPTIONS",
        "MARKET_MAKING",
        "MARKET_MAKING_CONTINUOUS",
        "MARKET_MAKING_EVENT_SETTLED",
    }
    for entry in manifest["archetypes"]:
        if entry["archetype_id"] in _REPLACED:
            continue
        entries.append(entry)
    entries.extend(_VOL_SPLIT)
    entries.extend(_MM_SPLIT)
    entries.extend(_MEV_SPLIT)
    entries.extend(_CROSS_DOMAIN_SPLIT)

    mapping: dict[str, dict] = {}
    for entry in entries:
        archetype_id = entry["archetype_id"]
        for cell in entry["cells"]:
            if cell.get("status") not in ("SUPPORTED", "PARTIAL"):
                continue
            category = cell["category"]
            instrument = cell["instrument_type"]
            if not _category_allowed(archetype_id, category):
                continue

            universe = _category_venues(category, instrument, archetype_id)
            venues = universe if universe else list(cell.get("venue_ids", []))
            if category == "DEFI":
                venues = _expand_defi_venues(venues)

            instruments = _resolve_instruments_stub(
                archetype_id, category, instrument, venues
            )

            for venue in venues:
                key = _slot_key(archetype_id, category, instrument, venue)
                mapping[key] = {
                    "archetype_id": archetype_id,
                    "category": category,
                    "instrument_type": instrument,
                    "venue": venue,
                    "instrument_bucket": _CATEGORY_TO_INSTRUMENT_BUCKET.get(category),
                    "instruments": instruments,
                    "source": "stub:venue-only",
                }

    return mapping


def _upload_to_gcs(content: str, target: str) -> None:
    from google.cloud import storage

    bucket_name, _, object_path = target.partition("/")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_path)
    blob.upload_from_string(content, content_type="application/json; charset=utf-8")
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
    parser.add_argument(
        "--upload",
        action="store_true",
        help=f"Upload to gs://{GCS_BUCKET}/{GCS_OBJECT_PATH} instead of printing.",
    )
    parser.add_argument(
        "--gcs-target",
        type=str,
        default=None,
        help="Override GCS target as '<bucket>/<path>'. Implies --upload.",
    )
    parser.add_argument(
        "--with-real-instruments",
        action="store_true",
        help="(Phase 10) Read real parquet from instruments-store-* buckets. "
        "Currently no-op — uses stub resolver.",
    )
    args = parser.parse_args()

    mapping = _build_mapping()
    payload = {
        "schema_version": "0.1.0",
        "generated_at": "auto",
        "source_script": "scripts/enumerate_strategy_instruments.py",
        "resolver": "stub:venue-only" if not args.with_real_instruments else "stub:venue-only",
        "slot_count": len(mapping),
        "slots": mapping,
    }
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
