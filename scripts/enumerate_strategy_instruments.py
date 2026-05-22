"""Strategy → instruments resolver.

Joins the combinatoric catalogue envelope (archetype × venue × instrument_type)
with the latest instrument-definitions records from the per-category
``instruments-store-*`` GCS buckets, producing a mapping:

    { slot_label_or_archetype_dim_key: { ..., instruments: [instrument_key, ...] } }

Output: gs://strategy-store-cefi-central-element-323112/catalogue/
strategy_instruments.json. UI / terminal / order-booking consumers read this
to answer "which concrete instruments can I trade for this strategy slot today?"

The instruments-service writes per-(category, day, venue) parquet rolls to
``gs://instruments-store-{category}-central-element-323112/
instrument_availability/by_date/day=YYYY-MM-DD/venue={VENUE}/instruments.parquet``.
This script picks the latest day per venue, reads the parquet, filters by
instrument_type matching the catalogue cell, and collects unique instrument keys.

Two modes:
- Default (``--with-real-instruments=False``): emits venue tokens as
  instrument proxies. Fast, credential-free, useful for CI / smoke tests.
- ``--with-real-instruments``: reads parquet from the real instruments-store
  buckets, normalises venue casing (catalogue lowercase ↔ parquet uppercase),
  maps instrument_type vocabularies (catalogue "perp" ↔ parquet "PERPETUAL"),
  and emits real ``instrument_key`` lists per slot.
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

from unified_api_contracts.gcs_paths import AssetGroup, bucket_name, strategy_store_bucket

_PROJECT_ID = "central-element-323112"

GCS_BUCKET = strategy_store_bucket(_PROJECT_ID)
GCS_OBJECT_PATH = "catalogue/strategy_instruments.json"

# Per-category instrument-store bucket. CROSS_CATEGORY has no dedicated bucket
# (it's a virtual asset_group spanning others); TRADFI's universe is in the
# UAC registry rather than a parquet, so bucket_name() returns None for it.
_CATEGORY_TO_INSTRUMENT_BUCKET: dict[str, str | None] = {
    "CEFI": bucket_name(AssetGroup.CEFI, _PROJECT_ID),
    "DEFI": bucket_name(AssetGroup.DEFI, _PROJECT_ID),
    "SPORTS": bucket_name(AssetGroup.SPORTS, _PROJECT_ID),
    "PREDICTION": bucket_name(AssetGroup.PREDICTION, _PROJECT_ID),
    "TRADFI": bucket_name(AssetGroup.TRADFI, _PROJECT_ID),
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
    """Stub resolver — emits venue tokens as instrument proxies."""
    return list(expanded_venues)


# ---------------------------------------------------------------------------
# Real parquet resolver
# ---------------------------------------------------------------------------

# Catalogue uses lowercase venue tokens; parquet uses uppercase with hyphens
# and per-asset-class qualifiers. Map catalogue token to parquet venue
# variants — first match in the latest day's parquet wins.
_CATALOGUE_VENUE_TO_PARQUET: dict[str, list[str]] = {
    "binance": ["BINANCE-SPOT", "BINANCE-FUTURES", "BINANCE"],
    "okx": ["OKX-SPOT", "OKX-FUTURES", "OKX-SWAP", "OKX"],
    "bybit": ["BYBIT-SPOT", "BYBIT-FUTURES", "BYBIT"],
    "hyperliquid": ["HYPERLIQUID"],
    "deribit": ["DERIBIT"],
    "coinbase": ["COINBASE-SPOT", "COINBASE"],
    "kraken": ["KRAKEN-SPOT", "KRAKEN"],
    "bitget": ["BITGET-SPOT", "BITGET-FUTURES", "BITGET"],
    "gate": ["GATE-SPOT", "GATE-FUTURES", "GATE"],
    "kucoin": ["KUCOIN-SPOT", "KUCOIN-FUTURES", "KUCOIN"],
    "aster": ["ASTER"],
    "bit_com": ["BIT_COM", "BIT-COM"],
    "uniswap_v3": ["UNISWAPV3-ETH", "UNISWAPV3"],
    "pancakeswap_v3": ["PANCAKESWAPV3"],
    "balancer": ["BALANCER", "BALANCER-ETH"],
    "curve": ["CURVE-ETH", "CURVE"],
    "sushiswap": ["SUSHISWAP"],
    "maverick": ["MAVERICK"],
    "gmx": ["GMX"],
    "drift": ["DRIFT"],
    "kamino": ["KAMINO"],
    "raydium": ["RAYDIUM"],
    "orca": ["ORCA"],
    "jito": ["JITO"],
    "lido": ["LIDO"],
    "etherfi": ["ETHERFI"],
    "ethena": ["ETHENA"],
    "aave_v3": ["AAVE-V3", "AAVE_V3", "AAVE-V3-ETH"],
    "compound_v3": ["COMPOUND-V3", "COMPOUND_V3"],
    "morpho": ["MORPHO-ETHEREUM", "MORPHO"],
    "spark": ["SPARK"],
    "ibkr": ["IBKR"],
    "cme": ["CME"],
    "ice": ["ICE"],
    "cboe": ["CBOE"],
    "saxo": ["SAXO"],
    "lmax": ["LMAX"],
    "eurex": ["EUREX"],
    "nyse": ["NYSE"],
    "nasdaq": ["NASDAQ"],
    "polymarket": ["POLYMARKET"],
    "kalshi": ["KALSHI"],
    "unity": ["UNITY"],
    "betfair_direct": ["BETFAIR-DIRECT", "BETFAIR"],
    "smarkets_direct": ["SMARKETS-DIRECT", "SMARKETS"],
    "sporttrade": ["SPORTTRADE"],
    "sportradar": ["SPORTRADAR"],
    "fanduel": ["FANDUEL"],
    "draftkings": ["DRAFTKINGS"],
}

# Catalogue instrument_type → parquet instrument_type values
_INSTRUMENT_TYPE_TO_PARQUET: dict[str, set[str]] = {
    "spot": {"SPOT_PAIR", "SPOT", "SPOT_ASSET"},
    "perp": {"PERPETUAL", "PERP"},
    "dated_future": {"FUTURE", "DATED_FUTURE"},
    "option": {"OPTION", "CALL", "PUT"},
    "lending": {"LENDING"},
    "lp": {"POOL", "LP"},
    "staking": {"STAKING", "YIELD_BEARING"},
    "event_settled": {"EVENT_SETTLED", "EVENT"},
}

# Per-day parquet read cache: (category, parquet_venue) → list[instrument_key]
_VENUE_INSTRUMENT_CACHE: dict[tuple[str, str], list[dict]] = {}


def _gcs_fs():
    import gcsfs
    return gcsfs.GCSFileSystem()


# Per-bucket cache: bucket → { parquet_venue: latest_parquet_path }.
# Built lazily once per bucket — single fs.find() instead of N exists() calls.
_BUCKET_VENUE_LATEST: dict[str, dict[str, str]] = {}


def _build_bucket_venue_index(bucket: str) -> dict[str, str]:
    """One GCS walk per bucket, return parquet_venue → latest_day_path."""
    fs = _gcs_fs()
    pattern = f"{bucket}/instrument_availability/by_date/"
    venue_to_path: dict[str, str] = {}
    try:
        # Recursive list: yields all day=*/venue=*/instruments.parquet paths
        all_paths = fs.find(pattern)
    except FileNotFoundError:
        return venue_to_path
    for p in all_paths:
        if not p.endswith("/instruments.parquet"):
            continue
        # Path: bucket/instrument_availability/by_date/day=YYYY-MM-DD/venue=NAME/instruments.parquet
        parts = p.split("/")
        venue_part = next((s for s in parts if s.startswith("venue=")), None)
        day_part = next((s for s in parts if s.startswith("day=")), None)
        if venue_part is None or day_part is None:
            continue
        venue = venue_part.split("=", 1)[1]
        existing = venue_to_path.get(venue)
        # Keep the lexicographically largest day path (which is also the latest
        # since day= uses YYYY-MM-DD).
        if existing is None or p > existing:
            venue_to_path[venue] = p
    return venue_to_path


def _latest_day_for_venue(category: str, parquet_venue: str) -> str | None:
    bucket = _CATEGORY_TO_INSTRUMENT_BUCKET.get(category)
    if bucket is None:
        return None
    if bucket not in _BUCKET_VENUE_LATEST:
        _BUCKET_VENUE_LATEST[bucket] = _build_bucket_venue_index(bucket)
    return _BUCKET_VENUE_LATEST[bucket].get(parquet_venue)


def _read_venue_parquet(category: str, parquet_venue: str) -> list[dict]:
    cache_key = (category, parquet_venue)
    if cache_key in _VENUE_INSTRUMENT_CACHE:
        return _VENUE_INSTRUMENT_CACHE[cache_key]
    path = _latest_day_for_venue(category, parquet_venue)
    if path is None:
        _VENUE_INSTRUMENT_CACHE[cache_key] = []
        return []
    import pyarrow.parquet as pq
    fs = _gcs_fs()
    with fs.open(path, "rb") as fh:
        table = pq.read_table(fh)
    cols = ["instrument_key", "instrument_type", "status", "base_asset", "quote_asset"]
    available = [c for c in cols if c in table.column_names]
    rows = table.select(available).to_pylist()
    _VENUE_INSTRUMENT_CACHE[cache_key] = rows
    return rows


def _resolve_instruments_real(
    archetype_id: str,
    category: str,
    instrument: str,
    expanded_venues: list[str],
) -> list[str]:
    """Real resolver — reads parquet from instruments-store-* buckets."""
    if category not in _CATEGORY_TO_INSTRUMENT_BUCKET or _CATEGORY_TO_INSTRUMENT_BUCKET[category] is None:
        # No bucket for this category (TRADFI today, CROSS_CATEGORY) — fall back to venue tokens
        return list(expanded_venues)

    type_set = _INSTRUMENT_TYPE_TO_PARQUET.get(instrument, set())
    keys: list[str] = []
    seen: set[str] = set()

    for venue_token in expanded_venues:
        # DEFI venues come as "uniswap_v3@ethereum" — strip chain suffix for parquet lookup
        catalogue_venue = venue_token.split("@")[0]
        parquet_variants = _CATALOGUE_VENUE_TO_PARQUET.get(catalogue_venue, [catalogue_venue.upper()])

        for pv in parquet_variants:
            rows = _read_venue_parquet(category, pv)
            if not rows:
                continue
            for row in rows:
                if row.get("status") and row["status"] != "active":
                    continue
                row_type = row.get("instrument_type", "")
                if type_set and row_type not in type_set:
                    continue
                key = row.get("instrument_key", "")
                if key and key not in seen:
                    seen.add(key)
                    keys.append(key)
            if rows:
                break  # found data for this venue variant; don't try other variants

    return keys


def _build_mapping(use_real: bool = False) -> dict[str, dict]:
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

            resolver = _resolve_instruments_real if use_real else _resolve_instruments_stub
            instruments = resolver(archetype_id, category, instrument, venues)

            for venue in venues:
                key = _slot_key(archetype_id, category, instrument, venue)
                mapping[key] = {
                    "archetype_id": archetype_id,
                    "category": category,
                    "instrument_type": instrument,
                    "venue": venue,
                    "instrument_bucket": _CATEGORY_TO_INSTRUMENT_BUCKET.get(category),
                    "instruments": instruments,
                    "source": "parquet:instruments-store" if use_real else "stub:venue-only",
                }

    return mapping


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

    mapping = _build_mapping(use_real=args.with_real_instruments)
    payload = {
        "schema_version": "0.2.0",
        "generated_at": "auto",
        "source_script": "scripts/enumerate_strategy_instruments.py",
        "resolver": "parquet:instruments-store" if args.with_real_instruments else "stub:venue-only",
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
