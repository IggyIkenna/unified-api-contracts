"""Instrument catalogue + availability matrix generator.

Joins the static SSOTs (DataTypeCapability registry, SchemaSpec registry,
coverage_starts) with the live availability manifest from each asset_group
bucket to produce three artefacts published to GCS:

- ``instrument-catalogue.json`` — drilldown-friendly, keyed by canonical
  ``(asset_group, data_type, venue, instrument_type)`` tuple. Includes
  bucket, partition layout, schema columns, capability flags, coverage %,
  capture_status counts, latest captured day, live/batch ready bools.
- ``shard-dynamics.json`` — pure static spec dump (no manifest data).
  Useful for adapter authors + AI agents reasoning about layout without
  GCS access.
- ``instrument-catalogue.md`` — human matrix grouped by asset_group →
  data_type → venue with 🟢 ≥90% / 🟡 50–90% / 🔴 <50% / ⚪ no-data
  band emoji + live-ready / batch-ready badges.

Usage::

    python scripts/generate_instrument_catalogue.py \\
        --project-id central-element-323112 \\
        --output-dir /tmp/catalogue

Set ``--dry-run`` to skip the GCS upload and only write to ``--output-dir``.

Catalogue plan: instrument_catalogue_availability_matrix_2026_04_29.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import TypedDict

import pandas as pd

from unified_api_contracts.canonical.coverage_starts import coverage_start
from unified_api_contracts.canonical.gcs_paths import (
    AssetGroup,
    BucketKind,
    bucket_name,
)
from unified_api_contracts.registry.data_type_capability import (
    DATA_TYPE_CAPABILITY_REGISTRY,
    DataTypeCapability,
)
from unified_api_contracts.registry.schema_spec import (
    SCHEMA_SPEC_REGISTRY,
    find_schema,
)


class TupleEntry(TypedDict, total=False):
    asset_group: str
    data_type: str
    venue: str
    instrument_type: str | None
    bucket: str | None
    coverage_start: str | None
    expected_days: int
    captured_days: int
    empty_confirmed_days: int
    attempted_failed_days: int
    coverage_pct: float
    latest_captured_day: str | None
    live_ready: bool
    batch_ready: bool
    retry_needed: bool
    live_capable: bool
    batch_capable: bool
    streaming_protocol: str | None
    requires_credentials: bool
    ttm_cutoff_days: int | None
    liquidity_cutoff_usd: float | None
    retention_days: int | None
    notes: str | None
    schema: list[dict[str, object]]


# ---------------------------------------------------------------------------
# Manifest aggregation
# ---------------------------------------------------------------------------


def _expected_day_count(coverage_start_date: date | None, today: date) -> int:
    """Number of days between coverage_start and today (inclusive).

    Falls back to a 1-year window when coverage_start is unknown so the
    coverage % ratio stays bounded.
    """
    if coverage_start_date is None:
        coverage_start_date = today - timedelta(days=365)
    if coverage_start_date > today:
        return 0
    return (today - coverage_start_date).days + 1


def _aggregate_tuple(
    manifest_df: pd.DataFrame,
    capability: DataTypeCapability,
    today: date,
) -> TupleEntry:
    """Compute one catalogue row from the manifest + capability registry."""
    schema = find_schema(capability.asset_group, capability.data_type)

    if manifest_df.empty:
        # No manifest data at all — emit zeros, no readiness.
        coverage_start_date = coverage_start(capability.asset_group, capability.venue)
        expected = _expected_day_count(coverage_start_date, today)
        return _build_entry(
            capability=capability,
            schema_columns=_schema_columns(schema),
            coverage_start_date=coverage_start_date,
            expected=expected,
            captured=0,
            empty=0,
            failed=0,
            latest_captured=None,
            today=today,
        )

    df = manifest_df
    if "venue" in df.columns:
        # Venue-prefix alias: a registry token of ``BINANCE`` matches manifest
        # rows for ``BINANCE``, ``BINANCE-FUTURES``, ``BINANCE-SPOT``, etc.
        # The instrument_type axis below still disambiguates per row, so the
        # alias does not double-count.
        # Empty-venue special case: registry says ``venue=""`` (e.g. sports
        # rows captured per-source rather than per-venue) — match only rows
        # where the manifest venue is empty/NaN, not every row.
        venue_col = df["venue"].astype(str)
        if capability.venue == "":
            df = df[(venue_col == "") | (venue_col == "nan")]
        else:
            df = df[venue_col.str.startswith(capability.venue)]
    if "data_type" in df.columns and capability.data_type:
        df = df[df["data_type"] == capability.data_type]
    if (
        capability.instrument_type is not None
        and "instrument_type" in df.columns
    ):
        # Empty-string instrument_type matches both empty and NaN.
        if capability.instrument_type == "":
            it_col = df["instrument_type"].astype(str)
            df = df[(it_col == "") | (it_col == "nan")]
        else:
            df = df[df["instrument_type"] == capability.instrument_type]

    # Coverage is measured in UNIQUE DAYS, not rows. A single
    # (venue, data_type, instrument_type) tuple has many rows per day
    # (one per instrument_id / symbol / chain etc.) — counting rows
    # would inflate captured beyond expected_days and break the ratio.
    #
    # Pre-v5 fallback: when a manifest doesn't have a capture_status
    # column, treat every row as captured. After concat'ing pre-v5 +
    # v5 manifests we may get a frame where capture_status is NaN for
    # some rows — those rows behave as pre-v5 (treat-as-captured) so
    # we don't lose visibility on adapters that haven't migrated yet
    # (e.g. DeFi market-data BALANCER / COMPOUND_V3 today).
    if "capture_status" in df.columns and "date" in df.columns:
        cs = df["capture_status"]
        captured_dates = df.loc[(cs == "captured") | cs.isna(), "date"]
        empty_dates = df.loc[cs == "empty_confirmed", "date"]
        failed_dates = df.loc[cs == "attempted_failed", "date"]
        captured = int(captured_dates.nunique())
        empty = int(empty_dates.nunique())
        failed = int(failed_dates.nunique())
    elif "date" in df.columns:
        captured = int(df["date"].nunique())
        empty = 0
        failed = 0
    else:
        captured = int(len(df))
        empty = 0
        failed = 0

    latest_captured: str | None = None
    if "date" in df.columns and captured > 0:
        if "capture_status" in df.columns:
            cs = df["capture_status"]
            captured_rows = df[(cs == "captured") | cs.isna()]
        else:
            captured_rows = df
        if not captured_rows.empty:
            latest_value = captured_rows["date"].max()
            if pd.notna(latest_value):
                latest_captured = str(latest_value)

    coverage_start_date = coverage_start(capability.asset_group, capability.venue)
    # Denominator floor: if the manifest's earliest captured day is later
    # than the registry's coverage_start, use the manifest date instead.
    # This prevents inflated denominators for venues where the adapter
    # started capturing recently even though the venue itself is older
    # (e.g. DERIBIT options 2025-07-18 captured even though Deribit launched
    # 2016, or POLYMARKET trades 2024-10-XX even though venue launched 2020).
    if "date" in df.columns and len(df) > 0:
        try:
            earliest_in_manifest = df["date"].min()
            if pd.notna(earliest_in_manifest):
                earliest_str = str(earliest_in_manifest)
                earliest_date = datetime.strptime(earliest_str, "%Y-%m-%d").date()
                if coverage_start_date is None or earliest_date > coverage_start_date:
                    coverage_start_date = earliest_date
        except (ValueError, TypeError):
            pass
    expected = _expected_day_count(coverage_start_date, today)

    return _build_entry(
        capability=capability,
        schema_columns=_schema_columns(schema),
        coverage_start_date=coverage_start_date,
        expected=expected,
        captured=captured,
        empty=empty,
        failed=failed,
        latest_captured=latest_captured,
        today=today,
    )


def _build_entry(
    *,
    capability: DataTypeCapability,
    schema_columns: list[dict[str, object]],
    coverage_start_date: date | None,
    expected: int,
    captured: int,
    empty: int,
    failed: int,
    latest_captured: str | None,
    today: date,
) -> TupleEntry:
    # honest-coverage: empty_confirmed counts as captured-attempt — the source
    # was queried and legitimately returned zero rows.
    realised = captured + empty
    coverage_pct = (realised / expected) if expected > 0 else 0.0
    coverage_pct = min(1.0, coverage_pct)

    is_recent = False
    if latest_captured is not None:
        try:
            latest_date = datetime.strptime(latest_captured, "%Y-%m-%d").date()
            is_recent = latest_date >= today - timedelta(days=1)
        except ValueError:
            is_recent = False

    live_ready = capability.live_capable and is_recent
    batch_ready = capability.batch_capable and coverage_pct >= 0.9
    retry_needed = failed > 0

    bucket_value = bucket_name(
        capability.asset_group, project_id="{project_id}", kind=BucketKind.INSTRUMENTS
    )

    return {
        "asset_group": capability.asset_group.value,
        "data_type": capability.data_type,
        "venue": capability.venue,
        "instrument_type": capability.instrument_type,
        "bucket": bucket_value,
        "coverage_start": coverage_start_date.isoformat() if coverage_start_date else None,
        "expected_days": expected,
        "captured_days": captured,
        "empty_confirmed_days": empty,
        "attempted_failed_days": failed,
        "coverage_pct": round(coverage_pct, 4),
        "latest_captured_day": latest_captured,
        "live_ready": live_ready,
        "batch_ready": batch_ready,
        "retry_needed": retry_needed,
        "live_capable": capability.live_capable,
        "batch_capable": capability.batch_capable,
        "streaming_protocol": capability.streaming_protocol,
        "requires_credentials": capability.requires_credentials,
        "ttm_cutoff_days": capability.ttm_cutoff_days,
        "liquidity_cutoff_usd": capability.liquidity_cutoff_usd,
        "retention_days": capability.retention_days,
        "notes": capability.notes,
        "schema": schema_columns,
    }


def _schema_columns(spec: object) -> list[dict[str, object]]:
    if spec is None:
        return []
    columns_attr = getattr(spec, "columns", None)
    if not columns_attr:
        return []
    return [
        {
            "name": col.name,
            "dtype": col.dtype,
            "nullable": col.nullable,
            "unit": col.unit,
            "description": col.description,
        }
        for col in columns_attr
    ]


# ---------------------------------------------------------------------------
# Catalogue building
# ---------------------------------------------------------------------------


def build_catalogue(
    manifest_loader: "ManifestLoader",
    today: date | None = None,
) -> tuple[list[TupleEntry], dict[str, object]]:
    """Build (catalogue_entries, shard_dynamics_dict).

    ``manifest_loader`` is a callable ``(asset_group, kind) -> DataFrame``.
    Tests inject a fake; production injects a UTL-backed loader.

    Per asset_group we load BOTH the instruments-store manifest and the
    market-data-tick manifest, concatenate them, and filter per tuple. Tick
    data types (trades / funding_rate / liquidations) live in market-data-tick;
    sports FIXTURES / ODDS live in instruments-store; the merged frame
    surfaces both.
    """
    today_date = today or date.today()
    entries: list[TupleEntry] = []
    cached_manifests: dict[AssetGroup, pd.DataFrame] = {}

    for capability in DATA_TYPE_CAPABILITY_REGISTRY:
        ag = capability.asset_group
        if ag not in cached_manifests:
            instruments_df = manifest_loader(ag, BucketKind.INSTRUMENTS)
            market_data_df = manifest_loader(ag, BucketKind.MARKET_DATA)
            frames = [df for df in (instruments_df, market_data_df) if not df.empty]
            cached_manifests[ag] = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        manifest_df = cached_manifests[ag]
        entries.append(_aggregate_tuple(manifest_df, capability, today_date))

    shard_dynamics = _build_shard_dynamics()
    return entries, shard_dynamics


def _build_shard_dynamics() -> dict[str, object]:
    """Static spec dump — deterministic from UAC, no manifest data."""
    schemas = []
    for spec in SCHEMA_SPEC_REGISTRY:
        schemas.append(
            {
                "asset_group": spec.asset_group.value,
                "data_type": spec.data_type,
                "source": spec.source,
                "columns": [asdict(c) for c in spec.columns],
            }
        )
    capabilities = []
    for cap in DATA_TYPE_CAPABILITY_REGISTRY:
        capabilities.append(
            {
                "asset_group": cap.asset_group.value,
                "data_type": cap.data_type,
                "venue": cap.venue,
                "instrument_type": cap.instrument_type,
                "live_capable": cap.live_capable,
                "batch_capable": cap.batch_capable,
                "streaming_protocol": cap.streaming_protocol,
                "requires_credentials": cap.requires_credentials,
                "ttm_cutoff_days": cap.ttm_cutoff_days,
                "liquidity_cutoff_usd": cap.liquidity_cutoff_usd,
                "retention_days": cap.retention_days,
                "notes": cap.notes,
                "sources": list(cap.sources),
            }
        )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schemas": schemas,
        "capabilities": capabilities,
    }


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def render_markdown(entries: list[TupleEntry]) -> str:
    """Render the human matrix grouped by asset_group → data_type → venue."""
    by_ag: dict[str, list[TupleEntry]] = {}
    for entry in entries:
        by_ag.setdefault(entry["asset_group"], []).append(entry)

    out: list[str] = [
        "# Instrument Catalogue — Availability Matrix",
        "",
        f"_Generated: {datetime.now(timezone.utc).isoformat()}_",
        "",
        "**Coverage band**: 🟢 ≥90% · 🟡 50–90% · 🔴 <50% · ⚪ no data.",
        "**Readiness**: 🟢-LIVE = live-capable + latest captured within 1 day. "
        "🟢-BATCH = batch-capable + coverage ≥90%.",
        "",
    ]

    for ag in sorted(by_ag.keys()):
        out.append(f"## {ag.upper()}")
        out.append("")
        out.append(
            "| Data type | Venue | Inst. type | Coverage | Captured / Expected | "
            "Latest | Live | Batch | Retry |"
        )
        out.append("|---|---|---|---|---|---|---|---|---|")
        for entry in sorted(
            by_ag[ag],
            key=lambda e: (e["data_type"], e["venue"], e.get("instrument_type") or ""),
        ):
            coverage_emoji = _coverage_emoji(entry["coverage_pct"], entry["expected_days"])
            live_badge = "🟢-LIVE" if entry["live_ready"] else ""
            batch_badge = "🟢-BATCH" if entry["batch_ready"] else ""
            retry_badge = "⚠️" if entry["retry_needed"] else ""
            out.append(
                f"| {entry['data_type']} | {entry['venue']} | "
                f"{entry.get('instrument_type') or '—'} | "
                f"{coverage_emoji} {entry['coverage_pct']:.1%} | "
                f"{entry['captured_days']} / {entry['expected_days']} | "
                f"{entry.get('latest_captured_day') or '—'} | "
                f"{live_badge} | {batch_badge} | {retry_badge} |"
            )
        out.append("")

    return "\n".join(out)


def _coverage_emoji(pct: float, expected: int) -> str:
    if expected == 0:
        return "⚪"
    if pct >= 0.9:
        return "🟢"
    if pct >= 0.5:
        return "🟡"
    if pct == 0:
        return "⚪"
    return "🔴"


# ---------------------------------------------------------------------------
# Manifest loaders
# ---------------------------------------------------------------------------


class ManifestLoader:
    """Callable interface — see ``GCSManifestLoader`` for production impl."""

    def __call__(
        self, asset_group: AssetGroup, kind: BucketKind
    ) -> pd.DataFrame:
        raise NotImplementedError


class GCSManifestLoader:
    """Reads the consolidated availability_index parquet per (asset_group, kind) bucket.

    Reads the consolidated parquet directly via gcsfs/pandas rather than going
    through UTL's ``read_availability_index``. Reason: when the consolidated
    blob is stale (>120s), UTL falls back to merging all per-VM shards live —
    that's a 1-2 minute operation per bucket because the cefi market-data
    bucket has ~1032 per-VM shards. The catalogue is regenerated nightly, so
    a few minutes of staleness on the consolidated blob is acceptable.
    """

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id

    def __call__(
        self, asset_group: AssetGroup, kind: BucketKind
    ) -> pd.DataFrame:
        bucket = bucket_name(asset_group, self.project_id, kind=kind)
        if bucket is None:
            return pd.DataFrame()
        try:
            return pd.read_parquet(f"gs://{bucket}/_index/availability_index.parquet")
        except FileNotFoundError:
            return pd.DataFrame()


class StaticManifestLoader:
    """Test-friendly loader — backed by an in-memory dict."""

    def __init__(self, manifests: dict[AssetGroup, pd.DataFrame]) -> None:
        self.manifests = manifests

    def __call__(
        self, asset_group: AssetGroup, kind: BucketKind
    ) -> pd.DataFrame:
        del kind  # only INSTRUMENTS is used
        return self.manifests.get(asset_group, pd.DataFrame())


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True, help="GCP project id")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/tmp/instrument-catalogue"),
        help="Local output directory (Bandit B108: caller-controlled, not a hardcoded /tmp)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip GCS upload — only write to output dir",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    loader = GCSManifestLoader(args.project_id)
    entries, shard_dynamics = build_catalogue(loader)

    catalogue_path = args.output_dir / "instrument-catalogue.json"
    shard_path = args.output_dir / "shard-dynamics.json"
    md_path = args.output_dir / "instrument-catalogue.md"

    catalogue_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "entries": entries,
            },
            indent=2,
            default=str,
        )
    )
    shard_path.write_text(json.dumps(shard_dynamics, indent=2, default=str))
    md_path.write_text(render_markdown(entries))

    print(f"Wrote {catalogue_path} ({len(entries)} entries)")
    print(f"Wrote {shard_path}")
    print(f"Wrote {md_path}")

    if args.dry_run:
        print("Dry run — skipping GCS upload")
        return

    from unified_api_contracts.canonical.gcs_paths import strategy_store_bucket
    from unified_cloud_interface.gcs import upload_blob  # type: ignore[import-untyped]

    target_bucket = strategy_store_bucket(args.project_id)
    for path in (catalogue_path, shard_path, md_path):
        gcs_uri = f"catalogue/instrument/{path.name}"
        upload_blob(bucket=target_bucket, blob_name=gcs_uri, source_path=str(path))
        print(f"Uploaded gs://{target_bucket}/{gcs_uri}")


if __name__ == "__main__":
    main()
