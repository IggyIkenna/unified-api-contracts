"""Book-summary intra-bar column spec -- SSOT for MDPS precomputed book columns.

This module is the single source of truth for every book-microstructure column
that MDPS writes into the processed candle for CeFi / prediction asset groups.
TradFi, DeFi, and Sports rows have no L5 book -- those columns are NULL.

## Design decisions (2026-06-28)

### Time-weighting formula
For a bar [t_start, t_close) with n samples at timestamps t_1 <= ... <= t_n:

  w_i = (t_{i+1} - t_i) / (t_close - t_start)   for i < n
  w_n = (t_close - t_n) / (t_close - t_start)

  TW mean:  mu_tw  = sum(w_i * x_i)
  TW std:   sigma_tw = sqrt(sum(w_i * (x_i - mu_tw)**2))  (population std, weights sum to 1)

Edge case: n = 1 -> mu_tw = x_1, sigma_tw = NaN (undefined for single sample).

### Right-edge convention
A sample stamped exactly at t_close belongs to bar N+1, not N.
Implemented by: interval_idx = floor((t_sample - t_day_start) / T).

### Base vs target timeframe
Columns are computed per-target-timeframe directly from the raw book_snapshot_5
ticks in that bar. No intermediate 15s aggregate is materialised; the raw ticks
are the base for every timeframe.

### Null rule
A column is NULL for the entire bar when zero book snapshots fall within it
(e.g. an instrument that opened late, or a gap). Per-level depth columns
additionally become NULL when the source did not supply that level.

### Column naming convention
  book_{signal}_{aggregation}
  book_bid_qty_L{n}_tw_mean  -- per-level bid quantity (L1 = top of book)
  book_ask_qty_L{n}_tw_mean  -- per-level ask quantity

SSOT ref: plans/active/mdps_book_microstructure_precompute_columns_2026_06_28.md § Todo [DESIGN] P1
Cross-link: unified_api_contracts.internal.domain.market_data_processing.candle_schema
"""

from __future__ import annotations

import dataclasses
from typing import Literal

BookColumnGroup = Literal["spread", "mid", "microprice", "imbalance", "depth"]


@dataclasses.dataclass(frozen=True)
class BookColumnSpec:
    """Specification for one precomputed book-summary candle column.

    Attributes
    ----------
    name:
        Canonical column name as written in the Parquet file.
    dtype:
        Polars / Arrow dtype string.  All book columns use ``Float64``.
    null_rule:
        When this column is NULL.
    aggregation:
        Human-readable aggregation formula.  This is the contract between MDPS
        (writer) and features-service (reader).
    group:
        Logical group for documentation and schema-version tracking.
    """

    name: str
    dtype: str
    null_rule: str
    aggregation: str
    group: BookColumnGroup


# ---------------------------------------------------------------------------
# Group 1: Spread
# ---------------------------------------------------------------------------
_SPREAD_COLUMNS: tuple[BookColumnSpec, ...] = (
    BookColumnSpec(
        name="book_spread_bps_tw_mean",
        dtype="Float64",
        null_rule="null when bar has zero book snapshots",
        aggregation=(
            "time-weighted mean of "
            "(ask_price_0 - bid_price_0) / mid_price * 10000 bps"
        ),
        group="spread",
    ),
    BookColumnSpec(
        name="book_spread_bps_tw_std",
        dtype="Float64",
        null_rule="null when bar has fewer than 2 book snapshots",
        aggregation=(
            "time-weighted population std of spread_bps; "
            "sigma_tw = sqrt(sum(w_i * (spread_i - mu_tw)**2)) where weights sum to 1"
        ),
        group="spread",
    ),
    BookColumnSpec(
        name="book_spread_bps_max",
        dtype="Float64",
        null_rule="null when bar has zero book snapshots",
        aggregation="max(spread_bps) over all snapshots in bar",
        group="spread",
    ),
    BookColumnSpec(
        name="book_spread_bps_min",
        dtype="Float64",
        null_rule="null when bar has zero book snapshots",
        aggregation="min(spread_bps) over all snapshots in bar",
        group="spread",
    ),
    BookColumnSpec(
        name="book_spread_bps_close",
        dtype="Float64",
        null_rule="null when bar has zero book snapshots",
        aggregation="spread_bps of the last (right-edge-closest) snapshot in bar",
        group="spread",
    ),
)

# ---------------------------------------------------------------------------
# Group 2: Mid price (OHLC of mid)
# ---------------------------------------------------------------------------
_MID_COLUMNS: tuple[BookColumnSpec, ...] = (
    BookColumnSpec(
        name="book_mid_open",
        dtype="Float64",
        null_rule="null when bar has zero book snapshots",
        aggregation=(
            "mid_price of the first snapshot in bar "
            "= (bid_price_0 + ask_price_0) / 2"
        ),
        group="mid",
    ),
    BookColumnSpec(
        name="book_mid_high",
        dtype="Float64",
        null_rule="null when bar has zero book snapshots",
        aggregation="max(mid_price) over all snapshots in bar",
        group="mid",
    ),
    BookColumnSpec(
        name="book_mid_low",
        dtype="Float64",
        null_rule="null when bar has zero book snapshots",
        aggregation="min(mid_price) over all snapshots in bar",
        group="mid",
    ),
    BookColumnSpec(
        name="book_mid_close",
        dtype="Float64",
        null_rule="null when bar has zero book snapshots",
        aggregation="mid_price of the last snapshot in bar",
        group="mid",
    ),
)

