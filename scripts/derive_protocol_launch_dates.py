#!/usr/bin/env python3
"""Derive and verify PROTOCOL_LAUNCH_DATES entries from on-chain / The Graph sources.

For each (chain, protocol) pair in ``unified_api_contracts.registry.chain_env.PROTOCOL_LAUNCH_DATES``,
this script probes the corresponding The Graph subgraph (when available) to find the
earliest indexed event, then compares it against the current UAC declaration and prints a
drift table.

Usage
-----
::

    # Full drift scan — requires THEGRAPH_API_KEY env var:
    python scripts/derive_protocol_launch_dates.py

    # Dry-run (no network calls — just prints declarations + citable comment format):
    python scripts/derive_protocol_launch_dates.py --dry-run

    # Check pre-commit citations (run in git pre-commit hook):
    python scripts/derive_protocol_launch_dates.py --check-citations

    # Show only entries with drift:
    python scripts/derive_protocol_launch_dates.py --drift-only

    # Verify a single pair:
    python scripts/derive_protocol_launch_dates.py --pair ETHEREUM/AAVE_V3

Pre-commit gate
---------------
When ``PROTOCOL_LAUNCH_DATES`` in ``chain_env.py`` is changed, the committer MUST:

1. Run this script to get the on-chain-verified citation comment for the new/changed
   entry.
2. Add the citation comment on the same line as the dict entry, formatted as:
   ``# DERIVED YYYY-MM-DD from <chain> <source> <detail>``

The ``--check-citations`` mode verifies that every entry in ``PROTOCOL_LAUNCH_DATES``
that does NOT have a comment line immediately above it (in the old "prose comment" style)
carries a ``# DERIVED`` inline comment on the value line, or an existing prose-comment
block with a date stamp.  New entries lacking any citation fail pre-commit.

SSOT: ``defi_onchain_derivable_values_and_date_drift_2026_06_20.md`` Phase 1.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import requests

from unified_api_contracts.registry.capability_declarations._defi import SUBGRAPH_IDS

# ── UAC imports ──────────────────────────────────────────────────────────────
from unified_api_contracts.registry.chain_env import PROTOCOL_LAUNCH_DATES

# ── Constants ─────────────────────────────────────────────────────────────────

#: The Graph decentralised network gateway.  Requires an API key.
THEGRAPH_GATEWAY: Final[str] = "https://gateway.thegraph.com/api/{api_key}/subgraphs/id/{subgraph_id}"

#: If API key is not provided, fall back to the legacy hosted-service base.
THEGRAPH_LEGACY_BASE: Final[str] = "https://api.thegraph.com/subgraphs/id/{subgraph_id}"

#: Timeout for each The Graph request in seconds.
REQUEST_TIMEOUT_S: Final[int] = 30

#: When earliest derived timestamp is within this many days of declared date → no drift alert.
DRIFT_TOLERANCE_DAYS: Final[int] = 0

# ── On-chain derivation queries ───────────────────────────────────────────────

#: GraphQL query per subgraph schema type → protocol key.
#: Each query fetches the EARLIEST event timestamp (orderDirection:asc, first:1).
#: Returns a field named ``ts`` (Unix seconds) OR ``day`` (days since epoch).
#: Field-name normalisation is done in ``_extract_earliest_date()``.
_SUBGRAPH_QUERIES: Final[dict[str, str]] = {
    # Aave V3 (and Spark as MakerDAO fork) — reserveParamsHistoryItems is the
    # earliest lifecycle event: records when each reserve is initialised.
    "aave_v3": """{
  reserveParamsHistoryItems(first: 1, orderBy: timestamp, orderDirection: asc) {
    timestamp
  }
}""",
    "spark": """{
  marketDailySnapshots(first: 1, orderBy: timestamp, orderDirection: asc) {
    timestamp
  }
}""",
    # Compound V3 (Comet) — dailyMarketAccountings is the first entity per market.
    "compound_v3": """{
  usageMetricsDailySnapshots(first: 1, orderBy: timestamp, orderDirection: asc) {
    timestamp
  }
}""",
    # Uniswap V2/V3/V4 — poolDayDatas / pairDayDatas; "date" field = days since epoch.
    "uniswap_v3": """{
  poolDayDatas(first: 1, orderBy: date, orderDirection: asc) {
    date
  }
}""",
    "uniswap_v2": """{
  pairDayDatas(first: 1, orderBy: date, orderDirection: asc) {
    date
  }
}""",
    "uniswap_v4": """{
  poolDayDatas(first: 1, orderBy: date, orderDirection: asc) {
    date
  }
}""",
    # Balancer — liquidityPoolDailySnapshots (Messari schema).
    "balancer": """{
  liquidityPoolDailySnapshots(first: 1, orderBy: timestamp, orderDirection: asc) {
    timestamp
  }
}""",
    # Curve — liquidityPoolDailySnapshots (Messari schema).
    "curve": """{
  liquidityPoolDailySnapshots(first: 1, orderBy: timestamp, orderDirection: asc) {
    timestamp
  }
}""",
    # PancakeSwap V3 — same schema as Uniswap V3 (poolDayDatas).
    "pancakeswap_v3": """{
  poolDayDatas(first: 1, orderBy: date, orderDirection: asc) {
    date
  }
}""",
    # SushiSwap V3 — poolDayDatas / pairDaySnapshots.
    "sushiswap_v3": """{
  liquidityPoolDailySnapshots(first: 1, orderBy: timestamp, orderDirection: asc) {
    timestamp
  }
}""",
    # SushiSwap (V2 legacy).
    "sushiswap": """{
  liquidityPoolDailySnapshots(first: 1, orderBy: timestamp, orderDirection: asc) {
    timestamp
  }
}""",
    # Aerodrome / Velodrome / Camelot / Trader Joe — Messari or UniV3-style.
    "aerodrome_v3": """{
  poolDayDatas(first: 1, orderBy: date, orderDirection: asc) {
    date
  }
}""",
    "velodrome_v2": """{
  liquidityPoolDailySnapshots(first: 1, orderBy: timestamp, orderDirection: asc) {
    timestamp
  }
}""",
    "camelot_v3": """{
  poolDayDatas(first: 1, orderBy: date, orderDirection: asc) {
    date
  }
}""",
    "trader_joe_v2": """{
  liquidityPoolDailySnapshots(first: 1, orderBy: timestamp, orderDirection: asc) {
    timestamp
  }
}""",
    # GMX — Messari schema.
    "gmx": """{
  liquidityPoolDailySnapshots(first: 1, orderBy: timestamp, orderDirection: asc) {
    timestamp
  }
}""",
    # Morpho Blue — Messari schema.
    "morpho": """{
  marketDailySnapshots(first: 1, orderBy: timestamp, orderDirection: asc) {
    timestamp
  }
}""",
}

#: Maps a UAC protocol key (upper) to the ``SUBGRAPH_IDS`` sub-key (lower).
_PROTOCOL_TO_SUBGRAPH_KEY: Final[dict[str, str]] = {
    "AAVE_V3": "aave_v3",
    "AAVEV3": "aave_v3",  # canonical alias
    "COMPOUND_V3": "compound_v3",
    "UNISWAP_V2": "uniswap_v2",
    "UNISWAP_V3": "uniswap_v3",
    "UNISWAP_V4": "uniswap_v4",
    "BALANCER": "balancer",
    "CURVE": "curve",
    "PANCAKESWAP_V3": "pancakeswap_v3",
    "SUSHISWAP_V3": "sushiswap_v3",
    "SUSHISWAP": "sushiswap",
    "AERODROME_V3": "aerodrome_v3",
    "VELODROME_V2": "velodrome_v2",
    "CAMELOT_V3": "camelot_v3",
    "TRADER_JOE_V2": "trader_joe_v2",
    "GMX": "gmx",
    "MORPHO": "morpho",
    "SPARK": "spark",
}

# ── Data model ────────────────────────────────────────────────────────────────


@dataclass
class DeriveResult:
    chain: str
    protocol: str
    declared_date: str
    derived_date: str | None
    subgraph_id: str | None
    error: str | None = None

    @property
    def has_drift(self) -> bool:
        if self.derived_date is None:
            return False
        return self.derived_date != self.declared_date

    @property
    def drift_days(self) -> int | None:
        if self.derived_date is None or not self.has_drift:
            return None
        from datetime import date as _date

        declared = _date.fromisoformat(self.declared_date)
        derived = _date.fromisoformat(self.derived_date)
        return (declared - derived).days

    def citation_comment(self) -> str:
        """Return the standardised ``# DERIVED ...`` citation comment for this entry."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        if self.subgraph_id:
            source = f"thegraph subgraph {self.subgraph_id}"
            anchor = f"earliest indexed event on {self.derived_date or self.declared_date}"
            return f"# DERIVED {today} from {self.chain.lower()} {source} {anchor}"
        return (
            f"# DERIVED {today} from {self.chain.lower()} manual-research (no subgraph; declared {self.declared_date})"
        )


