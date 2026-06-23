#!/usr/bin/env python3
# Epic: infrastructure_master
# Lifecycle: campaign
# Delete-when: unity_child_books.py data auto-generated from UAC registry (no manual update needed)
"""Apply a YAML/JSON update to ``unity_child_books.py``.

USAGE
-----

1. Pull the final book-9 / book-10 identity and commission terms from
   https://quant-portal.olesportsresearch.com/unity
   (requires user-authenticated login; this script does NOT perform the pull).

2. Drop the pulled data into ``data/unity_child_books_update.yaml`` with shape::

        books:
          - child_venue_id: REAL_BOOK_9_ID
            display_name: Real Book 9 Name
            commission_bps: 45       # int or string, bps not %
            commission_type: FLAT    # or TIERED / PERCENT / COMMISSION_ON_WIN / MAKER_TAKER
            supported_sports: [SOCCER, TENNIS]
            notes: Commission verified from quant-portal on 2026-05-01
            confirmed: true
          - child_venue_id: REAL_BOOK_10_ID
            ...

3. Dry-run first to preview the diff::

        python scripts/update_unity_child_books.py \
            --input data/unity_child_books_update.yaml \
            --dry-run

4. Apply the update (writes ``unity_child_books.py`` + runs ``ruff format``)::

        python scripts/update_unity_child_books.py \
            --input data/unity_child_books_update.yaml

5. Run quality gates and commit::

        bash scripts/quality-gates.sh
        git add unified_api_contracts/internal/unity_child_books.py
        git commit -m "feat(unity): finalize books 9 and 10 from quant-portal"

BEHAVIOR
--------
- Validates each input record via
  :func:`unified_api_contracts.internal.validate_unity_child_book`.
- By default the script REPLACES existing ``TBD_BOOK_9`` / ``TBD_BOOK_10`` stubs
  (same order) with supplied books. Use ``--replace-ids`` to replace different ids.
- Always keeps the total book count at 10.
- Writes the file and runs ``ruff format`` on it.

EXIT CODES
----------
0 = success (or dry-run clean diff)
1 = input file missing / invalid YAML
2 = validation failure on one or more books
3 = wrong number of books after merge (must stay 10)
"""

from __future__ import annotations

import argparse
import difflib
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, cast

import yaml

from unified_api_contracts.internal import (
    UNITY_CHILD_BOOKS,
    UnityChildVenue,
    validate_unity_child_book,
)
from unified_api_contracts.internal.architecture_v2 import CommissionStructureType

if TYPE_CHECKING:
    from collections.abc import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET_FILE = (
    REPO_ROOT / "unified_api_contracts" / "internal" / "unity_child_books.py"
)
DEFAULT_REPLACE_IDS: tuple[str, ...] = ("TBD_BOOK_9", "TBD_BOOK_10")