# ---------------------------------------------------------------------------
# Group 3: Microprice
# ---------------------------------------------------------------------------
_MICROPRICE_COLUMNS: tuple[BookColumnSpec, ...] = (
    BookColumnSpec(
        name="book_microprice_tw_mean",
        dtype="Float64",
        null_rule="null when bar has zero book snapshots or bid_vol_0 + ask_vol_0 = 0",
        aggregation=(
            "time-weighted mean of microprice "
            "= (bid_price_0 * ask_vol_0 + ask_price_0 * bid_vol_0) / (bid_vol_0 + ask_vol_0)"
        ),
        group="microprice",
    ),
    BookColumnSpec(
        name="book_microprice_tilt_bps_tw_mean",
        dtype="Float64",
        null_rule="null when bar has zero book snapshots or mid_price = 0",
        aggregation=(
            "time-weighted mean of (microprice - mid_price) / mid_price * 10000 bps; "
            "positive = microprice above mid (ask-heavy book), negative = bid-heavy"
        ),
        group="microprice",
    ),
)

# ---------------------------------------------------------------------------
# Group 4: Book imbalance
# ---------------------------------------------------------------------------
_IMBALANCE_COLUMNS: tuple[BookColumnSpec, ...] = (
    BookColumnSpec(
        name="book_imbalance_tw_mean",
        dtype="Float64",
        null_rule="null when bar has zero book snapshots",
        aggregation=(
            "time-weighted mean of L5 imbalance "
            "= (sum_bid_qty_L1-5 - sum_ask_qty_L1-5) / (sum_bid_qty_L1-5 + sum_ask_qty_L1-5) "
            "in [-1, 1]; +1 = fully bid-heavy, -1 = fully ask-heavy"
        ),
        group="imbalance",
    ),
    BookColumnSpec(
        name="book_imbalance_tw_std",
        dtype="Float64",
        null_rule="null when bar has fewer than 2 book snapshots",
        aggregation="time-weighted population std of L5 imbalance (same formula as spread_bps_tw_std)",
        group="imbalance",
    ),
    BookColumnSpec(
        name="book_imbalance_close",
        dtype="Float64",
        null_rule="null when bar has zero book snapshots",
        aggregation="L5 imbalance of the last snapshot in bar",
        group="imbalance",
    ),
    BookColumnSpec(
        name="book_imbalance_sign_persist",
        dtype="Float64",
        null_rule="null when bar has fewer than 2 book snapshots",
        aggregation=(
            "fraction of consecutive snapshot pairs where sign(imbalance[i]) == sign(imbalance[i+1]); "
            "range [0, 1]; 1 = book stayed directionally consistent throughout bar"
        ),
        group="imbalance",
    ),
)

# ---------------------------------------------------------------------------
# Group 5: Per-level depth (L1 = top-of-book = level index 0)
# ---------------------------------------------------------------------------
_DEPTH_COLUMNS: tuple[BookColumnSpec, ...] = tuple(
    BookColumnSpec(
        name=f"book_{side}_qty_L{level}_tw_mean",
        dtype="Float64",
        null_rule=(
            f"null when bar has zero book snapshots "
            f"or source did not supply level {level} on the {side} side"
        ),
        aggregation=(
            f"time-weighted mean of {side}_volume_{level - 1} "
            f"(level {level} {side}-side resting quantity; L1 = best {side})"
        ),
        group="depth",
    )
    for side in ("bid", "ask")
    for level in range(1, 6)
)

# ---------------------------------------------------------------------------
# Master column tuple -- 25 columns total (within plan spec of ~15-25)
# ---------------------------------------------------------------------------
BOOK_SUMMARY_COLUMNS: tuple[BookColumnSpec, ...] = (
    *_SPREAD_COLUMNS,       # 5 columns
    *_MID_COLUMNS,          # 4 columns
    *_MICROPRICE_COLUMNS,   # 2 columns
    *_IMBALANCE_COLUMNS,    # 4 columns
    *_DEPTH_COLUMNS,        # 10 columns (5 bid + 5 ask)
)

# Name-indexed lookup for O(1) access by column name
BOOK_SUMMARY_COLUMNS_BY_NAME: dict[str, BookColumnSpec] = {
    col.name: col for col in BOOK_SUMMARY_COLUMNS
}

# Ordered list of column names (preserves group order for schema definition)
BOOK_SUMMARY_COLUMN_NAMES: tuple[str, ...] = tuple(col.name for col in BOOK_SUMMARY_COLUMNS)


def book_summary_column_names_for_group(group: BookColumnGroup) -> tuple[str, ...]:
    """Return column names for a specific logical group."""
    return tuple(col.name for col in BOOK_SUMMARY_COLUMNS if col.group == group)


__all__ = [
    "BOOK_SUMMARY_COLUMNS",
    "BOOK_SUMMARY_COLUMNS_BY_NAME",
    "BOOK_SUMMARY_COLUMN_NAMES",
    "BookColumnGroup",
    "BookColumnSpec",
    "book_summary_column_names_for_group",
]