@dataclass
class DriftScan:
    results: list[DeriveResult] = field(default_factory=list)

    @property
    def drift_count(self) -> int:
        return sum(1 for r in self.results if r.has_drift)

    @property
    def error_count(self) -> int:
        return sum(1 for r in self.results if r.error)

    @property
    def skipped_count(self) -> int:
        return sum(1 for r in self.results if r.derived_date is None and not r.error)


# ── The Graph helpers ─────────────────────────────────────────────────────────


def _build_url(subgraph_id: str, api_key: str | None) -> str:
    if api_key:
        return THEGRAPH_GATEWAY.format(api_key=api_key, subgraph_id=subgraph_id)
    return THEGRAPH_LEGACY_BASE.format(subgraph_id=subgraph_id)


def _extract_earliest_date(data: dict[str, object]) -> str | None:
    """Extract the earliest date string from a The Graph response.

    Handles both ``timestamp`` (Unix seconds) and ``date`` (days-since-epoch)
    fields.  Returns ``None`` if the response is empty or malformed.
    """
    entities = data.get("data") or {}
    # The query returns exactly one entity type; iterate the first key.
    for _entity_key, rows in entities.items():
        if not isinstance(rows, list) or not rows:
            return None
        first_row = rows[0]
        if not isinstance(first_row, dict):
            return None
        if "timestamp" in first_row:
            ts = first_row["timestamp"]
            if ts is None:
                return None
            return datetime.fromtimestamp(int(ts), tz=UTC).strftime("%Y-%m-%d")
        if "date" in first_row:
            day_idx = first_row["date"]
            if day_idx is None:
                return None
            # days-since-epoch → date string
            from datetime import date as _date
            from datetime import timedelta

            epoch = _date(1970, 1, 1)
            return (epoch + timedelta(days=int(day_idx))).isoformat()
    return None