def _coerce_book(raw: dict[str, object]) -> UnityChildVenue:
    """Parse a single YAML dict into a ``UnityChildVenue`` with strict types."""
    missing = {"child_venue_id", "display_name", "commission_bps"} - raw.keys()
    if missing:
        raise ValueError(f"book entry missing required keys: {sorted(missing)}")

    child_venue_id = str(raw["child_venue_id"])
    display_name = str(raw["display_name"])
    # commission_bps can come in as int, float, str, or Decimal; normalise.
    raw_bps = raw["commission_bps"]
    if isinstance(raw_bps, Decimal):
        bps = raw_bps
    elif isinstance(raw_bps, (int, str)):
        bps = Decimal(raw_bps)
    elif isinstance(raw_bps, float):
        # floats are legal YAML but risky — go via string.
        bps = Decimal(str(raw_bps))
    else:
        raise ValueError(
            f"{child_venue_id}: commission_bps must be int/str/Decimal, "
            f"got {type(raw_bps).__name__}"
        )

    ctype_raw = raw.get("commission_type", "FLAT")
    if isinstance(ctype_raw, CommissionStructureType):
        ctype = ctype_raw
    else:
        ctype = CommissionStructureType(str(ctype_raw))

    sports_raw = raw.get("supported_sports", [])
    if not isinstance(sports_raw, list):
        raise ValueError(f"{child_venue_id}: supported_sports must be a list")
    supported_sports: list[str] = [str(s) for s in cast("list[object]", sports_raw)]

    notes = str(raw.get("notes", ""))
    confirmed_raw = raw.get("confirmed", True)
    confirmed = bool(confirmed_raw)

    max_bet_raw = raw.get("max_bet_usd")
    max_bet_usd: Decimal | None
    if max_bet_raw is None:
        max_bet_usd = None
    elif isinstance(max_bet_raw, Decimal):
        max_bet_usd = max_bet_raw
    elif isinstance(max_bet_raw, (int, str, float)):
        max_bet_usd = Decimal(str(max_bet_raw))
    else:
        raise ValueError(
            f"{child_venue_id}: max_bet_usd must be numeric, "
            f"got {type(max_bet_raw).__name__}"
        )

    return UnityChildVenue(
        child_venue_id=child_venue_id,
        display_name=display_name,
        commission_bps=bps,
        commission_type=ctype,
        supported_sports=supported_sports,
        max_bet_usd=max_bet_usd,
        notes=notes,
        confirmed=confirmed,
    )


def _load_input(path: Path) -> list[UnityChildVenue]:
    if not path.exists():
        print(f"ERROR: input file not found: {path}", file=sys.stderr)
        sys.exit(1)
    try:
        raw = yaml.safe_load(path.read_text())
    except yaml.YAMLError as err:
        print(f"ERROR: failed to parse YAML: {err}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(raw, dict) or "books" not in raw:
        print("ERROR: input must be a mapping with top-level 'books' list", file=sys.stderr)
        sys.exit(1)
    books_raw = raw["books"]
    if not isinstance(books_raw, list):
        print("ERROR: 'books' must be a list", file=sys.stderr)
        sys.exit(1)
    books: list[UnityChildVenue] = []
    for entry in cast("list[object]", books_raw):
        if not isinstance(entry, dict):
            print(
                f"ERROR: each book entry must be a mapping, got {type(entry).__name__}",
                file=sys.stderr,
            )
            sys.exit(1)
        books.append(_coerce_book(cast("dict[str, object]", entry)))
    return books


def _validate_all(books: Iterable[UnityChildVenue]) -> list[str]:
    all_errors: list[str] = []
    for book in books:
        all_errors.extend(validate_unity_child_book(book))
    return all_errors


def _merge(
    existing: list[UnityChildVenue],
    updates: list[UnityChildVenue],
    replace_ids: list[str],
) -> list[UnityChildVenue]:
    """Replace entries whose child_venue_id is in ``replace_ids`` with ``updates``.

    Positional replacement — the Nth id in ``replace_ids`` is replaced by the Nth
    book in ``updates``.
    """
    if len(updates) != len(replace_ids):
        print(
            f"ERROR: got {len(updates)} update books but {len(replace_ids)} "
            f"replace_ids — must match 1:1",
            file=sys.stderr,
        )
        sys.exit(3)
    existing_by_id = {b.child_venue_id: b for b in existing}
    missing = [rid for rid in replace_ids if rid not in existing_by_id]
    if missing:
        print(f"ERROR: replace_ids not found in registry: {missing}", file=sys.stderr)
        sys.exit(3)
    replace_map = dict(zip(replace_ids, updates, strict=True))
    merged: list[UnityChildVenue] = []
    for book in existing:
        if book.child_venue_id in replace_map:
            merged.append(replace_map[book.child_venue_id])
        else:
            merged.append(book)
    return merged


def _format_book_literal(book: UnityChildVenue) -> str:
    """Render a single UnityChildVenue as Python source."""
    pct = f"{book.commission_bps / Decimal('100')}%"
    sports_repr = (
        "[" + ", ".join(f'"{s}"' for s in book.supported_sports) + "]"
    )
    lines = [
        "    UnityChildVenue(",
        f'        child_venue_id="{book.child_venue_id}",',
        f'        display_name="{book.display_name}",',
        f'        commission_bps=Decimal("{book.commission_bps}"),  # {pct}',
        f"        commission_type=CommissionStructureType.{book.commission_type.value},",
        f"        supported_sports={sports_repr},",
    ]
    if book.max_bet_usd is not None:
        lines.append(f'        max_bet_usd=Decimal("{book.max_bet_usd}"),')
    lines.append(f'        notes="{book.notes}",')
    lines.append(f"        confirmed={book.confirmed},")
    lines.append("    ),")
    return "\n".join(lines)


def _render_file_source(existing_source: str, books: list[UnityChildVenue]) -> str:
    """Rewrite the ``UNITY_CHILD_BOOKS`` literal in-place, preserving the rest."""
    marker_start = "UNITY_CHILD_BOOKS: list[UnityChildVenue] = ["
    marker_end = "]"
    start_idx = existing_source.find(marker_start)
    if start_idx == -1:
        print("ERROR: could not find UNITY_CHILD_BOOKS literal in source", file=sys.stderr)
        sys.exit(3)
    # Find the matching closing bracket at column 0 on its own line.
    rest = existing_source[start_idx + len(marker_start) :]
    depth = 1
    offset = 0
    for i, ch in enumerate(rest):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                offset = i
                break
    if depth != 0:
        print("ERROR: unbalanced brackets while parsing UNITY_CHILD_BOOKS", file=sys.stderr)
        sys.exit(3)
    end_idx = start_idx + len(marker_start) + offset + len(marker_end)

    body = "\n" + "\n".join(_format_book_literal(b) for b in books) + "\n"
    new_literal = marker_start + body + marker_end
    return existing_source[:start_idx] + new_literal + existing_source[end_idx:]


def _run_ruff_format(path: Path) -> None:
    result = subprocess.run(
        ["ruff", "format", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"WARNING: ruff format failed: {result.stderr}", file=sys.stderr)


def _print_diff(old: str, new: str) -> None:
    diff = difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile="unity_child_books.py (current)",
        tofile="unity_child_books.py (after update)",
    )
    sys.stdout.writelines(diff)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="YAML/JSON file with 'books' list",
    )
    _ = parser.add_argument(
        "--replace-ids",
        nargs="+",
        default=list(DEFAULT_REPLACE_IDS),
        help="child_venue_ids to replace (default: TBD_BOOK_9 TBD_BOOK_10)",
    )
    _ = parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print diff without writing",
    )
    args = parser.parse_args()

    input_path = cast(Path, args.input)
    replace_ids = cast("list[str]", args.replace_ids)
    dry_run = cast(bool, args.dry_run)

    updates = _load_input(input_path)
    errors = _validate_all(updates)
    if errors:
        print("ERROR: input book validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 2

    merged = _merge(list(UNITY_CHILD_BOOKS), updates, replace_ids)
    if len(merged) != 10:
        print(
            f"ERROR: merged registry has {len(merged)} books (must be 10)",
            file=sys.stderr,
        )
        return 3

    existing_source = TARGET_FILE.read_text()
    new_source = _render_file_source(existing_source, merged)

    if dry_run:
        _print_diff(existing_source, new_source)
        print(
            f"\n[dry-run] would replace {replace_ids} with "
            f"{[b.child_venue_id for b in updates]}",
        )
        return 0

    _ = TARGET_FILE.write_text(new_source)
    _run_ruff_format(TARGET_FILE)
    print(
        f"Wrote {TARGET_FILE.relative_to(REPO_ROOT)}; replaced {replace_ids} "
        f"with {[b.child_venue_id for b in updates]}.",
    )
    print("Next: bash scripts/quality-gates.sh && git commit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