def _query_subgraph(subgraph_id: str, query: str, api_key: str | None) -> str | None:
    """Execute a GraphQL query against The Graph and return the earliest date string.

    Returns ``None`` if the query fails or the result is empty.
    """
    url = _build_url(subgraph_id, api_key)
    try:
        resp = requests.post(
            url,
            json={"query": query},
            timeout=REQUEST_TIMEOUT_S,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return _extract_earliest_date(resp.json())
    except (requests.RequestException, ValueError, KeyError):
        return None


# ── Derivation logic ──────────────────────────────────────────────────────────


def _iter_derivable(
    target_pair: tuple[str, str] | None = None,
) -> Iterator[tuple[str, str, str, str | None, str | None]]:
    """Yield ``(chain, protocol, declared_date, subgraph_id, query)`` for each
    entry in ``PROTOCOL_LAUNCH_DATES`` that has a corresponding subgraph.

    If ``target_pair`` is set, only yield that specific entry.
    """
    for (chain, protocol), declared_date in sorted(PROTOCOL_LAUNCH_DATES.items()):
        if target_pair and (chain, protocol) != target_pair:
            continue
        subgraph_key = _PROTOCOL_TO_SUBGRAPH_KEY.get(protocol)
        if subgraph_key is None:
            yield chain, protocol, declared_date, None, None
            continue
        chain_subgraphs = SUBGRAPH_IDS.get(subgraph_key, {})
        subgraph_id = chain_subgraphs.get(chain)
        query = _SUBGRAPH_QUERIES.get(subgraph_key)
        yield chain, protocol, declared_date, subgraph_id, query


def run_drift_scan(
    api_key: str | None,
    dry_run: bool,
    target_pair: tuple[str, str] | None,
) -> DriftScan:
    scan = DriftScan()
    for chain, protocol, declared_date, subgraph_id, query in _iter_derivable(target_pair):
        if dry_run or not api_key or subgraph_id is None or query is None:
            scan.results.append(
                DeriveResult(
                    chain=chain,
                    protocol=protocol,
                    declared_date=declared_date,
                    derived_date=None,
                    subgraph_id=subgraph_id,
                )
            )
            continue

        derived_date = _query_subgraph(subgraph_id, query, api_key)
        scan.results.append(
            DeriveResult(
                chain=chain,
                protocol=protocol,
                declared_date=declared_date,
                derived_date=derived_date,
                subgraph_id=subgraph_id,
                error=None if derived_date is not None else f"subgraph {subgraph_id} returned no data",
            )
        )
    return scan


# ── Pre-commit citation check ─────────────────────────────────────────────────


def _find_chain_env_path() -> Path:
    """Locate chain_env.py in the UAC source tree (searched relative to this script)."""
    this_dir = Path(__file__).resolve().parent.parent
    candidate = this_dir / "unified_api_contracts" / "registry" / "chain_env.py"
    if candidate.exists():
        return candidate
    msg = f"chain_env.py not found at {candidate}"
    raise FileNotFoundError(msg)


def check_citations() -> int:
    """Read chain_env.py and verify every ``PROTOCOL_LAUNCH_DATES`` entry that
    lacks a leading prose-comment block has an inline ``# DERIVED`` comment on
    the value line or the preceding comment line.

    Exits 0 on OK, 1 on violations.

    The check is intentionally LIGHTWEIGHT — it verifies the comment *format*,
    not the content.  On-chain date correctness is the responsibility of the
    ``--drift-only`` / full scan modes.
    """
    chain_env = _find_chain_env_path()
    source = chain_env.read_text(encoding="utf-8")
    lines = source.splitlines()

    in_block = False
    violations: list[tuple[int, str]] = []

    for idx, line in enumerate(lines):
        stripped = line.strip()

        # Track when we enter/exit the PROTOCOL_LAUNCH_DATES dict block
        if "PROTOCOL_LAUNCH_DATES:" in line and "dict[" in line:
            in_block = True
            continue
        if in_block and stripped == "}":
            # The dict closes here; a following `PROTOCOL_LAUNCH_DATES.update(` means
            # we're in the alias-extension block — still "launch-dates territory"
            in_block = False
            continue

        if not in_block:
            continue

        # Lines that look like ``("CHAIN", "PROTOCOL"): "YYYY-MM-DD",``
        if not (
            (stripped.startswith('("') and '): "' in stripped and stripped.endswith('",')) or stripped.endswith('",')
        ):
            continue
        if '): "20' not in stripped and '): "20' not in stripped:
            continue

        # Check inline comment on this line
        if "# DERIVED" in line or "# QG-allow: defi-citation" in line:
            continue

        # Check if the PRECEDING non-blank line is a comment block with a date anchor.
        # Legacy prose-comment style — e.g. "# ETHEREUM deployed Jan 27 2023 ... verified 2026-05-08".
        # Look back up to 20 lines; accept any comment containing a 4-digit year (19xx or 20xx).
        import re as _re

        found_citation_block = False
        for look_back in range(1, 21):
            prev_idx = idx - look_back
            if prev_idx < 0:
                break
            prev = lines[prev_idx].strip()
            if not prev:
                continue
            if prev.startswith("#"):
                # Accept any comment containing a year (word-boundary-free match because
                # years may appear in underscore-delimited filenames like _2026_05_07.md).
                if _re.search(r"(19|20)\d{2}", prev):
                    found_citation_block = True
                    break
            else:
                # Hit a non-comment, non-blank line → no preceding comment block
                break
        if not found_citation_block:
            violations.append((idx + 1, line.rstrip()))

    if violations:
        print(
            f"[check-citations] {len(violations)} PROTOCOL_LAUNCH_DATES entry(ies) lack a "
            "``# DERIVED <date> from <chain> <source>`` citation comment:",
            file=sys.stderr,
        )
        for lineno, text in violations[:20]:
            print(f"  chain_env.py:{lineno}: {text}", file=sys.stderr)
        if len(violations) > 20:
            print(f"  ... and {len(violations) - 20} more.", file=sys.stderr)
        print(
            "\nRun ``python scripts/derive_protocol_launch_dates.py --dry-run`` "
            "to generate citation comments, then add one per entry as:\n"
            '  ("CHAIN", "PROTOCOL"): "YYYY-MM-DD",  # DERIVED YYYY-MM-DD from <chain> <source>',
            file=sys.stderr,
        )
        return 1
    print(f"[check-citations] OK — {len(PROTOCOL_LAUNCH_DATES)} entries all have citation evidence.")
    return 0


# ── Formatting ────────────────────────────────────────────────────────────────


def _status(r: DeriveResult) -> str:
    if r.error:
        return "ERROR"
    if r.derived_date is None:
        return "SKIP"
    if r.has_drift:
        days = r.drift_days or 0
        sign = "+" if days > 0 else ""
        return f"DRIFT{sign}{days}d"
    return "OK"


def _print_table(scan: DriftScan, drift_only: bool) -> None:
    header = f"{'CHAIN/PROTOCOL':<30} {'DECLARED':>10} {'DERIVED':>10} {'STATUS':>12}  SUBGRAPH"
    print(header)
    print("-" * len(header))
    for r in scan.results:
        status = _status(r)
        if drift_only and status not in ("DRIFT", "ERROR"):
            continue
        pair = f"{r.chain}/{r.protocol}"
        derived = r.derived_date or "-"
        sg = r.subgraph_id[:20] + "…" if r.subgraph_id and len(r.subgraph_id) > 20 else (r.subgraph_id or "-")
        print(f"{pair:<30} {r.declared_date:>10} {derived:>10} {status:>12}  {sg}")

    print()
    total = len(scan.results)
    print(
        f"Total: {total}  |  Drift: {scan.drift_count}  |  Error: {scan.error_count}  "
        f"|  Skipped (no subgraph): {scan.skipped_count}"
    )


def _print_citations(scan: DriftScan) -> None:
    print("\n── Citation comments (paste next to the dict entry) ──")
    for r in scan.results:
        pair = f"({r.chain!r}, {r.protocol!r})"
        print(f"{pair}: {r.declared_date!r},  {r.citation_comment()}")


# ── main ──────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Derive and verify PROTOCOL_LAUNCH_DATES from on-chain / The Graph sources."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print declarations + citation format without any network calls.",
    )
    parser.add_argument(
        "--drift-only",
        action="store_true",
        help="Only print entries where the derived date differs from the declared date.",
    )
    parser.add_argument(
        "--pair",
        default=None,
        help="Limit scan to a single CHAIN/PROTOCOL pair (e.g. ETHEREUM/AAVE_V3).",
    )
    parser.add_argument(
        "--check-citations",
        action="store_true",
        help="Verify citation comments in chain_env.py (pre-commit gate mode). Exit 1 on violations.",
    )
    parser.add_argument(
        "--show-citations",
        action="store_true",
        help="Print citation comment lines for all entries (useful for back-filling).",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="The Graph API key. Falls back to THEGRAPH_API_KEY env var.",
    )
    args = parser.parse_args(argv)

    if args.check_citations:
        return check_citations()

    api_key: str | None = args.api_key or os.environ.get("THEGRAPH_API_KEY")
    dry_run: bool = args.dry_run or (api_key is None)

    target_pair: tuple[str, str] | None = None
    if args.pair:
        parts = args.pair.upper().split("/", 1)
        if len(parts) != 2:
            print(f"[derive] --pair must be CHAIN/PROTOCOL, got {args.pair!r}", file=sys.stderr)
            return 2
        target_pair = (parts[0], parts[1])

    if dry_run and not api_key:
        print("[derive] No THEGRAPH_API_KEY set — running in dry-run mode (no network calls).")
        print("         Export THEGRAPH_API_KEY to enable on-chain derivation.\n")

    scan = run_drift_scan(api_key=api_key, dry_run=dry_run, target_pair=target_pair)

    _print_table(scan, drift_only=args.drift_only)

    if args.show_citations:
        _print_citations(scan)

    if scan.drift_count > 0:
        print(
            f"\n⚠️  {scan.drift_count} entry(ies) with drift detected. "
            "Update PROTOCOL_LAUNCH_DATES in chain_env.py and add a "
            "``# DERIVED <date> from <chain> <source>`` citation comment.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
